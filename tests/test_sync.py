import base64
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from patch_readme import patch
from sync_github import SyncError, synchronize
import install

SOURCE = ('# Team\n\n| user | role | current | learned | next |\n'
          '|---|---|---|---|---|\n| alice | 硬件 | C | 加法 | 除法 |\n'
          '| bob | 软件 | 指针 | 循环 | 数组 |\n\n'
          '### alice · 阶段记录\n\n- old\n\n> 共用备注\n\n## 链接\nhttps://example.com\n')
SUMMARY = dict(username='alice', role='硬件', current='浮点', learned='加法', next='除法')


class FakeGitHub:
    def __init__(self, actor='alice', private=True, sha='old', push=True):
        self.actor, self.private, self.sha, self.push = actor, private, sha, push
        self.content = SOURCE
        self.writes = []
        self.diverge = False

    def __call__(self, endpoint, payload=None):
        if endpoint == 'user':
            return {'login': self.actor}
        if endpoint == 'repos/team/private':
            return {'private': self.private, 'permissions': {'push': self.push}}
        if payload is not None:
            self.writes.append(payload)
            if payload['sha'] != self.sha:
                raise SyncError('conflict')
            self.content = base64.b64decode(payload['content']).decode('utf-8')
            if self.diverge:
                self.content += '\nAnother change\n'
            self.sha = 'new'
            return {'commit': {'sha': 'commit123'}}
        return {'type': 'file', 'encoding': 'base64', 'sha': self.sha,
                'content': base64.b64encode(self.content.encode('utf-8')).decode('ascii')}


class PatchTests(unittest.TestCase):
    def test_member_only_and_idempotence(self):
        result = patch(SOURCE, SUMMARY)
        self.assertIn('| bob | 软件 | 指针 | 循环 | 数组 |', result)
        self.assertIn('## 链接\nhttps://example.com', result)
        self.assertEqual(result, patch(result, SUMMARY))

    def test_detail_preserves_shared_note(self):
        summary = dict(SUMMARY, detail='### alice · 阶段记录\n\n- new')
        result = patch(SOURCE, summary)
        self.assertIn('- new\n\n> 共用备注', result)
        self.assertIn('## 链接', result)

    def test_missing_duplicate_bad_input(self):
        for source, summary in [(SOURCE.replace('alice', 'other'), SUMMARY),
                                (SOURCE + SOURCE, SUMMARY), (SOURCE, []),
                                (SOURCE, dict(SUMMARY, username='x/evil'))]:
            with self.subTest(source=source[:10]), self.assertRaises(ValueError):
                patch(source, summary)

    def test_escape_table(self):
        result = patch(SOURCE, dict(SUMMARY, current='ADC | PWM\nUART'))
        self.assertIn('ADC &#124; PWM UART', result)

    def test_cli_unicode_bom_crlf(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / '中文 空格'; root.mkdir()
            src, data, out = (root / x for x in ('首页.md', '摘要.json', '新首页.md'))
            src.write_bytes(('\ufeff' + SOURCE.replace('\n', '\r\n')).encode('utf-8'))
            data.write_bytes(('\ufeff' + json.dumps(SUMMARY, ensure_ascii=False)).encode('utf-8'))
            process = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/patch_readme.py'),
                                      '--readme', str(src), '--summary', str(data), '--output', str(out)],
                                     capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = out.read_bytes()
            self.assertTrue(result.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn(b'\n', result.replace(b'\r\n', b''))


class InstallTests(unittest.TestCase):
    def test_dsh_git_ancestor(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / '.git').mkdir(); (root / '学习').mkdir()
            self.assertEqual(install.destination('dsh', root / '学习'), root.resolve() / '.dsh/skills' / install.NAME)

    def test_dsh_requires_scope(self):
        with self.assertRaises(ValueError):
            install.destination('dsh')

    def test_install_dry_run_update_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / '中文 空格' / install.NAME
            install.install(target, dry_run=True)
            self.assertFalse(target.exists())
            install.install(target)
            self.assertTrue((target / 'SKILL.md').is_file())
            self.assertFalse((target / 'scripts/__pycache__').exists())
            with self.assertRaises(ValueError):
                install.install(target)
            (target / 'private-config.json').write_text('local-only')
            install.install(target, update=True)
            self.assertEqual((target / 'private-config.json').read_text(), 'local-only')
            self.assertEqual(len(list(target.parent.glob('*-backup-*'))), 1)


class SyncTests(unittest.TestCase):
    def run_sync(self, api, **options):
        return synchronize('team/private', 'main', 'README.md', 'alice', SUMMARY, api=api, **options)

    def test_preview_no_write(self):
        api = FakeGitHub()
        self.assertEqual(self.run_sync(api)['status'], 'preview')
        self.assertEqual(api.writes, [])

    def test_unchanged(self):
        api = FakeGitHub(); api.content = patch(SOURCE, SUMMARY)
        self.assertEqual(self.run_sync(api)['status'], 'unchanged')
        self.assertEqual(api.writes, [])

    def test_wrong_actor_public_no_permission(self):
        for api in (FakeGitHub(actor='bob'), FakeGitHub(private=False), FakeGitHub(push=False)):
            with self.assertRaises(SyncError): self.run_sync(api, apply=True, expected_sha='old')
            self.assertEqual(api.writes, [])

    def test_conflict_no_write(self):
        api = FakeGitHub(sha='changed')
        with self.assertRaises(SyncError): self.run_sync(api, apply=True, expected_sha='old')
        self.assertEqual(api.writes, [])

    def test_apply_then_verify(self):
        api = FakeGitHub()
        result = self.run_sync(api, apply=True, expected_sha='old')
        self.assertEqual(result['status'], 'synced')
        self.assertEqual(result['commit'], 'commit123')
        self.assertEqual(len(api.writes), 1)
        self.assertIn('| bob | 软件 | 指针 | 循环 | 数组 |', api.content)

    def test_verify_failure_not_success(self):
        api = FakeGitHub(); api.diverge = True
        with self.assertRaises(SyncError): self.run_sync(api, apply=True, expected_sha='old')
        self.assertEqual(len(api.writes), 1)

    def test_malformed_summary_before_network(self):
        api = FakeGitHub()
        with self.assertRaises(SyncError):
            synchronize('team/private', 'main', 'README.md', 'alice', [], api=api)
        self.assertEqual(api.writes, [])


if __name__ == '__main__':
    unittest.main()
