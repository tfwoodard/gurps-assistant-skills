"""Equipment tables: weapon, armor and shield tables as the GURPS books print them.

A table is a title ("Lamp Table"), then groups. A group is a heading line (a skill with its
defaults, "LAMPS (DX-4, Torch-2)", or a kind, "Hand Lamps"), sometimes a header row in
italics (TL, Weapon, Damage...; a header carries on over later groups until another is printed), and
rows. A row whose first column is empty ("or" in the Weapon column) is another way of using the item
above it: another attack mode. After the groups, a line "Notes" heads numbered notes ("[1] ...").
A table can run over several pages, and from a boxed panel onto the page.

take_tables() takes each table the plan names out of a chapter's lines and makes of it:

  * a `tables` entry, named by the title: each group as a heading and a table block, and the notes;
  * an `equipment` entry for each item, named as printed in its row: its rows as a table block
    under its group's heading, and the notes its rows cite. An item printed in more than one table
    (a spear for melee and for throwing) is one entry with each table's rows. Its fields: `kind`
    (the plan's), `group` (each group it is in, as printed), and its first row's cells by column
    (`tl`, `cost`, `weight`, `lc`... as printed), with `modes` holding every row's cells when it has
    more than one.

Every table is checked as the text tables are (entry_text.read_text_table): the rows leave blank
columns between them, the header names each column, each column's cells line up. A row may leave a
cell empty (an attack mode has no TL or cost of its own; many rows cite no note), but a row with
nothing in the first column must follow an item's row. A table that fails is reported in `errors`
and nothing of it is written.
"""
import re

from entry_text import (ALIGN_TOLERANCE, COLUMN_GAP, join_lines, marked, plain, slugify,
                        table_data, whole_end)

NOTE = re.compile(r'^\s*\[(\d+)\]\s*')
CITES = re.compile(r'\[(\d+(?:\s*,\s*\d+)*)\]')


def is_header(l, first_word):
    words = l.get('words') or []
    return bool(words) and words[0][0] == first_word and all(s['italic'] for s in l['spans'] if s['text'].strip())


def columns_of(header, rows, size):
    """Column separators (x) from the blanks every row leaves clear. (Not the header's: a table
    of many narrow columns sets its header words closer together than its cells.)"""
    left = min(l['x0'] for l in rows)
    right = max(l['x1'] for l in rows)
    step = 0.5
    n = int((right - left) / step) + 1
    covered = [False] * n
    for l in rows:
        for _, x0, x1 in l['words']:
            for k in range(max(0, int((x0 - left) / step)), min(n, int((x1 - left) / step) + 1)):
                covered[k] = True
    seps, start = [], None
    for k, c in enumerate(covered + [True]):
        if not c and start is None:
            start = k
        elif c and start is not None:
            if (k - start) * step >= COLUMN_GAP * size:
                seps.append(left + (start + k) / 2 * step)
            start = None
    return seps


def split_by_header(header, rows, seps):
    """More separators where two header words fall in one column: the widest gap the rows leave
    clear between the two words' left edges (a narrow column of figures set close to the next)."""
    def col_of(x):
        return sum(1 for s_ in seps if s_ <= x)

    out = list(seps)
    words = header['words']
    for a, b in zip(words, words[1:]):
        if col_of((a[1] + a[2]) / 2) != col_of((b[1] + b[2]) / 2) or any(a[1] < s_ < b[1] for s_ in out):
            continue
        lo, hi = a[1], b[1] + 0.5
        spans = sorted((w[1], w[2]) for r in rows for w in r['words'] if w[2] > lo and w[1] < hi)
        best, x = None, lo
        for x0, x1 in spans:
            if x0 > x and (best is None or x0 - x > best[1] - best[0]):
                best = (x, x0)
            x = max(x, x1)
        if x < hi and (best is None or hi - x > best[1] - best[0]):
            best = (x, hi)
        if best and best[1] - best[0] >= 1.0:
            out.append((best[0] + best[1]) / 2)
    return sorted(out)


def header_cells(header, rows, seps):
    """Each header word to the column whose cells it overlaps most (by its middle where it
    overlaps none)."""
    n = len(seps) + 1
    grid = [cells_of(r, seps) for r in rows]
    extent = []
    for c in range(n):
        ws = [w for g in grid for w in g[c]]
        extent.append((min(w[1] for w in ws), max(w[2] for w in ws)) if ws else None)
    out = [[] for _ in range(n)]
    for w in header['words']:
        overlap = [(min(w[2], e[1]) - max(w[1], e[0]), c) for c, e in enumerate(extent) if e]
        best = max(overlap) if overlap else (0, 0)
        out[best[1] if best[0] > 0 else cells_of({'words': [w]}, seps).index([w])].append(w)
    return out


def cells_of(l, seps):
    edges = [float('-inf')] + seps + [float('inf')]
    out = [[] for _ in range(len(seps) + 1)]
    for w in l['words']:
        mid = (w[1] + w[2]) / 2
        out[next(i for i in range(len(out)) if edges[i] <= mid < edges[i + 1])].append(w)
    return out


def aligned(col):
    """The cells of a column that line up with no other: left, right, centre or the end of the
    first word (as entry_text.read_text_table)."""
    ways = {'left': [w[0][1] for w in col], 'right': [w[-1][2] for w in col],
            'centre': [(w[0][1] + w[-1][2]) / 2 for w in col], 'figure': [w[0][2] for w in col],
            'decimal': [whole_end(w[0]) for w in col]}
    lines = {}
    for way, xs in ways.items():
        best = max(xs, key=lambda x: sum(1 for y in xs if abs(x - y) <= ALIGN_TOLERANCE))
        if sum(1 for y in xs if abs(best - y) <= ALIGN_TOLERANCE) >= 2:
            lines[way] = best
    return [k for k in range(len(col)) if not any(abs(ways[way][k] - x) <= ALIGN_TOLERANCE for way, x in lines.items())]


def read_table(spec, lines, report, vocab):
    """One table's lines (title first) -> (groups, notes, failures). A group is
    {'heading', 'columns', 'rows': [cells]}; notes are {number: text}."""
    first_word = spec.get('header_starts', 'TL')
    group_size = spec.get('group_size', 11.0)
    title = lines[0]
    failures = []
    parts = []                      # [header line, [(group line, [row lines])]]
    notes_lines = []
    in_notes = False
    prev_group = False
    for l in lines[1:]:
        text = plain(l['text']).strip()
        is_group = False
        if in_notes:
            notes_lines.append(l)
        elif abs(l['size'] - group_size) < 0.3 and l['bold'] and text in ('Notes',) + tuple(spec.get('notes_headings', ())):
            in_notes = True
        elif abs(l['size'] - group_size) < 0.3 and l['bold']:
            is_group = True
            if prev_group:
                # a group's heading carried onto a second line ("LAMPS (DX-4, Torch-2," / "or Lantern-1)")
                g, rs = parts[-1][1][-1]
                parts[-1][1][-1] = (dict(g, text=f'{g["text"]} {l["text"]}', spans=g['spans'] + l['spans'],
                                         words=g.get('words', []) + l.get('words', [])), rs)
            else:
                if not parts:
                    parts.append([None, []])
                parts[-1][1].append((l, []))
        elif text.startswith('Notes ') and abs(l['size'] - group_size) < 0.3:
            # "Notes" set on the line of the first note
            in_notes = True
            notes_lines.append(dict(l, text=text[len('Notes '):], words=l['words'][1:]))
        elif is_header(l, first_word):
            # a header printed under a group's heading, before its rows, heads that group too
            if parts and parts[-1][1] and not parts[-1][1][-1][1]:
                g = parts[-1][1].pop()
                if not parts[-1][1]:
                    parts.pop()
                parts.append([l, [g]])
            else:
                parts.append([l, []])
        else:
            if not parts or not parts[-1][1]:
                failures.append(f'a row before any group: {l["text"][:60]!r}')
                prev_group = False
                continue
            parts[-1][1][-1][1].append(l)
        prev_group = is_group
    for _, gs in parts:
        for g_line, rs in gs:
            if not rs:
                failures.append(f'the group {plain(g_line["text"])[:40]!r} has no rows')
    groups = []
    header = None
    # Groups under headers printed alike (the same words at the same places, page after page)
    # share their columns: a group whose rows leave a column empty (no row cites a note) still
    # has it. Their rows are pooled to find the columns.
    def header_key(h):
        return tuple((w[0], round(w[1] / 3)) for w in h['words'])

    pooled = {}
    for head_line, gs in parts:
        header = head_line or header
        if header is not None:
            pooled.setdefault(header_key(header), []).extend(r for _, rs in gs for r in rs)
    header = None
    for head_line, gs in parts:
        header = head_line or header
        if header is None:
            failures.append(f'no header row before the group {gs[0][0]["text"][:40]!r}' if gs else 'no header row')
            continue
        rows = [r for _, rs in gs for r in rs]
        if not rows:
            continue
        size = header['size']
        all_rows = pooled[header_key(header)]
        seps = split_by_header(header, all_rows, columns_of(header, all_rows, size))
        head_cells = header_cells(header, all_rows, seps)
        columns = [' '.join(w[0] for w in c) for c in head_cells]
        for k, c in enumerate(columns):
            if not c:
                failures.append(f'the header {header["text"]!r} has no word over column {k + 1}')
        # Two header words over one column: its cells run into each other from row to row, so no
        # blank parts them all. Each row is split at its widest space between the two words'
        # places (a lone cell goes to the word it sits nearer); the alignment check below then
        # tells whether that read the columns as the page sets them.
        grid = {id(r): cells_of(r, seps) for r in rows}
        while any(len(c) > 1 for c in head_cells):
            k = next(i for i, c in enumerate(head_cells) if len(c) > 1)
            a, b = head_cells[k][0], head_cells[k][1]
            for r in rows:
                ws = grid[id(r)][k]
                if len(ws) >= 2:
                    gaps = [(ws[i + 1][1] - ws[i][2], i) for i in range(len(ws) - 1)]
                    cut = max(gaps)[1] + 1
                elif ws:
                    mid = (ws[0][1] + ws[0][2]) / 2
                    cut = 1 if abs(mid - (a[1] + a[2]) / 2) <= abs(mid - (b[1] + b[2]) / 2) else 0
                else:
                    cut = 0
                grid[id(r)] = grid[id(r)][:k] + [ws[:cut], ws[cut:]] + grid[id(r)][k + 1:]
            head_cells = head_cells[:k] + [[a], head_cells[k][1:]] + head_cells[k + 1:]
            seps = seps[:k] + [(a[2] + b[1]) / 2] + seps[k:]
            report.setdefault('columns_split_by_row', []).append(f'{plain(title["text"])}: {a[0]} / {b[0]}')
        columns = [' '.join(w[0] for w in c) for c in head_cells]
        # a line that carries on a row's cells (a damage that does not fit on one line): nothing
        # in its first two columns, and the row before it has its own first column
        merged_rows = []
        for r in rows:
            cells = grid[id(r)]
            if merged_rows and not cells[0] and len(cells) > 1 and not cells[1] and \
                    any(cells[2:]) and merged_rows[-1][1]:
                merged_rows[-1][0].append(r)
            else:
                merged_rows.append(([r], bool(cells[0])))
        for k in range(len(seps) + 1):
            col = [grid[id(r)][k] for r in rows if grid[id(r)][k]]
            if len(col) >= 2:
                for j in aligned(col):
                    failures.append(f'in column {k + 1} ({columns[k]}), {" ".join(w[0] for w in col[j])!r} does not '
                                    f'line up with the other cells')
        by_first = {id(rs[0]): rs for rs, _ in merged_rows}
        for g_line, rs in gs:
            out_rows = []
            for r in rs:
                if id(r) not in by_first:
                    continue                       # a carried-on line, joined to its row
                parts_ = [grid[id(x)] for x in by_first[id(r)]]
                row = [' '.join(' '.join(w[0] for w in p_[k]) for p_ in parts_ if p_[k]) for k in range(len(seps) + 1)]
                if not row[0] and not out_rows:
                    failures.append(f'{g_line["text"][:30]!r}: a row with nothing in its first column opens the group: '
                                    f'{r["text"][:50]!r}')
                out_rows.append(row)
            groups.append({'heading': plain(g_line['text']).strip(), 'heading_marked': marked(g_line),
                           'columns': columns, 'rows': out_rows})
    notes = {}
    order = []
    for l in notes_lines:
        m = NOTE.match(plain(l['text']))
        if m:
            order.append([m.group(1), [marked(l)]])
        elif order:
            order[-1][1].append(marked(l))
        else:
            order.append(['', [marked(l)]])       # a note for the whole table, before the numbered ones
    for number, parts_ in order:
        notes[number] = join_lines(parts_, report, f'tables/{slugify(plain(title["text"]))}', vocab)
    return groups, notes, failures


def table_end(lines, i, spec):
    """Where a table that starts at lines[i] (its title) ends: at a heading the size of the title
    or larger, or a line of another box, once past the title; at the first such after its notes."""
    title = lines[i]
    stop = spec.get('until')
    for j in range(i + 1, len(lines)):
        l = lines[j]
        if stop and l['page'] == stop['page'] and plain(l['text']).strip() == stop['text']:
            return j
        if l.get('heading') and l['size'] >= title['size'] - 0.3:
            return j
        if l.get('box') and l.get('box') != title.get('box'):
            return j
    return len(lines)


def take_tables(lines, plan, report, vocab, source, chapter):
    """Take the plan's equipment tables out of `lines`. Returns (the other lines, entries as
    (category, entry))."""
    specs = plan.get('equipment_tables', [])
    entries, items, table_notes = [], {}, {}
    taken = set()
    for spec in specs:
        i = next((k for k, l in enumerate(lines) if l['page'] == spec['page'] and
                  plain(l['text']).strip() == spec['title'] and id(l) not in taken), None)
        if i is None:
            report['errors'].append(f'plan equipment table {spec["title"]!r}: no such title on p{spec["page"]}')
            continue
        j = table_end(lines, i, spec)
        region = lines[i:j]
        taken |= {id(l) for l in region}
        groups, notes, failures = read_table(spec, region, report, vocab)
        name = spec.get('name', plain(region[0]['text']).strip())
        table_notes[name] = notes
        report.setdefault('equipment_tables', []).append({
            'title': name, 'page': spec['page'], 'pages': sorted({l['page'] for l in region}),
            'groups': len(groups), 'rows': sum(len(g['rows']) for g in groups), 'notes': len(notes), 'failures': failures})
        if failures:
            report['errors'].append(f'equipment table {name!r} (p{spec["page"]}) was not read: ' + '; '.join(failures[:6]))
            continue
        # the whole table
        content = []
        for g in groups:
            content.append({'type': 'heading', 'level': 3, 'text': g['heading']})
            content.append({'type': 'table', 'title': '', 'columns': g['columns'], 'rows': g['rows'],
                            'data': table_data(g['columns'], g['rows'], report, f'tables/{slugify(name)}')})
        if notes:
            content.append({'type': 'heading', 'level': 3, 'text': 'Notes'})
            content.append({'type': 'list', 'ordered': False, 'items': [notes[n] for n in notes], 'keys': list(notes)})
        entries.append(('tables', {'slug': slugify(name), 'name': name, 'source': source, 'chapter': chapter,
                                   'section': spec.get('section', name), 'page': region[0]['page'],
                                   'fields': {'kind': 'equipment', 'about': spec.get('about', name)},
                                   'level': 2, 'content': content}))
        # each item
        for g in groups:
            keys = [slugify(c).replace('-', '_') or f'column_{k + 1}' for k, c in enumerate(g['columns'])]
            current = None
            for row in g['rows']:
                if row[0]:
                    item_name = row[spec.get('name_column', 1)]
                    slug = slugify(item_name)
                    current = items.get(slug)
                    if current is None:
                        first = dict(zip(keys, row))
                        fields = {'kind': spec['kind'], 'group': [g['heading']]}
                        fields.update({k: v for k, v in first.items() if v and k != keys[spec.get('name_column', 1)]})
                        current = {'slug': slug, 'name': item_name, 'source': source, 'chapter': chapter,
                                   'section': name, 'page': region[0]['page'], 'fields': fields, 'level': 2,
                                   'content': [], '_rows': [], '_tables': [], '_notes': []}
                        items[slug] = current
                        entries.append(('equipment', current))
                    elif g['heading'] not in current['fields']['group']:
                        current['fields']['group'].append(g['heading'])
                    current['_tables'].append((name, g['heading'], g['columns']))
                    current['_rows'].append((name, g['heading'], row, g['columns']))
                elif current is not None:
                    current['_rows'].append((name, g['heading'], row, g['columns']))
                for cited in CITES.findall(row[-1] if g['columns'][-1] == 'Notes' else ''):
                    for n in re.split(r'\s*,\s*', cited):
                        if current is not None and n in notes and (name, n) not in current['_notes']:
                            current['_notes'].append((name, n))
    # each item's content: per table and group, its rows; then the notes it cites
    for slug, e in items.items():
        seen = []
        for table, heading, columns in e.pop('_tables'):
            if (table, heading) in seen:
                continue
            seen.append((table, heading))
            rows = [r for t, h, r, _ in e['_rows'] if (t, h) == (table, heading)]
            e['content'].append({'type': 'heading', 'level': 3, 'text': heading})
            e['content'].append({'type': 'table', 'title': '', 'columns': columns, 'rows': rows,
                                 'data': table_data(columns, rows, report, f'equipment/{slug}')})
        all_rows = e.pop('_rows')
        if len(all_rows) > 1:
            # every row, keyed by its own table's columns (a spear's melee and thrown rows differ)
            tables_ = {t for t, _, _, _ in all_rows}
            e['fields']['modes'] = []
            for t, _, r, columns in all_rows:
                keys = [slugify(c).replace('-', '_') or f'column_{k + 1}' for k, c in enumerate(columns)]
                mode = {k: v for k, v in zip(keys, r) if v}
                if len(tables_) > 1:
                    mode['table'] = t
                e['fields']['modes'].append(mode)
        cited = e.pop('_notes')
        if cited:
            e['content'].append({'type': 'list', 'ordered': False, 'items': [table_notes[t][n] for t, n in cited],
                                 'keys': [c[1] for c in cited]})
    return [l for l in lines if id(l) not in taken], entries
