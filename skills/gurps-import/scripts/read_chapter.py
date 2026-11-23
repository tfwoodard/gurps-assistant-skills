#!/usr/bin/env python3
"""Read a chapter's pages by layout, with the options its plan records.

    read_chapter.py PLAN.json --library ROOT --out scratch/ch2-layout.json [--print]

A chapter's plan keeps, under `layout`, how its pages are to be read, so that reading them again
gives the same lines:

    "layout": {"file": "sources/B/GURPS Basic Set - Characters.pdf", "pages": "32-118",
               "page_offset": 2, "boxes": true, "icon_fonts": ["GURPSICONS"],
               "icon_text": ["GURPSICONS:1=[exotic]"], "icons_alone": true,
               "aside_fonts": ["NewAster-Italic@14"], "replace_chars": ["¥=×"],
               "margin_lines": []}

This runs pdf_layout.py with them (`file` is relative to the library's root). `--print` shows the
command and runs nothing. Keys ending `_why` are notes for people and are passed over; any other
key this does not know is an error, so a misspelt option is not silently dropped.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LISTS = {'icon_fonts': '--icon-fonts', 'icon_text': '--icon-text', 'aside_fonts': '--aside-fonts',
         'replace_chars': '--replace-chars', 'margin_lines': '--margin-lines', 'not_boxes': '--not-boxes',
         'usual_gutters': '--usual-gutters', 'set_gutters': '--set-gutters'}
FLAGS = {'boxes': '--boxes', 'icons_alone': '--icons-alone'}


def command(layout, library, out):
    """The pdf_layout.py arguments for a plan's `layout`."""
    unknown = [k for k in layout if k not in LISTS and k not in FLAGS and not k.endswith('_why') and
               k not in ('file', 'pages', 'page_offset')]
    if unknown:
        raise ValueError(f'layout options this does not know: {", ".join(unknown)}')
    for need in ('file', 'pages'):
        if need not in layout:
            raise ValueError(f'the plan\'s layout has no `{need}`')
    args = [os.path.join(library, *layout['file'].split('/')), '--pages', str(layout['pages']),
            '--page-offset', str(layout.get('page_offset', 0))]
    for key, flag in FLAGS.items():
        if layout.get(key):
            args.append(flag)
    for key, flag in LISTS.items():
        if layout.get(key):
            args += [flag] + [str(v) for v in layout[key]]
    return args + ['--out', out]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan')
    ap.add_argument('--library', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--print', action='store_true', dest='only_print')
    a = ap.parse_args(argv)
    with open(a.plan, encoding='utf-8') as f:
        plan = json.load(f)
    if 'layout' not in plan:
        sys.exit(f'{a.plan}: no `layout`')
    try:
        args = command(plan['layout'], a.library, a.out)
    except ValueError as e:
        sys.exit(f'{a.plan}: {e}')
    if a.only_print:
        print('pdf_layout.py ' + ' '.join(f'"{x}"' if ' ' in x else x for x in args))
        return 0
    r = subprocess.run([sys.executable, os.path.join(HERE, 'pdf_layout.py')] + args, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    # pdf_layout.py reports on stderr; a PDF library's own font warnings are noise here
    for line in (r.stdout + r.stderr).splitlines():
        if 'fontTools' not in line:
            print(line)
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
