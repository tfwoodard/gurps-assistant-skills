"""Text helpers shared by the converters: lines from pdf_layout.py -> entry text and blocks.

Pure functions, no I/O. Each takes the converter's `report` where it has something
to say, so nothing is decided silently.
"""
import re
import unicodedata

ROLL = re.compile(r'^\s*(\d{1,3})\s*(?:[–—-]\s*(\d{1,3}))?\s*$')
NUMBER = re.compile(r'^\s*([+−–-]?)\s*(\d{1,3}(?:,\d{3})*|\d+)\s*$')


def slugify(s):
    """'Lamp-Wright’s Öil' -> 'lamp-wrights-oil': accents dropped, apostrophes too."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = s.lower().replace('’', '').replace("'", '')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def norm(s):
    """For matching headings: lower case, straight quotes, single spaces."""
    return re.sub(r'\s+', ' ', s.replace('’', "'").replace('‘', "'")).strip().lower()


def marked(line):
    """A line's text with italic and bold spans marked as Markdown. Punctuation after a styled run
    stays outside its marks, and neighbouring italic runs join."""
    out = []
    for sp in line['spans']:
        m = re.match(r'^(.*?)([,;:.]*)$', sp['text'], re.S)
        t, tail = m.group(1), m.group(2)
        if not t:
            out.append(sp['text'])
            continue
        if sp['italic'] and sp['bold']:
            t = f'***{t}***'
        elif sp['italic']:
            t = f'*{t}*'
        elif sp['bold']:
            t = f'**{t}**'
        out.append(t + tail)
    return re.sub(r'(?<!\*)\*(\s+)\*(?!\*)', r'\1', ' '.join(out))


def plain(s):
    return re.sub(r'\*+', '', s).strip()


SMALL_WORDS = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'in', 'into', 'of', 'on', 'or', 'the',
               'to', 'with'}


ACRONYMS = {'GM', 'GMS', 'NPC', 'NPCS', 'PC', 'PCS', 'GURPS', 'ST', 'DX', 'IQ', 'HT', 'HP', 'FP', 'TL', 'DR', 'LC', 'SM'}   # kept in capitals


def fix_case(text):
    """Display type set in small capitals reads back in a jumble of cases ("CharaCteristiC and
    skill"), and titles set in capitals read back all in capitals. Such a heading is title-cased;
    the words stay the same. Anything else is unchanged."""
    letters = re.sub(r'[^A-Za-z]', '', text)
    all_caps = len(letters) >= 4 and letters.isupper()
    if not all_caps and not re.search(r'[a-z][A-Z]|\b[a-z]+[A-Z]|^[a-z]|\b[A-Z]{2}[a-z]', text):
        return text
    out = []
    parts = text.split(' ')
    for i, orig in enumerate(parts):
        w = orig.lower()
        core = re.sub(r'[^A-Za-z]', '', orig)
        if core.upper() in ACRONYMS:
            out.append(orig.upper())                        # an acronym (XP, SL) in capitals
        elif all_caps and re.fullmatch(r'\([A-Z]{2,3}\)', orig):
            out.append(orig)                                # a short abbreviation in brackets: "(PK)"
        elif re.fullmatch(r'[a-z]\.', orig):
            out.append(orig)                                # an abbreviation ("c." for circa)
        elif i and i < len(parts) - 1 and w in SMALL_WORDS and not out[-1].endswith(':'):   # not a title's last word
            out.append(w)
        else:
            k = next((j for j, ch in enumerate(w) if ch.isalpha()), 0)   # "(elves)" -> "(Elves)"
            w = w[:k] + w[k:k + 1].upper() + w[k + 1:]
            if all_caps:
                # each part of a hyphenated word set in capitals: "META-TRAITS" -> "Meta-Traits"
                w = re.sub(r'-([a-z])', lambda m: '-' + m.group(1).upper(), w)
            out.append(w)
    return ' '.join(out)


def split_items(s):
    """Split a printed list at commas outside parentheses."""
    items, depth, cur = [], 0, ''
    for ch in s:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            items.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        items.append(cur.strip())
    return items


class Vocabulary(set):
    """The words a book prints whole, with (optionally) a `dictionary` of English words beside
    them. The book's own words are the first evidence for how a broken word is spelt; the
    dictionary only settles the ones the book prints nowhere else."""
    dictionary = frozenset()


def vocabulary(lines):
    """Every word the lines print whole (not broken at a line end), lower-cased: the evidence for
    whether a word broken across lines is hyphenated or only split."""
    vocab = Vocabulary()
    broken = False                    # the line before ended in a hyphen
    for l in lines:
        words = l['text'].split()
        for i, w in enumerate(words):
            if i == len(words) - 1 and w.endswith('-'):
                continue              # the first half of a broken word
            if i == 0 and broken:
                continue              # and its second half, which is no word either
            vocab.add(re.sub(r'^[^\w]+|[^\w-]+$', '', w).lower())
        broken = bool(words) and words[-1].endswith('-')
    return vocab


SUFFIXES = ('’s', "'s", 'ing', 'ed', 'es', 'ly', 'er', 'ers', 's', 'd')


def known(word, vocab):
    """True when the book prints the word, or the word without one common ending ("reporting"
    when it prints "report"): a word seen only once, broken at a line's end, still has its kin
    elsewhere."""
    if word in vocab:
        return True
    for x in SUFFIXES:
        stem = word[:-len(x)]
        if word.endswith(x) and len(stem) >= 3:
            # "reporting" from "report"; "tuning" from "tune"
            if (len(stem) >= 4 and stem in vocab) or (x in ('ing', 'ed', 'er', 'ers') and stem + 'e' in vocab):
                return True
    return False


# endings that are words by themselves but only end a word when they follow a line-end hyphen
ENDINGS = {'less', 'lessly', 'lessness', 'ness', 'ment', 'ments', 'able', 'ably', 'ful', 'fully', 'ward', 'wards',
           'ship', 'hood', 'like', 'wise', 'some', 'ally', 'ing', 'ings', 'ion', 'ions'}


def join_lines(parts, report, where, vocab=None):
    """Join a run of line texts into one string. A line ending in a hyphen joins the next with no
    space. With `vocab` (the words the book prints whole: vocabulary(), book_words.py) each such
    hyphen is settled, and every decision is in the report:

      * a figure or an abbreviation beside it ("12-" / "hour", "HT-" / "5"): kept (`hyphens_kept`);
      * the book prints the hyphenated form elsewhere and not the joined one: kept (`hyphens_kept`);
      * it prints the joined word (or its kin: known()) and not the hyphenated: dropped
        (`dehyphenated`, which check_coverage.py credits);
      * it prints neither, and a half is no word by itself ("cer-" / "tificate"): dropped
        (`dehyphenated`, with why);
      * it prints neither, and the second half is only an ending ("noise-" / "lessly"): dropped;
      * it prints both, or neither and both halves are words ("near-" / "perfect"): kept as a
        compound (`hyphens_kept`, with why). A converter's plan lists the few of these that
        should be one word.

    A styled run that carries on over the line break is marked once."""
    out = ''
    for p in parts:
        end = re.search(r'-(\*{0,3})$', out)
        if not out:
            out = p
        elif end:
            marks = end.group(1)
            if marks and p.startswith(marks) and not p.startswith(marks + '*'):
                out, p = out[:-len(marks)], p[len(marks):]     # one styled run across the line break
            head = re.search(r'([\w’\']+)-$', out)
            tail = re.match(r'^\*{0,3}([\w’\']+)', p)
            if vocab is not None and head and tail:
                h, t = head.group(1), tail.group(1)
                whole, hyph = (h + t).lower(), (h + '-' + t).lower()
                shown = out[-20:] + p[:20]
                if re.search(r'\d', h + t) or (h.isupper() and len(h) > 1):
                    # a figure or an abbreviation beside the hyphen: a range, "12-hour", "HT-5"
                    report.setdefault('hyphens_kept', []).append(
                        {'entry': where, 'text': shown, 'why': 'a figure or an abbreviation'})
                    out += p
                    continue
                if t.lower() in ('or', 'and', 'nor'):
                    # a hanging hyphen: "stealth-" / "or invisibility-based" is "stealth- or ..."
                    report.setdefault('hyphens_kept', []).append(
                        {'entry': where, 'text': out[-20:] + ' ' + p[:20], 'why': 'a hanging hyphen before a conjunction'})
                    out += ' ' + p
                    continue
                whole_known, hyph_known = known(whole, vocab), known(hyph, vocab)
                dictionary = getattr(vocab, 'dictionary', None)
                if not whole_known and not hyph_known and dictionary and known(whole, dictionary):
                    # The book prints neither form elsewhere, but the joined word is an English
                    # word ("for-" / "got", "kit-" / "tens"), which a compound of two words
                    # ("near-" / "perfect") is not.
                    report.setdefault('dehyphenated', []).append(
                        {'entry': where, 'from': h + '-' + t, 'to': h + t, 'why': 'an English word, by the dictionary'})
                    out = out[:-1] + p
                    continue
                if hyph_known and not whole_known:
                    report.setdefault('hyphens_kept', []).append(
                        {'entry': where, 'text': shown, 'why': 'the book prints it hyphenated elsewhere'})
                    out += p
                    continue
                if whole_known and not hyph_known:
                    report.setdefault('dehyphenated', []).append({'entry': where, 'from': h + '-' + t, 'to': h + t})
                    out = out[:-1] + p
                    continue
                if not whole_known and not hyph_known:
                    halves = known(h.lower(), vocab) and known(t.lower(), vocab)
                    if not halves or t.lower() in ENDINGS:
                        # Neither form is printed elsewhere, and a half is no word by itself
                        # ("cer-" / "tificate") or the second is only an ending ("noise-" /
                        # "lessly"): the hyphen only marks the break.
                        why = 'a half is not a word by itself' if not halves else 'the second half is only an ending'
                        report.setdefault('dehyphenated', []).append(
                            {'entry': where, 'from': h + '-' + t, 'to': h + t, 'why': why})
                        out = out[:-1] + p
                        continue
                # Both forms are printed elsewhere, or neither is and both halves are words
                # ("near-" / "perfect", "mail-" / "room"): kept hyphenated, as a compound. This is
                # the one case decided without evidence from the book; the plan's `whole_words`
                # joins the ones that should be one word.
                report.setdefault('hyphens_kept', []).append(
                    {'entry': where, 'text': shown, 'why': 'the book prints both forms' if hyph_known else
                     'both halves are words, and the book prints neither form elsewhere'})
                out += p
                continue
            elif vocab is not None and (re.match(r'^\*{0,3}\d', p) or re.search(r'[)\]]-$', out)):
                # a figure after it, or a bracket before it ("Engineer (same)-" / "4"): a modifier
                report.setdefault('hyphens_kept', []).append(
                    {'entry': where, 'text': out[-20:] + p[:20], 'why': 'a figure or an abbreviation'})
                out += p
                continue
            elif vocab is not None and re.search(r'\s-$', out):
                # A dash standing by itself at the line's end ("roll vs. IQ -" / "Complexity") is a
                # minus sign or a dash between words, not a broken word: the next word follows it.
                report.setdefault('hyphens_kept', []).append(
                    {'entry': where, 'text': out[-20:] + ' ' + p[:20], 'why': 'a dash standing by itself, not a broken word'})
                out += ' ' + p
                continue
            else:
                kind = 'hyphen-join'
            report['questions'].append({'entry': where, 'kind': kind, 'text': out[-20:] + p[:20]})
            out += p
        else:
            m = re.search(r'(?<!\*)(\*{1,3})$', out)
            if m and p.startswith(m.group(1)) and not p.startswith(m.group(1) + '*'):
                out = out[:-len(m.group(1))] + ' ' + p[len(m.group(1)):]   # one styled run across the break
            else:
                out += ' ' + p
    return out


def runs_on(prev, l):
    """A sentence carried into the next column or page: the line before stops without closing
    punctuation and this one starts in lower case."""
    return (not re.search(r'[.!?:;]["”’)]*$', plain(prev['text'])) and
            bool(re.match(r'^[a-z]', plain(l['text']))))


SENTENCE_END = re.compile(r'[.!?:…]["”’)\]]*\**$')
INDENT = (5.0, 22.0)                  # points: a paragraph's first line starts this much further in


def mark_paragraphs(lines):
    """For books that show a new paragraph by indenting its first line, with no space above it:
    give every line `para` (True where a paragraph starts), which new_paragraph() then goes by.

    A line starts a paragraph when it stands in from the line below it in its column (or, for a
    paragraph of one line, from the line above) and the line above it ends a sentence or isn't in
    its column. Lines that step sideways round a picture don't end sentences, so they aren't
    taken for paragraphs. A column's first line that isn't indented carries on the paragraph
    before it, wherever that broke."""
    def group(l):
        return (l['page'], l['column'], l.get('box'))

    body = [l for l in lines if not l.get('heading')]
    pos = {id(l): i for i, l in enumerate(lines)}
    hang = None                       # (group, x0) of a labelled line set flush, its later lines hanging
    edge = {}                         # each column's left edge: the least x0 of its lines
    for l in body:
        edge[group(l)] = min(edge.get(group(l), l['x0']), l['x0'])
    for i, l in enumerate(body):
        prev = body[i - 1] if i and group(body[i - 1]) == group(l) and pos[id(body[i - 1])] == pos[id(l)] - 1 and \
            0 < l['baseline'] - body[i - 1]['baseline'] < 2.5 * l['size'] else None
        nxt = body[i + 1] if i + 1 < len(body) and group(body[i + 1]) == group(l) and \
            pos[id(body[i + 1])] == pos[id(l)] + 1 and 0 < body[i + 1]['baseline'] - l['baseline'] < 2.5 * l['size'] else None
        ended = prev is None or bool(SENTENCE_END.search(plain(prev['text'])))
        if nxt is not None and INDENT[0] <= l['x0'] - nxt['x0'] <= INDENT[1]:
            l['para'] = ended
        elif prev is not None and prev.get('para') and abs(l['x0'] - prev['x0']) < 1.5:
            l['para'] = ended                      # one-line paragraphs, one after another
        elif prev is not None and INDENT[0] <= l['x0'] - prev['x0'] <= INDENT[1]:
            l['para'] = ended                      # a one-line paragraph that ends its column
        elif prev is None and INDENT[0] <= l['x0'] - edge[group(l)] <= INDENT[1]:
            # a one-line paragraph under a heading, or opening a column; but not where the column
            # before broke off mid-sentence (a hanging list carried over: "... [-20];" / "Supernatural ...")
            before = body[i - 1] if i and pos[id(body[i - 1])] == pos[id(l)] - 1 else None
            l['para'] = not (before is not None and before.get('box') == l.get('box') and
                             re.search(r'[;,]\**$', plain(before['text']).rstrip()))
        else:
            l['para'] = False
        if hang and hang[0] == group(l) and l['x0'] > hang[1] + INDENT[0] - 1 and not starts_with_label(l):
            l['para'] = False                      # a line hanging under a flush labelled line
        elif not l['para'] and ended and starts_with_label(l):
            # a labelled line set flush, its own lines hanging under it ("Attributes: ST 10 [0];")
            l['para'] = True
        if starts_with_label(l) and l['para'] and abs(l['x0'] - edge[group(l)]) < 1.5:
            hang = (group(l), l['x0'])
        elif l['para'] or not hang or hang[0] != group(l) or l['x0'] <= hang[1] + 1:
            hang = None
    return lines


def starts_with_label(l):
    """True when a line opens with a label in bold or italic ending in a colon ("Attributes:")."""
    first = next((sp for sp in l.get('spans') or [] if sp['text'].strip()), None)
    if not first or not (first['bold'] or first['italic']):
        return False
    lead = first['text'].strip()
    if not re.match(r'^[^\W\d_][^:]{0,40}:$', lead):
        return False
    rest = [sp for sp in l['spans'][l['spans'].index(first) + 1:] if sp['text'].strip()]
    # the label alone on its line, or followed by text in another style
    return not rest or not (rest[0]['bold'] == first['bold'] and rest[0]['italic'] == first['italic'])


def new_paragraph(l, prev):
    if prev is None or l.get('box') != prev.get('box') or l.get('scrap') != prev.get('scrap'):
        return True
    if 'para' in l:                   # the book indents its paragraphs: mark_paragraphs() has read them
        return l['para']
    if l['column'] != prev['column'] or l['page'] != prev['page'] or l['baseline'] < prev['baseline']:
        return not runs_on(prev, l)
    return l['baseline'] - prev['baseline'] > 1.6 * prev['size']


def strip_bullet(text):
    """An item's text without its bullet, keeping the marks it shares with the words after it
    ("**• Name**: ..." -> "**Name**: ..."); marks around the bullet alone go with it."""
    t = re.sub(r'^\s*(\**)\s*[•●▪]\s*', r'\1', text)
    m = re.match(r'^(\*{1,3})\1(?=\s)\s*', t)          # "**•** Name" left an empty pair
    return t[m.end():] if m else t


def ends_fields(run, l, labels):
    """True when `l` starts the prose after a run of labelled field lines ("Motive: ...", "Aim:
    ..." under a name, then the biography with no blank line between): the run opens with one of
    `labels` in bold, its last line stops well short of the widest line of the run and `l`, and
    `l` starts a sentence without a label of its own."""
    if not run or not labels:
        return False
    known = {x.lower() for x in labels}
    if (label_of(run[0]) or '').lower() not in known or (label_of(l) or '').lower() in known:
        return False
    last = run[-1]
    return (last['x1'] < max(x['x1'] for x in run + [l]) - 3 * last['size'] and
            bool(re.match(r'^[A-Z‘“"\'(]', plain(l['text']))))


def blocks_from_lines(lines, report, where, vocab=None, base_level=None, field_labels=()):
    """Lines -> content blocks: headings (lines marked `heading` by pdf_layout.py, at a smaller size
    than the entry's own when `base_level` is given), bulleted lists (lines starting "•"), and
    paragraphs (a new one at a column, page or box change or a wider gap, and, with the entry's
    `field_labels`, where its labelled field lines end: ends_fields()). A line carrying a
    `block` (merge_lines()) is that block, and ends the paragraph before it."""
    blocks, buf, items, prev, bullet_x0 = [], [], [], None, None
    printed = {}                  # id(heading block) -> its words as printed
    run = []                      # the lines of the paragraph being read

    def flush():
        nonlocal buf, items, run
        run = []
        if buf:
            blocks.append({'type': 'paragraph', 'text': join_lines(buf, report, where, vocab)})
        if items:
            blocks.append({'type': 'list', 'ordered': False,
                           'items': [join_lines(i, report, where, vocab) for i in items]})
        buf, items = [], []

    for l in lines:
        if l.get('block'):            # lines a converter already read as one block (a table, fields)
            flush()
            blocks.append(l['block'])
            prev = None
            continue
        text = marked(l)
        if l.get('heading') and (base_level is None or l['heading'] > base_level):
            flush()
            if blocks and blocks[-1]['type'] == 'heading' and prev is not None and prev.get('heading') == l['heading'] \
                    and l['baseline'] - prev['baseline'] < 1.6 * l['size']:
                # One heading, two lines: its case is fixed as a whole, from the words as printed
                # (a first line already title-cased would hide that the second is in capitals).
                printed[id(blocks[-1])] += ' ' + plain(text)
                blocks[-1]['text'] = fix_case(printed[id(blocks[-1])])
            else:
                blocks.append({'type': 'heading', 'level': l['heading'], 'text': fix_case(plain(text))})
                printed[id(blocks[-1])] = plain(text)
            prev = l
            continue
        bullet = re.match(r'^\s*[•●▪]\s*', plain(l['text']))
        if bullet:
            if buf:
                flush()
            items.append([strip_bullet(text)])
            bullet_x0 = l['x0']
        elif items and prev is not None and not new_paragraph(l, prev) and l['x0'] > bullet_x0 + 1:
            items[-1].append(text)
        else:
            if items or new_paragraph(l, prev) or ends_fields(run, l, field_labels):
                flush()
            buf.append(text)
            run.append(l)
        prev = l
    flush()
    return blocks


def cell_value(s):
    """A table cell as data: "—" is None; "+N", "−N" and plain numbers are numbers; a roll ("01–09",
    "00") is {"min", "max"}; anything else is the printed text."""
    t = plain(s).strip()
    if t in ('—', '–', '-', ''):
        return None
    m = NUMBER.match(t)
    if m:
        n = int(m.group(2).replace(',', ''))
        return -n if m.group(1) in ('−', '–', '-') else n
    return t


def roll_value(s):
    m = ROLL.match(plain(s))
    if not m:
        return cell_value(s)
    lo, hi = m.group(1), m.group(2) or m.group(1)
    to_n = lambda v: 100 if v in ('00', '000') else int(v)
    return {'min': to_n(lo), 'max': to_n(hi)}


def table_data(columns, rows, report, where, roll_column=None):
    """Rows of cells -> `data`: one object per row keyed by the column headers in words. An empty
    cell in a leading column, under a cell that isn't, takes the value above (a cell printed once
    for several rows); every such fill is reported."""
    keys = [slugify(c).replace('-', '_') or f'column_{i + 1}' for i, c in enumerate(columns)]
    data, above = [], {}
    for r, row in enumerate(rows):
        obj = {}
        lead = True
        for i, (k, cell) in enumerate(zip(keys, row)):
            if not cell.strip() and lead and i in above and any(c.strip() for c in row[i + 1:]):
                obj[k] = above[i]
                report.setdefault('filled_down', []).append({'entry': where, 'row': r + 1, 'column': columns[i] if
                                                             i < len(columns) else k})
                continue
            if cell.strip():
                lead = False
            obj[k] = roll_value(cell) if i == roll_column else cell_value(cell)
            above[i] = obj[k]
        data.append(obj)
    return data


def merge_lines(run, block):
    """A run of lines -> one line that carries `block` in their place: it keeps the first line's
    position, so placement by position still works, and all their text, for the vocabulary."""
    first = run[0]
    return dict(first, text=' '.join(x['text'] for x in run), block=block,
                spans=[s for x in run for s in x['spans']],
                x1=max(x['x1'] for x in run), baseline=run[-1]['baseline'])


def split_row(line, n):
    """A line of an unruled table -> its n cells, split at the n-1 widest gaps between words."""
    words = line['words']
    if len(words) < n:
        return None
    gaps = sorted(range(len(words) - 1), key=lambda i: words[i + 1][1] - words[i][2], reverse=True)[:n - 1]
    cells, start = [], 0
    for g in sorted(gaps):
        cells.append(' '.join(w[0] for w in words[start:g + 1]))
        start = g + 1
    cells.append(' '.join(w[0] for w in words[start:]))
    return cells


def label_of(line):
    """The bold label a line starts with ("Max:" -> "Max"), or None."""
    sp = line['spans'][0] if line.get('spans') else None
    if sp and sp['bold'] and not sp['italic'] and sp['text'].rstrip().endswith(':'):
        return sp['text'].rstrip()[:-1].strip()
    return None


def field_text(run):
    """The words after the label, across the run's lines."""
    return plain(re.sub(r'^\s*\S[^:]*:\s*', '', ' '.join(x['text'] for x in run), count=1))


def top_fields(seg, labels, report, name, usual=()):
    """The field lines an entry opens with ("Max: 2", "Range: Touch"), each a bold label in
    `labels` (printed label, lower case -> field name). A field runs on to the next line when that
    line starts in lower case, the field has an unclosed bracket, or it stops on a word that
    cannot end it ("... a weapon with the"); each run-on is listed under the
    report's `field_lines_joined`, a label printed other than as in `usual` under
    `labels_as_printed`, and a label among them not set in bold under `labels_not_bold`. Returns (how many lines were read, one line carrying the fields block or
    None, {field name: text})."""
    fields, items, k = {}, [], 0
    while k < len(seg):
        lab = label_of(seg[k])
        if not lab and k and not seg[k].get('block'):
            # Among the field lines, a label the book forgot to set in bold.
            m = re.match(r'^\s*([A-Za-z]+):', plain(seg[k]['text']))
            if m and m.group(1).lower() in labels:
                lab = m.group(1)
                report.setdefault('labels_not_bold', []).append({'entry': name, 'label': lab})
        if not lab or lab.lower() not in labels:
            break
        run = [seg[k]]
        while k + len(run) < len(seg):
            nxt = seg[k + len(run)]
            text = field_text(run)
            if label_of(nxt) or nxt.get('heading') or nxt.get('box') or nxt.get('block'):
                break
            if not (re.match(r'^[a-z]', plain(nxt['text'])) or text.count('(') > text.count(')') or
                    re.search(r'\b(the|a|an|with|of|to|and|or|for|in|on)$', text)):
                break
            run.append(nxt)
            report.setdefault('field_lines_joined', []).append({'entry': name, 'label': lab, 'text': field_text(run)})
        if usual and lab.lower() not in usual:
            report.setdefault('labels_as_printed', []).append({'entry': name, 'label': lab})
        fields[labels[lab.lower()]] = field_text(run)
        items.append({'label': lab, 'text': field_text(run)})
        k += len(run)
    if not k:
        return 0, None, {}
    return k, merge_lines(seg[:k], {'type': 'fields', 'title': '', 'items': items}), fields


def block_fields(seg, labels, report, name):
    """The block of labelled fields an entry opens with when its fields run to several lines and
    two can share one ("CN: 12 Type: Lore of Lamps", then "Ingredients: ..." over three lines):
    every line up to the first blank line, or to a change of column or page where the line
    before ends its sentence. Each bold label in `labels` (printed label, lower case -> field
    name) starts a field, wherever on its line it stands; the field is the text up to the next
    label. A bold "Word:" in the block that isn't one of the labels is an error. Returns (how
    many lines were read, one line carrying the fields block or None, {field name: text})."""
    if not seg or (label_of(seg[0]) or '').lower() not in labels:
        return 0, None, {}
    k = 1
    while k < len(seg):
        prev, l = seg[k - 1], seg[k]
        if l.get('heading') or l.get('box') or l.get('block'):
            break
        if l['column'] != prev['column'] or l['page'] != prev['page'] or l['baseline'] < prev['baseline']:
            if not label_of(l) and re.search(r'[.!?]["”’)]*$', plain(prev['text'])):
                break
        elif l['baseline'] - prev['baseline'] > 1.6 * prev['size']:
            break
        k += 1
    items = []                           # [label as printed, [line fragments]]
    for l in seg[:k]:
        fresh = True                     # a field's text on a new line is a new fragment
        for sp in l['spans']:
            text = sp['text'].strip()
            if sp['bold'] and not sp['italic'] and text.endswith(':'):
                if text[:-1].strip().lower() not in labels:
                    report['errors'].append({'error': f'{name}: label {text!r} among its fields is not one '
                                                      f'of {sorted(labels)}'})
                items.append([text[:-1].strip(), []])
                fresh = True
            elif items and text:
                if fresh:
                    items[-1][1].append(text)
                else:
                    items[-1][1][-1] += ' ' + text
                fresh = False
    block = {'type': 'fields', 'title': '',
             'items': [{'label': lab, 'text': join_lines(parts, report, name)} for lab, parts in items]}
    fields = {labels[i['label'].lower()]: i['text'] for i in block['items'] if i['label'].lower() in labels}
    return k, merge_lines(seg[:k], block), fields


# --- tables set in the text, without rules ---------------------------------------------------

ROW_LEADING = 1.35       # x the type size: lines further apart than this are not rows of one table
COLUMN_GAP = 0.5         # x the type size: the least width of the blank between two columns (a word space is about a quarter)
ALIGN_TOLERANCE = 2.5    # points: how far a column's cells may stray from its common edge or centre
PHRASE_GAP = 0.8         # x the type size: words of a header further apart than this are different phrases


def is_table_header(l):
    """A line of a text table's header: set wholly in bold italic at the size of the text. Spans
    with no letters in them (a multiplication sign from a symbol font) don't count either way."""
    lettered = [s for s in l.get('spans') or [] if re.search(r'[^\W\d_]', s['text'])]
    # (a line ending in a colon is a label for the text after it, not a header)
    return (not l.get('heading') and not l.get('block') and bool(lettered) and
            all(s['bold'] and s['italic'] for s in lettered) and not plain(l['text']).rstrip().endswith(':'))


def read_text_table(header, rows):
    """Header line(s) and the row lines under them -> (columns, rows of cells, banners, failures).

    The columns are the blanks that every row leaves clear: no row has a word there. A header can
    be set over several lines. Each of its phrases (words a word space apart) names the column it
    stands over, the lines read downwards ("Self-Control" over "Number"). A phrase that reaches
    across the blank between two columns is a banner over the columns it spans, and over any
    unnamed columns to their right ("Wounding Multiplier" over "×2", "×3", "×4").

    `failures` says, in words, everything about the table that does not check out; an empty list
    means it was read with nothing left to doubt:

      * the rows leave at least one blank column between them;
      * every row has something in every column;
      * every column has a name in the header or stands under a banner;
      * each column's cells line up: left edges, right edges, centres, or figures ending together."""
    headers = header if isinstance(header, list) else [header]
    size = headers[0]['size']
    shown = ' / '.join(h['text'] for h in headers)
    failures = []
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
    if not seps:
        return [], [], [], ['its rows leave no blank column between them: it reads as one column']
    ncols = len(seps) + 1
    edges = [float('-inf')] + seps + [float('inf')]

    def column_of(x):
        return next(i for i in range(ncols) if edges[i] <= x < edges[i + 1])

    def cells(l):
        out = [[] for _ in range(ncols)]
        for w in l['words']:
            out[column_of((w[1] + w[2]) / 2)].append(w)
        return out

    grid = [cells(l) for l in rows]
    extent = []                       # each column's cells, from their leftmost edge to their rightmost
    for c in range(ncols):
        ws = [w for r in grid for w in r[c]]
        extent.append((min(w[1] for w in ws), max(w[2] for w in ws)) if ws else (edges[c], edges[c]))

    # --- the header: phrases, each a column's name or a banner over several ---------------------
    names = [[] for _ in range(ncols)]
    banners = []
    for h in headers:
        phrases = []
        for w in h['words']:
            if phrases and w[1] - phrases[-1][-1][2] <= PHRASE_GAP * size:
                phrases[-1].append(w)
            else:
                phrases.append([w])
        # A banner is one phrase standing over the cells of two or more columns. A name wider
        # than its own column's cells (a long name over a column of short figures) reaches into
        # the blank beside them, perhaps past its middle, but not over the next cells.
        spans = []
        for ph in phrases:
            x0, x1 = ph[0][1], ph[-1][2]
            over = [c for c in range(ncols) if min(x1, extent[c][1]) - max(x0, extent[c][0]) >= 0.4 * size]
            spans.append((ph, x0, x1, over))
        own = set()                    # columns with a phrase of their own on this line
        for ph, x0, x1, over in spans:
            if len(over) < 2:
                c = over[0] if over else column_of((x0 + x1) / 2)
                names[c].append(' '.join(w[0] for w in ph))
                own.add(c)
        for ph, x0, x1, over in spans:
            if len(over) < 2:
                continue
            text = ' '.join(w[0] for w in ph)
            # Which columns it is a banner over: a run of columns holding those it stands over,
            # none of them named beside it on its own line, such that it is centred on the run or
            # starts where the run starts. (Its ends may fall short of the outer columns' cells,
            # so overlap alone can miss one.) Of runs that fit equally, the widest.
            runs = [(a, b) for a in range(over[0] + 1) for b in range(over[-1], ncols)
                    if not any(c in own for c in range(a, b + 1))]
            mid = (x0 + x1) / 2
            centred = [(b - a, -abs(mid - (extent[a][0] + extent[b][1]) / 2), a, b) for a, b in runs
                       if abs(mid - (extent[a][0] + extent[b][1]) / 2) <= size]
            started = [(b - a, -abs(x0 - extent[a][0]), a, b) for a, b in runs if abs(x0 - extent[a][0]) <= size]
            # centred on a run if it is on any (the widest such: cells are narrower than the names
            # over them, so a banner centred on four columns is centred on the middle two as well);
            # failing that, starting where a run starts
            best = max(centred) if centred else max(started) if started else None
            if best is None:
                failures.append(f'the banner {text!r} in its header is neither centred over a run of columns nor '
                                f'starts with one')
            if best is not None:
                banners.append({'text': text, 'from': best[2], 'to': best[3]})
    columns = [' '.join(parts) for parts in names]
    for b in banners:                          # a banner runs on over unnamed columns to its right
        while b['to'] + 1 < ncols and not columns[b['to'] + 1] and \
                not any(o is not b and o['from'] <= b['to'] + 1 <= o['to'] for o in banners):
            b['to'] += 1
    for c in range(ncols):
        if not columns[c] and not any(b['from'] <= c <= b['to'] for b in banners):
            failures.append(f'its header has no words over column {c + 1}: {shown!r}')
    if not any(columns):
        failures.append(f'its header names no column of its own: {shown!r}')
    banners = [{'text': b['text'], 'columns': [b['from'] + 1, b['to'] + 1]} for b in banners]

    # --- the rows ---------------------------------------------------------------------------
    out_rows = [[' '.join(w[0] for w in c) for c in r] for r in grid]
    for i, r in enumerate(out_rows):
        if any(not c for c in r):
            failures.append(f'row {i + 1} has nothing in column {r.index("") + 1}: {rows[i]["text"]!r}')
    for c in range(ncols):
        col = [r[c] for r in grid if r[c]]
        if len(col) < 2:
            continue
        # Where a cell can line up with the others: its left edge, its right edge, its centre, or
        # the end of its first word (figures set to end together, their units after them: "8
        # seconds" over "15 seconds"). Each way has its line: the place most cells share. A cell
        # must stand on one of those lines, and a line counts only when two or more cells share it.
        ways = {'left': [w[0][1] for w in col], 'right': [w[-1][2] for w in col],
                'centre': [(w[0][1] + w[-1][2]) / 2 for w in col], 'figure': [w[0][2] for w in col]}
        lines_ = {}
        for way, xs in ways.items():
            best = max(xs, key=lambda x: sum(1 for y in xs if abs(x - y) <= ALIGN_TOLERANCE))
            if sum(1 for y in xs if abs(best - y) <= ALIGN_TOLERANCE) >= 2:
                lines_[way] = best
        stray = [k for k in range(len(col))
                 if not any(abs(ways[way][k] - x) <= ALIGN_TOLERANCE for way, x in lines_.items())]
        if stray:
            texts = ', '.join(repr(' '.join(w[0] for w in col[k])) for k in stray[:4])
            failures.append(f'in column {c + 1} ({columns[c] or "no name"}), {texts} '
                            f'{"does" if len(stray) == 1 else "do"} not line up with the other cells')
    return columns, out_rows, banners, failures


def table_block(headers, rows, report, where, title='', fold=None):
    """Read one text table and note it in the report's `tables`. Returns its block, or None when
    a check failed (the failure is in the report's `errors`, and nothing is written on a guess)."""
    columns, cells, banners, failures = read_text_table(headers, rows)
    shown = ' / '.join(h['text'] for h in headers)
    note = {'entry': where, 'page': headers[0]['page'], 'header': shown, 'columns': columns, 'rows': cells,
            'failures': failures}
    if banners:
        note['banners'] = banners
    report.setdefault('tables', []).append(note)
    if failures:
        report['errors'].append(f'{where} (p{headers[0]["page"]}): the table under {shown!r} was not read: ' +
                                '; '.join(failures))
        return None
    if fold:
        # A table set as several narrower ones side by side ("Skill | Probability" twice, to
        # save height): the parts must carry the same names, and their rows follow one another.
        n, rem = divmod(len(columns), fold)
        parts = [columns[k * n:(k + 1) * n] for k in range(fold)] if not rem and n else []
        if not parts or any(p_ != parts[0] for p_ in parts) or banners:
            report['errors'].append(f'{where} (p{headers[0]["page"]}): the table under {shown!r} does not fold '
                                    f'into {fold} parts with the same column names: {columns}')
            note['failures'].append(f'does not fold into {fold} like parts')
            return None
        cells = [r[k * n:(k + 1) * n] for k in range(fold) for r in cells]
        columns = parts[0]
        # the names were printed once over each part and are kept once: say so, for the word count
        report.setdefault('folded_keys', []).append({'region': shown, 'entry': where, 'cells': columns * (fold - 1)})
        note.update(columns=columns, rows=cells, folded=fold)
    names = [c or next((f'{b["text"]} {i + 2 - b["columns"][0]}' for b in banners
                        if b['columns'][0] <= i + 1 <= b['columns'][1]), '') for i, c in enumerate(columns)]
    block = {'type': 'table', 'title': title, 'columns': columns, 'rows': cells,
             'data': table_data(names, cells, report, where)}
    if banners:
        block['banners'] = banners
    return block


def with_text_tables(lines, report, where):
    """Lines -> the same lines with each text table as one line carrying a table block.

    A table is one or more header lines (is_table_header), one under another, with two or more
    lines under them at the text's leading, in their column, up to a wider gap. Each is read by
    read_text_table and listed in the report's `tables` with its header, its rows and what did
    not check out. One that fails a check is left as the lines it was and goes in the report's
    `errors`."""
    def follows(nxt, prev, first):
        return (not nxt.get('heading') and not nxt.get('block') and nxt['page'] == first['page'] and
                nxt['column'] == first['column'] and nxt.get('box') == first.get('box') and
                0 < nxt['baseline'] - prev['baseline'] <= ROW_LEADING * first['size'])

    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        if not is_table_header(l):
            out.append(l)
            i += 1
            continue
        headers = [l]
        j = i + 1
        while j < len(lines) and is_table_header(lines[j]) and follows(lines[j], headers[-1], l):
            headers.append(lines[j])
            j += 1
        rows, prev = [], headers[-1]
        while j < len(lines) and not is_table_header(lines[j]) and follows(lines[j], prev, l):
            rows.append(lines[j])
            prev = lines[j]
            j += 1
        if len(rows) < 2:
            out += headers + rows
            i = j
            continue
        block = table_block(headers, rows, report, where)
        if block is None:
            out += headers + rows
        else:
            out.append(merge_lines(headers + rows, block))
        i = j
    return out


# --- lists keyed by a roll or a number ---------------------------------------------------------

KEY = re.compile(r'^\s*(?P<key>\d+(?:\s*[-–]\s*\d+)?\+?)\s+[–—-]\s+\S')


def with_keyed_lists(lines, report, where, vocab=None):
    """Lines -> the same lines with each keyed list as one line carrying a list block.

    A keyed list is three or more items, each starting with a number or a range of numbers and a
    dash ("3 – Spell fails entirely.", "5-6 – Spell is cast ..."), at one left edge, their
    following lines set in further (a hanging indent), with nothing else between them. It is the
    way a book prints the results of a roll as running text. Each item keeps its words as
    printed; the list is noted in the report's `keyed_lists`."""
    def where_(l):
        return (l['page'], l['column'], l.get('box'))

    def item_start(l, edges=None):
        """A line that starts an item: at the list's left edge in its column (a list can carry on
        into the next column, whose edge it takes from its first item there)."""
        if l.get('heading') or l.get('block') or not KEY.match(plain(l['text'])):
            return False
        return edges is None or where_(l) not in edges or abs(l['x0'] - edges[where_(l)]) <= 1.5

    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        if not item_start(l):
            out.append(l)
            i += 1
            continue
        edges, items, j = {where_(l): l['x0']}, [], i
        while j < len(lines) and item_start(lines[j], edges) and lines[j].get('box') == l.get('box'):
            edges.setdefault(where_(lines[j]), lines[j]['x0'])
            edge = edges[where_(lines[j])]
            run = [lines[j]]
            j += 1
            while j < len(lines) and not lines[j].get('heading') and not lines[j].get('block') and                     where_(lines[j]) == where_(run[0]) and not item_start(lines[j], edges) and                     (lines[j]['x0'] > edge + 3 or ('para' in lines[j] and not lines[j]['para'])):
                run.append(lines[j])
                j += 1
            items.append(run)
        if len(items) < 3:
            out.append(l)
            i += 1
            continue
        texts = [join_lines([marked(x) for x in run], report, where, vocab) for run in items]
        block = {'type': 'list', 'ordered': False, 'items': texts,
                 'keys': [KEY.match(plain(t)).group('key') for t in texts]}
        report.setdefault('keyed_lists', []).append({'entry': where, 'page': l['page'], 'items': len(texts),
                                                     'keys': block['keys']})
        out.append(merge_lines([x for run in items for x in run], block))
        i = j
    return out
