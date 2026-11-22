#!/usr/bin/env python3
"""Read a GURPS Character Assistant 5 character file (.gca5).

    gca5.py list  FILE.gca5                      # the characters in the file
    gca5.py read  FILE.gca5 [--character NAME] [--out record.json]
    gca5.py sheet FILE.gca5 [--character NAME] [--out sheet.md]

The character file is the character's record, and GCA does the arithmetic
(library-layout.md §9, docs/adr/0006). This script only reads what GCA saved:
every score, level and point cost it prints is the file's own. The one thing
it adds up is each kind of trait's points, which it labels as its own sum.

The file is XML in the `gca5` namespace, laid out as GCA's schema `gca5.xsd`
says: a `character` with `vitals`, a `campaign` block (point totals and the
log), and `traits` grouped by kind, each `trait` with its name, name
extension, points, level or score, `calcs` (how GCA got there), `ref` (page,
notes, the data file tags it was built from), modifiers and bonuses.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET

KINDS = ('attributes', 'cultures', 'languages', 'advantages', 'perks', 'features', 'disadvantages', 'quirks',
         'skills', 'spells', 'equipment', 'templates')
MODE_FIELDS = ('name', 'chardamage', 'chardamtype', 'charreach', 'charparry', 'charparryscore', 'characc',
               'charrangehalfdam', 'charrangemax', 'charrof', 'charshots', 'charrcl', 'charbulk', 'charminst',
               'charskillused', 'charskillscore')


def strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return root


def text(el, path, default=''):
    found = el.find(path) if el is not None else None
    return (found.text or '').strip() if found is not None and found.text else default


def number(s):
    """A saved number as int or float; anything else as written."""
    try:
        f = float(s)
    except (TypeError, ValueError):
        return s
    return int(f) if f == int(f) else f


def party_paths(path):
    """The character files a party file (.gca5party) names: one path per line, before its
    <gmconsole> block. None when the file isn't one."""
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        head = f.read()
    if head.lstrip().startswith('<?xml') or head.lstrip().startswith('<gca5'):
        return None
    return [ln.strip() for ln in head.split('<gmconsole', 1)[0].splitlines() if ln.strip()]


def characters(path):
    try:
        root = strip_ns(ET.parse(path).getroot())
    except ET.ParseError as e:
        if party_paths(path) is not None:
            raise SystemExit('this is a party file: it names character files and holds none (use `list`)')
        raise SystemExit(f'not a GCA character file: {e}')
    return root.findall('character')


def pick(chars, name):
    if not chars:
        raise SystemExit('no character in this file')
    if name is None:
        if len(chars) > 1:
            names = ', '.join(text(c, 'name') for c in chars)
            raise SystemExit(f'this file holds {len(chars)} characters ({names}): name one with --character')
        return chars[0]
    hits = [c for c in chars if text(c, 'name').lower() == name.lower()]
    if len(hits) != 1:
        raise SystemExit(f'{name!r}: {len(hits)} characters by that name in this file')
    return hits[0]


def modifiers(trait):
    out = []
    for m in trait.findall('modifiers/modifier'):
        name = text(m, 'name')
        ext = text(m, 'nameext')
        out.append({'name': f'{name} ({ext})' if ext else name, 'value': text(m, 'value') or text(m, 'cost'),
                    'level': number(text(m, 'level')) if text(m, 'level') else None})
    return out


def modes(trait):
    """A weapon's attack modes as GCA saved them for this character. Current files have one
    `attackmode` per mode; older ones have a single `weaponmodesdata` block whose values run the
    modes together with `|`, kept here as saved."""
    out = []
    for m in trait.findall('attackmodes/attackmode'):
        mode = {f: text(m, f) for f in MODE_FIELDS if text(m, f)}
        if mode:
            out.append(mode)
    old = trait.find('weaponmodesdata')
    if not out and old is not None:
        mode = {f: text(old, f) for f in MODE_FIELDS if f != 'name' and text(old, f)}
        if text(old, 'mode'):
            mode['name'] = text(old, 'mode')
        if mode:
            out.append(mode)
    return out


def read_trait(t, kind):
    name, ext = text(t, 'name'), text(t, 'nameext')
    out = {'id': t.get('idkey', ''), 'name': name, 'full_name': f'{name} ({ext})' if ext else name}
    if ext:
        out['nameext'] = ext
    for f in ('points', 'score', 'level', 'count', 'cost', 'weight'):
        if text(t, f):
            out[f] = number(text(t, f))
    if text(t, 'type'):
        out['type'] = text(t, 'type')
    if kind in ('skills', 'spells') and text(t, 'stepoff'):
        step = number(text(t, 'step', '0'))
        out['relative'] = text(t, 'stepoff') + (f'{step:+}' if step else '+0')
    for f in ('page', 'usernotes', 'notes', 'itemnotes', 'mainwin'):
        if text(t, f'ref/{f}'):
            out[f] = number(text(t, f'ref/{f}')) if f == 'mainwin' else text(t, f'ref/{f}')
    if text(t, 'parentkey'):
        out['parent'] = text(t, 'parentkey')
    if text(t, 'hide') not in ('', '0'):
        out['hidden'] = True
    mods = modifiers(t)
    if mods:
        out['modifiers'] = mods
    md = modes(t)
    if md:
        out['modes'] = md
    return out


def read(char):
    """A character element -> a plain record of what GCA saved."""
    rec = {'name': text(char, 'name'), 'player': text(char, 'player'), 'bodytype': text(char, 'bodytype'),
           'saved_by': text(char, 'author/version'),
           'vitals': {f: text(char, f'vitals/{f}') for f in ('race', 'height', 'weight', 'age', 'appearance')
                      if text(char, f'vitals/{f}')},
           'built_with': {'library': text(char, 'library/name'),
                          'books': [(b.text or '').strip() for b in char.findall('library/book')]},
           'campaign': {f: number(text(char, f'campaign/{f}'))
                        for f in ('name', 'basetl', 'basepoints', 'disadlimit', 'quirklimit', 'loggedpoints',
                                  'otherpoints', 'totalpoints', 'totalmoney') if text(char, f'campaign/{f}')},
           'log': [{'date': text(e, 'entrydate'), 'campaign_date': text(e, 'campaigndate'),
                    'points': number(text(e, 'charpoints', '0')), 'money': number(text(e, 'charmoney', '0')),
                    'caption': text(e, 'caption'), 'notes': text(e, 'notes')}
                   for e in char.findall('campaign/logentries/logentry')],
           'description': text(char, 'description'), 'notes': text(char, 'notes'), 'traits': {}}
    for kind in KINDS:
        rec['traits'][kind] = [read_trait(t, kind) for t in char.findall(f'traits/{kind}/trait')]
    # the only arithmetic here: each kind's saved points, added up
    rec['points_summed_here'] = {k: sum(t.get('points', 0) for t in v if isinstance(t.get('points', 0), (int, float)))
                                 for k, v in rec['traits'].items() if any('points' in t for t in v)}
    rec['points_summed_here']['total'] = sum(rec['points_summed_here'].values())
    return rec


# --- the readable sheet ----------------------------------------------------------------------

def pts(t):
    return f' [{t["points"]}]' if 'points' in t else ''


def trait_line(t):
    line = t['full_name']
    if t.get('level') not in (None, 0, 1) and 'type' not in t:
        line += f' {t["level"]}'
    if t.get('modifiers'):
        line += ' (' + '; '.join(f'{m["name"]}, {m["value"]}' for m in t['modifiers']) + ')'
    line += pts(t)
    if t.get('page'):
        line += f' ({t["page"]})'
    return line


def sheet(rec):
    """The record as Markdown. Hidden traits and component traits of templates are left out and
    counted, so nothing goes missing without a line saying so."""
    out = [f'# {rec["name"] or "Unnamed character"}', '']
    who = [f'**Player:** {rec["player"]}'] if rec['player'] else []
    who += [f'**{k.capitalize()}:** {v}' for k, v in rec['vitals'].items()]
    if who:
        out += ['  \n'.join(who), '']
    c = rec['campaign']
    if c:
        out += [f'**Points:** {rec["points_summed_here"]["total"]} spent (added up here from the points GCA saved '
                f'on each trait); campaign base {c.get("basepoints", "?")}, logged {c.get("loggedpoints", 0)}, '
                f'other {c.get("otherpoints", 0)}. **TL:** {c.get("basetl", "?")}', '']
    left_out = 0
    attrs = [t for t in rec['traits']['attributes'] if t['name'].strip('-') and not t.get('hidden')]
    main = sorted((t for t in attrs if isinstance(t.get('mainwin'), (int, float))), key=lambda t: t['mainwin'])
    shown = main or attrs
    left_out += len(rec['traits']['attributes']) - len(shown)
    if shown:
        out += ['## Attributes', '', '| Attribute | Score | Points |', '|---|---|---|']
        out += [f'| {t["name"]} | {t.get("score", "")} | {t.get("points", "")} |' for t in shown] + ['']
    for kind, title in (('advantages', 'Advantages'), ('perks', 'Perks'), ('languages', 'Languages'),
                        ('cultures', 'Cultural familiarities'), ('features', 'Features'),
                        ('disadvantages', 'Disadvantages'), ('quirks', 'Quirks'), ('templates', 'Templates')):
        rows = [t for t in rec['traits'][kind] if not t.get('hidden')]
        left_out += len(rec['traits'][kind]) - len(rows)
        if rows:
            out += [f'## {title}', ''] + [f'- {trait_line(t)}' for t in rows] + ['']
    for kind, title in (('skills', 'Skills'), ('spells', 'Spells')):
        rows = [t for t in rec['traits'][kind] if not t.get('hidden')]
        left_out += len(rec['traits'][kind]) - len(rows)
        if rows:
            out += [f'## {title}', '', '| Name | Type | Level | Relative | Points | Page |', '|---|---|---|---|---|---|']
            out += [f'| {t["full_name"]} | {t.get("type", "")} | {t.get("level", "")} | {t.get("relative", "")} | '
                    f'{t.get("points", "")} | {t.get("page", "")} |' for t in rows] + ['']
    gear = [t for t in rec['traits']['equipment'] if not t.get('hidden')]
    left_out += len(rec['traits']['equipment']) - len(gear)
    if gear:
        out += ['## Equipment', '', '| Item | Count | Cost | Weight |', '|---|---|---|---|']
        out += [f'| {t["full_name"]} | {t.get("count", "")} | {t.get("cost", "")} | {t.get("weight", "")} |'
                for t in gear] + ['']
        attacks = [(t, m) for t in gear for m in t.get('modes', [])]
        if attacks:
            out += ['### Attacks', '', '| Weapon | Mode | Skill | Level | Damage | Reach or range |', '|---|---|---|---|---|---|']
            for t, m in attacks:
                dmg = ' '.join(x for x in (m.get('chardamage', ''), m.get('chardamtype', '')) if x)
                rng = m.get('charreach') or '/'.join(x for x in (m.get('charrangehalfdam', ''), m.get('charrangemax', '')) if x)
                out.append(f'| {t["full_name"]} | {m.get("name", "")} | {m.get("charskillused", "").strip(chr(34))} | '
                           f'{m.get("charskillscore", "")} | {dmg} | {rng} |')
            out.append('')
    if rec['notes']:
        out += ['## Notes', '', rec['notes'], '']
    if rec['log']:
        out += ['## Campaign log', ''] + [
            f'- {e["date"]}: {e["caption"] or "(no caption)"}' + (f', {e["points"]:+} points' if e['points'] else '')
            for e in rec['log']] + ['']
    books = rec['built_with']['books']
    out += ['---', '', f'Built in GCA with: {", ".join(b.split(chr(92))[-1] for b in books) or "no data files recorded"}.'
            + (f' Saved by {rec["saved_by"]}.' if rec['saved_by'] else '')]
    if left_out:
        out += ['', f'{left_out} traits GCA hides or uses only as dividers are not shown.']
    return '\n'.join(out) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('list', 'read', 'sheet'))
    ap.add_argument('file')
    ap.add_argument('--character')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    if a.cmd == 'list' and party_paths(a.file) is not None:
        for line in party_paths(a.file):
            print(line)
        return 0
    chars = characters(a.file)
    if a.cmd == 'list':
        for c in chars:
            print(f'{text(c, "name") or "(unnamed)"}\t{text(c, "player")}')
        return 0
    rec = read(pick(chars, a.character))
    body = json.dumps(rec, ensure_ascii=False, indent=1) + '\n' if a.cmd == 'read' else sheet(rec)
    if a.out:
        with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(body)
        print(f'wrote {a.out}')
    else:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stdout.write(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
