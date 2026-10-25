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
from sync_github import SyncError, synchronize, automatic_sync
from sync_policy import (PolicyError, classify_control, validate_summary, revision,
                         atomic_json, load_state, control, state_lock)
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

    def test_freeform_detail_rejected(self):
        with self.assertRaises(ValueError):
            patch(SOURCE, dict(SUMMARY, detail='private text'))

    def test_missing_duplicate_bad_input(self):
        for source, summary in [(SOURCE.replace('alice', 'other'), SUMMARY),
                                (SOURCE + SOURCE, SUMMARY), (SOURCE, []),
                                (SOURCE, dict(SUMMARY, username='x/evil'))]:
            with self.subTest(source=source[:10]), self.assertRaises(ValueError):
                patch(source, summary)

    def test_escape_table(self):
        result = patch(SOURCE, dict(SUMMARY, current='ADC | PWM [text]'))
        self.assertIn('ADC &#124; PWM &#91;text&#93;', result)
        with self.assertRaises(ValueError):
            patch(SOURCE, dict(SUMMARY, current='ADC\nPRIVATE'))

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



class PrivacyTests(unittest.TestCase):
    def test_sensitive_patterns_never_write(self):
        values = ('token=abc123', 'ghp_' + 'a' * 30, 'sk-' + 'x' * 30,
                  'me@example.com', '13812345678', '/Users/alice/private',
                  'D:\\private\\data.txt', 'https://example.com/?key=private',
                  '我的密码是123', '因为私人原因没学')
        for value in values:
            with self.subTest(value=value[:5]):
                api = FakeGitHub()
                with self.assertRaises(SyncError):
                    synchronize('team/private', 'main', 'README.md', 'alice',
                                dict(SUMMARY, current=value), apply=True, expected_sha='old', api=api)
                self.assertEqual(api.writes, [])

    def test_unknown_fields_and_length(self):
        for summary in (dict(SUMMARY, chat='hello'), dict(SUMMARY, learned='x' * 361)):
            with self.assertRaises(PolicyError): validate_summary(summary)

    def test_exact_controls_only(self):
        self.assertEqual(classify_control('暂停同步'), 'pause')
        self.assertEqual(classify_control('恢复同步'), 'resume')
        self.assertEqual(classify_control('仅本地：今日内容'), 'local')
        for text in ('不要暂停同步', '什么是恢复同步', '> 暂停同步', '```暂停同步```', '今天结束学习'):
            self.assertIsNone(classify_control(text))
        self.assertIsNone(classify_control('暂停同步', origin='file'))
        self.assertIsNone(classify_control('恢复同步', origin='assistant'))


class AutoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.progress = self.root / '.learning/subjects/c/progress.yaml'
        self.progress.parent.mkdir(parents=True)
        self.progress.write_text('nodes: {}\n')
        self.path = self.root / '.learning/github-sync.json'
        self.state = dict(version=1, username='alice', repo='team/private', branch='main',
                          path='README.md', workspace=str(self.root),
                          progress='.learning/subjects/c/progress.yaml', enabled=True,
                          paused=False, local_only_ids=[], last_seen_revision='')
        self.state['last_seen_revision'] = revision(self.state)
        atomic_json(self.path, self.state)

    def tearDown(self): self.temp.cleanup()

    def event(self, change=True):
        if change: self.progress.write_text('nodes: {c01: updated}\n')
        return dict(type='exercise_passed', revision=revision(self.state), record_ids=['c01'])

    def test_formal_change_auto_commits_once(self):
        api = FakeGitHub(); event = self.event()
        result = automatic_sync(self.path, event, SUMMARY, api)
        self.assertEqual(result['status'], 'synced')
        self.assertEqual(automatic_sync(self.path, event, SUMMARY, api)['status'], 'unchanged')
        self.assertEqual(len(api.writes), 1)

    def test_same_revision_does_not_trigger(self):
        api = FakeGitHub()
        self.assertEqual(automatic_sync(self.path, self.event(False), SUMMARY, api)['status'], 'unchanged')
        self.assertEqual(api.writes, [])

    def test_pause_resume_no_backfill(self):
        atomic_json(self.path, control(load_state(self.path), 'pause'))
        event = self.event(); api = FakeGitHub()
        self.assertEqual(automatic_sync(self.path, event, SUMMARY, api)['status'], 'paused')
        atomic_json(self.path, control(load_state(self.path), 'resume'))
        self.assertEqual(automatic_sync(self.path, event, SUMMARY, api)['status'], 'unchanged')
        self.assertEqual(api.writes, [])

    def test_persistent_local_only_exclusion(self):
        atomic_json(self.path, control(load_state(self.path), 'local', ['c01']))
        api = FakeGitHub()
        self.assertEqual(automatic_sync(self.path, self.event(), SUMMARY, api)['status'], 'local_only')
        self.assertEqual(api.writes, [])
        self.assertIn('c01', load_state(self.path)['local_only_ids'])

    def test_stale_or_unsupported_event_no_write(self):
        event = self.event(); api = FakeGitHub()
        for bad in (dict(event, revision='stale'), dict(event, type='chat'),
                    dict(event, record_ids=[])):
            with self.assertRaises(PolicyError): automatic_sync(self.path, bad, SUMMARY, api)
        self.assertEqual(api.writes, [])

    def test_control_lock_blocks_concurrent_write(self):
        api = FakeGitHub(); event = self.event()
        with state_lock(self.path):
            with self.assertRaises(PolicyError): automatic_sync(self.path, event, SUMMARY, api)
        self.assertEqual(api.writes, [])

    def test_sensitive_summary_does_not_advance_state(self):
        api = FakeGitHub(); event = self.event()
        before = self.path.read_bytes()
        with self.assertRaises(PolicyError):
            automatic_sync(self.path, event, dict(SUMMARY, current='token=private'), api)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(api.writes, [])

    def test_cli_legacy_apply_cannot_bypass_policy(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts/sync_github.py'),
                               '--repo', 'team/private', '--username', 'alice',
                               '--summary', 'nonexistent.json', '--apply', '--expected-sha', 'old'],
                              capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(b'Standalone --apply is disabled', proc.stderr)


if __name__ == '__main__':
    unittest.main()
