#!/usr/bin/env python3
"""Character sheets: a filled-in GURPS 4e character sheet (the Basic Set's form, front side), read
from its words' positions and fonts.

    character_sheets.py LAYOUT.json [--page N]       # print each sheet's reading, and what failed

pdf_layout.py gives a sheet page's words with their position, type size and font (`sheets`, from
the plan's `sheet_pages`). The form's printed labels are in the book's type; the values written in
are in another (the plan's `hand_font`, default FletchersHand, with its italic and bold: a word in
those keeps its emphasis, *not*). The form never moves, so its fields
are places on the page (FORM, in points from the page's top left): a value goes to the field its
middle falls in. A sheet is read only when the form's labels stand where FORM says (ANCHORS).

Fields: the header (name, player, point total, height, weight, size modifier, age, unspent points,
appearance); the attributes and secondary characteristics, each its value and the points in its
brackets (HP and FP their current value too); basic lift, damage, basic speed and move; the
encumbrance table; DR, parry, block; TL; and the lists: languages, cultural familiarities,
reaction modifiers (each under the form's label for it, Appearance or Status, and carried on over
the lines under it), advantages and perks, disadvantages and quirks, skills. A list's row is the
words on one baseline, its cells by column; a line set in under a row carries it on (a trait's
modifiers, a skill's specialty), its cells added to the row's. A line in a list that starts with a
note mark (`*`, `†`) is a note under the sheet (`notes`). Every value is kept as written.

Nothing is guessed: a written word in no field, a list line that carries on no row, or a label
missing from its place refuses the sheet (`failures`), and nothing of it is used. The printed
labels are the form, not the character: read_sheet() returns them apart, for the word count.
"""
import argparse
import json
import sys

HAND_FONT = 'FletchersHand'
TOLERANCE = 3.0       # points: how far a printed label may stand from its place in FORM
SET_IN = 5.0          # points: a list line starting this far right of the list's names carries a row on
LINE = 3.0            # points: words whose tops are this close stand on one line
NOTE_MARKS = ('*', '†', '‡')

# printed labels that fix the form's place: the top of the sheet never moves (text, x0, top)
ANCHORS = [('Name', 209, 23), ('Player', 382, 23), ('Appearance', 209, 55), ('ST', 66, 92), ('HP', 186, 92),
           ('FP', 190, 202), ('Languages', 331, 77), ('ENCUMBRANCE', 87, 264)]
# labels whose place moves with what is written above them (a longer list of languages pushes the
# right-hand boxes down; the lists' boxes are as long as their lists): found on the page, once each
MOVING = ['TL:', 'Cultural', 'DR', 'PARRY', 'BLOCK', 'Reaction', 'ADVANTAGES', 'DISADVANTAGES', 'SKILLS']
MIDDLE = 306          # points: a list's box whose heading starts left of this is in the left half
BOTTOM = 752          # points: the foot of the form (notes are written down to it)

# fields of the fixed top: name -> (x0, x1, top, bottom)
FIELDS = {
    'name': (230, 380, 10, 32), 'player': (405, 494, 10, 32), 'point_total': (540, 615, 10, 32),
    'height': (218, 264, 33, 48), 'weight': (276, 322, 33, 48), 'size_modifier': (378, 419, 33, 48),
    'age': (435, 489, 33, 48), 'unspent_points': (540, 615, 33, 48), 'appearance': (255, 615, 49, 65),
    'basic_lift': (140, 178, 228, 242), 'damage_thrust': (236, 272, 228, 242), 'damage_swing': (286, 330, 228, 242),
    'basic_speed': (135, 171, 242, 256), 'basic_speed_points': (171, 191, 242, 256),
    'basic_move': (255, 303, 242, 256), 'basic_move_points': (303, 323, 242, 256),
}
ATTRIBUTES = [('ST', 'HP', 86, 114), ('DX', 'Will', 122, 150), ('IQ', 'Per', 158, 186), ('HT', 'FP', 194, 222)]
PRIMARY = {'value': (88, 134), 'points': (134, 162)}
SECONDARY = {'value': (212, 254), 'current': (254, 290), 'points': (290, 320)}
ENCUMBRANCE = [('None (0)', 274, 287), ('Light (1)', 287, 300), ('Medium (2)', 300, 313), ('Heavy (3)', 313, 326),
               ('X-Heavy (4)', 326, 340)]
ENC_COLUMNS = {'basic_lift': (148, 190), 'move': (224, 259), 'dodge': (294, 326)}
# a list's columns in each half of the sheet, as (name, x0, x1); the first is the row's name
HALF = {'left': (60, 326), 'right': (328, 595)}
COLUMNS = {
    'languages': [('name', 330, 458), ('spoken', 458, 528), ('written', 528, 560), ('points', 560, 595)],
    'cultural_familiarities': [('name', 400, 560), ('points', 560, 595)],
    'reaction_modifiers': [('text', 386, 615)],
    ('traits', 'left'): [('name', 60, 292), ('points', 292, 326)],
    ('traits', 'right'): [('name', 328, 558), ('points', 558, 595)],
    ('skills', 'right'): [('name', 328, 465), ('level', 465, 505), ('relative_level', 505, 556), ('points', 556, 595)],
    ('skills', 'left'): [('name', 60, 200), ('level', 200, 240), ('relative_level', 240, 290), ('points', 290, 326)],
}
SECTIONS = {'ADVANTAGES': 'advantages', 'DISADVANTAGES': 'disadvantages', 'SKILLS': 'skills'}


def place(words, failures):
    """The places of the moving labels, and from them the boxes of the fields and lists below the
    fixed top: (fields, lists), each name -> box, a list's -> (box, columns)."""
    at = {}
    for t in MOVING:
        hits = [w for w in words if w['text'] == t]
        if len(hits) != 1:
            failures.append(f"the form's label {t!r} is on the sheet {len(hits)} times, not once")
        else:
            at[t] = hits[0]
    if failures:
        return {}, {}
    top = lambda t: at[t]['top']
    fields = {'tl': (400, 560, top('TL:') - 3, top('TL:') + 9), 'tl_points': (560, 595, top('TL:') - 3, top('TL:') + 9),
              'dr': (322, 388, top('DR') + 9, top('PARRY') - 2), 'parry': (322, 388, top('PARRY') + 8, top('BLOCK') - 2),
              'block': (322, 388, top('BLOCK') + 8, top('BLOCK') + 32)}
    heads = sorted(((at[t], name) for t, name in SECTIONS.items()), key=lambda x: x[0]['top'])
    half = lambda w: 'left' if w['x0'] < MIDDLE else 'right'
    lists = {'languages': ((330, 595, 86, top('TL:') - 3), COLUMNS['languages']),
             'cultural_familiarities': ((400, 595, top('Cultural') + 9, top('Reaction') - 2),
                                        COLUMNS['cultural_familiarities'])}
    below = [h for h, _ in heads if half(h) == 'right' and h['top'] > top('Reaction')]
    lists['reaction_modifiers'] = ((386, 615, top('Reaction') + 9, (min(h['top'] for h in below) - 3) if below else BOTTOM),
                                   COLUMNS['reaction_modifiers'])
    for h, name in heads:
        side = half(h)
        later = [g['top'] for g, _ in heads if half(g) == side and g['top'] > h['top']]
        first = h['top'] + 9
        if name == 'skills':          # the box's own header row: Name, Level, Relative Level
            sub = [w for w in words if w['text'] == 'Relative' and abs(w['top'] - h['top']) < 30]
            first = (sub[0]['top'] + 9) if sub else first
        x0, x1 = HALF[side]
        lists[name] = ((x0, x1, first, (min(later) - 3) if later else BOTTOM),
                       COLUMNS[('skills' if name == 'skills' else 'traits', side)])
    return fields, lists


def inside(w, box):
    x0, x1, top, bottom = box
    cx, cy = (w['x0'] + w['x1']) / 2, (w['top'] + w['bottom']) / 2
    return x0 <= cx < x1 and top <= cy < bottom


def lines_of(words):
    """Words -> lines (lists of words left to right), by their feet (a written word and the
    printed one beside it stand on one line though their sizes differ)."""
    out = []
    for w in sorted(words, key=lambda w: (w['top'], w['x0'])):
        if out and abs(w['bottom'] - out[-1][0]['bottom']) <= LINE:
            out[-1].append(w)
        else:
            out.append([w])
    return [sorted(l, key=lambda w: w['x0']) for l in out]


def text(words):
    """Words as one value, in reading order. A run of words written in the hand's italic or bold
    keeps its emphasis, as entries mark it (*not*); words that touch (each font's words are made
    apart, so a bracket and the word in it are two) join with no space."""
    def mark(w):
        f = w['font'].lower()
        return '**' if 'bold' in f else '*' if 'italic' in f or 'oblique' in f else ''
    out, prev, open_ = '', None, ''
    for w in sorted(words, key=lambda w: (round(w['top'] / LINE), w['x0'])):
        m = mark(w)
        touching = prev is not None and abs(w['top'] - prev['top']) <= LINE and w['x0'] - prev['x1'] < 0.15 * w['size']
        if m != open_:
            out += open_
            open_ = ''
        # a name broken before its /TL runs on with no space ("Electronics Repair" / "/TL7 (Sonar)")
        sep = '' if prev is None or touching or w['text'].startswith('/') else ' '
        if m and not open_:
            out += sep + m
            open_ = m
            sep = ''
        out += sep + w['text']
        prev = w
    return out + open_


def read_list(name, words, columns, failures, notes):
    rows = []
    for line in lines_of(words):
        if line[0]['text'].startswith(NOTE_MARKS) and name in ('skills', 'advantages', 'disadvantages'):
            notes.append(text(line))
            continue
        cells = {c: [w for w in line if c_x0 <= (w['x0'] + w['x1']) / 2 < c_x1] for c, c_x0, c_x1 in columns}
        first = min(w['x0'] for w in line)
        names = min((w['x0'] for w in cells[columns[0][0]]), default=None)
        carries = rows and (names is None or names > min(r['_left'] for r in rows) + SET_IN)
        if carries:
            for c, ws in cells.items():
                rows[-1]['_cells'][c] += ws
            continue
        if names is None:
            failures.append(f'{name}: a line with no {columns[0][0]} and no row above it: {text(line)!r}')
            continue
        rows.append({'_left': first, '_cells': {c: list(ws) for c, ws in cells.items()}})
    return [{c: text(ws) for c, ws in r['_cells'].items() if ws} for r in rows]


def read_reactions(words, labels):
    """The reaction modifiers: each starts on a line the form labels (Appearance, Status...); a
    line with no label carries the one above it on."""
    rows = []
    for line in lines_of(words):
        label = [w for w in labels if abs(w['bottom'] - line[0]['bottom']) <= LINE and w['x1'] <= line[0]['x0'] + 1]
        if label or not rows:
            rows.append({'label': ' '.join(w['text'] for w in label), 'words': list(line)} if label else {'words': list(line)})
        else:
            rows[-1]['words'] += line
    return [dict({'label': r['label']} if r.get('label') else {}, text=text(r['words'])) for r in rows]


def read_sheet(words, hand_font=HAND_FONT):
    """A sheet page's words -> (sheet, labels, failures). `sheet` holds every written value by
    field; `labels` the form's printed words (for the word count)."""
    failures = []
    is_hand = lambda w: w['font'].startswith(hand_font)       # its italic and bold too
    labels_all = [w for w in words if not is_hand(w) and not w.get('furniture')]
    for t, x, y in ANCHORS:
        if not any(w['text'] == t and abs(w['x0'] - x) <= TOLERANCE and abs(w['top'] - y) <= TOLERANCE
                   for w in labels_all):
            failures.append(f'the form\'s label {t!r} is not at ({x}, {y}): not the character sheet this reader knows')
    if failures:
        return {}, [], failures
    moving_fields, lists = place(labels_all, failures)
    if failures:
        return {}, [], failures
    page = [w for w in words if not w.get('furniture')]
    hand = [w for w in page if is_hand(w)]
    labels = [w for w in page if not is_hand(w)]
    placed = set()
    sheet = {}

    def take(box):
        got = [w for w in hand if id(w) not in placed and inside(w, box)]
        placed.update(id(w) for w in got)
        return got

    for f, box in list(FIELDS.items()) + list(moving_fields.items()):
        got = take(box)
        if got:
            sheet[f] = text(got)
    attributes = {}
    for primary, secondary, top, bottom in ATTRIBUTES:
        a = {k: text(ws) for k, (x0, x1) in PRIMARY.items() if (ws := take((x0, x1, top, bottom)))}
        b = {k: text(ws) for k, (x0, x1) in SECONDARY.items() if (ws := take((x0, x1, top, bottom)))}
        if a:
            attributes[primary] = a
        if b:
            attributes[secondary] = b
    sheet['attributes'] = attributes
    enc = []
    for level, top, bottom in ENCUMBRANCE:
        row = {k: text(ws) for k, (x0, x1) in ENC_COLUMNS.items() if (ws := take((x0, x1, top, bottom)))}
        if row:
            enc.append(dict(level=level, **row))
    if enc:
        sheet['encumbrance'] = enc
    notes = []
    for name, (box, columns) in lists.items():
        got = take(box)
        if name == 'reaction_modifiers':
            rows = read_reactions(got, [w for w in labels_all if inside(w, box) and w['text'].strip('_')])
        else:
            rows = read_list(name, got, columns, failures, notes)
        if rows:
            sheet[name] = rows
    if notes:
        sheet['notes'] = notes
    left = [w for w in hand if id(w) not in placed]
    for w in left:
        failures.append(f'a written word in no field of the form: {w["text"]!r} at ({w["x0"]}, {w["top"]})')
    return sheet, labels, failures


# the sheet as the entry's text: (field, the form's label for it)
HEADER = [('name', 'Name'), ('player', 'Player'), ('point_total', 'Point Total'), ('height', 'Height'),
          ('weight', 'Weight'), ('size_modifier', 'Size Modifier'), ('age', 'Age'),
          ('unspent_points', 'Unspent Points'), ('appearance', 'Appearance'), ('basic_lift', 'Basic Lift')]
AFTER = [('dr', 'DR'), ('parry', 'Parry'), ('block', 'Block')]
TABLES = [('languages', 'Languages', [('name', 'Language'), ('spoken', 'Spoken'), ('written', 'Written'),
                                      ('points', 'Points')]),
          ('cultural_familiarities', 'Cultural Familiarities', [('name', 'Culture'), ('points', 'Points')]),
          ('reaction_modifiers', 'Reaction Modifiers', [('label', 'Reaction'), ('text', 'Modifiers')]),
          ('advantages', 'Advantages and Perks', [('name', 'Trait'), ('points', 'Points')]),
          ('disadvantages', 'Disadvantages and Quirks', [('name', 'Trait'), ('points', 'Points')]),
          ('skills', 'Skills', [('name', 'Skill'), ('level', 'Level'), ('relative_level', 'Relative Level'),
                                ('points', 'Points')])]
ORDER = ['ST', 'DX', 'IQ', 'HT', 'HP', 'Will', 'Per', 'FP']


def table(title, columns, rows):
    """A table block, its `data` keyed by column (an empty cell is a field the sheet leaves blank:
    nothing is filled down)."""
    keys = [c.lower().replace(' ', '_') for c in columns]
    return {'type': 'table', 'title': title, 'columns': columns, 'rows': rows,
            'data': [{k: v for k, v in zip(keys, r) if v} for r in rows]}


def with_points(value, points):
    return f'{value} [{points}]' if points else value


def sheet_blocks(sheet, level=3):
    """The sheet as blocks of an entry's text: a heading, then its fields and lists as tables."""
    rows = [[label, sheet[k]] for k, label in HEADER if sheet.get(k)]
    if sheet.get('damage_thrust') or sheet.get('damage_swing'):
        rows.append(['Damage', ', '.join(f'{n} {sheet[k]}' for k, n in (('damage_thrust', 'Thr'), ('damage_swing', 'Sw'))
                                         if sheet.get(k))])
    for k, label in (('basic_speed', 'Basic Speed'), ('basic_move', 'Basic Move'), ('tl', 'TL')):
        if sheet.get(k):
            rows.append([label, with_points(sheet[k], sheet.get(f'{k}_points'))])
    rows += [[label, sheet[k]] for k, label in AFTER if sheet.get(k)]
    out = [{'type': 'heading', 'level': level, 'text': 'Character Sheet'}, table('', ['Field', 'As Written'], rows)]
    att = sheet.get('attributes', {})
    out.append(table('Attributes', ['Attribute', 'Value', 'Current', 'Points'],
                     [[a, att[a].get('value', ''), att[a].get('current', ''), att[a].get('points', '')]
                      for a in ORDER if a in att]))
    if sheet.get('encumbrance'):
        out.append(table('Encumbrance', ['Level', 'Basic Lift', 'Move', 'Dodge'],
                         [[r['level'], r.get('basic_lift', ''), r.get('move', ''), r.get('dodge', '')]
                          for r in sheet['encumbrance']]))
    for key, title, cols in TABLES:
        if sheet.get(key):
            out.append(table(title, [c for _, c in cols], [[r.get(k, '') for k, _ in cols] for r in sheet[key]]))
    out += [{'type': 'paragraph', 'text': n} for n in sheet.get('notes', [])]
    return out


def attach_sheets(entries, plan, layout, report):
    """The plan's `sheets` ({"page", "entry"}): each sheet page read (read_sheet) into its entry:
    the reading in the entry's fields as `sheet` (with `sheet_page`), and as text, under a heading
    "Character Sheet", in its content. The form's printed words go to the report's `left_out`, for
    the word count. A sheet that fails, a spec naming no sheet page or no entry, and a sheet page
    no spec names are errors."""
    specs = plan.get('sheets', [])
    pages = {s['page']: s for s in layout.get('sheets', [])}
    by_ref = {f'{c}/{e["slug"]}': e for c, e in entries}
    hand = plan.get('hand_font', HAND_FONT)
    for spec in specs:
        where = f'sheet p{spec["page"]} ({spec["entry"]})'
        if spec['page'] not in pages:
            report['errors'].append(f"{where}: p{spec['page']} is not one of the layout's sheet pages")
            continue
        e = by_ref.get(spec['entry'])
        if e is None:
            report['errors'].append(f'{where}: {spec["entry"]} is no entry of the chapter')
            continue
        sheet, labels, failures = read_sheet(pages[spec['page']]['words'], hand)
        report.setdefault('sheets', []).append(
            {'page': spec['page'], 'entry': spec['entry'], 'failures': failures,
             'lists': {k: len(v) for k, v in sheet.items() if isinstance(v, list)}})
        if failures:
            report['errors'].append(f'{where}: the sheet was not read: ' + '; '.join(failures[:5]) +
                                    (f' (and {len(failures) - 5} more)' if len(failures) > 5 else ''))
            continue
        e['fields']['sheet'] = sheet
        e['fields']['sheet_page'] = spec['page']
        e['content'] += sheet_blocks(sheet, (e.get('level') or 2) + 1)
        report['left_out'].append({'page': spec['page'], 'text': ' '.join(w['text'] for w in labels),
                                   'why': "the character sheet's printed form (its labels and rules)"})
    named = {s['page'] for s in specs}
    for p_ in sorted(set(pages) - named):
        report['errors'].append(f"sheet page p{p_} is read into no entry: give it one in the plan's sheets")


def read_points_summary(lines):
    """A character's Points Summary panel (its lines, and the lines of the panel its points are
    printed in, when that is another) -> (rows as [category, points], joins, failures). A category's
    label may run on to a second line, set in; its points stand in brackets on the label's line (or
    on its second line), their figures spaced apart ("[ 2 5 8 ]": read as 258, each such join given
    in `joins` as (printed, read), for the word count). Empty brackets are a category with no points."""
    labels, values, failures, joins = [], [], [], []
    for l in sorted(lines, key=lambda l: (l['top'], l['x0'])):
        ws = l['words']
        k = next((i for i, w in enumerate(ws) if w[0].startswith('[')), len(ws))
        if ws[:k]:
            labels.append((l['top'], ' '.join(w[0] for w in ws[:k]), ws[0][1]))
        if ws[k:]:
            values.append((l['top'], ws[k:]))
    if not labels or labels[0][1].upper() != 'POINTS SUMMARY':
        return [], [], ['the panel does not start with its title, POINTS SUMMARY']
    labels = labels[1:]
    left = min((x for _, _, x in labels), default=0)
    cats = []
    for top, t, x in labels:
        if cats and x > left + 3:                 # a label run on to a second line, set in
            joiner = '' if cats[-1]['text'].endswith('/') else ' '
            cats[-1]['text'] += joiner + t
            cats[-1]['tops'].append(top)
        else:
            cats.append({'text': t, 'tops': [top]})
    rows = [[c['text'], ''] for c in cats]
    for top, ws in values:
        printed = ' '.join(w[0] for w in ws)
        read = ''.join(w[0] for w in ws).strip('[] ')
        if not (printed.startswith('[') and printed.endswith(']')):
            failures.append(f'points not in brackets: {printed!r}')
            continue
        i = next((i for i, c in enumerate(cats) if any(abs(t - top) <= LINE for t in c['tops'])), None)
        if i is None:
            failures.append(f'points {printed!r} beside no category')
            continue
        rows[i][1] = read
        if len(printed.strip('[] ').split()) > 1:
            joins.append((printed, read))
    return rows, joins, failures


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('layout')
    ap.add_argument('--page', type=int)
    a = ap.parse_args(argv)
    with open(a.layout, encoding='utf-8') as f:
        doc = json.load(f)
    bad = 0
    for s in doc.get('sheets', []):
        if a.page and s['page'] != a.page:
            continue
        sheet, labels, failures = read_sheet(s['words'])
        print(json.dumps({'page': s['page'], 'sheet': sheet, 'labels': len(labels), 'failures': failures},
                         ensure_ascii=False, indent=1))
        bad += bool(failures)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
