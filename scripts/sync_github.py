"""Preview or apply one member's progress via an already authenticated GitHub CLI."""
import argparse
import base64
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from patch_readme import patch


class SyncError(Exception):
    pass


def gh_api(endpoint, payload=None):
    cmd = ['gh', 'api', '--hostname', 'github.com', '--method', 'PUT' if payload is not None else 'GET', endpoint]
    if payload is not None:
        cmd += ['--input', '-']
    try:
        process = subprocess.run(cmd, input=json.dumps(payload) if payload is not None else None,
                                 encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=60, shell=False)
    except FileNotFoundError:
        raise SyncError('GitHub CLI (gh) is missing; install from https://cli.github.com/') from None
    except subprocess.TimeoutExpired:
        raise SyncError('GitHub request timed out; re-read remote state before retrying') from None
    if process.returncode:
        # Do not echo server text, which could contain credentials or private content.
        raise SyncError('GitHub API failed; check gh auth status, permissions, network, and remote version')
    try:
        return json.loads(process.stdout)
    except ValueError:
        raise SyncError('Unexpected GitHub response') from None


def read_content(repo, branch, path, api):
    endpoint = 'repos/' + repo + '/contents/' + quote(path, safe='/')
    response = api(endpoint + '?ref=' + quote(branch, safe=''))
    if response.get('type') != 'file' or response.get('encoding') != 'base64' or not response.get('sha'):
        raise SyncError('Expected an existing base64-encoded README file')
    try:
        content = base64.b64decode(response['content']).decode('utf-8')
    except (ValueError, UnicodeError, KeyError):
        raise SyncError('Cannot decode README as UTF-8') from None
    return endpoint, response['sha'], content


def synchronize(repo, branch, path, username, summary, apply=False, expected_sha=None, api=gh_api):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise SyncError('Repository must be owner/name')
    if not branch or branch.startswith('-') or not path or path.startswith('/') or '..' in path.split('/'):
        raise SyncError('Invalid branch or repository-relative file path')
    if not isinstance(summary, dict) or not isinstance(summary.get('username'), str):
        raise SyncError('Summary must contain a username string')
    if summary['username'].casefold() != username.casefold():
        raise SyncError('Summary username differs from the configured learner')
    actor = api('user').get('login', '')
    if actor.casefold() != username.casefold():
        raise SyncError('Authenticated GitHub account differs from the learner; no write performed')
    repository = api('repos/' + repo)
    if repository.get('private') is not True:
        raise SyncError('Target must be a private repository')
    if repository.get('permissions', {}).get('push') is not True:
        raise SyncError('No write access to target repository')
    endpoint, sha, source = read_content(repo, branch, path, api)
    if apply and (not expected_sha or expected_sha != sha):
        raise SyncError('README version changed or --expected-sha missing; preview again')
    try:
        result = patch(source, summary)
    except (ValueError, KeyError, IndexError) as exc:
        raise SyncError(str(exc)) from None
    if result == source:
        return {'status': 'unchanged', 'sha': sha}
    if not apply:
        return {'status': 'preview', 'sha': sha,
                'diff': ''.join(difflib.unified_diff(source.splitlines(True), result.splitlines(True),
                                                   fromfile='remote/' + path, tofile='proposed/' + path))}
    response = api(endpoint, {'message': '更新 ' + username + ' 学习进度', 'branch': branch, 'sha': sha,
                              'content': base64.b64encode(result.encode('utf-8')).decode('ascii')})
    commit = response.get('commit', {}).get('sha')
    if not commit:
        raise SyncError('Commit response is incomplete; inspect remote state before retrying')
    _, verified_sha, verified = read_content(repo, branch, path, api)
    if verified != result:
        raise SyncError('Remote content changed after commit; inspect history before retrying')
    return {'status': 'synced', 'commit': commit, 'sha': verified_sha,
            'url': 'https://github.com/' + repo + '/blob/' + quote(branch, safe='') + '/' + quote(path, safe='/')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--branch', default='main')
    parser.add_argument('--path', default='README.md')
    parser.add_argument('--username', required=True)
    parser.add_argument('--summary', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--expected-sha')
    args = parser.parse_args()
    if args.apply and not args.expected_sha:
        parser.error('--apply requires the SHA returned by a fresh preview')
    try:
        summary = json.loads(args.summary.read_text(encoding='utf-8-sig'))
        result = synchronize(args.repo, args.branch, args.path, args.username, summary,
                             args.apply, args.expected_sha)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (SyncError, ValueError, OSError) as exc:
        print('Not synchronized: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
