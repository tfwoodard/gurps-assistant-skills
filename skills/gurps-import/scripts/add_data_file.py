#!/usr/bin/env python3
"""Add a GCA data file to the library, or read it again after it changed (library-layout.md §12).

    add_data_file.py --library ROOT "PATH/GURPS Basic Set 4th Ed.--Characters.gdf"
                     [--source B] [--origin official|community|homebrew|generated]
                     [--folder gca/books] [--notes "..."] [--date YYYY-MM-DD] [--dry-run]

It copies the file, unchanged and under its own name, to the library's folder for it; writes
what gdf.py reads from it to gca/parsed/<file-slug>.json; replaces the file's records in
gca/parsed/_index.json; and adds or replaces its record in library.json's `data_files`, and its
name in its source's `data_files`.

The report says what changed since the file was last read (definitions added, removed and
altered, by item name) and lists every line gdf.py could not read. Lines it could not read never
stop the file being added: they are faults in the file, kept in the parsed JSON's `problems` and
counted in the record, for the Librarian to see and to report to the file's maintainer.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdf  # noqa: E402


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', os.path.splitext(name)[0].lower()).strip('-')


def names(header_value):
    """A Requires= or Taboo= line's file names."""
    return [n.strip().strip('"{}').strip() for n in gdf.split_top(header_value or '') if n.strip()]


def load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def dump(path, data, indent=1):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write('\n')


def definitions(parsed):
    """{item name: [its definitions' content, in file order]} (a file can define a name twice)."""
    out = {}
    for s in parsed['sections']:
        for it in s['items']:
            if 'item' in it:
                out.setdefault(f'{s["name"]}/{it["item"]}', []).append(
                    {k: v for k, v in it.items() if k != 'line'})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file')
    ap.add_argument('--library', required=True)
    ap.add_argument('--source', help='the code of the source whose traits it defines')
    ap.add_argument('--origin', default='official', choices=('official', 'community', 'homebrew', 'generated'))
    ap.add_argument('--folder', help='where it is kept in the library [gca/books; gca/generated for a generated file]')
    ap.add_argument('--notes', default='')
    ap.add_argument('--date')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)

    lib_path = os.path.join(a.library, 'library.json')
    library = load(lib_path, None)
    if not library or not library.get('gurps_library'):
        sys.exit(f'{a.library}: not a GURPS library (no library.json with "gurps_library": true)')
    if a.source and a.source not in [s['code'] for s in library.get('sources', [])]:
        sys.exit(f'{a.source}: no source with that code in library.json; add the source first, or leave --source out')

    name = os.path.basename(a.file)
    folder = a.folder or ('gca/generated' if a.origin == 'generated' else 'gca/books')
    with open(a.file, 'rb') as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    parsed = gdf.parse(gdf.read_text(a.file), name)
    records = gdf.records(parsed)
    counts = gdf.counts(parsed)

    parsed_path = os.path.join(a.library, 'gca', 'parsed', slugify(name) + '.json')
    index_path = os.path.join(a.library, 'gca', 'parsed', '_index.json')
    old = load(parsed_path, None)
    changes = None
    if old:
        before, after = definitions(old), definitions(parsed)
        changes = {'added': sorted(set(after) - set(before)), 'removed': sorted(set(before) - set(after)),
                   'altered': sorted(k for k in set(before) & set(after) if before[k] != after[k])}

    data_files = library.setdefault('data_files', [])
    previous = next((d for d in data_files if d['file'].lower() == name.lower()), None)
    record = {'file': name, 'folder': folder, 'origin': a.origin,
              'source': a.source or (previous or {}).get('source'),
              'description': parsed['header'].get('description', ''),
              'requires': names(parsed['header'].get('requires')), 'taboo': names(parsed['header'].get('taboo')),
              'sha256': sha, 'status': 'imported', 'date': a.date or datetime.date.today().isoformat(),
              'counts': counts, 'problems': len(parsed['problems']),
              'notes': a.notes or (previous or {}).get('notes', '')}
    have = {d['file'].lower() for d in data_files} | {name.lower()}
    report = {'file': name, 'to': f'{folder}/{name}', 'parsed': f'gca/parsed/{slugify(name)}.json',
              'sha256': sha, 'same_as_before': bool(previous and previous.get('sha256') == sha),
              'counts': counts, 'definitions': len(records),
              'requires': [{'file': r, 'in_library': r.lower() in have} for r in record['requires']],
              'changes': changes, 'problems': parsed['problems']}

    if not a.dry_run:
        dest = os.path.join(a.library, *folder.split('/'), name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.abspath(dest) != os.path.abspath(a.file):
            shutil.copyfile(a.file, dest)
        with open(dest, 'rb') as f:
            if hashlib.sha256(f.read()).hexdigest() != sha:
                sys.exit(f'{dest}: the copy does not match the original')
        dump(parsed_path, parsed)
        index = [r for r in load(index_path, []) if r['file'].lower() != name.lower()] + records
        index.sort(key=lambda r: (r['file'].lower(), r['line']))
        dump(index_path, index, indent=None)
        if previous:
            data_files[data_files.index(previous)] = record
        else:
            data_files.append(record)
        data_files.sort(key=lambda d: d['file'].lower())
        for s in library.get('sources', []):
            listed = s.setdefault('data_files', []) if s['code'] == record['source'] else s.get('data_files', [])
            if s['code'] == record['source'] and name not in listed:
                listed.append(name)
        dump(lib_path, library, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
