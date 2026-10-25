"""Prepare a local README patch; no network and no credentials."""
import argparse
import json
import re
import html
from sync_policy import validate_summary
from pathlib import Path


def cell(value):
    value = html.escape(value, quote=False).strip()
    for char in ('[', ']', '`', '*', '_', '!'):
        value = value.replace(char, '&#' + str(ord(char)) + ';')
    return value.replace('|', '&#124;')


def patch(source, summary):
    validate_summary(summary)
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
    # Regenerate only an existing personal section from the same safe fields.
    heading = '### ' + username + ' · 阶段记录'
    pattern = re.compile(r'^' + re.escape(heading) + r'[ \t]*\r?\n.*?(?=^#{1,3} |^> |\Z)', re.M | re.S)
    matches = list(pattern.finditer(result))
    if len(matches) > 1:
        raise ValueError('Duplicate personal stage sections')
    if matches:
        detail = heading + newline_style * 2
        detail += '- **正在学习**：' + cell(summary['current']) + newline_style
        detail += '- **已学概览**：' + cell(summary['learned']) + newline_style
        detail += '- **下一步**：' + cell(summary['next']) + newline_style * 2
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
