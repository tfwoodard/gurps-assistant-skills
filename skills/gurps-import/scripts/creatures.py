"""Creature stat blocks, as the Basic Set prints them, for convert_traits.py's `creatures` sections.

A creature is a heading (its name), perhaps a description, then its stat block:

    ST 4; DX 14; IQ 4; HT 12.
    Will 10; Per 12; Speed 6.5; Dodge 9;
        Move 5 (Water Move 8).
    SM -2; 20 lbs.
    Traits: Night Vision 2; Wild Animal; ...
    Skills: Swimming-15.

The stat lines (the characteristic names in bold) start at the line opening "ST" and a number,
and run to the first labelled line. Their characteristics are read in printed order, split at
the semicolons and full stops between them (never inside brackets): `{"ST": "4", ...,
"Move": "5 (Water Move 8)", "SM": "-2", "Weight": "20 lbs."}`, each value as printed.
The weight is the one item printed without a name. A comma where the others print a semicolon
("Speed 7, Dodge 10") is read as one and reported; anything else is an error.

The labelled lines ("Traits:", "Skills:", "Traits and Skills:", "Cost:", the label in bold
italic) each run on over the lines hanging under them, and are kept as printed, in order. A
line after them that starts a paragraph of its own and has no label ends the stat block: the
text from there on is the creature's, after its profile.
"""
import re

from entry_text import join_lines, marked, plain, starts_with_label

NAMES = ('ST', 'DX', 'IQ', 'HT', 'HP', 'FP', 'Will', 'Per', 'Speed', 'Dodge', 'Move', 'SM', 'Parry', 'Block', 'DR')
NAME = '|'.join(NAMES)
STAT_START = re.compile(r'^ST\s+[\d+−-]')
ITEM = re.compile(r'^(?P<name>' + NAME + r')\s+(?P<value>\S.*)$', re.S)
WEIGHT = re.compile(r'^[\d,.]+\+?\s*(?:lbs?|tons?|oz)\.?$')
COMMA = re.compile(r',\s+(?=(?:' + NAME + r')\s)')


def is_stat_start(l):
    """True for the line that opens a stat block ("ST 4; DX 14; ...")."""
    return bool(STAT_START.match(plain(l['text'])))


def split_top(text):
    """Split a stat line at "; " and at ". " before a capital, never inside brackets."""
    parts, depth, cur, i = [], 0, '', 0
    while i < len(text):
        ch = text[i]
        depth += ch in '(['
        depth -= ch in ')]'
        if depth == 0 and (ch == ';' or (ch == '.' and re.match(r'\s+[A-Z]', text[i + 1:]))) and \
                re.match(r'\s', text[i + 1:i + 2] or ' '):
            parts.append(cur.strip())
            cur = ''
        else:
            cur += ch
        i += 1
    if cur.strip():
        parts.append(cur.strip())
    return parts


def read_stats(text, report, where):
    """A creature's stat lines, joined -> {name: value as printed}, in printed order; None when a
    part can't be read (an error in the report)."""
    stats, ok = {}, True
    for part in split_top(text):
        if WEIGHT.match(part):
            items = [('Weight', part)]
        else:
            m = ITEM.match(part)
            if not m:
                report['errors'].append(f'{where}: {part!r} in its stat lines is no characteristic '
                                        f'({", ".join(NAMES)}) and no weight')
                ok = False
                continue
            pieces = COMMA.split(part)
            if len(pieces) > 1:
                report.setdefault('stat_lines', []).append(
                    {'entry': where, 'text': part, 'read': 'a comma between two characteristics, read as the '
                                                           'semicolon the others print'})
            items = [(ITEM.match(p).group('name'), ITEM.match(p).group('value').strip()) for p in pieces]
        for name, value in items:
            if name != 'Weight':
                value = re.sub(r'\.$', '', value)      # the full stop that ends the printed line
            if name in stats:
                report['errors'].append(f'{where}: {name} is printed twice in its stat lines')
                ok = False
            stats[name] = value
    return stats if ok else None


def label_of(l):
    return next(sp for sp in l['spans'] if sp['text'].strip())['text'].strip()[:-1]


def stat_block(lines, report, where, vocab=None):
    """A creature's lines from its stat start on -> (profile block, fields, lines after it), or
    (None, None, lines) when the stat lines can't be read. `fields` holds `attributes` (the
    characteristics) and each labelled line's text under its label in snake case (`traits`,
    `skills`, `traits_and_skills`, `cost`)."""
    k = 0
    while k < len(lines) and not starts_with_label(lines[k]):
        k += 1
    stats = read_stats(join_lines([plain(l['text']) for l in lines[:k]], report, where), report, where)
    if stats is None:
        return None, None, lines
    runs = []                                  # [label, [marked line texts]]
    while k < len(lines):
        l = lines[k]
        if starts_with_label(l):
            label = label_of(l)
            text = re.sub(r'^\*{1,3}' + re.escape(label) + r':?\*{1,3}:?\s*', '', marked(l))
            runs.append([label, [text] if text else []])
        elif runs and not l.get('para') and not l.get('heading'):
            runs[-1][1].append(marked(l))      # a line hanging under the label
        else:
            break
        k += 1
    printed = [{'label': label, 'text': join_lines(parts, report, where, vocab)} for label, parts in runs]
    fields = {'attributes': stats}
    for p in printed:
        key = re.sub(r'\W+', '_', p['label'].lower()).strip('_')
        if key in fields or key == 'kind':
            report['errors'].append(f'{where}: the label {p["label"]!r} is printed twice in its stat block')
            continue
        fields[key] = plain(p['text'])
    report['left_out'].append({'page': lines[0]['page'], 'text': ' '.join(n for n in stats if n != 'Weight'),
                               'why': "a creature's characteristic names: kept as its profile's keys"})
    return {'type': 'profile', 'characteristics': stats, 'lines': printed}, fields, lines[k:]
