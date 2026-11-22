#!/usr/bin/env python3
"""Read and write GURPS Character Assistant data files (.gdf, format version 3).

    gdf.py parse FILE.gdf --out parsed.json [--index records.json]   # read a data file (library-layout.md §12)
    gdf.py show FILE.gdf "AD:Combat Reflexes"                        # one definition, as read
    gdf.py write --library-data DIR --source CODE --title "Book Title" --out FILE.gdf
                 [--requires "Other File.gdf" ...] [--date YYYY-MM-DD]   # generate from entries' `define`s

The format is the one the GCA Data File Reference Guide describes: a header of
`Key=value` lines, then sections headed `[Name]`. In the trait sections each
logical line is one definition: its name (with an optional name extension in
brackets), then the values the section puts before the tags (an advantage's
cost, a skill's type), then `tag(value)` pairs, all separated by commas.
`<Category>` lines file the definitions below them. A line that ends with `_`,
`,` or `|` continues on the next. `*` or `//` at the start of a line, and ` //`
within one, start a comment. Lines starting `#` are data file commands
(`#ReplaceTags in "AD:Luck" with cost(10)`): they are kept as commands, never
applied, because what they do depends on the files loaded before this one.

`parse` reports what it could not read as a definition under `problems`, with
the line number; nothing is skipped silently.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

# section name (lower case) -> the prefix GCA gives its traits
TRAIT_SECTIONS = {
    'attributes': 'ST', 'advantages': 'AD', 'perks': 'PE', 'languages': 'LA', 'cultures': 'CU',
    'features': 'FE', 'disadvantages': 'DI', 'quirks': 'QU', 'skills': 'SK', 'spells': 'SP',
    'templates': 'TE', 'equipment': 'EQ', 'modifiers': '',
}
SECTION_NAMES = {   # as the guide writes them, for output
    'attributes': 'Attributes', 'advantages': 'Advantages', 'perks': 'Perks', 'languages': 'Languages',
    'cultures': 'Cultures', 'features': 'Features', 'disadvantages': 'Disadvantages', 'quirks': 'Quirks',
    'skills': 'Skills', 'spells': 'Spells', 'templates': 'Templates', 'equipment': 'Equipment',
    'modifiers': 'Modifiers', 'groups': 'Groups', 'lists': 'Lists', 'author': 'Author',
}
# library category for each prefix (library-layout.md §12)
CATEGORY_OF = {'ST': 'attributes', 'AD': 'advantages', 'PE': 'advantages', 'LA': 'advantages', 'CU': 'advantages',
               'FE': 'advantages', 'DI': 'disadvantages', 'QU': 'disadvantages', 'SK': 'skills', 'SP': 'spells',
               'TE': 'templates', 'EQ': 'equipment', '': 'modifiers'}
# data file commands (the guide's "Data File Commands"), which change what earlier files defined
COMMANDS = {'#addtolist', '#addtolistbytag', '#clone', '#clonemod', '#delete', '#deleteallcats', '#deletebytag',
            '#deletecat', '#deletefromgroup', '#deletefromlist', '#deletemodgroup', '#deletemodsfromgroup', '#get',
            '#if', '#elseif', '#else', '#end', '#log', '#mergemodtags', '#mergetags', '#modifiergroupwarnings',
            '#replacetags', '#replacemodtags', '#store', '#verbose'}
SECTION_LINE = re.compile(r'^\[([^\]]+)\]\s*$')
CATEGORY_LINE = re.compile(r'^<(.*)>\s*$')
TAG = re.compile(r'^([A-Za-z_%][\w%]*)\((.*)\)$', re.S)
SPACED_TAG = re.compile(r'^[A-Za-z_]\w*\s+\(.*\)$', re.S)     # a tag typed with a space before its bracket
OPEN, CLOSE = '({', ')}'


def read_text(path):
    """The file's text. A data file is UTF-8 only when its first line says so; otherwise it is
    in the Windows code page GCA has always used."""
    with open(path, 'rb') as f:
        raw = f.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        return raw[3:].decode('utf-8')
    first = raw.split(b'\n', 1)[0].strip().lower()
    return raw.decode('utf-8' if first == b'encoding=utf-8' else 'cp1252', errors='replace')


def strip_comment(line):
    """The line without its comment. `//` starts one at the start of a line or after a space."""
    if line.startswith('//') or line.startswith('*'):
        return ''
    m = re.search(r'\s//', line)
    return line[:m.start()] if m else line


def logical_lines(text):
    """Yield (line number, text, in_author) for each logical line: comments removed, continued
    lines joined. Inside [Author] every line is kept as written, since its comments are its
    content."""
    author = False
    held, held_at = '', 0
    for n, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        m = SECTION_LINE.match(stripped)
        if m and not held:
            author = m.group(1).strip().lower() == 'author'
            yield n, stripped, False
            continue
        if author:
            yield n, raw.rstrip(), True
            continue
        line = strip_comment(stripped).strip()
        if not line:
            continue                      # blank and comment lines never end a continued line
        if not held:
            held_at = n
        if line.endswith('_'):
            held += line[:-1]
            continue
        held += line
        if line.endswith(',') or line.endswith('|'):
            continue
        yield held_at, held, False
        held = ''
    if held:
        yield held_at, held, False


def split_top(text, sep=','):
    """Split on `sep` outside brackets, braces and double quotes. Unbalanced closers are kept as
    text rather than raising: real files have them."""
    parts, depth, quote, cur = [], 0, False, []
    for ch in text:
        if quote:
            cur.append(ch)
            quote = ch != '"'
        elif ch == '"':
            quote = True
            cur.append(ch)
        elif ch in OPEN:
            depth += 1
            cur.append(ch)
        elif ch in CLOSE:
            depth = max(depth - 1, 0)
            cur.append(ch)
        elif ch == sep and depth == 0:
            parts.append(''.join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    parts.append(''.join(cur).strip())
    return parts


def balanced(text):
    depth, quote = 0, False
    for ch in text:
        if quote:
            quote = ch != '"'
        elif ch == '"':
            quote = True
        elif ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not quote


def split_name(text):
    """'Guns (Pistol)' -> ('Guns', 'Pistol'). Quotes or braces around a name that holds a comma
    are removed."""
    text = text.strip()
    if len(text) > 1 and ((text[0] == '"' and text[-1] == '"') or (text[0] == '{' and text[-1] == '}')):
        text = text[1:-1].strip()
    if text.endswith(')'):
        depth = 0
        for i in range(len(text) - 1, -1, -1):
            if text[i] == ')':
                depth += 1
            elif text[i] == '(':
                depth -= 1
                if depth == 0:
                    if i > 0:
                        return text[:i].strip(), text[i + 1:-1].strip()
                    break
    return text, ''


def full_name(name, ext):
    return f'{name} ({ext})' if ext else name


def parse_item(text):
    """A definition line -> {'name', 'nameext', 'values', 'tags'}. `tags` keeps the file's order;
    a tag given twice keeps both, the later under 'name#2'."""
    parts = split_top(text)
    name, ext = split_name(parts[0])
    values, tags = [], {}
    for p in parts[1:]:
        m = TAG.match(p)
        if m and balanced(m.group(2)):
            key, n = m.group(1).lower(), 2
            while key in tags:
                key = f'{m.group(1).lower()}#{n}'
                n += 1
            tags[key] = m.group(2).strip()
        elif tags:
            # text after the first tag that isn't a tag: part of nothing we can name
            tags.setdefault('_loose', [])
            tags['_loose'].append(p)
        else:
            values.append(p)
    return {'name': name, 'nameext': ext, 'values': values, 'tags': tags}


def parse(text, file=''):
    """Text of a data file -> {'file', 'header', 'sections': [...], 'problems': [...]}.

    A trait section is {'name', 'items': [...]} where an item is a definition
    ({'line', 'category', 'name', 'nameext', 'values', 'tags', 'item'}) or a command
    ({'line', 'command', 'text'}). Other sections keep their logical lines as
    {'line', 'category', 'text'}. A section name can appear more than once in a file; each
    appearance is its own section, in file order."""
    out = {'file': file, 'header': {}, 'sections': [], 'problems': []}
    section, kind, category = None, None, ''
    for n, line, in_author in logical_lines(text):
        m = SECTION_LINE.match(line) if not in_author else None
        if m:
            name = m.group(1).strip()
            kind = name.lower()
            section = {'name': SECTION_NAMES.get(kind, name), 'items': []}
            out['sections'].append(section)
            category = ''
            continue
        if section is None:
            key, eq, value = line.partition('=')
            if eq:
                out['header'][key.strip().lower()] = value.strip()
            else:
                out['problems'].append({'line': n, 'text': line[:120], 'why': 'header line without ='})
            continue
        if in_author:
            section['items'].append({'line': n, 'text': line})
            continue
        c = CATEGORY_LINE.match(line)
        if c and kind != 'author':
            category = c.group(1).strip()
            continue
        if line.startswith('#'):
            command, _, rest = line.partition(' ')
            if command.lower() in COMMANDS:
                section['items'].append({'line': n, 'command': command, 'text': rest.strip()})
                continue
            if kind in TRAIT_SECTIONS:
                out['problems'].append({'line': n, 'text': line[:120], 'why': 'not a data file command the guide lists'})
                continue
        if kind in TRAIT_SECTIONS:
            item = parse_item(line)
            if not item['name']:
                out['problems'].append({'line': n, 'text': line[:120], 'why': 'definition without a name'})
                continue
            if '_loose' in item['tags']:
                out['problems'].append({'line': n, 'text': full_name(item['name'], item['nameext']),
                                        'why': 'text between tags that is not a tag: ' +
                                               '; '.join(x[:60] for x in item['tags']['_loose'])})
            spaced = [v for v in item['values'] if SPACED_TAG.match(v)]
            if spaced:
                out['problems'].append({'line': n, 'text': full_name(item['name'], item['nameext']),
                                        'why': 'text between tags that is not a tag: ' + '; '.join(x[:60] for x in spaced)})
            if not balanced(line):
                out['problems'].append({'line': n, 'text': full_name(item['name'], item['nameext']),
                                        'why': 'brackets or quotes do not pair up'})
            prefix = TRAIT_SECTIONS[kind]
            item = {'line': n, 'category': category, **item,
                    'item': (prefix + ':' if prefix else '') + full_name(item['name'], item['nameext'])}
            section['items'].append(item)
        else:
            section['items'].append({'line': n, 'category': category, 'text': line})
    return out


def records(parsed):
    """Index records, one per definition (library-layout.md §12)."""
    out = []
    for s in parsed['sections']:
        for it in s['items']:
            if 'item' not in it:
                continue
            out.append({'item': it['item'], 'file': parsed['file'], 'section': s['name'],
                        'category': it['category'], 'name': it['name'], 'nameext': it['nameext'],
                        'page': it['tags'].get('page', ''), 'line': it['line']})
    return out


def counts(parsed):
    c = {}
    for s in parsed['sections']:
        if s['name'].lower() in TRAIT_SECTIONS:
            n = sum(1 for it in s['items'] if 'item' in it)
            m = sum(1 for it in s['items'] if 'command' in it)
            if n:
                c[s['name']] = c.get(s['name'], 0) + n
            if m:
                c['commands'] = c.get('commands', 0) + m
    return c


# --- writing ---------------------------------------------------------------------------------

def quote_name(name):
    return '{' + name + '}' if ',' in name else name


def item_line(name, ext, values, tags, strict=True):
    """One definition as a data file line. `strict` (for a file being generated) refuses what
    GCA would misread: brackets or quotes that don't pair up, and a double quote in a name.
    Published files have both, so a file being written out as read is not held to it."""
    if strict:
        for label, text in [('name', full_name(name, ext))] + [(k, v) for k, v in tags.items()]:
            if not balanced(str(text)):
                raise ValueError(f'{full_name(name, ext)}: brackets or quotes do not pair up in {label}')
        if '"' in full_name(name, ext):
            raise ValueError(f'{full_name(name, ext)}: a name cannot hold a double quote')
    parts = [quote_name(full_name(name, ext))] + [str(v) for v in values]
    parts += [f'{k.split("#")[0]}({v})' for k, v in tags.items() if k != '_loose']
    parts += list(tags.get('_loose', []))
    return ', '.join(parts)


def serialize(parsed):
    """A parsed data file as text again: the same definitions, commands and lines, one per line.
    Comments and the original line breaks are not kept; parse(serialize(p)) gives p's content."""
    out = []
    if parsed['header'].get('encoding'):
        out.append(f'Encoding={parsed["header"]["encoding"]}')
    out.append(f'Version={parsed["header"].get("version", "3")}')
    for k, v in parsed['header'].items():
        if k not in ('encoding', 'version'):
            out.append(f'{k.capitalize()}={v}')
    for s in parsed['sections']:
        out += ['', f'[{s["name"]}]']
        category = ''
        for it in s['items']:
            if it.get('category', category) != category:
                category = it['category']
                out.append(f'<{category}>')
            if 'command' in it:
                out.append(f'{it["command"]} {it["text"]}'.rstrip())
            elif 'item' in it:
                out.append(item_line(it['name'], it['nameext'], it['values'], it['tags'], strict=False))
            else:
                out.append(it['text'])
    return '\n'.join(out) + '\n'


def defines(library_data, source):
    """Every `define` on the entries of `source` under a library-data folder, as
    (section key, category list, name, nameext, values, tags, entry ref), sorted by section,
    category and name."""
    found, errors = [], []
    for path in sorted(glob.glob(os.path.join(library_data, '*', '*.json'))):
        if os.path.basename(path).startswith('_'):
            continue
        with open(path, encoding='utf-8') as f:
            entry = json.load(f)
        if entry.get('source') != source:
            continue
        ref = f'{os.path.basename(os.path.dirname(path))}/{entry.get("slug", "")}'
        for g in entry.get('gca', []):
            d = g.get('define')
            if not d:
                continue
            key = str(d.get('section', '')).lower()
            if key not in TRAIT_SECTIONS:
                errors.append(f'{ref}: {g.get("item")}: section {d.get("section")!r} is not a trait section')
                continue
            prefix, _, rest = g.get('item', '').partition(':') if TRAIT_SECTIONS[key] else ('', '', g.get('item', ''))
            if prefix != TRAIT_SECTIONS[key] or not rest:
                errors.append(f'{ref}: {g.get("item")!r} does not carry the prefix of [{SECTION_NAMES[key]}] '
                              f'({TRAIT_SECTIONS[key] or "none"})')
                continue
            name, ext = split_name(rest)
            cats = d.get('category') or ['']
            found.append((key, [cats] if isinstance(cats, str) else list(cats), name, ext,
                          list(d.get('values', [])), dict(d.get('tags', {})), ref))
    return found, errors


def generate(found, title, source, requires=(), date=None):
    """The text of a generated data file (library-layout.md §12, "Generated data files")."""
    date = date or datetime.date.today().isoformat()
    out = ['Encoding=UTF-8', 'Version=3',
           f'Description={date}. Generated by the GURPS Assistant library from its entries for {title} ({source}).']
    if requires:
        out.append('Requires=' + ', '.join(f'"{r}"' for r in requires))
    out += ['', '[Author]',
            f'* Generated {date} by the GURPS Assistant library from its entries for {title} ({source}).',
            '* The entries are the master copy: correct the entry and generate this file again.',
            '* Do not edit this file by hand.']
    order = list(TRAIT_SECTIONS)
    for key in sorted({f[0] for f in found}, key=order.index):
        out += ['', f'[{SECTION_NAMES[key]}]']
        rows = sorted((f for f in found if f[0] == key), key=lambda f: (f[1][0].lower(), f[2].lower(), f[3].lower()))
        category = None
        for _, cats, name, ext, values, tags, _ref in rows:
            if cats[0] != category:
                category = cats[0]
                if category:
                    out.append(f'<{category}>')
            if len(cats) > 1 and 'cat' not in tags:
                tags = {**tags, 'cat': ', '.join(cats)}
            out.append(item_line(name, ext, values, tags))
    return '\n'.join(out) + '\n'


# --- command line ----------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('parse')
    p.add_argument('file')
    p.add_argument('--out')
    p.add_argument('--index', help='write the index records here')
    p = sub.add_parser('show')
    p.add_argument('file')
    p.add_argument('item', help='e.g. "AD:Combat Reflexes"; a modifier by its bare name')
    p = sub.add_parser('write')
    p.add_argument('--library-data', required=True, action='append')
    p.add_argument('--source', required=True)
    p.add_argument('--title', required=True)
    p.add_argument('--requires', action='append', default=[])
    p.add_argument('--date')
    p.add_argument('--out', required=True)
    a = ap.parse_args(argv)

    if a.cmd in ('parse', 'show'):
        parsed = parse(read_text(a.file), os.path.basename(a.file))
    if a.cmd == 'parse':
        if a.out:
            with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(parsed, f, ensure_ascii=False, indent=1)
                f.write('\n')
        if a.index:
            with open(a.index, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(records(parsed), f, ensure_ascii=False, indent=1)
                f.write('\n')
        print(json.dumps({'file': parsed['file'], 'header': {k: v[:80] for k, v in parsed['header'].items()},
                          'counts': counts(parsed), 'problems': parsed['problems']}, ensure_ascii=False, indent=1))
        return 1 if parsed['problems'] else 0
    if a.cmd == 'show':
        want = a.item.lower()
        hits = [it for s in parsed['sections'] for it in s['items'] if it.get('item', '').lower() == want]
        if not hits:
            print(f'{a.item}: not defined in {parsed["file"]}', file=sys.stderr)
            return 1
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return 0
    found, errors = [], []
    for d in a.library_data:
        f, e = defines(d, a.source)
        found += f
        errors += e
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    if not found:
        print(f'no entry of {a.source} has a definition to write', file=sys.stderr)
        return 1
    try:
        text = generate(found, a.title, a.source, a.requires, a.date)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    check = parse(text, os.path.basename(a.out))        # what GCA will be given must read back clean
    if check['problems']:
        print(json.dumps(check['problems'], ensure_ascii=False, indent=1), file=sys.stderr)
        return 1
    with open(a.out, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(text)
    print(json.dumps({'file': os.path.basename(a.out), 'counts': counts(check),
                      'entries': sorted({f[6] for f in found})}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
