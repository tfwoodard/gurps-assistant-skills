#!/usr/bin/env python3
"""Convert a chapter of trait write-ups (advantages, disadvantages, modifiers) into entries.

    convert_traits.py LAYOUT.json --plan PLAN.json --out OUT_DIR [--taken CATEGORY=_index.json ...]
                      [--words WORDS.txt] [--dictionary ENGLISH.txt]

LAYOUT.json is pdf_layout.py's reading of the chapter's pages, made with --boxes, with the
book's type icons as words (--icon-text FONT:GLYPH=[word]) and its pull quotes set aside
(--aside-fonts). The chapter is read as the books print it:

  * A heading larger than a trait's name starts a **section**. A section the plan marks `traits`
    is a list of traits; any other becomes a `rules` entry under its own heading.
  * In a trait list, a line at the trait-name size starts a **trait**: its name, then the icons
    that give its types. The line under it, at the cost size, is its cost as printed
    ("15 points", "5 points/level", "Variable", "+50%") or a pointer ("see Rank, p. 29").
    Everything up to the next trait is its text; smaller headings in it are its own.
  * Each **box** is a `rules` entry of its own, named by its title, unless the plan says
    otherwise.
  * Pull quotes repeat words of the text and are left out, and listed.

The plan (kept in Drive beside the source, never in the repo):

    {"source": "B", "chapter": "ch2",
     "name_size": 14.0, "cost_size": 11.0,
     "icons": ["exotic", "mental", "physical", "social", "supernatural", "attack"],
     "sections": [{"heading": "Advantage List", "page": 34,
                   "traits": {"category": "advantages", "kind": "advantage"}}],
     "boxes": {"32.1": {"leave_out": "the chapter's title, printed in a frame"},
               "46.1": {"adds_to": "advantages/damage-resistance"},
               "154.1": {"into": "disadvantages/short-lifespan", "under": "Some Heading"}},
     "entries": {"advantages/luck": {"relations": [...], "fields": {...}, "audience": "gm"}},
     "not_traits": [{"page": 32, "text": "Mental, Physical, and Social"}],
     "intro": {"name": "Advantages"},
     "rename": [{"page": 110, "name": "Armor Divisor", "to": "Armor Divisor (Limitation)"}],   (+ "section" when two share a page)
     "leave_out_lines": [{"page": 52, "text": "GURPS", "why": "lettering in the picture"}]}

`whole_words` lists words broken at a line's end that are one word, where the converter kept the
hyphen for want of evidence (the report's `hyphens_kept` gives each such case and why);
`hyphenated_words` lists the ones it joined that keep their hyphen ("second-hand").
`intro` names the entry for text printed before the chapter's first heading. `rename` gives a
trait another name than the one printed, where two different things in one category share one
(layout §4); the printed name stays in the entry's `fields.printed_name`. Where the book prints one
trait twice in a chapter, the second gets a `slug` and a `relation` there instead of a new name:
{"page": 165, "name": "Minor Addiction", "section": "Physical Quirks", "slug": "minor-addiction-physical",
 "relation": {"role": "reprint-of", "to": "disadvantages/minor-addiction"}}. `leave_out_lines` are
single lines that are not text of the chapter.

A box that is a table on a tinted panel of its own (the layout marks it `bands`) belongs to an
entry: `into` names it, and `under` a heading in it to put the table straight after, or `after_text`
the opening words of the paragraph to put it after (else it goes at the entry's end); `title_lines` says how many of its first lines are its title, and `fold` that it
is set as that many like tables side by side, to be read one after another.

`lead_lines` says how many lines after the title are text before the table ("This table
summarizes ..."): they go into the entry as a paragraph before it. `after_lines` says how many of
the panel's last lines are text after the table (a way to work out what it lists): they go in as
a paragraph after it. `empty_cells` lists the cells, as [row, column] counted from 1, that the
page prints blank ("No lamps are lit." filling a row whose last column is left empty); any other
empty cell fails the table, and so does one listed that is not blank.

`sections` names only the sections that are trait lists (matched by heading and page; a heading
set over two or more lines is given joined). A list's `traits.category` may be `"by-cost"` for a
section of advantages and disadvantages together: a cost printed with a minus makes a
disadvantage, any other an advantage, and `categories` ({name: category}) names exceptions.
A plan `entries` key may carry a page ("rules/example-contd@18") to reach one of several entries
of one name in the chapter (a running example's parts, each titled the same). A list's `traits`
can also say:

  * `"line": "skill"` when the line under a name is an attribute and a difficulty ("IQ/Hard"), and
    `"technique"` when it is a difficulty alone: read into `attribute` and `difficulty`; `"spell"`
    when it is a spell's class and what resists it ("Regular; Resisted by HT"): `class`, `resisted`;
  * `"marks": {"†": "specialties", "/TL": "tl"}` for marks printed after a name, each a
    true-or-false field (the name loses them, and `printed_name` keeps it as printed);
  * `"labels": {"Defaults": "defaults"}` for labelled paragraphs that are fields as well as text (a
    label naming several, a list of fields);
    `"fields_from": "start"` (the default), `"end"` or `"both"` says where in a trait's text its own
    labelled paragraphs are;
  * `"starred": "self_control"` to make a field of the asterisk a list prints after some costs;
  * `"no_cost_line": true` for a list whose traits print no line of their own because the
    section's text gives one cost for all (perks), with that cost under `fields`;
  * `"name_size"` for the size its traits' names are set in, when it is not the chapter's;
  * `"line": "points"` for a template's point total, read into `points`.

A section can be a list of creatures instead: `"creatures": {"kind": "animal", "name_size": 10.9,
"group_size": 13.9}`. A heading at either size whose text holds a stat line ("ST 4; DX 14; ...",
read by creatures.py) is a `creatures` entry: its description, then its stat block as a `profile`
(characteristics in printed order, then the labelled lines as printed), its `fields` the
characteristics as `attributes` and each labelled line under its label (`traits`, `skills`,
`cost`). A heading at the group size with no stat line is a group (an "Otters" over
two kinds of otter): an entry of its own, which each creature under it, up to the next heading
at the group size, `adds-to`. The report's `creature_groups` lists each group's members, and
`stat_lines` any part of a stat line read otherwise than as printed.

`trait_ends` lists headings ({page, text}) that end the trait before them: what follows, up to
the next trait, goes to the section's own entry ("ESP Abilities" after "ESP Talent").
`split_labelled` ({ref: {fields, except}}) makes each paragraph of that entry that opens with a
label ("*Body of Air:* ...") an entry of its own, named by the label, with the paragraphs after
it, adding to the entry it came from; a label in `except` ("Note") stays with that entry.

`--taken` (or `--library-data`, for every category index in a library-data folder) gives the slugs
the library holds: a trait of the same name as another source's, in the same category, becomes a
`version-of` it (docs/adr/0007); one of the same name as another chapter's of this source is an
error until the plan's `entries` gives it a `slug` of its own.

Writes OUT_DIR/<category>--<slug>.json and .md, `_records.json` (index records, each with
`_category`) and `_report.json`: `errors` (the conversion is not to be used while there are
any), `questions`, `left_out`, `dehyphenated`, `table_like` (lines spaced like table rows, to
be looked at on the page) and counts. Exit status 1 when there are errors.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from entry_text import (SMALL_WORDS, blocks_from_lines, fix_case, is_table_header, mark_paragraphs,  # noqa: E402
                        marked, plain, slugify, table_block, vocabulary, with_keyed_lists, with_text_tables)
from render_entry import render  # noqa: E402
from equipment_tables import take_tables  # noqa: E402
import creatures  # noqa: E402

# fields that hold words printed on the page
PRINTED_FIELDS = ('cost', 'types', 'see', 'attribute', 'difficulty', 'printed_name', 'class', 'resisted', 'points')
SKILL_LINE = re.compile(r'^(?P<attribute>(?:ST|DX|IQ|HT|Will|Per)(?: or (?:ST|DX|IQ|HT|Will|Per))*)/(?P<difficulty>[A-Z][A-Za-z ]+)$')
TECHNIQUE_LINE = re.compile(r'^(?P<difficulty>Average|Hard)$')
SPELL_CLASS = r'(?:Regular|Area|Information|Special|Missile|Melee|Blocking|Enchantment|Charm)'
# a spell's line: its classes, then what resists it, as printed ("Regular; Resisted by HT")
SPELL_LINE = re.compile(r'^(?P<spell_class>' + SPELL_CLASS + r'(?:; ' + SPELL_CLASS + r')*)(?:; (?P<resisted>Resist.*))?$')
SEE = re.compile(r'^see\b', re.I)
# a paragraph that opens with a label in bold or italic ("*Body of Air:* Your body ...")
LABELLED = re.compile(r'^(?P<marks>\*{1,3})(?P<label>[^*:]{2,60})(?::(?P=marks)|(?P=marks):)\s*(?P<rest>.*)$', re.S)


def near(a, b, tol=0.3):
    return abs(a - b) <= tol


def heading_text(run):
    """The words of a heading set over one or more lines, as printed."""
    return ' '.join(plain(marked(l)) for l in run)


def joining_words(l):
    """A heading line of nothing but small joining words ("AND", set smaller between "LAMPS" and
    "LANTERNS")."""
    words = plain(l['text']).lower().split()
    return bool(words) and all(w in SMALL_WORDS or w == '&' for w in words)


def group_headings(lines, is_heading):
    """[(kind, run of lines)]: consecutive heading lines of one size, close together, are one
    heading, and so are the lines either side of a line of joining words set in another size;
    every other line is its own run."""
    out = []
    for l in lines:
        prev = out[-1][1][-1] if out and out[-1][0] == 'heading' else None
        alike = prev is not None and (near(prev['size'], l['size']) or joining_words(l) or
                                      (joining_words(prev) and len(out[-1][1]) > 1 and near(out[-1][1][-2]['size'], l['size'])))
        if is_heading(l) and alike and prev['page'] == l['page'] and prev['column'] == l['column'] and \
                0 < l['baseline'] - prev['baseline'] < 1.6 * max(l['size'], prev['size']):
            out[-1][1].append(l)
        else:
            out.append(('heading' if is_heading(l) else 'line', [l]))
    return out


def split_name(text, icons):
    """'Clinging [physical] [exotic]' -> ('Clinging', ['physical', 'exotic'], '[physical] [exotic]').
    'X [mental]/[physical] [exotic]' gives all three, and the printed form says which are either/or."""
    pat = r'\[(' + '|'.join(map(re.escape, icons)) + r')\]'
    m = re.search(r'\s*' + pat, text)
    if not m:
        return text.strip(), [], ''
    tail = text[m.start():].strip()
    rest = re.sub(pat, '', tail)
    if rest.strip(' /,'):
        return None, [], tail                       # words after the icons: not a trait's name line
    return text[:m.start()].strip(), re.findall(pat, tail), tail


def table_like(l):
    """A body line spaced like a table's row: a gap between two of its words far wider than a
    word space."""
    ws = l.get('words') or []
    return any(b[1] - a[2] > 2.5 * l['size'] for a, b in zip(ws, ws[1:]))


def convert_chapter(layout, plan, taken=None, words=None, dictionary=None):
    taken = taken or {}
    report = {'errors': [], 'questions': [], 'left_out': [], 'dehyphenated': [], 'table_like': [], 'tables': [],
              'printed_fields': list(PRINTED_FIELDS), 'same_name': [], 'counts': {}}
    icons = plan.get('icons', [])
    name_size, cost_size = plan['name_size'], plan['cost_size']
    source, chapter = plan['source'], plan['chapter']
    box_plans = plan.get('boxes', {})
    lines = [l for l in layout['lines'] if not l.get('furniture')]
    for l in lines:
        if l.get('aside'):
            report['left_out'].append({'page': l['page'], 'text': l['text'], 'why': 'pull quote'})
    lines = [l for l in lines if not l.get('aside')]
    for spec in plan.get('leave_out_lines', []):
        hit = [l for l in lines if l['page'] == spec['page'] and l['text'].strip() == spec['text']]
        if not hit:
            report['errors'].append(f'plan leave_out_lines: no line {spec["text"]!r} on p{spec["page"]}')
        for l in hit:
            report['left_out'].append({'page': l['page'], 'text': l['text'], 'why': spec['why']})
        lines = [l for l in lines if not any(l is h for h in hit)]
    renames = {(r['page'], r['name'], r.get('section', '').lower()): r for r in plan.get('rename', [])}
    ended = set()                             # trait_ends headings found
    renamed = set()

    def rename_key(page, name, section):
        return next((k for k in ((page, name, section.lower()), (page, name, '')) if k in renames), None)
    vocab = vocabulary(lines)                         # the chapter's words,
    vocab |= set(words or ())                         # the book's when given,
    vocab |= {w.lower() for w in plan.get('whole_words', [])}      # and broken words the plan says are one word
    vocab |= {w.lower() for w in plan.get('hyphenated_words', [])}  # or says keep their hyphen
    vocab.dictionary = frozenset(dictionary or ())    # English words, for what the book prints nowhere else
    # the equipment tables the plan names: entries of their own, out of the text
    lines, table_entries = take_tables(lines, plan, report, vocab, source, chapter)
    if plan.get('indent', True):
        mark_paragraphs(lines)
    body = [l for l in lines if not l.get('box')]
    not_traits = {(n['page'], n['text']) for n in plan.get('not_traits', [])}
    trait_sections = {(s['page'], s['heading'].lower()): s for s in plan.get('sections', [])}
    used_sections = set()
    entries = list(table_entries)           # (category, entry)

    def add(category, name, first, section, fields, content_lines, level, base_size, extra=None):
        where = f'{category}/{slugify(name)}'
        content_lines = with_text_tables(content_lines, report, where)
        content_lines = with_keyed_lists(content_lines, report, where, vocab)
        blocks = blocks_from_lines(content_lines, report, where, vocab)
        for k, b in enumerate(blocks):
            # A table set in the text is read with the text round it: the paragraph before says
            # what it is a table of, the one after often carries it on ("further levels continue
            # to double") or closes it ("this table is not open-ended"). Say which are there.
            if b['type'] == 'table':
                b['read_with'] = [side for side, j in (('before', k - 1), ('after', k + 1))
                                  if 0 <= j < len(blocks) and blocks[j]['type'] == 'paragraph']
        entry = {'slug': slugify(name), 'name': name, 'source': source, 'chapter': chapter, 'section': section,
                 'page': first['page'], 'fields': fields, 'level': level, 'content': blocks}
        entry.update(extra or {})
        for l in content_lines:
            if not l.get('heading') and not l.get('block') and table_like(l):
                report['table_like'].append({'entry': where, 'page': l['page'], 'text': l['text']})
        entries.append((category, entry))
        return entry

    def creature_section(c, title, title_printed, head, inner, parent, level, size):
        """A section that is a list of creatures. A heading at the creatures' name size (or the
        groups') whose text holds a stat line is a creature; a heading at the group size with no
        stat line is a group ("Otters"), an entry of its own that the creatures under it add to."""
        sizes = [c['name_size']] + ([c['group_size']] if c.get('group_size') else [])
        starts = [j for j, (k, run) in enumerate(inner)
                  if k == 'heading' and any(near(run[0]['size'], s) for s in sizes)]
        intro = [l for _, run in inner[:starts[0] if starts else len(inner)] for l in run]
        if intro:
            add('rules', title, head[0], parent, dict(plan.get('rules_fields', {})), intro, level, size)
        else:
            report['left_out'].append({'page': head[0]['page'], 'text': title_printed,
                                       'why': 'a heading with nothing under it but other entries'})
        if not starts:
            report['errors'].append(f'p{head[0]["page"]}: creatures section {title!r} has no creature headings '
                                    f'at {sizes}')
        group = None                              # (slug, name) of the group open
        for m, j in enumerate(starts):
            name_run = inner[j][1]
            name, first = fix_case(heading_text(name_run)), name_run[0]
            rest = [l for _, run in inner[j + 1:starts[m + 1] if m + 1 < len(starts) else len(inner)] for l in run]
            at_group_size = bool(c.get('group_size')) and near(first['size'], c['group_size'])
            s = next((k for k, l in enumerate(rest) if creatures.is_stat_start(l)), None)
            if s is None:
                if not at_group_size:
                    report['errors'].append(f'p{first["page"]}: {name!r} has no stat line ("ST ...") in its text; '
                                            f'only a heading at the group size can be a group')
                    continue
                add('creatures', name, first, title, {'kind': c['kind']}, rest, first.get('heading', level + 1),
                    first['size'])
                group = (slugify(name), name)
                report.setdefault('creature_groups', []).append({'group': name, 'page': first['page'], 'members': []})
                continue
            if at_group_size:
                group = None                      # a creature headed like a group stands alone ("Herons")
            where = f'creatures/{slugify(name)}'
            profile, fields, after = creatures.stat_block(rest[s:], report, where, vocab)
            if profile is None:
                continue
            extra = {'relations': [{'role': 'adds-to', 'to': f'creatures/{group[0]}'}]} if group else {}
            entry = add('creatures', name, first, group[1] if group else title, dict(fields, kind=c['kind']),
                        rest[:s], first.get('heading', level + 1), first['size'], extra)
            entry['fields'] = dict({'kind': c['kind']}, **fields)
            entry['content'].append(dict(profile, name=name))
            entry['content'] += blocks_from_lines(after, report, where, vocab)
            if group:
                report['creature_groups'][-1]['members'].append(name)

    # --- sections of the page text -----------------------------------------------------------
    runs = group_headings(body, lambda l: bool(l.get('heading')))
    section_at = [i for i, (k, run) in enumerate(runs) if k == 'heading' and run[0]['size'] > name_size + 0.3]
    if not section_at or section_at[0] != 0:
        stray = [l for k, run in runs[:section_at[0] if section_at else len(runs)] for l in run]
        if stray and plan.get('intro'):
            # text before the first heading (the chapter's opening, its title set apart in a frame)
            add('rules', plan['intro']['name'], stray[0], plan['intro']['name'],
                dict(plan.get('rules_fields', {}), **plan['intro'].get('fields', {})), stray, 1, 1e9)
        elif stray:
            report['errors'].append(f'p{stray[0]["page"]}: text before the chapter\'s first heading: {stray[0]["text"][:60]!r}')
    parents = {}           # heading size -> the heading now open at that size
    for n, i in enumerate(section_at):
        head = runs[i][1]
        title_printed = heading_text(head)
        title = fix_case(title_printed)
        size = head[0]['size']
        parents = {s: t for s, t in parents.items() if s > size}
        parent = parents[min(parents)] if parents else title
        parents[size] = title
        end = section_at[n + 1] if n + 1 < len(section_at) else len(runs)
        inner = runs[i + 1:end]
        spec = trait_sections.get((head[0]['page'], title.lower())) or trait_sections.get((head[0]['page'], title_printed.lower()))
        level = head[0].get('heading', 1)
        if not spec:
            content = [l for _, run in inner for l in run]
            if content or n + 1 == len(section_at) or runs[section_at[n + 1]][1][0]['size'] >= size:
                if content:
                    add('rules', title, head[0], parent, dict(plan.get('rules_fields', {})), content, level, size)
                else:
                    report['questions'].append({'entry': f'rules/{slugify(title)}', 'kind': 'heading-only',
                                                'text': f'p{head[0]["page"]}: {title!r} has no text of its own'})
                    report['left_out'].append({'page': head[0]['page'], 'text': title_printed, 'why': 'a heading with nothing under it but other entries'})
            else:
                report['left_out'].append({'page': head[0]['page'], 'text': title_printed,
                                           'why': 'a heading with nothing under it but other entries'})
            continue
        used_sections.add((spec['page'], spec['heading'].lower()))
        if spec.get('creatures'):
            creature_section(spec['creatures'], title, title_printed, head, inner, parent, level, size)
            continue
        t = spec['traits']
        # split the section at its trait names
        starts = []
        for j, (k, run) in enumerate(inner):
            if k == 'heading' and near(run[0]['size'], t.get('name_size', name_size)) and \
                    (run[0]['page'], heading_text(run)) not in not_traits and \
                    (run[0]['page'], heading_text(run)) not in {(e['page'], e['text']) for e in plan.get('trait_ends', [])}:
                starts.append(j)
        intro = [l for _, run in inner[:starts[0] if starts else len(inner)] for l in run]
        # A heading the plan says ends the trait before it ("ESP Abilities" after "ESP Talent"):
        # what follows it, up to the next trait, is the section's, not the trait's.
        ends = {(e['page'], e['text']) for e in plan.get('trait_ends', [])}
        cut = {}                                  # start index -> where its trait ends
        for m_, j_ in enumerate(starts):
            stop = starts[m_ + 1] if m_ + 1 < len(starts) else len(inner)
            for k_ in range(j_ + 1, stop):
                kind_, run_ = inner[k_]
                if kind_ == 'heading' and (run_[0]['page'], heading_text(run_)) in ends:
                    cut[j_] = k_
                    ended.add((run_[0]['page'], heading_text(run_)))
                    intro += [l for _, run in inner[k_:stop] for l in run]
                    break
        if intro:
            add('rules', title, head[0], parent, dict(plan.get('rules_fields', {})), intro, level, size)
        else:
            report['left_out'].append({'page': head[0]['page'], 'text': title_printed,
                                       'why': 'a heading with nothing under it but other entries'})
        for m, j in enumerate(starts):
            name_run = inner[j][1]
            # as printed, an asterisk after it too (plain() would take that for a mark of emphasis)
            printed = ' '.join(l['text'].strip() for l in name_run)
            name, types, tail = split_name(printed, icons)
            page = name_run[0]['page']
            if name is None:
                report['errors'].append(f'p{page}: {printed!r}: words after the type icons; if this is not a '
                                        f'trait\'s name, list it in the plan\'s not_traits')
                continue
            # marks a list prints after a name (a dagger for "takes a specialty", /TL for a
            # skill that differs by tech level): fields of their own, and off the name
            marked_as = {field: False for field in t.get('marks', {}).values()}
            bare = name
            while any(bare.endswith(mk) for mk in t.get('marks', {})):
                mk = next(x for x in t['marks'] if bare.endswith(x))
                marked_as[t['marks'][mk]] = True
                bare = bare[:-len(mk)].rstrip()
            as_printed, name = name, bare
            printed_name, key = name, rename_key(page, name, title)
            again = {}
            if key:
                renamed.add(key)
                name = renames[key].get('to', name)
                # the same trait printed a second time in the chapter: its own file, marked as what it is
                if renames[key].get('slug'):
                    again['slug'] = renames[key]['slug']
                if renames[key].get('relation'):
                    again['relations'] = [renames[key]['relation']]
            rest = [l for _, run in inner[j + 1:cut.get(j, starts[m + 1] if m + 1 < len(starts) else len(inner))]
                    for l in run]
            cost_lines = []
            while not t.get('no_cost_line') and rest and near(rest[0]['size'], cost_size) and rest[0].get('heading') and \
                    rest[0]['page'] == (cost_lines or name_run)[-1]['page'] and \
                    0 < rest[0]['baseline'] - (cost_lines or name_run)[-1]['baseline'] < 1.8 * name_size and \
                    len(cost_lines) < 3 and (not cost_lines or abs(rest[0]['x1'] - cost_lines[0]['x1']) < 2.5):
                # A cost set over two lines keeps the right-hand edge of its first; a heading in the
                # trait's text ("Special Limitations") starts from the left.
                cost_lines.append(rest.pop(0))
            fields = {'kind': t['kind']}
            if key and name != printed_name:
                fields['printed_name'] = printed_name
            if types:
                fields['types'] = types
                if '/' in tail or ',' in tail:
                    fields['types_printed'] = tail
            if t.get('no_cost_line'):
                # A list whose traits print no cost of their own: the section's text gives one for
                # all of them (every perk costs 1 point), which the plan states in `fields`.
                if not rest:
                    report['errors'].append(f'p{page}: {name!r} has no text')
                    continue
                cost = None
            elif not cost_lines:
                report['errors'].append(f'p{page}: {name!r} has no cost line under its name; if it is not a '
                                        f'trait, list it in the plan\'s not_traits')
                continue
            else:
                # as printed, its asterisk too: plain() would take that for a mark of emphasis
                cost = ' '.join(l['text'].strip() for l in cost_lines)
            fields.update(marked_as)
            if as_printed != name:
                fields['printed_name'] = as_printed
            kind_of_line = t.get('line', 'cost')
            if cost is None:
                pass
            elif SEE.match(cost):
                fields['see'] = cost
            elif kind_of_line == 'points':
                fields['points'] = cost          # a template's point total, as printed
            elif kind_of_line == 'spell':
                # a spell's line gives its class (or classes) and, when it can be resisted, by what
                hit = SPELL_LINE.match(cost)
                if not hit:
                    report['errors'].append(f'p{page}: {name!r}: the line under its name, {cost!r}, is not a spell '
                                            f'class (and what resists it)')
                    continue
                fields['class'] = hit.group('spell_class')
                if hit.group('resisted'):
                    fields['resisted'] = hit.group('resisted')
            elif kind_of_line in ('skill', 'technique'):
                # a skill's line gives its controlling attribute and its difficulty ("IQ/Hard");
                # a technique's, its difficulty alone
                hit = (SKILL_LINE if kind_of_line == 'skill' else TECHNIQUE_LINE).match(cost)
                if not hit:
                    report['errors'].append(f'p{page}: {name!r}: the line under its name, {cost!r}, is not '
                                            + ('an attribute and a difficulty' if kind_of_line == 'skill' else 'a difficulty'))
                    continue
                fields.update(hit.groupdict())
            else:
                fields['cost'] = cost
                fields['leveled'] = bool(re.search(r'/\s*level', cost))
                if t.get('starred'):
                    # what the book's asterisk after a cost means in this list, as a field of its
                    # own (for disadvantages: the trait takes a self-control number)
                    fields[t['starred']] = cost.endswith('*')
            fields.update(t.get('fields', {}))
            category = t['category']
            if category == 'by-cost':
                # A section of advantages and disadvantages together: a cost printed with a minus
                # is a disadvantage's; the plan's `categories` names any other exception.
                category = t.get('categories', {}).get(name) or \
                    ('disadvantages' if re.match(r'^\s*[-−–]', cost or '') else 'advantages')
                fields['kind'] = {'advantages': 'advantage', 'disadvantages': 'disadvantage'}.get(category, fields['kind'])
            entry = add(category, name, name_run[0], title, fields, rest, name_run[0].get('heading', level + 1),
                        t.get('name_size', name_size), again)
            # labelled paragraphs the list gives each trait ("Defaults: IQ-5 or ..."): fields too,
            # as printed; they stay in the text where they are. Only the trait's own, which the
            # list sets in one place (its `fields_from`): at the start of the text, before anything
            # else (a skill's Defaults), or at its end (a spell's Duration and Cost, a template's
            # lists), after the last paragraph with a label of another kind (a specialty, an
            # example), tables and notes allowed among them. The same labels elsewhere belong to a
            # specialty or an example, and are passed over and listed.
            def label_of_block(b):
                if b['type'] != 'paragraph':
                    return None
                m = LABELLED.match(b['text'])
                if m:
                    return m.group('label').strip()
                label, colon, _ = plain(b['text']).partition(':')
                return label if colon and label in t.get('labels', {}) else None

            def labelled(b):
                label = label_of_block(b)
                if label not in t.get('labels', {}):
                    return None
                return label, plain(b['text']).partition(':')[2].strip()

            blocks = entry['content']
            where_from = t.get('fields_from', 'start')
            own = set()
            if where_from in ('start', 'both'):
                k = 0
                while k < len(blocks) and labelled(blocks[k]):
                    own.add(k)
                    k += 1
            if where_from in ('end', 'both'):
                # (a note after them, "Note: ...", is no label of another kind)
                notes = set(t.get('notes', ['Note', 'Notes']))
                others = [k for k, x in enumerate(blocks) if label_of_block(x) and not labelled(x) and
                          label_of_block(x) not in notes]
                after = others[-1] + 1 if others else 0
                own |= {k for k in range(after, len(blocks)) if labelled(blocks[k])}
            for k in sorted(own):
                label, rest_of = labelled(blocks[k])
                # a label can name several fields at once ("Duration, Cost, and Time to cast")
                targets = t['labels'][label]
                for field in [targets] if isinstance(targets, str) else targets:
                    entry['fields'].setdefault(field, rest_of)
            passed = [labelled(x)[0] for k, x in enumerate(blocks) if k not in own and labelled(x)]
            if passed:
                report.setdefault('labels_passed_over', []).append({'entry': f'{t["category"]}/{entry["slug"]}',
                                                                     'labels': passed})

    for e_ in plan.get('trait_ends', []):
        if (e_['page'], e_['text']) not in ended:
            report['errors'].append(f'plan trait_ends: no heading {e_["text"]!r} on p{e_["page"]} after a trait')
    for key in set(renames) - renamed:
        report['errors'].append(f'plan rename: no trait {key[1]!r} on p{key[0]}')
    for key in set(trait_sections) - used_sections:
        report['errors'].append(f'plan section {trait_sections[key]["heading"]!r} (p{key[0]}) matches no heading; '
                                f'headings found: ' + '; '.join(f'p{runs[i][1][0]["page"]} {fix_case(heading_text(runs[i][1]))}' for i in section_at))

    # --- boxes -------------------------------------------------------------------------------
    for region in layout.get('regions', []):
        bid = region['id']
        bl = [l for l in lines if l.get('box') == bid]
        bp = box_plans.get(bid, {})
        if not bl:
            continue
        if bp.get('leave_out'):
            report['left_out'] += [{'page': l['page'], 'text': l['text'], 'why': bp['leave_out']} for l in bl]
            continue
        if region.get('kind') == 'table':
            report['errors'].append(f'box {bid} (p{region["page"]}) is a ruled table: this converter does not read tables yet')
            continue
        if region.get('bands'):
            # A table on a tinted panel of its own, set beside or under the trait it belongs to
            # and often wider than a column. The page does not say whose it is; the plan does.
            target = bp.get('into')
            if not target and bp.get('name'):
                # a table panel that is an entry of its own: a rules entry of that name holding it
                own ={'slug': slugify(bp['name']), 'name': bp['name'], 'source': source, 'chapter': chapter,
                       'section': bp.get('section', bp['name']), 'page': bl[0]['page'],
                       'fields': dict(plan.get('rules_fields', {}), box=True), 'level': 2, 'content': []}
                entries.append(('rules', own))
                target = f'rules/{own["slug"]}'
            owner = next((e for c, e in entries if f'{c}/{e["slug"]}' == target), None)
            if owner is None:
                report['errors'].append(
                    f'box {bid} (p{region["page"]}) is a table on a panel of its own (it starts {bl[0]["text"][:40]!r}): '
                    + (f'the plan puts it `into` {target}, which is no entry of the chapter' if target else
                       'say which entry it belongs to with `into` in the plan\'s boxes'))
                continue
            # its title, when it has one: the plan says how many of its first lines are that
            title_lines, bl = bl[:bp.get('title_lines', 0)], bl[bp.get('title_lines', 0):]
            # and the lines of text between its title and its header ("This table lists the lamps ..."),
            # which go before the table as a paragraph
            lead, bl = bl[:bp.get('lead_lines', 0)], bl[bp.get('lead_lines', 0):]
            # and the lines of text after it, at the panel's foot, which go after it as a paragraph
            n_after = bp.get('after_lines', 0)
            bl, after = (bl[:-n_after], bl[-n_after:]) if n_after else (bl, [])
            k = next((i for i, l in enumerate(bl) if not is_table_header(l)), len(bl))
            if k == 0 or len(bl) - k < 2:
                report['errors'].append(f'box {bid} (p{region["page"]}): no header line and two rows to read as a table')
                continue
            block = table_block(bl[:k], bl[k:], report, target, ' '.join(l['text'] for l in title_lines), bp.get('fold'),
                                empty=[tuple(c) for c in bp.get('empty_cells', [])])
            if block is None:
                continue
            blocks = owner['content']
            at = len(blocks)
            if bp.get('under'):
                heads = [i for i, b in enumerate(blocks) if b['type'] == 'heading' and b['text'] == bp['under']]
                if not heads:
                    report['errors'].append(f'box {bid}: {target} has no heading {bp["under"]!r} to put the table under')
                    continue
                at = heads[0] + 1
            if bp.get('after_text'):
                # the paragraph that cites the table ("... on the table on p. 99."), by its opening words
                paras = [i for i, b in enumerate(blocks) if b['type'] == 'paragraph' and
                         plain(b['text']).startswith(bp['after_text'])]
                if len(paras) != 1:
                    report['errors'].append(f'box {bid}: {target} has {len(paras)} paragraphs opening '
                                            f'{bp["after_text"]!r} to put the table after; it needs one')
                    continue
                at = paras[0] + 1
            for b in blocks_from_lines(lead, report, target, vocab):
                blocks.insert(at, b)
                at += 1
            blocks.insert(at, block)
            for j, b in enumerate(blocks_from_lines(after, report, target, vocab)):
                blocks.insert(at + 1 + j, b)
            block['read_with'] = [side for side, j in (('before', at - 1), ('after', at + 1))
                                  if 0 <= j < len(blocks) and blocks[j]['type'] == 'paragraph']
            continue
        bruns = group_headings(bl, lambda l: bool(l.get('heading')))
        if bruns[0][0] != 'heading' and not bp.get('name'):
            report['errors'].append(f'box {bid} (p{region["page"]}) has no title: give it a name in the plan\'s boxes')
            continue
        title_run = bruns[0][1] if bruns[0][0] == 'heading' else []
        # Two sidebars can share a frame: a later heading as large as the box's title starts
        # another entry, named by that heading.
        parts = [[]]
        for k, (kind, run) in enumerate(bruns):
            if k and title_run and kind == 'heading' and run[0]['size'] >= title_run[0]['size'] - 0.3:
                parts.append([])
            parts[-1].append((kind, run))
        for n, part in enumerate(parts):
            head = part[0][1] if part[0][0] == 'heading' and (n or title_run) else []
            name = (bp.get('name') if n == 0 else None) or fix_case(heading_text(head))
            content = [l for _, run in part[1 if head else 0:] for l in run]
            extra = {'relations': [{'role': 'adds-to', 'to': bp['adds_to']}]} if bp.get('adds_to') and n == 0 else {}
            fields = dict(plan.get('rules_fields', {}), box=True)
            first = (head or part[0][1])[0]
            add('rules', name, first, bp.get('section', name) if n == 0 else name, fields, content,
                first.get('heading', 2), first['size'], extra)
    for bid in box_plans:
        if bid not in {r['id'] for r in layout.get('regions', [])}:
            report['errors'].append(f'plan box {bid} is not a box in the layout')

    # --- labelled paragraphs that are entries of their own --------------------------------------
    # ("Body of Air: ..." inside Elemental Meta-Traits: each a meta-trait, read with the group)
    for ref, how in plan.get('split_labelled', {}).items():
        owner = next((e for c, e in entries if f'{c}/{e["slug"]}' == ref), None)
        if owner is None:
            report['errors'].append(f'plan split_labelled: {ref} is no entry of the chapter')
            continue
        category = ref.split('/', 1)[0]
        keep, new, current = [], [], None
        for b in owner['content']:
            m = LABELLED.match(b.get('text', '')) if b['type'] == 'paragraph' else None
            if m and m.group('label') not in how.get('except', []):
                label = m.group('label')
                page = next((l['page'] for l in lines if plain(l['text']).startswith(label + ':')), owner['page'])
                current = {'slug': slugify(label), 'name': label, 'source': source, 'chapter': chapter,
                           'section': owner['name'], 'page': page, 'fields': dict(how.get('fields', {})),
                           'level': owner.get('level', 2) + 1, 'content': [dict(b, text=m.group('rest'))],
                           'relations': [{'role': 'adds-to', 'to': ref}]}
                new.append(current)
            elif current is not None and b['type'] != 'heading' and not m:
                current['content'].append(b)
            else:
                current = None
                keep.append(b)
        if not new:
            report['errors'].append(f'plan split_labelled: {ref} has no labelled paragraphs')
        owner['content'] = keep
        entries += [(category, e) for e in new]
        report.setdefault('split', []).append({'entry': ref, 'into': [e['name'] for e in new]})

    # --- slugs, the plan's own notes on entries, names shared with other sources --------------
    seen = {}
    kinds = {}
    out = []
    used_plans = set()
    for category, e in entries:
        ref = f'{category}/{e["slug"]}'
        # An entry of the plan's for one of several of a name in this chapter (a running example's
        # parts, each "(cont'd)"): keyed by its page as well, "rules/x@18", and given its slug first.
        paged = f'{ref}@{e["page"]}'
        if paged in plan.get('entries', {}):
            used_plans.add(paged)
            ep = plan['entries'][paged]
            if ep.get('slug'):
                e['slug'] = ep['slug']
                ref = f'{category}/{e["slug"]}'
            e['fields'].update(ep.get('fields', {}))
            e['relations'] = e.get('relations', []) + ep.get('relations', [])
            if not e['relations']:
                del e['relations']
            if ep.get('audience'):
                e['audience'] = ep['audience']
        if ref in seen and e['fields'].get('kind') and kinds[ref] and e['fields']['kind'] != kinds[ref]:
            # The book gives two different traits one name and tells them apart by their kind (an
            # enhancement and a limitation both called Armor Divisor), as the data files do: both
            # keep the name, the later takes its kind in its slug, and each is marked distinct.
            first = ref
            e['slug'] = f'{e["slug"]}-{slugify(e["fields"]["kind"])}'
            ref = f'{category}/{e["slug"]}'
            e.setdefault('relations', []).append({'role': 'distinct-from', 'to': first})
            report['same_name'].append({'entry': ref, 'same_name_as': first,
                                        'told_apart_by': f'kind: {e["fields"]["kind"]} / {kinds[first]}'})
        if ref in seen:
            report['errors'].append(f'{ref}: two entries of this chapter take this slug (p{seen[ref]} and p{e["page"]}); '
                                    f'give one a `slug` or `name` in the plan\'s entries')
            continue
        seen[ref] = e['page']
        kinds[ref] = e['fields'].get('kind')
        ep = {} if paged in used_plans else plan.get('entries', {}).get(ref, {})
        if ep.get('slug'):
            e['slug'] = ep['slug']           # the plan gives it a file name of its own
        e['fields'].update(ep.get('fields', {}))
        if ep.get('relations'):
            e['relations'] = e.get('relations', []) + ep['relations']
        if ep.get('audience'):
            e['audience'] = ep['audience']
        held = taken.get(category, {}).get(e['slug'])
        other, other_chapter = held if isinstance(held, tuple) else (held, None)
        if other == source and other_chapter not in (None, chapter):
            # another chapter of this book has an entry of this name in this category already
            report['errors'].append(f'{ref} (p{e["page"]}): {source} {other_chapter} already has an entry '
                                    f'{category}/{e["slug"]}; give this one a `slug` in the plan\'s entries '
                                    f'(and a relation, if the two are read together)')
            continue
        if other and other != source:
            if not any(r['to'] == ref for r in e.get('relations', [])):
                e.setdefault('relations', []).append({'role': 'version-of', 'to': ref})
            report['same_name'].append({'entry': ref, 'held_by': other})
            e['slug'] = f'{e["slug"]}-{slugify(source)}'
        if not e['content'] and 'see' not in e['fields']:
            report['errors'].append(f'{ref} (p{e["page"]}): no text')
        out.append((category, e))
    for ref in plan.get('entries', {}):
        if ref not in seen and ref not in used_plans:
            report['errors'].append(f'plan entry {ref} matches no entry of the chapter')
    for category, _ in out:
        report['counts'][category] = report['counts'].get(category, 0) + 1
    return out, report


def record(category, e):
    r = {'_category': category, 'slug': e['slug'], 'name': e['name'], 'source': e['source'],
         'chapter': e['chapter'], 'section': e['section'], 'page': e['page']}
    r.update({k: v for k, v in e['fields'].items() if k != 'box'})
    for k in ('relations', 'audience', 'gca'):
        if e.get(k):
            r[k] = e[k]
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('layout')
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--taken', action='append', default=[], metavar='CATEGORY=INDEX.json')
    ap.add_argument('--library-data', help='a library-data folder: every category index in it counts as --taken')
    ap.add_argument('--dictionary', help='English words, to settle a broken word the book prints nowhere else '
                                         '(joined when the joined word is one): `english-words` for the package '
                                         'of that name, or a file with one word to a line')
    ap.add_argument('--words', help='the words the whole book prints (book_words.py), to settle words broken '
                                    'at a line end that the chapter alone cannot')
    a = ap.parse_args(argv)
    with open(a.layout, encoding='utf-8') as f:
        layout = json.load(f)
    with open(a.plan, encoding='utf-8') as f:
        plan = json.load(f)
    taken = {}
    for t in a.taken:
        category, _, path = t.partition('=')
        with open(path, encoding='utf-8') as f:
            taken[category] = {r['slug']: (r['source'], r.get('chapter')) for r in json.load(f)}
    if a.library_data:
        for category in sorted(os.listdir(a.library_data)):
            path = os.path.join(a.library_data, category, '_index.json')
            if category not in taken and os.path.exists(path):
                with open(path, encoding='utf-8') as f:
                    taken[category] = {r['slug']: (r['source'], r.get('chapter')) for r in json.load(f)}
    words = None
    if a.words:
        with open(a.words, encoding='utf-8') as f:
            words = {w.strip() for w in f if w.strip()}
    dictionary = None
    if a.dictionary == 'english-words':
        try:
            from english_words import get_english_words_set
        except ImportError:
            sys.exit('--dictionary english-words needs the english-words package: pip install english-words')
        dictionary = get_english_words_set(['web2', 'gcide'], alpha=True, lower=True)
    elif a.dictionary:
        with open(a.dictionary, encoding='utf-8') as f:
            dictionary = {w.strip().lower() for w in f if w.strip()}
    entries, report = convert_chapter(layout, plan, taken, words, dictionary)
    os.makedirs(a.out, exist_ok=True)
    for old in os.listdir(a.out):
        if old.endswith(('.json', '.md')):
            os.remove(os.path.join(a.out, old))
    for category, e in entries:
        base = os.path.join(a.out, f'{category}--{e["slug"]}')
        with open(base + '.json', 'w', encoding='utf-8', newline='\n') as f:
            json.dump(e, f, ensure_ascii=False, indent=1)
            f.write('\n')
        with open(base + '.md', 'w', encoding='utf-8', newline='\n') as f:
            f.write(render(e))
    with open(os.path.join(a.out, '_records.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump([record(c, e) for c, e in entries], f, ensure_ascii=False, indent=1)
        f.write('\n')
    with open(os.path.join(a.out, '_report.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print(json.dumps({'counts': report['counts'], 'errors': len(report['errors']), 'questions': len(report['questions']),
                      'left_out': len(report['left_out']), 'table_like': len(report['table_like'])}))
    for e in report['errors']:
        print('error:', e, file=sys.stderr)
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
