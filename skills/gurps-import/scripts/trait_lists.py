"""Trait lists: a book's summary tables of its traits, one row a trait (the Basic Set's appendix
"Trait Lists": advantages, disadvantages, enhancements, limitations, skills, techniques, spells).

A list is a heading, sometimes a key (lines explaining the columns' marks), and a table under a
header row (`Advantage M/P/Soc X/Sup Cost Page`). The table runs on across halves of a page set
side by side (the plan's `set_gutters` makes each half a column) and across pages, its header row
printed again at the top of each half; a header may have a line above it naming its columns
further ("Time to" over "Cast"). Each word of the header row names a column, and the columns are
parted where the fewest row words cross between one header word and the next column's cells
(header_seps). A row's cell that runs on to a second line (a skill's defaults, a spell's
prerequisites) carries on there, the row's other cells empty; so does a name, set in under
itself (with any other cell run on beside it). A subheading inside a list (MODIFIERS over the
enhancements, then ENHANCEMENTS) stays a heading in the entry.

The plan's `lists` names each one:

    {"heading": "Advantages", "page": 297, "header_starts": "Advantage",
     "name": "Advantages Table", "about": "Every advantage: its types, cost and page",
     "values": {"M/P/Soc": ["M", "P", "Soc", "M/P"]},
     "cells": [{"page": 302, "text": "DX or IQ", "column": "Attr", "why": "..."}]}

`values` gives what the list's key says a column holds: any other value is a misread, and refuses
the list. `cells` places words the page prints as one cell though they reach over a neighbouring
column's edge, where no one edge parts the columns for every row; one that matches no row is an
error. A word printed run on into the next cell with no space ("Repair/TL†IQ"), leaving that
cell empty, is split when it ends in a value the column holds in other rows, and the report's
`words_split` says so (check_coverage.py credits it).

A list runs from its heading to the next list's (or the chapter's end). take_lists() makes each a
`tables` entry named `name` (the heading kept as `printed_name`), its key and subheadings as
text, then one table block. Each part of the table (a half, a page) is read on its own columns,
and every part must give the same column names. A part is refused, and the list with it, when its
header names a column no cells fall in, when its cells don't line up (equipment_tables.aligned),
when a row leaves a cell empty (these lists print a mark in every cell), when a row's last cell
isn't a page number (or several), or when a line carries on no row. A refused list is an error
and writes nothing. The header printed again over each part is credited to the word count once
(`folded_keys`).
"""
import re

from entry_text import blocks_from_lines, fix_case, join_lines, plain, slugify, table_data
from equipment_tables import aligned, cells_of

PAGES = re.compile(r'^\d+(?:\s*,\s*\d+)*$')
SET_IN = 3.0          # points: a line whose first word starts this far right of its column's cells carries on


def place_cells(rows, grid, columns, cells_spec, used):
    """The plan's `cells`: words the page prints as one cell of a column though they reach over a
    neighbouring column's edge, where no one edge parts the columns for every row (a wide cell
    centred under its header beside another): [{"page", "text", "column", "why"}]."""
    for r, g in zip(rows, grid):
        for n, c in enumerate(cells_spec):
            if c['page'] != r['page'] or c['column'] not in columns:
                continue
            want = c['text'].split()
            texts = [w[0] for w in r['words']]
            at = next((i for i in range(len(texts) - len(want) + 1) if texts[i:i + len(want)] == want), None)
            if at is None:
                continue
            words = r['words'][at:at + len(want)]
            for col in g:
                col[:] = [w for w in col if not any(w is x for x in words)]
            g[columns.index(c['column'])] += words
            g[columns.index(c['column'])].sort(key=lambda w: w[1])
            used.add(n)


def split_run_on(grid, columns, report, where):
    """A word that runs on into the next column's value, printed with no space ("Repair/TL†IQ"):
    when a row's cell is empty and the cell before it ends in a word ending with a value the
    column prints in other rows, that value is split off into it (said in the report)."""
    for k in range(1, len(columns)):
        values = sorted({' '.join(w[0] for w in g[k]) for g in grid if len(g[k]) == 1}, key=len, reverse=True)
        for g in grid:
            if g[k] or not g[k - 1]:
                continue
            w = g[k - 1][-1]
            v = next((v for v in values if len(w[0]) > len(v) and w[0].endswith(v)), None)
            if v:
                cut = w[1] + (w[2] - w[1]) * (len(w[0]) - len(v)) / len(w[0])
                g[k - 1][-1] = [w[0][:-len(v)], w[1], cut]
                g[k].append([v, cut, w[2]])
                report.setdefault('words_split', []).append({'entry': where, 'word': w[0], 'into': [w[0][:-len(v)], v],
                                                             'why': f'no space before a value of column {columns[k]!r}'})


def is_header(l, first_word):
    return bool(l.get('heading')) and bool(l.get('words')) and l['words'][0][0] == first_word


def header_over(l, header):
    """A heading line just above a header row, inside its span and clear of its first column: more
    of its columns' names ("Time to" over "Cast"). A key line above the header starts at the
    margin, over the first column, and is not one."""
    words = header.get('words') or []
    return bool(l.get('heading')) and l['page'] == header['page'] and l.get('column') == header.get('column') and \
        0 < header['top'] - l['top'] <= 1.6 * header['size'] and len(words) > 1 and \
        l['x0'] >= words[1][1] - 1 and l['x1'] <= header['x1'] + 1


def header_seps(header, rows):
    """Column separators, one between each two words of the header row (each names a column): the
    place between the first word's middle and the next column's cells (the next word's middle, or
    the first row word starting under it, if sooner) that the fewest row words cross, the middle
    of the widest such stretch (a cell may reach left of its header word: "-1 or -5 to -15"
    under "Cost").
    A word that crosses it goes by its middle."""
    seps = []
    words = [w for r in rows for w in r['words']]
    for a, b in zip(header['words'], header['words'][1:]):
        # up to the next header word's middle, or the first word that starts at or after its start
        # (a cell of that column, set left under it or centred under a wider header), if sooner
        mid = (b[1] + b[2]) / 2
        lo, hi = (a[1] + a[2]) / 2, min([mid] + [w[1] for w in words if b[1] - 1 <= w[1] <= mid])
        xs = [lo + 0.5 * k for k in range(int((hi - lo) / 0.5) + 1)]
        if not xs:
            seps.append((a[2] + b[1]) / 2)
            continue
        cross = [sum(1 for w in words if w[1] < x < w[2]) for x in xs]
        least = min(cross)
        best, run = (0, 0), None
        for k, c in enumerate(cross + [least + 1]):
            if c == least and run is None:
                run = k
            elif c != least and run is not None:
                if k - run > best[1] - best[0]:
                    best = (run, k)
                run = None
        seps.append((xs[best[0]] + xs[best[1] - 1]) / 2)
    return seps


def read_part(header, over, rows, report, where, vocab, cells_spec=(), used=None):
    """One part of a list (a half or a page) -> (columns, rows of cells, failures)."""
    failures = []
    used = set() if used is None else used
    if not rows:
        return [], [], [f'p{header["page"]} {header.get("column")}: a header with no rows under it']
    seps = header_seps(header, rows)
    names = cells_of(header, seps)
    tops = cells_of(over, seps) if over else [[] for _ in names]
    columns = [' '.join(w[0] for w in t + n) for t, n in zip(tops, names)]
    if any(not n for n in names):
        failures.append(f'p{header["page"]}: a column with no name in the header {header["text"]!r} ({columns})')
    grid = [cells_of(r, seps) for r in rows]
    place_cells(rows, grid, columns, cells_spec, used)
    split_run_on(grid, columns, report, where)
    first_left = min(r['words'][0][1] for r, g in zip(rows, grid) if g[0])
    out, parts, firsts = [], [], []
    for r, g in zip(rows, grid):
        # a line set in carries on the row above: its name, and any other cell run on with it
        carries = not g[0] or r['words'][0][1] > first_left + SET_IN
        if carries:
            if not out:
                failures.append(f'p{r["page"]}: {r["text"][:40]!r} carries on no row')
                continue
            for k, ws in enumerate(g):
                if ws:
                    parts[-1][k].append(' '.join(w[0] for w in ws))
            continue
        firsts.append(g)
        parts.append([[' '.join(w[0] for w in ws)] if ws else [] for ws in g])
        out.append(None)
    cells = [[join_lines(p, report, where, vocab) if p else '' for p in row] for row in parts]
    for k in range(len(seps) + 1):
        col = [g[k] for g in firsts if g[k]]
        off = aligned(col) if len(col) >= 3 else []
        if off:
            failures.append(f'p{header["page"]}: column {columns[k]!r} has cells that line up with no others: ' +
                            ', '.join(repr(' '.join(w[0] for w in col[i])) for i in off[:3]))
    for row in cells:
        if any(not c for c in row):
            failures.append(f'p{header["page"]}: the row {row[0]!r} has an empty cell (every cell prints a mark): '
                            f'{dict(zip(columns, row))}')
        if not PAGES.match(row[-1]):
            failures.append(f'p{header["page"]}: the row {row[0]!r} ends {row[-1]!r}, not a page')
    return columns, cells, failures


def read_list(spec, lines, report, vocab, where):
    """A list's lines (its heading first) -> (text lines before the table, columns, cells, parts,
    failures)."""
    first = spec.get('header_starts', '')
    before, parts, current = [], [], None
    body = lines[1:]
    for i, l in enumerate(body):
        if is_header(l, first):
            over = next((p for p in reversed(body[max(0, i - 2):i]) if header_over(p, l)), None)
            if over is not None:
                if current is not None and current['rows'] and current['rows'][-1] is over:
                    current['rows'].pop()
                elif over in before:
                    before.remove(over)
            current = {'header': l, 'over': over, 'rows': []}
            parts.append(current)
        elif current is None:
            before.append(l)
        elif l.get('heading') and l['size'] > current['header']['size'] + 1 and \
                not header_over(l, next((x for x in body[i + 1:i + 3] if is_header(x, first)), {'page': None})):
            before.append(l)     # a subheading between parts is text of the list (it is never inside one)
        else:
            current['rows'].append(l)
    failures, columns, cells, used = [], None, [], set()
    if not parts:
        return before, [], [], [], [f'no header row starting {first!r}']
    for part in parts:
        cols, rows, fails = read_part(part['header'], part['over'], part['rows'], report, where, vocab,
                                      spec.get('cells', []), used)
        failures += fails
        if columns is None:
            columns = cols
        elif cols and cols != columns:
            failures.append(f'p{part["header"]["page"]}: the columns {cols} are not the first part\'s {columns}')
        cells += rows
    # the values the list's key gives a column (Diff: E, A, H, VH): any other is a misread
    for col, allowed in spec.get('values', {}).items():
        if col not in (columns or []):
            failures.append(f'plan values: no column {col!r} in {columns}')
            continue
        k = columns.index(col)
        odd = [r for r in cells if r[k] not in allowed]
        if odd:
            failures.append(f'column {col!r} holds values the plan does not give it: ' +
                            ', '.join(f'{r[0]!r}: {r[k]!r}' for r in odd[:5]))
    for n, c in enumerate(spec.get('cells', [])):
        if n not in used:
            failures.append(f'plan cells: {c["text"]!r} on p{c["page"]} is in no row of the list')
    return before, columns or [], cells, parts, failures


def take_lists(lines, plan, report, vocab, source, chapter):
    """Take the plan's trait lists out of `lines`. Returns (the other lines, entries as
    (category, entry))."""
    specs = plan.get('lists', [])
    starts = []
    for spec in specs:
        i = next((k for k, l in enumerate(lines) if l['page'] == spec['page'] and l.get('heading') and
                  fix_case(plain(l['text']).strip()).lower() == spec['heading'].lower()), None)
        if i is None:
            report['errors'].append(f'plan list {spec["heading"]!r}: no such heading on p{spec["page"]}')
        starts.append(i)
    found = sorted((i, s) for i, s in zip(starts, specs) if i is not None)
    taken, entries = set(), []
    for n, (i, spec) in enumerate(found):
        end = found[n + 1][0] if n + 1 < len(found) else len(lines)
        own = [l for l in lines[i:end] if not l.get('furniture') and not l.get('aside')]
        name = spec.get('name') or fix_case(plain(own[0]['text']).strip())
        where = f'tables/{slugify(name)}'
        before, columns, cells, parts, failures = read_list(spec, own, report, vocab, where)
        note = {'entry': where, 'page': spec['page'], 'columns': columns, 'rows': len(cells), 'parts': len(parts),
                'failures': failures}
        report.setdefault('lists', []).append(note)
        taken |= {id(l) for l in own}
        if failures:
            report['errors'].append(f'{where} (p{spec["page"]}): the list was not read: ' + '; '.join(failures[:5]) +
                                    (f' (and {len(failures) - 5} more)' if len(failures) > 5 else ''))
            continue
        # the header printed again over each part: its words are the columns' names, kept once
        if len(parts) > 1:
            report.setdefault('folded_keys', []).append(
                {'region': ' / '.join(p['header']['text'] for p in parts[1:]), 'entry': where,
                 'cells': [w[0] for p in parts[1:] for w in (p['over']['words'] if p['over'] else []) + p['header']['words']]})
        block = {'type': 'table', 'title': '', 'columns': columns, 'rows': cells,
                 'data': table_data(columns, cells, report, where)}
        fields = {'printed_name': fix_case(plain(own[0]['text']).strip())} if name != fix_case(plain(own[0]['text']).strip()) else {}
        fields.update(spec.get('fields', {}))
        if spec.get('about'):
            fields['about'] = spec['about']
        entries.append(('tables', {
            'slug': slugify(name), 'name': name, 'source': source, 'chapter': chapter,
            'section': fix_case(plain(own[0]['text']).strip()), 'page': own[0]['page'], 'fields': fields,
            'level': own[0].get('heading', 2),
            'content': blocks_from_lines(before, report, where, vocab) + [block]}))
    return [l for l in lines if id(l) not in taken], entries
