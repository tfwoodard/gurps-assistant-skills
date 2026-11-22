#!/usr/bin/env python3
"""Open a source's PDF at a printed page, in a browser window, for checking an import against the book.

    open_page.py B 37                     # the Basic Set at printed page 37
    open_page.py B 37 44 98               # several pages, one tab each
    open_page.py B 37 --print             # only print the address

The library is found from gurps-library.config.json (`drive_local_path`) or --library. The page
is a printed page number: the source's `files` in library.json say which PDF holds it and how far
its PDF pages are from its printed ones (library-layout.md §3).

Browsers open a PDF at a page from an address ending `#page=N`. Microsoft Edge is used when it
is installed, since it shows PDFs itself; otherwise the default browser. Nothing is copied: the
browser reads the library's own file.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
EDGE = (r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe')


def library_root(given):
    if given:
        return given
    for folder in (os.getcwd(), ROOT):
        path = os.path.join(folder, 'gurps-library.config.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                local = json.load(f).get('drive_local_path')
            if local:
                return local
    sys.exit('no library: give --library, or set drive_local_path in gurps-library.config.json')


def page_range(text):
    a, _, b = text.partition('-')
    return int(a), int(b or a)


def address(library, source, page):
    """(file URL with #page=N, PDF page) for a printed page of a source."""
    with open(os.path.join(library, 'library.json'), encoding='utf-8') as f:
        lib = json.load(f)
    src = next((s for s in lib.get('sources', []) if s['code'].lower() == source.lower()), None)
    if src is None:
        sys.exit(f'{source}: no source with that code in library.json')
    for f in src.get('files', []):
        first, last = page_range(f['pages'])
        if first <= page <= last:
            path = os.path.join(library, *f['file'].split('/'))
            if not os.path.exists(path):
                sys.exit(f'{path}: not there')
            pdf_page = page + f.get('page_offset', 0)
            return pathlib.Path(path).as_uri() + f'#page={pdf_page}', pdf_page
    sys.exit(f'{source}: no file holds printed page {page} (its files hold ' +
             ', '.join(f['pages'] for f in src.get('files', [])) + ')')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', help="the source's code, e.g. B")
    ap.add_argument('pages', nargs='+', type=int, help='printed page numbers')
    ap.add_argument('--library')
    ap.add_argument('--print', action='store_true', dest='only_print', help='print the addresses and open nothing')
    a = ap.parse_args(argv)
    library = library_root(a.library)
    edge = next((e for e in EDGE if os.path.exists(e)), None) or shutil.which('msedge')
    for page in a.pages:
        url, pdf_page = address(library, a.source, page)
        print(f'{a.source} p{page} (PDF page {pdf_page}): {url}')
        if a.only_print:
            continue
        if edge:
            subprocess.Popen([edge, url])
        else:
            webbrowser.open(url)
    return 0


if __name__ == '__main__':
    sys.exit(main())
