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

Every category's index and the import log are merged first, in scratch (merge_import.py, which
also says which entries a re-import no longer has); a merge that refuses stops the write with
nothing in the library changed. Then, in this order: the entry files (over any there already),
the removal of entries a re-import no longer has, each category's `_index.json`, the import log,
and last `library.json`, where the chapter becomes `imported`. An entry written over one that
is linked to GCA definitions keeps its `gca` (link_gca.py), in its files and its index record;
the summary counts them.

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
sys.path.insert(0, HERE)
from link_gca import with_gca  # noqa: E402
from render_entry import render  # noqa: E402


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
        glyphs = [l for l in cov.stdout.splitlines() if l.startswith('unmapped glyph')]
        if glyphs:
            sys.exit(f'check_coverage.py: the pages have {len(glyphs)} glyphs their fonts give no character for; '
                     f'nothing written. First: {glyphs[0]}')
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
    records_path = os.path.join(a.out, '_records.json')
    with tempfile.TemporaryDirectory() as tmp:
        # An entry written over one linked to its GCA definitions keeps the links (layout §6,
        # "Re-importing"): its .json, .md and index record get the old entry's `gca`.
        carried, unreadable = {}, []
        for (cat, slug), base in files.items():
            old = os.path.join(target, cat, slug + '.json')
            try:
                links = load(old).get('gca') if os.path.exists(old) else None
            except ValueError:
                unreadable.append(f'{cat}/{slug}')     # said in the summary: no links could be read from it
                continue
            if links:
                entry = load(base + '.json')
                if entry.get('gca') != links:
                    entry = with_gca(entry, links)
                    work = os.path.join(tmp, 'carried', f'{cat}--{slug}')
                    os.makedirs(os.path.dirname(work), exist_ok=True)
                    with open(work + '.json', 'w', encoding='utf-8', newline='\n') as f:
                        f.write(json.dumps(entry, ensure_ascii=False, indent=1) + '\n')
                    with open(work + '.md', 'w', encoding='utf-8', newline='\n') as f:
                        f.write(render(entry))
                    files[(cat, slug)] = work
                carried[(cat, slug)] = links
        if carried:
            for r in records:
                if (r['_category'], r['slug']) in carried:
                    r['gca'] = carried[(r['_category'], r['slug'])]
            records_path = os.path.join(tmp, '_records.json')
            with open(records_path, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(records, f, ensure_ascii=False, indent=1)
                f.write('\n')
        summary['gca_carried_over'] = len(carried)
        if unreadable:
            summary['old_entries_not_json'] = unreadable
        # Pass 1: every merge, into scratch, before anything in the library is touched. A merge
        # that refuses (a slug another chapter holds, say) stops the write with nothing changed.
        log_in = log_path
        if not os.path.exists(log_in):
            log_in = os.path.join(tmp, 'empty-log.json')
            with open(log_in, 'w', encoding='utf-8') as f:
                f.write('[]\n')
        merged = {}
        for cat in categories:
            index_path = os.path.join(target, cat, '_index.json')
            mine = sorted(slug for c, slug in files if c == cat)
            work = os.path.join(tmp, cat)
            cmd = [sys.executable, os.path.join(HERE, 'merge_import.py'), '--out', work,
                   '--records', records_path, '--edition', edition,
                   '--source', a.source, '--chapter', a.chapter, '--category', cat, '--date', date,
                   '--log-notes', a.notes, '--log', log_in]
            if os.path.exists(index_path):
                cmd += ['--index', index_path]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if r.returncode != 0:
                sys.exit(f'merge_import.py ({cat}): {r.stderr.strip() or r.stdout.strip()}; nothing written')
            have = {x['slug'] for x in load(os.path.join(work, '_index.json'))}
            lost = [s for s in mine if s not in have]
            if lost:
                sys.exit(f'{cat}/_index.json would lack {", ".join(lost[:5])} after the merge; nothing written')
            line = next(l for l in r.stdout.splitlines() if l.startswith('_index.json:'))
            gone = next((l.split(': ', 1)[1].split(', ') for l in r.stdout.splitlines()
                         if l.strip().startswith('No longer in this chapter')), [])
            summary['categories'][cat] = {'entries': len(mine), 'index': line.split(': ', 1)[1], 'removed': gone}
            merged[cat] = (work, mine, gone)
            log_in = os.path.join(work, '_import-log.json')        # the next category's log carries this one's record
        # Pass 2: the entries, then each index, the log, and last library.json.
        if not a.dry_run:
            for cat, (work, mine, gone) in merged.items():
                folder = os.path.join(target, cat)
                os.makedirs(folder, exist_ok=True)
                for slug in mine:
                    for ext in ('.json', '.md'):
                        shutil.copyfile(files[(cat, slug)] + ext, os.path.join(folder, slug + ext))
                        if not same(files[(cat, slug)] + ext, os.path.join(folder, slug + ext)):
                            sys.exit(f'{cat}/{slug}{ext}: the copy does not match')
                for slug in gone:                       # a re-import no longer has these entries
                    for ext in ('.json', '.md'):
                        path = os.path.join(folder, slug + ext)
                        if os.path.exists(path):
                            os.remove(path)
                shutil.copyfile(os.path.join(work, '_index.json'), os.path.join(folder, '_index.json'))
            shutil.copyfile(log_in, log_path)
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
