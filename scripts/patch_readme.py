"""Prepare a local README patch; no network and no credentials."""
import argparse
import json
import re
from pathlib import Path


def cell(value):
    return value.replace('|', '&#124;').replace('\r', ' ').replace('\n', ' ').strip()


def patch(source, summary):
    if not isinstance(summary, dict):
        raise ValueError('Summary must be a JSON object')
    for key in ('username', 'role', 'current', 'learned', 'next'):
        if not isinstance(summary.get(key), str) or not summary[key].strip():
            raise ValueError('Missing nonempty string: ' + key)
    newline_style = '\r\n' if '\r\n' in source else '\n'
    username = summary['username']
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', username):
        raise ValueError('Invalid GitHub username')
    lines = source.splitlines(keepends=True)
    hits = []
    for index, line in enumerate(lines):
        if not line.lstrip().startswith('|'):
            continue
        first = line.strip().split('|')[1].strip()
        link = re.fullmatch(r'\[([^\]]+)\]\(https://github\.com/([^/)]+)/?\)', first)
        found = link.group(2) if link else first
        if found.casefold() == username.casefold():
            hits.append(index)
    if len(hits) != 1:
        raise ValueError('Expected exactly one existing member row')
    index = hits[0]
    if len(lines[index].strip().split('|')) != 7:
        raise ValueError('Expected five-column progress table')
    row = '| [' + username + '](https://github.com/' + username + ') | '
    row += ' | '.join(cell(summary[k]) for k in ('role', 'current', 'learned', 'next')) + ' |'
    newline = '\r\n' if lines[index].endswith('\r\n') else '\n' if lines[index].endswith('\n') else ''
    # Leave equivalent rows byte-for-byte unchanged.
    old_cells = [v.strip() for v in lines[index].strip().split('|')[2:-1]]
    if old_cells != [cell(summary[k]) for k in ('role', 'current', 'learned', 'next')]:
        lines[index] = row + newline
    result = ''.join(lines)
    if 'detail' in summary:
        detail = summary['detail']
        heading = '### ' + username + ' · 阶段记录'
        if not isinstance(detail, str) or not detail.startswith(heading + '\n'):
            raise ValueError('detail must start with member stage heading')
        pattern = re.compile(r'^' + re.escape(heading) + r'[ \t]*\n.*?(?=^#{1,3} |^> |\Z)', re.M | re.S)
        if len(list(pattern.finditer(result))) != 1:
            raise ValueError('Expected exactly one member detail section')
        detail = detail.replace('\r\n', '\n').replace('\r', '\n').rstrip()
        detail = detail.replace('\n', newline_style) + newline_style * 2
        result = pattern.sub(lambda m: detail, result, count=1)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--readme', required=True, type=Path)
    parser.add_argument('--summary', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() in (args.readme.resolve(), args.summary.resolve()):
        parser.error('Output must be a separate proposed file')
    with args.readme.open(encoding='utf-8', newline='') as handle:
        source = handle.read()
    try:
        result = patch(source, json.loads(args.summary.read_text(encoding='utf-8-sig')))
    except (ValueError, KeyError, IndexError) as exc:
        parser.error(str(exc))
    with args.output.open('w', encoding='utf-8', newline='') as handle:
        handle.write(result)
    print('unchanged' if result == source else 'proposed local patch written')


if __name__ == '__main__':
    main()
