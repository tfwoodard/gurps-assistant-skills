#!/usr/bin/env python3
"""Write a converted chapter into a library kept in a local folder (library-layout.md §1).

    write_chapter.py OUT_DIR --library ROOT --layout LAYOUT.json --source B --chapter ch2
                     --notes "what was imported, what was left out" [--target library-data]
                     [--date YYYY-MM-DD] [--dry-run]

OUT_DIR is a converter's output: `<category>--<slug>.json` and `.md` for each entry,
`_records.json` and `_report.json`. Nothing is written unless the chapter is fit to write:

  * the converter's report has no errors;
  * check_coverage.py accounts for every word of LAYOUT.json;
  * every record has its entry's two files, and no file is there without a record.

Then, in this order: the entry files (over any there already), each category's `_index.json`
and the import log (through merge_import.py, which also says which entries a re-import no longer
has: their files are removed), and last `library.json`, where the chapter becomes `imported`.

`--target` is the library-data folder under ROOT: `library-data` for a library source,
`campaigns/<slug>/library-data` or `campaigns/<slug>/gm/library-data` for a campaign's (the
chapter's status is then set by hand in campaign.json, and this says so).

Every file written is read back and compared with what was meant. Prints a summary as JSON.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def same(a, b):
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        return fa.read() == fb.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out')
    ap.add_argument('--library', required=True)
    ap.add_argument('--layout', required=True, help='the layout JSON the chapter was converted from, for the coverage check')
    ap.add_argument('--source', required=True)
    ap.add_argument('--chapter', required=True)
    ap.add_argument('--notes', required=True, help="for the import log and the chapter's notes")
    ap.add_argument('--target', default='library-data')
    ap.add_argument('--date')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    date = a.date or datetime.date.today().isoformat()

    lib_path = os.path.join(a.library, 'library.json')
    if not os.path.exists(lib_path) or not load(lib_path).get('gurps_library'):
        sys.exit(f'{a.library}: not a GURPS library')
    library = load(lib_path)
    src = next((s for s in library.get('sources', []) if s['code'] == a.source), None)
    in_library = a.target == 'library-data'
    if in_library:
        if src is None:
            sys.exit(f'{a.source}: no source with that code in library.json')
        chapter = next((c for c in src['chapters'] if c['id'] == a.chapter), None)
        if chapter is None:
            sys.exit(f'{a.source}: no chapter {a.chapter}')
    edition = (src or {}).get('edition') or library.get('edition')

    # --- is it fit to write? -----------------------------------------------------------------
    report = load(os.path.join(a.out, '_report.json'))
    if report.get('errors'):
        sys.exit(f'the converter reported {len(report["errors"])} errors; nothing written. First: {report["errors"][0]}')
    cov = subprocess.run([sys.executable, os.path.join(HERE, 'check_coverage.py'), a.layout, a.out],
                         capture_output=True, text=True, encoding='utf-8')
    if cov.returncode != 0:
        missing = [l for l in cov.stdout.splitlines() if l.startswith('missing')]
        sys.exit(f'check_coverage.py: {len(missing)} words of the pages are in no entry; nothing written. '
                 f'First: {missing[0] if missing else cov.stdout[-200:]}')
    records = load(os.path.join(a.out, '_records.json'))
    wrong = [r['slug'] for r in records if r['source'] != a.source or r['chapter'] != a.chapter]
    if wrong:
        sys.exit(f'records of another source or chapter than {a.source} {a.chapter}: {", ".join(wrong[:5])}')
    files = {}
    for r in records:
        base = os.path.join(a.out, f'{r["_category"]}--{r["slug"]}')
        for ext in ('.json', '.md'):
            if not os.path.exists(base + ext):
                sys.exit(f'{r["_category"]}/{r["slug"]}: {os.path.basename(base + ext)} is not in {a.out}')
        files[(r['_category'], r['slug'])] = base
    extra = sorted(f for f in os.listdir(a.out) if not f.startswith('_') and f.endswith('.json') and
                   tuple(f[:-5].split('--', 1)) not in files)
    if extra:
        sys.exit(f'entry files with no record: {", ".join(extra[:5])}')
    categories = sorted({c for c, _ in files})
    summary = {'source': a.source, 'chapter': a.chapter, 'date': date, 'target': a.target, 'dry_run': a.dry_run,
               'coverage': cov.stdout.strip().splitlines()[-1], 'categories': {}}

    # --- entries, then indexes and the log, then library.json ----------------------------------
    target = os.path.join(a.library, *a.target.split('/'))
    log_path = os.path.join(target, '_import-log.json')
    with tempfile.TemporaryDirectory() as tmp:
        for cat in categories:
            folder = os.path.join(target, cat)
            index_path = os.path.join(folder, '_index.json')
            mine = sorted(slug for c, slug in files if c == cat)
            if not a.dry_run:
                os.makedirs(folder, exist_ok=True)
                for slug in mine:
                    for ext in ('.json', '.md'):
                        shutil.copyfile(files[(cat, slug)] + ext, os.path.join(folder, slug + ext))
                        if not same(files[(cat, slug)] + ext, os.path.join(folder, slug + ext)):
                            sys.exit(f'{cat}/{slug}{ext}: the copy does not match')
            work = os.path.join(tmp, cat)
            cmd = [sys.executable, os.path.join(HERE, 'merge_import.py'), '--out', work,
                   '--records', os.path.join(a.out, '_records.json'), '--edition', edition,
                   '--source', a.source, '--chapter', a.chapter, '--category', cat, '--date', date,
                   '--log-notes', a.notes]
            if os.path.exists(index_path):
                cmd += ['--index', index_path]
            if os.path.exists(log_path):
                cmd += ['--log', log_path]
            else:
                empty = os.path.join(tmp, 'empty-log.json')
                with open(empty, 'w', encoding='utf-8') as f:
                    f.write('[]\n')
                cmd += ['--log', empty]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if r.returncode != 0:
                sys.exit(f'merge_import.py ({cat}): {r.stderr.strip() or r.stdout.strip()}')
            line = next(l for l in r.stdout.splitlines() if l.startswith('_index.json:'))
            gone = next((l.split(': ', 1)[1].split(', ') for l in r.stdout.splitlines()
                         if l.strip().startswith('No longer in this chapter')), [])
            summary['categories'][cat] = {'entries': len(mine), 'index': line.split(': ', 1)[1], 'removed': gone}
            if a.dry_run:
                continue
            shutil.copyfile(os.path.join(work, '_index.json'), index_path)
            shutil.copyfile(os.path.join(work, '_import-log.json'), log_path)
            for slug in gone:                       # a re-import no longer has these entries
                for ext in ('.json', '.md'):
                    path = os.path.join(folder, slug + ext)
                    if os.path.exists(path):
                        os.remove(path)
            have = {r['slug'] for r in load(index_path)}
            lost = [s for s in mine if s not in have]
            if lost:
                sys.exit(f'{cat}/_index.json lacks {", ".join(lost[:5])} after the merge')
    if in_library and not a.dry_run:
        chapter.update(status='imported', date=date, notes=a.notes)
        with open(lib_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(library, f, ensure_ascii=False, indent=2)
            f.write('\n')
        summary['chapter_status'] = 'imported'
    elif not in_library:
        summary['chapter_status'] = "not set: set this chapter's status in the campaign's campaign.json by hand"
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
