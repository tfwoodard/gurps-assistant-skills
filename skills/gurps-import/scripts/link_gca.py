#!/usr/bin/env python3
"""Link a source's library entries to the GCA definitions that build them (library-layout.md §12,
docs/adr/0005).

    link_gca.py --library ROOT --source B [--links sources/B/plans/links.json] [--report OUT.json]
                [--write] [--category advantages ...]

The definitions are those of the data files `library.json` → `data_files` gives the source, as
read into `gca/parsed/`; the entries are the source's, in the trait categories (§12's table:
attributes, advantages, disadvantages, skills, spells, templates, equipment, modifiers). Rules,
tables, creatures and lore are never linked.

An entry is linked in one of two ways:

  exact      a definition of the entry's name, in its category's sections, whose page() cites the
             entry's source and page. An entry that takes specialties, or that GCA splits into
             variants, gets every definition of its name on that page ("Guns" -> "SK:Guns
             (Pistol)", "SK:Guns (Rifle)"); a definition whose full name is an entry's name
             ("Guns (Pistol)") goes to that entry rather than to the one of its base name.
  confirmed  the links file names its definitions (or says it has none, and why). The file is the
             Librarian's: what they confirmed, kept so a re-run gives the same links.

Everything else that may be it is a **proposal**, with its kind, and is never written until the
links file confirms it, by entry or by kind (`accept`: an entry whose proposals are all of an
accepted kind takes them; an accepted `pointer` takes only the definitions no other entry holds,
and a pointer left with none is counted as `pointer`, its write-up holding the link):

  runs-on        the name, cited on a later page the entry's write-up runs on to (up to the page
                 the category's next entry starts on)
  singular       the entry's name in the singular, or its words in another order, cited within its
                 pages ("Allies" -> "AD:Ally"; each of a base name's definitions)
  pointer       the name, cited elsewhere, for an entry that only points to a write-up (`see`)
  other-page     the name, cited on another page of the source
  no-page        the name, in a definition with no page()
  other-section  the name, in another category's section
  on-page        a definition no entry claims, cited on the entry's page, sharing a word of its name

Reported every run, none of it hidden: entries with no definition (with their proposals);
definitions with no entry (GCA's helper items, `_New Skill` and the like, counted apart; those the
links file says have none listed with its reason); pairs whose printed cost and the data file's
disagree; pairs not compared, and why; a definition two entries claim; a definition its file has
twice. A links file naming an entry or definition that isn't there is an error, and nothing is
written.

The links file (`sources/<code>/plans/links.json`):

    {"links": {"advantages/rank": ["AD:Rank"],
               "modifiers/accurate": [{"item": "Accurate", "group": "Enhancements"}]},
     "none": {"advantages/cybernetics": "the data file defines each implant as its own trait"},
     "not_entries": {"AD:Extra ST": "an attribute GCA keeps as an advantage"},
     "accept": ["runs-on"]}

A modifier is named with its group (GCA files modifiers by group, and one name can be in many).

Costs are compared only where both sides say one thing: a printed "N points" against a data file
cost of N, and "N points/level" against "N/2N" (GCA's running total by level); a modifier's
"+N%" against "+N%"; a skill's attribute and difficulty against its type ("DX/A"); a spell's "(VH)"
against its type. Nothing is worked out from rules (docs/adr/0006).

--write sets each entry's `gca` (each link {"item", "group" for a modifier, "file"}), renders its
.md again and rewrites its line of the category's `_index.json`; an entry whose links are gone
loses its `gca`. Prints a summary; --report writes the whole report as JSON.
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from edit_entry import dump_like, edit_index_line  # noqa: E402
from render_entry import render  # noqa: E402

# library category -> GCA sections (library-layout.md §12)
SECTIONS = {
    'attributes': ('Attributes',), 'advantages': ('Advantages', 'Perks', 'Languages', 'Cultures', 'Features'),
    'disadvantages': ('Disadvantages', 'Quirks'), 'skills': ('Skills',), 'spells': ('Spells',),
    'templates': ('Templates',), 'equipment': ('Equipment',), 'modifiers': ('Modifiers',),
}
CATEGORY_OF_SECTION = {s: c for c, ss in SECTIONS.items() for s in ss}
KINDS = ('runs-on', 'singular', 'pointer', 'other-page', 'no-page', 'other-section', 'on-page')
DIFFICULTY = {'easy': 'E', 'average': 'A', 'hard': 'H', 'very hard': 'VH'}
SMALL = {'a', 'an', 'and', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with'}


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def norm(name):
    """A name as compared: case, curly quotes (or GCA's doubled ones), dashes, spacing and the space in
    "TL 6" don't count."""
    s = name.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = s.replace("''", '"').replace('–', '-').replace('—', '-')
    s = re.sub(r'\bTL\s+(\d)', r'TL\1', s)
    return re.sub(r'\s+', ' ', s).strip().casefold()


def words(name):
    """The words of a name that can tie it to another, each without a plural ending."""
    out = set()
    for w in re.findall(r"[a-z0-9']+", norm(name)):
        if w in SMALL or len(w) < 3:
            continue
        for end in ('ies', 'es', 's'):
            if w.endswith(end) and len(w) > len(end) + 2:
                w = w[:-len(end)] + ('y' if end == 'ies' else '')
                break
        out.add(w)
    return out


def cited(page_tag):
    """page() -> {(book code, page)}: "M23, B243" -> {("M", 23), ("B", 243)}; "B29-31" gives 29 to 31."""
    out = set()
    for part in re.split(r'\s*,\s*', page_tag or ''):
        m = re.match(r'^\s*([A-Za-z][A-Za-z0-9]*?)(\d+)(?:\s*-\s*(\d+))?', part)
        if m:
            first = int(m.group(2))
            last = int(m.group(3)) if m.group(3) and int(m.group(3)) >= first else first
            out |= {(m.group(1), p) for p in range(first, min(last, first + 20) + 1)}
    return out


class Definition:
    def __init__(self, file, section, it):
        self.file, self.section = file, section
        self.item, self.name, self.nameext = it['item'], it['name'], it.get('nameext', '')
        self.category_name = it.get('category', '')
        self.category = CATEGORY_OF_SECTION[section]
        self.group = self.category_name if self.category == 'modifiers' else ''
        self.values, self.tags, self.line = it.get('values', []), it.get('tags', {}), it['line']
        self.page = self.tags.get('page', '')
        self.pages = cited(self.page)
        self.helper = self.name.startswith('_')
        # GCA names a modifier's variants "Delay: Fixed" or "Unreliable/Activation" as well as "Name (ext)"
        self.bases = [self.name] + ([b for b in (self.name.split(': ')[0], self.name.split('/')[0])
                                     if b != self.name] if self.category == 'modifiers' else [])

    @property
    def key(self):
        return (self.file, self.item, self.group)

    def link(self):
        return {'item': self.item, **({'group': self.group} if self.group else {}), 'file': self.file}

    def show(self):
        return {'item': self.item, **({'group': self.group} if self.group else {}), 'page': self.page,
                'file': self.file, 'line': self.line}


def read_definitions(library, source):
    lib = load(os.path.join(library, 'library.json'))
    files = [d['file'] for d in lib.get('data_files', []) if d.get('source') == source]
    src = next((s for s in lib.get('sources', []) if s.get('code') == source), None)
    if src is None:
        sys.exit(f'{source}: no source with that code in library.json')
    files += [f for f in src.get('data_files', []) if f not in files]
    defs = []
    for f in files:
        path = os.path.join(library, 'gca', 'parsed', slugify_file(f) + '.json')
        if not os.path.exists(path):
            sys.exit(f'{f}: not read into gca/parsed/ (add_data_file.py)')
        for s in load(path)['sections']:
            if s['name'] not in CATEGORY_OF_SECTION:
                continue
            defs += [Definition(f, s['name'], it) for it in s['items'] if 'item' in it]
    return files, defs


def slugify_file(name):
    from add_data_file import slugify
    return slugify(name)


def read_entries(library, source, categories):
    out = []
    for cat in categories:
        path = os.path.join(library, 'library-data', cat, '_index.json')
        if os.path.exists(path):
            out += [dict(r, _category=cat) for r in load(path) if r.get('source') == source]
    return out


def ref(e):
    return f'{e["_category"]}/{e["slug"]}'


def spans(entries):
    """Each entry's last page: the page its category's next entry in the chapter starts on (a
    write-up can run on to it), or the page after its own for the last."""
    by = collections.defaultdict(list)
    for e in entries:
        by[(e['_category'], e.get('chapter'))].append(e['page'])
    out = {}
    for e in entries:
        later = [p for p in by[(e['_category'], e.get('chapter'))] if p > e['page']]
        out[ref(e)] = min(later) if later else e['page'] + 1
    return out


# --- costs -------------------------------------------------------------------------------------

def compare(e, d):
    """(same, printed, data file) for a pair, or (None, why) when they can't be compared."""
    cat, f = e['_category'], e
    if cat in ('advantages', 'disadvantages'):
        printed = (f.get('cost') or '').replace('−', '-').rstrip('*').strip()
        v = d.values[0] if d.values else ''
        if not printed:
            return None, 'the entry prints no cost'
        if not v:
            return None, 'the definition gives no cost'
        m = re.fullmatch(r'([+-]?\d+) points?', printed)
        if m:                    # GCA may list costs for levels the trait can't take ("15/45"): the first is its cost
            return int(m.group(1)) == number(v.split('/')[0]), printed, v
        m = re.fullmatch(r'([+-]?\d+) points?/level', printed)
        if m:
            steps = v.split('/')
            n = int(m.group(1))
            return (len(steps) >= 2 and number(steps[0]) == n and number(steps[1]) == 2 * n), printed, v
        return None, f'printed "{shape(printed)}"'
    if cat == 'modifiers':
        printed = (f.get('cost') or '').replace('−', '-').strip()
        v = d.values[0] if d.values else ''
        if re.fullmatch(r'[+-]\d+%', printed) and v:
            return printed == v.strip(), printed, v
        m = re.fullmatch(r'([+-]\d+)%/level', printed)
        steps = [number(s.rstrip('%')) for s in v.split('/')]
        if m and len(steps) >= 2:
            n = int(m.group(1))
            return steps[0] == n and steps[1] == 2 * n, printed, v
        return None, f'printed "{shape(printed)}", data file "{shape(v)}"'
    if cat == 'skills':
        v = d.values[0] if d.values else ''
        diff = DIFFICULTY.get((f.get('difficulty') or '').casefold())
        att = f.get('attribute') or ''
        if not diff:
            return None, f'difficulty printed "{f.get("difficulty", "")}"'
        if f.get('kind') == 'technique':
            got = v.split('/')[-1]
            return got == diff, f.get('difficulty'), v
        if '/' not in v or ' or ' in att or not att:
            return None, f'attribute printed "{att}", data file "{shape(v)}"'
        return v == f'{att}/{diff}', f'{att}/{f.get("difficulty")}', v
    if cat == 'spells':
        t = d.tags.get('type', '')
        if '/' not in t:
            return None, 'the definition gives no type'
        vh = t.split('/')[-1].strip() == 'VH'
        return vh == bool(f.get('very_hard')), '(VH)' if f.get('very_hard') else 'not (VH)', t
    return None, f'{cat} are not compared'


def number(s):
    try:
        return int(s.strip().lstrip('+'))
    except ValueError:
        return None


def shape(s):
    return re.sub(r'\d+', 'N', s or '')


# --- matching ----------------------------------------------------------------------------------

def link(entries, defs, links_file, source):
    errors = []
    by_name = collections.defaultdict(list)          # (category, base or full name) -> definitions
    full = collections.defaultdict(list)             # (category, full name) -> definitions
    any_section = collections.defaultdict(list)      # name -> definitions in any section
    seen, twice = {}, []
    for d in defs:
        if d.key in seen:
            twice.append(d.show())
            continue
        seen[d.key] = d
        for b in dict.fromkeys(norm(x) for x in d.bases):
            by_name[(d.category, b)].append(d)
        full[(d.category, norm(d.item.split(':', 1)[1] if ':' in d.item else d.item))].append(d)
        any_section[norm(d.name)].append(d)
    unique = list(seen.values())
    by_item = collections.defaultdict(list)
    for d in unique:
        by_item[d.item].append(d)
    span = spans(entries)
    refs = {ref(e): e for e in entries}

    confirmed = links_file.get('links', {})
    none = links_file.get('none', {})
    accept = set(links_file.get('accept', []))
    for k in accept - set(KINDS):
        errors.append(f'links file accept: {k!r} is no kind of proposal ({", ".join(KINDS)})')
    for r in list(confirmed) + list(none):
        if r not in refs:
            errors.append(f'links file: {r} is no entry of the source')
    for r in set(confirmed) & set(none):
        errors.append(f'links file: {r} is given links and also said to have none')

    def resolve(r, spec):
        item, group = (spec, '') if isinstance(spec, str) else (spec.get('item', ''), spec.get('group', ''))
        hits = [d for d in by_item.get(item, []) if not group or d.group == group]
        if len(hits) != 1:
            errors.append(f'links file: {r}: {item!r}{" in " + group if group else ""} is '
                          f'{"no definition" if not hits else "in several groups; name its group"}')
            return None
        return hits[0]

    # exact matches first: a full-name match wins over a base-name one
    exact = {}
    for e in entries:
        page = (source, e['page'])
        n = norm(e['name'])
        both = full.get((e['_category'], n), []) + by_name.get((e['_category'], n), [])
        exact[ref(e)] = list({d.key: d for d in both if page in d.pages}.values())
    names_of = {ref(e): [norm(e['name'])] + ([norm(e['abbreviation'])] if e.get('abbreviation') else [])
                for e in entries}           # an attribute is also its abbreviation (GCA's ST:ST)
    by_full_entry = {}
    for r, hits in exact.items():
        for d in hits:
            if norm(refs[r]['name']) == norm(d.item.split(':', 1)[-1]):
                by_full_entry[d.key] = r
    for r, hits in exact.items():
        exact[r] = [d for d in hits if by_full_entry.get(d.key, r) == r]

    linked, how = {}, {}
    for r in refs:
        if r in confirmed:
            got = [resolve(r, s) for s in confirmed[r]]
            linked[r], how[r] = [d for d in got if d], 'confirmed'
        elif r in none:
            linked[r], how[r] = [], 'none'
        elif exact[r]:
            linked[r], how[r] = exact[r], 'exact'
    claimed = collections.defaultdict(list)
    for r, ds in linked.items():
        for d in ds:
            claimed[d.key].append(r)

    # proposals, for entries not linked
    proposals = {}
    for e in entries:
        r = ref(e)
        if r in linked:
            continue
        n, cat, page = norm(e['name']), e['_category'], e['page']
        named = next((list({d.key: d for d in full.get((cat, m), []) + by_name.get((cat, m), [])}.values())
                      for m in names_of[r] if full.get((cat, m)) or by_name.get((cat, m))), [])
        props = []
        for d in named:
            mine = sorted(p for b, p in d.pages if b == source)
            if not d.pages:
                kind = 'no-page'
            elif e.get('see'):
                kind = 'pointer'
            elif any(page < p <= span[r] for p in mine):
                kind = 'runs-on'
            else:
                kind = 'other-page'
            props.append((kind, d))
        if not named:
            props += [('other-section', d) for d in any_section.get(n, []) if d.category != cat]
        if not props:
            w = words(e['name'])
            near = [d for d in unique if d.category == cat and d.key not in claimed and not d.helper
                    and any(b == source and page <= p <= span[r] for b, p in d.pages)]
            alike = lambda d: any(words(b) == w and norm(b) != n for b in d.bases)
            props += [('singular', d) for d in near if alike(d)]
            props += [('on-page', d) for d in near if (source, page) in d.pages and w & words(d.name) and not alike(d)]
        proposals[r] = props
    # a kind the links file accepts links an entry whose proposals are all of that kind; a pointer
    # takes only the definitions no other entry holds (its write-up's entry comes first), last
    pointed_to_linked = []
    for pointers in (False, True):
        for r, props in proposals.items():
            kinds = {k for k, _ in props}
            if not props or len(kinds) != 1 or (kinds == {'pointer'}) != pointers or not kinds <= accept:
                continue
            taken = [d for _, d in props if not (pointers and claimed.get(d.key))]
            if not taken:
                pointed_to_linked.append({'entry': r, 'items': [d.item for _, d in props]})
                how[r] = 'pointer'
                continue
            linked[r], how[r] = taken, 'accepted'
            for d in taken:
                claimed[d.key].append(r)

    # definitions with no entry
    not_entries = links_file.get('not_entries', {})
    for item in not_entries:
        if item not in by_item:
            errors.append(f'links file not_entries: {item!r} is no definition of the source\'s data files')
    no_entry, helpers, known = [], 0, []
    linked_groups = {d.group for d in unique if d.key in claimed and d.group}
    for d in unique:
        if d.key in claimed:
            continue
        if d.helper:
            helpers += 1
        elif d.item in not_entries:
            known.append(dict(d.show(), why=not_entries[d.item]))
        else:
            if not any(b == source for b, _ in d.pages):
                why = f'cites no page of {source}'
            elif d.category == 'modifiers' and d.group not in linked_groups:
                why = "in a modifier group no entry's definition is in"
            else:
                why = f'cites {source}'
            no_entry.append(dict(d.show(), category=d.category, why=why))

    # costs
    differ, not_compared = [], collections.Counter()
    for r, ds in linked.items():
        for d in ds:
            got = compare(refs[r], d)
            if got[0] is None:
                not_compared[f'{refs[r]["_category"]}: {got[1]}'] += 1
            elif not got[0]:
                differ.append({'entry': r, 'item': d.item, **({'group': d.group} if d.group else {}),
                               'printed': got[1], 'data_file': got[2]})

    counts = {}
    for e in entries:
        c = counts.setdefault(e['_category'], collections.Counter())
        c['entries'] += 1
        c[how.get(ref(e), 'unlinked')] += 1
    return {
        'errors': errors,
        'counts': {c: dict(v) for c, v in counts.items()},
        'links': {r: [d.link() for d in sorted(ds, key=lambda d: (d.file, d.line))] for r, ds in linked.items()},
        'how': how,
        'no_definition': [{'entry': r, 'name': refs[r]['name'], 'page': refs[r]['page'],
                           'proposals': [dict(d.show(), kind=k) for k, d in proposals.get(r, [])]}
                          for r in refs if r not in linked and how.get(r) != 'pointer'],
        'said_to_have_none': [{'entry': r, 'why': none[r]} for r in none if r in refs],
        'pointers_to_linked': pointed_to_linked,
        'no_entry': no_entry,
        'no_entry_known': known,
        'helpers': helpers,
        'costs_differ': differ,
        'not_compared': dict(not_compared),
        'claimed_twice': [{'item': k[1], **({'group': k[2]} if k[2] else {}), 'entries': v}
                          for k, v in claimed.items() if len(v) > 1],
        'defined_twice': twice,
    }


# --- writing -----------------------------------------------------------------------------------

def with_gca(entry, links):
    """The entry with `gca` set (after `fields`, or after `relations` when it has them) or taken off."""
    out = {}
    for k, v in entry.items():
        if k == 'gca':
            continue
        out[k] = v
        if k == ('relations' if 'relations' in entry else 'fields') and links:
            out['gca'] = links
    if links and 'gca' not in out:
        out['gca'] = links
    return out


def write(library, entries, report):
    written = []
    by_cat = collections.defaultdict(list)
    for e in entries:
        r = ref(e)
        new = report['links'].get(r, [])
        if (e.get('gca') or []) != new:
            by_cat[e['_category']].append((e['slug'], new))
    for cat, changes in by_cat.items():
        base = os.path.join(library, 'library-data', cat)
        ipath = os.path.join(base, '_index.json')
        with open(ipath, encoding='utf-8') as f:
            index = f.read()
        for slug, new in changes:
            path = os.path.join(base, slug + '.json')
            with open(path, encoding='utf-8') as f:
                raw = f.read()
            entry = with_gca(json.loads(raw), new)
            text = dump_like(entry, raw) or json.dumps(entry, ensure_ascii=False, indent=1) + '\n'
            for p, t in ((path, text), (path[:-5] + '.md', render(entry))):
                with open(p, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(t)
            def change(rec, new=new):
                edition = rec.pop('edition', None)
                rec.pop('gca', None)
                if new:
                    rec['gca'] = new
                if edition is not None:
                    rec['edition'] = edition
                return rec
            index, _ = edit_index_line(index, slug, change)
            written.append(f'{cat}/{slug}')
        with open(ipath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(index)
    return written


def summary(report):
    lines = []
    for cat, c in sorted(report['counts'].items()):
        lines.append(f'{cat}: {c["entries"]} entries: ' + ', '.join(f'{c[k]} {k}' for k in
                     ('exact', 'confirmed', 'accepted', 'pointer', 'none', 'unlinked') if c.get(k)))
    kinds = collections.Counter(p['kind'] for x in report['no_definition'] for p in x['proposals'])
    bare = sum(1 for x in report['no_definition'] if not x['proposals'])
    lines.append(f'entries with no definition: {len(report["no_definition"])} ({bare} with no proposal; proposals: '
                 + (', '.join(f'{n} {k}' for k, n in kinds.most_common()) or 'none') + ')')
    lines.append(f'entries said to have none: {len(report["said_to_have_none"])}')
    lines.append(f'pointers whose write-up holds their definitions: {len(report["pointers_to_linked"])}')
    lines.append(f'definitions with no entry: {len(report["no_entry"])}, and {len(report["no_entry_known"])} the '
                 f'links file explains, and {report["helpers"]} GCA helper items')
    why = collections.Counter((d['category'], d['why']) for d in report['no_entry'])
    lines += [f'  {n} {cat}: {w}' for (cat, w), n in sorted(why.items())]
    lines.append(f'pairs whose costs differ: {len(report["costs_differ"])}')
    lines.append(f'pairs not compared: {sum(report["not_compared"].values())}' +
                 ''.join(f'\n  {n} {why}' for why, n in sorted(report['not_compared'].items(), key=lambda x: -x[1])))
    lines.append(f'definitions two entries claim: {len(report["claimed_twice"])}')
    lines.append(f'definitions a file has twice: {len(report["defined_twice"])}')
    for e in report['errors']:
        lines.append(f'error: {e}')
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--library', required=True)
    ap.add_argument('--source', required=True)
    ap.add_argument('--links', help="the links file, library-relative or absolute (default sources/<code>/plans/links.json)")
    ap.add_argument('--category', action='append', help='only these categories (default: every trait category)')
    ap.add_argument('--report', help='write the whole report here as JSON')
    ap.add_argument('--write', action='store_true', help="set the entries' gca")
    a = ap.parse_args(argv)
    lpath = a.links or f'sources/{a.source}/plans/links.json'
    if not os.path.isabs(lpath):
        lpath = os.path.join(a.library, lpath)
    links_file = load(lpath) if os.path.exists(lpath) else {}
    cats = a.category or list(SECTIONS)
    bad = [c for c in cats if c not in SECTIONS]
    if bad:
        sys.exit(f'{", ".join(bad)}: not a trait category ({", ".join(SECTIONS)})')
    files, defs = read_definitions(a.library, a.source)
    defs = [d for d in defs if d.category in cats]
    entries = read_entries(a.library, a.source, cats)
    report = link(entries, defs, links_file, a.source)
    report = dict({'source': a.source, 'data_files': files, 'links_file': os.path.exists(lpath) and lpath or None},
                  **report)
    if a.report:
        with open(a.report, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
            f.write('\n')
    print(summary(report))
    if report['errors']:
        if a.write:
            print('nothing written: the links file has errors')
        return 1
    if a.write:
        done = write(a.library, entries, report)
        print(f'wrote {len(done)} entries (their .json, .md and index line)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
