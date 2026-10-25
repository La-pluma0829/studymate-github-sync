"""Local automatic-sync policy: explicit setup, formal revisions, pause and exclusions."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

EVENTS = {'learning_started', 'exercise_passed', 'project_passed', 'session_ended'}
FIELDS = ('username', 'role', 'current', 'learned', 'next')
LIMITS = {'username': 39, 'role': 60, 'current': 180, 'learned': 360, 'next': 180}
PATTERNS = (
    r'(?i)(?:gh[pousr]_[A-Za-z0-9_]{12,}|github_pat_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{12,})',
    r'(?i)\b(?:bearer|password|passwd|token|api[_ -]?key|cookie|secret)\s*[:= ]\s*\S+',
    r'(?i)(?:-----BEGIN .*PRIVATE KEY-----|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})',
    r'(?<!\d)(?:\+?86[ -]?)?1[3-9]\d{9}(?!\d)',
    r'(?:/Users/|/home/|/private/|/var/|/tmp/|[A-Za-z]:[\\/]|\\\\[^\\\s]+\\)',
    r'(?i)(?:https?://|www\.|(?:\d{1,3}\.){3}\d{1,3})',
    r'(?:密码|口令|密钥|令牌|手机号|身份证|家庭住址|病历|医院诊断|私人原因)',
)


class PolicyError(ValueError):
    pass


def validate_summary(summary):
    if not isinstance(summary, dict) or set(summary) != set(FIELDS):
        raise PolicyError('Summary must contain exactly username, role, current, learned, next; no free-form detail')
    for field in FIELDS:
        value = summary[field]
        if not isinstance(value, str) or not value.strip() or len(value) > LIMITS[field]:
            raise PolicyError('Invalid type or length in summary field: ' + field)
        if any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise PolicyError('Control or multiline characters in field: ' + field)
        if any(re.search(pattern, value) for pattern in PATTERNS):
            raise PolicyError('Potential private information in field: ' + field)
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', summary['username']):
        raise PolicyError('Invalid GitHub username')
    return summary


def classify_control(message, origin='user'):
    # Only call on a fresh human instruction, never on retrieved text/history.
    if origin != 'user':
        return None
    message = message.strip()
    if message in ('暂停同步', '恢复同步', '仅本地'):
        return {'暂停同步': 'pause', '恢复同步': 'resume', '仅本地': 'local'}[message]
    if message.startswith(('仅本地：', '仅本地:')):
        return 'local'
    return None


def revision(state):
    workspace = Path(state['workspace']).resolve()
    progress = (workspace / state['progress']).resolve()
    try:
        relative = progress.relative_to(workspace)
    except ValueError:
        raise PolicyError('Progress source escapes configured workspace') from None
    if relative.name != 'progress.yaml' or not progress.is_file():
        raise PolicyError('Expected an existing formal progress.yaml')
    return hashlib.sha256(progress.read_bytes()).hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(prefix=path.name + '-', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_state(path):
    state = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(state, dict) or state.get('version') != 1:
        raise PolicyError('Unknown sync policy version')
    required = ('username', 'repo', 'branch', 'path', 'workspace', 'progress', 'enabled',
                'paused', 'last_seen_revision', 'local_only_ids')
    if any(k not in state for k in required):
        raise PolicyError('Incomplete sync configuration')
    if type(state['enabled']) is not bool or type(state['paused']) is not bool:
        raise PolicyError('Invalid enabled/paused values')
    if not isinstance(state['local_only_ids'], list):
        raise PolicyError('Invalid local-only exclusions')
    return state


@contextmanager
def state_lock(path):
    lock = Path(str(path) + '.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise PolicyError('Another sync/control operation is active; do not force or retry blindly') from None
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def control(state, action, record_ids=()):
    current = revision(state)
    if action == 'pause':
        state['paused'] = True
    elif action == 'resume':
        state['paused'] = False
    elif action == 'local':
        if not record_ids or any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', x) for x in record_ids):
            raise PolicyError('Local-only requires stable node/record IDs, not private content')
        state['local_only_ids'] = sorted(set(state['local_only_ids']) | set(record_ids))
    else:
        raise PolicyError('Unknown control action')
    # No queued snapshots are replayed after pause/resume/local-only.
    state['last_seen_revision'] = current
    state.pop('last_error', None)
    return state


def check_auto(state, event, summary):
    if not state['enabled'] or state['paused']:
        return 'paused', None
    if not isinstance(event, dict) or set(event) != {'type', 'revision', 'record_ids'}:
        raise PolicyError('Invalid learning event')
    if event['type'] not in EVENTS:
        raise PolicyError('Not a supported formal learning event')
    current = revision(state)
    if event['revision'] != current:
        raise PolicyError('Event does not match the current formal progress revision')
    if current == state['last_seen_revision']:
        return 'unchanged', current
    ids = event['record_ids']
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', x) for x in ids):
        raise PolicyError('Learning event needs stable node/record IDs')
    if set(ids) & set(state['local_only_ids']):
        return 'local_only', current
    validate_summary(summary)
    if summary['username'].casefold() != state['username'].casefold():
        raise PolicyError('Learner differs from the configured account')
    return 'ready', current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--configure', action='store_true')
    group.add_argument('--control', choices=('pause', 'resume', 'local'))
    group.add_argument('--status', action='store_true')
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--progress', help='Workspace-relative formal progress.yaml')
    parser.add_argument('--username')
    parser.add_argument('--repo')
    parser.add_argument('--branch', default='main')
    parser.add_argument('--path', default='README.md')
    parser.add_argument('--record-id', action='append', default=[])
    args = parser.parse_args()
    try:
        if args.configure:
            if args.state.exists():
                raise PolicyError('Configuration already exists; review it instead of overwriting controls')
            if not all((args.workspace, args.progress, args.username, args.repo)):
                raise PolicyError('Setup requires workspace, progress, username and repo after user authorization')
            workspace = args.workspace.resolve()
            progress = (workspace / args.progress).resolve()
            relative = progress.relative_to(workspace)
            args.state.resolve().relative_to(workspace)
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo):
                raise PolicyError('Invalid repository')
            state = dict(version=1, username=args.username, repo=args.repo, branch=args.branch,
                         path=args.path, workspace=str(workspace), progress=relative.as_posix(),
                         enabled=True, paused=False, local_only_ids=[], last_seen_revision='')
            state['last_seen_revision'] = revision(state)
            atomic_json(args.state, state)
            print('Configured: future formal changes only; no historical backfill')
        elif args.status:
            state = load_state(args.state)
            print(json.dumps({'enabled': state['enabled'], 'paused': state['paused'],
                              'local_only_count': len(state['local_only_ids'])}))
        else:
            with state_lock(args.state):
                state = control(load_state(args.state), args.control, args.record_id)
                atomic_json(args.state, state)
            print('Control saved:', args.control)
    except (ValueError, OSError, KeyError, TypeError):
        parser.error('Policy operation failed; check configuration, source and record IDs (private values omitted)')


if __name__ == '__main__':
    main()
