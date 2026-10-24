"""Install the skill into an explicitly selected Codex or DSH skill root."""
import argparse
import shutil
import tempfile
from pathlib import Path

NAME = 'studymate-github-sync'
SOURCE = Path(__file__).resolve().parents[1]
FILES = ('SKILL.md', 'README.md', 'agents', 'scripts', 'references', 'tests')


def destination(host, workspace=None, skills_dir=None):
    if skills_dir:
        root = Path(skills_dir).expanduser().resolve()
    elif host == 'dsh' and workspace:
        workspace = Path(workspace).expanduser().resolve()
        if not workspace.is_dir():
            raise ValueError('Workspace must be an existing directory')
        project = next((p for p in (workspace, *workspace.parents) if (p / '.git').exists()), workspace)
        root = project / '.dsh' / 'skills'
    elif host == 'dsh':
        raise ValueError('DSH requires --workspace or --skills-dir (the actual profile skill root)')
    else:
        import os
        root = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'
    return root / NAME


def install(target, update=False, dry_run=False, source=SOURCE):
    target = target.resolve()
    source = source.resolve()
    if target == source or source in target.parents or target in source.parents:
        raise ValueError('Source and destination must not overlap')
    if target.exists() and not update:
        raise ValueError('Destination exists; use --update after reviewing changes')
    if target.exists() and not target.is_dir():
        raise ValueError('Destination is not a directory')
    if dry_run:
        return str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Stage first; copy only distribution files, never learning data or credentials.
    with tempfile.TemporaryDirectory(prefix='studymate-install-', dir=target.parent) as scratch:
        stage = Path(scratch) / NAME
        stage.mkdir()
        for name in FILES:
            item = source / name
            if item.is_dir():
                shutil.copytree(item, stage / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            elif item.is_file():
                shutil.copy2(item, stage / name)
        if not target.exists():
            stage.rename(target)
        else:
            # Existing non-distribution files are left intact. Keep a backup first.
            backup = Path(tempfile.mkdtemp(prefix=NAME + '-backup-', dir=target.parent))
            shutil.copytree(target, backup / NAME)
            shutil.copytree(stage, target, dirs_exist_ok=True)
            print('Previous version backup:', backup)
    return str(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=('codex', 'dsh'), required=True)
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--skills-dir', type=Path)
    parser.add_argument('--update', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.workspace and args.skills_dir:
        parser.error('Choose --workspace or --skills-dir, not both')
    try:
        target = destination(args.host, args.workspace, args.skills_dir)
        print('Planned:' if args.dry_run else 'Installed:', install(target, args.update, args.dry_run))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
