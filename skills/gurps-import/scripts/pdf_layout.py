#!/usr/bin/env python3
"""Read a chapter's PDF pages as lines with their layout (docs/adr/0002).

    pdf_layout.py BOOK.pdf --pages 30-109 [--page-offset 2] --out ch3-layout.json
    pdf_layout.py BOOK.pdf --pages 87 --page-offset 2 --text      # a readable view, for planning
    pdf_layout.py BOOK.pdf --pages 46-116 --icon-fonts IconFont OtherIcons --out ...

`--pages` are printed page numbers (library-layout.md §3); --page-offset is the
number of PDF pages before printed page 1 (the source's `page_offset`).

Characters are grouped into lines by their **baseline**, so large and small
capitals set on one line stay together, and into words by the space between
them. Each page's **gutter** is found from where its words lie: an x position
near the middle that (almost) no word crosses (words set larger than the body
text, like a title across both columns, aren't counted); a page set in three columns has
two, one near each third (its columns are left, middle and right). A line is split at the gutter
into its left and right parts; a line with a word across it is "full" width.
On a page with no gutter every line is "full". Lines are read in bands: a full
line ends a band, and within a band the left column is read before the right.

Each line records:

    {"page": 87, "column": "left" | "middle" | "right" | "full", "top": 112.4, "baseline": 121.1,
     "x0": 51.0, "x1": 290.2, "text": "Lamp Warden", "size": 14.0, "bold": true, "italic": false,
     "font": "CaslonAntique-Bold", "spans": [{"text", "size", "bold", "italic"}],
     "words": [["Lamp", 51.0, 70.2], ...], "furniture": false, "heading": 2}

`spans` splits the line where its style changes; `words` gives each word's
text, x0 and x1, for tables and rows of labels. `furniture` marks running
heads, footers and bare page numbers (lines in the top or bottom margin).
`heading` is a level (1 = largest type) for lines set larger than the body
text in a size the chapter uses rarely (a size used as much as a sidebar's
text is text, not headings). `fonts` lists every size with how many characters use it; `body_size` is
the commonest. `gutters` gives each page's gutter x positions (null: one column).

Tilted text. Notes printed at an angle (handwriting on scraps of paper pinned across a page)
are read scrap by scrap: characters set at the same angle are turned level about the page's
centre, read into lines there, and grouped into scraps (lines near each other, one under
another). Their lines follow the page's body lines, scrap by scrap in the order their first
lines start down the page, each carrying `tilt` (degrees, anticlockwise) and `scrap` ("<page>.t<n>"); their
positions are in the levelled frame, their column is "full", and they are never furniture
(a note pinned over the top margin is still a note). Their size is the type size set, not the
height of the turned glyph.

Icons. Books mark things with symbol glyphs (a career level's cross) and small
vector drawings (its shield or skull). Glyphs in a font named by --icon-fonts
(a part of the font's name is enough) are taken out of the text and listed
under `marks` ({"page", "x0", "x1", "top", "bottom", "font", "text"}). Small
filled drawings (both sides under 20 points) are listed under `shapes`
({"page", "x0", "x1", "top", "bottom", "pts"}); `pts`, the number of points in
the path, tells one drawn icon from another. An icon printed inline in the
text ("the lamp marked with ✦") can be kept in its line: --icon-text
IconFont=✦ pts:12=◆ puts that text where the glyph or drawing stands.

Boxes and tables (--boxes). Panels printed on a background image that doesn't
fill the page (sidebars, boxed tables) are read as regions of their own: each
gets its own column check, its lines come after the page's body lines and carry
`box` (its id, "<page>.<n>"), and the page's gutter is found from the text
outside them. A box with ruled rows (rules, or shaded row bands) is read as a
table: `regions` lists each box ({"id", "kind": "box" | "table", "page",
"bbox"}), and a table adds "columns" (the header cells) and "rows" (cells as
plain text); its lines carry `table` too. An illustration cut out with a soft mask
(mostly see-through) is not a panel, even where its rectangle runs over text;
nor is a rectangle the page's lines run across (a word over its edge, or a line
carrying on into it, on a quarter of its rows). A box's own lines are read in
one or two columns, never three: a table's columns aren't text columns. A box holding
several ruled tables, each under its own larger title, is read as one region per table,
numbered "<box id>.<n>" (216.1.1, 216.1.2).
`image_notes` lists each one set aside, and any mask that couldn't be read.
A drop capital (a letter twice the size of the text beside it, set into the
lines below its paragraph's first) is moved to the start of that first line and
listed under `drop_capitals`.

The output is the book's text: write it to scratch outside the repo, never
commit it. Needs pdfplumber.
"""
import argparse
import collections
import json
import math
import re
import sys

import pdfplumber
from pdfminer.pdffont import PDFSimpleFont

# Some fonts' character maps send a capital's code to its lower-case letter (code 84, "T" in the
# font's standard encoding, read as "t"), so the text loses its capitals though the page shows
# them. In a simple font a code in A-Z stands for that capital: read it so, and count each fix by
# font (`case_fixed` in the output). Small-caps fonts ("-SC" in the name) are left alone: they set
# their small capitals at those codes too, and entry_text.fix_case() restores those words.
CASE_FIXED = collections.Counter()
NOT_BOXES = set()                        # ids of frames that are no panels (--not-boxes)
SET_GUTTERS = {}                         # printed page -> its gutters, as the plan gives them (--set-gutters)
REPLACE_CHARS = {}                       # characters a book's fonts give wrongly -> what the page prints (--replace-chars)
CHARS_REPLACED = collections.Counter()
# A glyph whose font gives no character for it comes through as "(cid:129)". It is almost always
# a symbol (a bullet, a dash) that reads as nonsense where it stands: each is listed in the output
# (`unmapped_glyphs`, by font, with a count and the first page), and check_coverage.py prints
# them, until --replace-chars says what the page prints there.
UNMAPPED_GLYPH = re.compile(r'^\(cid:\d+\)$')
UNMAPPED = {}                             # (glyph, font) -> pages it was seen on
_to_unichr = PDFSimpleFont.to_unichr


def _to_unichr_keeping_capitals(self, cid):
    u = _to_unichr(self, cid)
    if 65 <= cid <= 90 and u == chr(cid + 32) and 'SC' not in str(getattr(self, 'basefont', '')):
        CASE_FIXED[str(getattr(self, 'basefont', '?'))] += 1
        return chr(cid)
    return u


PDFSimpleFont.to_unichr = _to_unichr_keeping_capitals

BOLD = re.compile(r'bold|black|heavy|semibold|demi', re.I)
ITALIC = re.compile(r'italic|oblique', re.I)
MARGIN_TOP, MARGIN_BOTTOM = 0.06, 0.06   # fractions of the page height
BASELINE_TOLERANCE = 1.5                 # points between baselines on one line
WORD_GAP = 0.18                          # a gap wider than this x the type size splits words
GUTTER_HALF = 5.0                        # points from a lone column's text to the gutter beside it
GUTTER_ZONE = (0.38, 0.62)               # where to look for a gutter, as fractions of the width
THIRDS_ZONES = ((0.25, 0.42), (0.58, 0.75))   # where a three-column page's two gutters fall
FULL_PAGE_ROWS = 24                      # rows of body text from which a three-column page allows one crossing line
THIRD_SHARE = 0.2                        # ...and the least share of its words each column holds
SHAPE_MAX = 20                           # points: larger drawings aren't icons
BOX_MIN = (100, 24)                      # points: a smaller image isn't a boxed panel
RULE_MAX_WIDTH = 3.0                     # points: a thicker stroke is a band of tint, not a table's rule
DISPLAY_HEADING = 3.0                    # x the text's size: a heading this large, alone at its height, heads the page below it
RULE_MIN_APART = 3.0                    # points: strokes closer together than this are bands of tint too
RUN_ON_GAP = 4.0                         # points: a word this near a box's edge is on the same line
STANDFIRST_LINES = 8       # an opening paragraph across the page may run to this many lines
STANDFIRST_SHARE = 0.2     # of the words under it, at least this share on each side of a gutter
RULE_SLACK = 10.0                        # points: a table's rules may reach this far past its panel's sides
RUN_OVER_SHARE = 0.25                    # a box with this share of its lines crossing its edges is no panel
PANEL_OPAQUE = 0.75                      # a masked image less opaque than this is an illustration
TILT_MIN = 0.5                           # degrees: text turned less than this is level
SCRAP_GAP = 4.0                          # a gap wider than this x the type size parts two tilted notes side by side
SCRAP_LEADING = 3.0                      # lines further apart than this x the type size are different notes
HEADING_SHARE = 0.08                     # a larger size used for more than this share of the body's characters is text


def parse_pages(s):
    a, _, b = s.partition('-')
    a = int(a)
    b = int(b) if b else a
    if b < a:
        sys.exit(f'--pages {s}: the range runs backwards')
    return a, b


def font_name(f):
    return f.split('+', 1)[-1]


def baseline(c, height):
    m = c.get('matrix')
    return round(height - m[5], 1) if m else round(c['bottom'], 1)


DASHES = '-‐‑–—−'


def raised_dashes(chars, height):
    """{id(char): baseline} for a dash or minus set a little above or below the line it belongs
    to ("-500", "1053-1115" with a raised dash): one touching a character of the same size whose
    baseline is within a quarter of the type size takes that character's baseline."""
    out = {}
    for c in chars:
        if c['text'] not in DASHES:
            continue
        b = baseline(c, height)
        for d in chars:
            if d is c or d['text'] in DASHES or abs(d['size'] - c['size']) > 0.5:
                continue
            bd = baseline(d, height)
            if 0 < abs(bd - b) <= 0.25 * c['size'] and (abs(d['x0'] - c['x1']) < 0.6 or abs(c['x0'] - d['x1']) < 0.6):
                out[id(c)] = bd
                break
    return out


def drop_capitals(rows, page_no=None, notes=None):
    """A drop capital (a letter at least twice the size of the text beside it, sitting on a lower
    line of its paragraph) moves to the start of the paragraph's first line: the highest row
    above it, within its height, that starts just right of it. Each one moved goes in `notes`."""
    for b, row in rows:
        row.sort(key=lambda c: c['x0'])
        if len(row) < 2 or not row[0]['text'].isalpha():
            continue
        cap, rest = row[0], row[1:]
        sizes = sorted(c['size'] for c in rest)
        if cap['size'] < 2 * sizes[len(sizes) // 2]:
            continue
        above = [(b2, r2) for b2, r2 in rows if cap['top'] - 2 <= b2 < b and r2 is not row and
                 min(c['x0'] for c in r2) >= cap['x1'] - 1 and
                 min(c['x0'] for c in r2) - cap['x1'] < 3 * sizes[len(sizes) // 2]]
        if not above:
            continue
        b2, first = min(above, key=lambda r: r[0])
        lead = min(first, key=lambda c: c['x0'])
        row.remove(cap)
        first.append(dict(lead, text=cap['text'], x0=lead['x0'] - 0.02, x1=lead['x0'] - 0.01))
        if notes is not None:
            notes.append({'page': page_no, 'note': f'drop capital {cap["text"]!r} moved to the line at '
                                                   f'baseline {b2}'})


def make_words(chars, height, page_no=None, notes=None):
    """Characters -> words, each on one baseline, split at space characters and at gaps wider
    than WORD_GAP x the type size. Drop capitals join their paragraph's first line, and a dash set
a little off the line joins the line it touches."""
    base = raised_dashes(chars, height)
    rows = []
    for c in sorted(chars, key=lambda c: (base.get(id(c), baseline(c, height)), c['x0'])):
        b = base.get(id(c), baseline(c, height))
        if rows and abs(b - rows[-1][0]) <= BASELINE_TOLERANCE:
            rows[-1][1].append(c)
        else:
            rows.append((b, [c]))
    drop_capitals(rows, page_no, notes)
    groups = []
    for b, row in rows:
        cur = []
        kept = []
        for c in sorted(row, key=lambda c: c['x0']):
            # A glyph printed twice in the same place (a shadow or outline effect) is one glyph.
            if any(k['text'] == c['text'] and abs(k['x0'] - c['x0']) < 0.15 * max(c['x1'] - c['x0'], 1) and
                   abs(k['top'] - c['top']) < 1 for k in kept[-3:]):
                continue
            kept.append(c)
        for c in kept:
            if c['text'].isspace():
                if cur:
                    groups.append((b, cur))
                cur = []
                continue
            if cur and c['x0'] - cur[-1]['x1'] > WORD_GAP * min(c['size'], cur[-1]['size']):
                groups.append((b, cur))
                cur = []
            cur.append(c)
        if cur:
            groups.append((b, cur))
    return [{'text': ''.join(c['text'] for c in cs), 'x0': min(c['x0'] for c in cs),
             'x1': max(c['x1'] for c in cs), 'top': min(c['top'] for c in cs),
             'bottom': max(c['bottom'] for c in cs), 'baseline': b, 'chars': cs} for b, cs in groups]


def tilt(c):
    """The angle a character is set at, in quarter degrees anticlockwise (0.0: level)."""
    m = c.get('matrix')
    if not m or abs(m[1]) < 1e-6:
        return 0.0
    a = round(math.degrees(math.atan2(m[1], m[0])) * 4) / 4
    return a if abs(a) >= TILT_MIN else 0.0


def levelled(c, angle, width, height):
    """A copy of a tilted character turned level about the page's centre: where it would sit,
    and at what size, had its note been pinned straight."""
    m = c['matrix']
    th = math.radians(angle)
    cx, cy = width / 2, height / 2
    dx, dy = m[4] - cx, m[5] - cy
    x = cx + dx * math.cos(th) + dy * math.sin(th)
    y = cy - dx * math.sin(th) + dy * math.cos(th)
    # pdfminer's `adv` is the glyph's advance before the text matrix scales it; the glyph's box
    # is that advance by the type size, turned. Its height gives the type size back.
    wide = c.get('adv', c['x1'] - c['x0']) * math.hypot(m[0], m[1])
    size = round((c['bottom'] - c['top'] - wide * abs(math.sin(th))) / math.cos(th), 1)
    return dict(c, x0=x, x1=x + wide, bottom=height - y, top=height - y - size, size=size,
                matrix=None, real_top=c['top'], real_x0=c['x0'])


def scraps(words):
    """Levelled words of one angle -> scraps: lists of words whose lines sit near each other, one
    under another. A line is cut where its words stand far apart (two notes side by side)."""
    rows = collections.defaultdict(list)
    for w in words:
        rows[w['baseline']].append(w)
    segs = []
    for b, raw in sorted(rows.items()):
        cur = []
        for w in sorted(raw, key=lambda w: w['x0']):
            if cur and w['x0'] - cur[-1]['x1'] > SCRAP_GAP * word_size(w):
                segs.append(cur)
                cur = []
            cur.append(w)
        segs.append(cur)
    group = list(range(len(segs)))

    def find(i):
        while group[i] != i:
            i = group[i]
        return i
    for i, a in enumerate(segs):
        for j in range(i + 1, len(segs)):
            b = segs[j]
            size = max(word_size(a[0]), word_size(b[0]))
            if b[0]['baseline'] - a[0]['baseline'] > SCRAP_LEADING * size:
                break
            if min(a[-1]['x1'], b[-1]['x1']) - max(a[0]['x0'], b[0]['x0']) > 0:
                group[find(j)] = find(i)
    out = collections.defaultdict(list)
    for i, seg in enumerate(segs):
        out[find(i)] += seg
    return list(out.values())


def tilted_lines(chars, page_no, width, height):
    """Tilted characters -> their lines, scrap by scrap from the top of the page down."""
    by_angle = collections.defaultdict(list)
    for c in chars:
        by_angle[tilt(c)].append(c)
    found = []
    for angle, cs in by_angle.items():
        words = make_words([levelled(c, angle, width, height) for c in cs], height)
        for ws in scraps(words):
            # A note's place on the page is where its first line starts: a line tilted upwards
            # ends higher than a note beside it begins.
            first = min(ws, key=lambda w: (w['baseline'], w['x0']))['chars'][0]
            found.append(((first['real_top'], first['real_x0']), angle, ws))
    out = []
    for n, (_, angle, ws) in enumerate(sorted(found, key=lambda f: f[0])):
        for l in order_lines(ws, [], page_no, height):
            l.update(tilt=angle, scrap=f'{page_no}.t{n + 1}', furniture=False)
            out.append(l)
    return out


def slanted(c):
    """True for text set oblique by slanting a roman font (its text matrix skews), as some books
    print their italics."""
    m = c.get('matrix')
    return bool(m and m[0] and abs(m[2] / m[0]) > 0.1)


def style(c):
    f = font_name(c.get('fontname', ''))
    return {'size': round(float(c.get('size', 0)), 1), 'bold': bool(BOLD.search(f)),
            'italic': bool(ITALIC.search(f)) or slanted(c), 'font': f}


def word_style(w):
    """The style most of a word's characters have. A word of large and small capitals takes the
    larger size."""
    counts = collections.Counter()
    for c in w['chars']:
        s = style(c)
        counts[(s['size'], s['bold'], s['italic'], s['font'])] += 1
    (size, bold, italic, font), _ = counts.most_common(1)[0]
    return {'size': max(k[0] for k in counts), 'bold': bold, 'italic': italic, 'font': font}


def find_gutters(words, width, left=0.0, three=True):
    """The x of each gutter between `left` and `left + width`: two, one near each third, when the
    page is set in three columns (each holding a good share of the words; not looked for when
    `three` is false); else one near the middle; else none."""
    # A three-column find is checked by each column's share of the words, so it may allow one more
    # crossing line than a single gutter does.
    thirds = [find_gutter(words, width, left, z, slack=1) for z in THIRDS_ZONES] if three else [None]
    if all(t is not None for t in thirds):
        edges = [float('-inf')] + thirds + [float('inf')]
        counts = [sum(1 for w in words if edges[i] <= (w['x0'] + w['x1']) / 2 < edges[i + 1]) for i in range(3)]
        if min(counts) >= THIRD_SHARE * len(words):
            return thirds
    g = find_gutter(words, width, left)
    return [] if g is None else [g]


def gutters_under_a_standfirst(words, width, left=0.0, three=True):
    """`find_gutters`, and where the whole page shows none, once more without its first few lines
    (up to STANDFIRST_LINES): an opening paragraph set across the page, over the columns. The
    lines left out still cross the gutters found, so they are read full-width. A blank that
    does not part two columns (`side_by_side`) is no gutter: a page of full-width text beside a
    picture, whose short last lines leave one."""
    found = find_gutters(words, width, left, three)
    if found:
        return found
    tops = sorted({w['baseline'] for w in body_words(words)})
    for k in range(2, min(STANDFIRST_LINES, len(tops) - 1) + 1):
        below = [w for w in words if w['baseline'] > tops[k - 1]]
        found = find_gutters(below, width, left, three)
        # Columns, not a blank beside one block of text: each side of a gutter holds its share.
        if found and all(side_by_side(below, g) for g in found):
            return found
    return []


def side_by_side(words, g):
    """The words left and right of `g` are two columns: each side holds its share of them
    (STANDFIRST_SHARE), and the two run down the page together: of the shorter side's lines, at
    least half have a line of the other side level with them (a block at the top left and
    another at the bottom right are not columns, though a wide line or two may reach across)."""
    sides = [[w['baseline'] for w in words if ((w['x0'] + w['x1']) / 2 < g) == left] for left in (True, False)]
    if min(map(len, sides)) < max(1, STANDFIRST_SHARE * len(words)):
        return False
    rows = [{int(b // 14) for b in side} for side in sides]
    few, many = sorted(rows, key=len)
    return sum(1 for r in few if {r - 1, r, r + 1} & many) >= 0.5 * len(few)


def word_size(w):
    return max(c['size'] for c in w['chars']) if w.get('chars') else w.get('size', 0)


def body_words(words):
    """The words set at most a point larger than the commonest size: titles and headings set
    larger, which may run across both columns, left out."""
    sizes = collections.Counter(round(word_size(w)) for w in words)
    if not sizes:
        return words
    body = sizes.most_common(1)[0][0]
    return [w for w in words if round(word_size(w)) <= body + 1]


def find_gutter(words, width, left=0.0, zone=None, slack=0):
    """The x of the gutter in `zone` (fractions of the width; default the middle) between `left`
    and `left + width`, or None. Counts, for each point across the zone, the words that cross it;
    the gutter is the middle of the widest run that at most a few cross."""
    zone = zone or GUTTER_ZONE
    lo, hi = int(left + width * zone[0]), int(left + width * zone[1])
    words = body_words(words)          # a title set across both columns doesn't hide the gutter
    if len(words) < 12:
        return None
    rows = len({w['baseline'] for w in words})
    # A few lines may cross; on a full three-column page (`slack`), one more: a standfirst set
    # across the columns.
    allowed = max(slack if rows >= FULL_PAGE_ROWS else 0, rows // 50)
    cover = [0] * (hi - lo + 1)
    for w in words:
        for x in range(max(lo, int(w['x0']) + 1), min(hi, int(w['x1'])) + 1):
            cover[x - lo] += 1
    best, run = None, None
    for i, n in enumerate(cover + [allowed + 1]):
        if n <= allowed:
            run = (run[0], i) if run else (i, i)
        elif run:
            if best is None or run[1] - run[0] > best[1] - best[0]:
                best = run
            run = None
    if best is None or best[1] - best[0] < 2:
        return None
    # A column with no body text in it (only a boxed panel, or nothing) leaves the gap open to the
    # edge of the zone: the gutter then runs beside the text that is there, not down the middle
    # of the blank, where it would cut through whatever the empty column does hold.
    if best[0] == 0 and best[1] < len(cover) - 1:
        return lo + best[1] - GUTTER_HALF
    if best[1] >= len(cover) - 1 and best[0] > 0:
        return lo + best[0] + GUTTER_HALF
    return lo + (best[0] + best[1]) / 2


def column_names(n):
    return {1: ['left', 'right'], 2: ['left', 'middle', 'right']}.get(n, [])


def segments(raw, gutters):
    """One baseline's words -> [(column, words)], split where the gutters fall between words."""
    if not gutters:
        return [('full', raw)]
    names = column_names(len(gutters))
    edges = [float('-inf')] + list(gutters) + [float('inf')]
    parts = [[w for w in raw if w['x0'] >= edges[i] and w['x1'] <= edges[i + 1]] for i in range(len(names))]
    if sum(len(p) for p in parts) < len(raw):     # a word crosses a gutter: a full-width line
        return [('full', raw)]
    filled = [i for i, p in enumerate(parts) if p]
    for a, b in zip(filled, filled[1:]):
        left, right = parts[a], parts[b]
        # A space between two words of one full-width line can fall on a gutter too; the
        # gap between columns is wider than a word space.
        # But two columns' lines can share a baseline, so a jump in type size across the gutter
        # (a quote in one column, a heading in the other) is two lines.
        sl = max(c['size'] for c in left[-1]['chars'])
        sr = max(c['size'] for c in right[0]['chars'])
        size = max(sl, sr)
        # A change of typeface as well, across more than a word space, makes a smaller jump
        # enough: two columns' headings side by side, one in small capitals and one in capitals
        # a little larger.
        gap = right[0]['x0'] - left[-1]['x1']
        faces = left[-1]['chars'][-1].get('fontname') != right[0]['chars'][0].get('fontname') and gap >= 0.4 * size
        if gap < max(4.0, 0.6 * size) and max(sl, sr) < (1.2 if faces else 1.25) * min(sl, sr):
            return [('full', raw)]
    return [(names[i], parts[i]) for i in filled]


def glued(prev, w):
    """True when an inline icon and the word beside it touch on the page ("✠," prints no space)."""
    icon = prev['chars'][0].get('fontname') == 'Icon' or w['chars'][0].get('fontname') == 'Icon'
    return icon and w['x0'] - prev['x1'] < 1.0


def make_line(ws, page_no, column, height):
    spans = []
    weights = collections.Counter()
    text = ''
    for k, w in enumerate(ws):
        st = word_style(w)
        sep = '' if k and glued(ws[k - 1], w) else ' '
        text = text + sep + w['text'] if text else w['text']
        weights[(st['size'], st['font'])] += len(w['text'])
        if spans and all(spans[-1][k2] == st[k2] for k2 in ('size', 'bold', 'italic')):
            spans[-1]['text'] += sep + w['text']
        else:
            spans.append({'text': w['text'], 'size': st['size'], 'bold': st['bold'], 'italic': st['italic']})
    (size, font), _ = weights.most_common(1)[0]
    top = min(w['top'] for w in ws)
    bottom = max(w['bottom'] for w in ws)
    # A bare number is furniture when it is the page's own number (a table's "99" is not).
    furniture = top < height * MARGIN_TOP or bottom > height * (1 - MARGIN_BOTTOM) or \
        text.strip() == str(page_no)
    return {'page': page_no, 'column': column, 'top': round(top, 1), 'baseline': ws[0]['baseline'],
            'x0': round(min(w['x0'] for w in ws), 1), 'x1': round(max(w['x1'] for w in ws), 1),
            'text': text, 'size': size, 'bold': all(s['bold'] for s in spans),
            'italic': all(s['italic'] for s in spans), 'font': font, 'spans': spans,
            'words': [[w['text'], round(w['x0'], 1), round(w['x1'], 1)] for w in ws],
            'furniture': furniture}


def order_lines(words, gutters, page_no, height, full_rows=frozenset(), blocks=()):
    """Words of one region -> lines in reading order: split at the gutters, then read in bands.
    `blocks` are [(words, gutters)]: a stretch of the region read on its own, with gutters of its
    own (the notes under a table across the page, set in two columns on a page of three). Like a
    full-width line, each ends a band."""
    in_block = {id(w) for ws, _ in blocks for w in ws}
    rows = collections.defaultdict(list)
    for w in words:
        if id(w) not in in_block:
            rows[w['baseline']].append(w)
    segs = []                       # (baseline, column, words)
    for b, raw in rows.items():
        # (a row of a table set across the page is one line, whatever gaps its columns leave)
        for col, ws in ([('full', raw)] if any(id(w) in full_rows for w in raw) else
                        segments(sorted(raw, key=lambda w: w['x0']), gutters)):
            segs.append((b, col, ws))
    segs.sort(key=lambda s: s[0])
    # A display heading (three times the text's size or more) that stands alone at its height,
    # the other columns left blank beside it, heads everything below it on the page even when it
    # is short enough to sit inside one column: it ends a band as a full-width line does.
    sizes = sorted(max(c['size'] for c in w['chars']) for w in words)
    usual = sizes[len(sizes) // 2] if sizes else 0
    for k, (b, col, ws) in enumerate(segs):
        big = max(c['size'] for w in ws for c in w['chars'])
        if col != 'full' and gutters and usual and big >= DISPLAY_HEADING * usual and \
                not any(o is not segs[k] and b - 0.8 * big <= o[0] <= b + 0.2 * big for o in segs):
            segs[k] = (b, 'full', ws)
    # A full-width line or a block ends a band; within a band, read the columns left to right.
    stops = [(b, [make_line(ws, page_no, 'full', height)]) for b, c, ws in segs if c == 'full']
    stops += [(min(w['baseline'] for w in ws), order_lines(ws, g, page_no, height)) for ws, g in blocks if ws]
    stops.sort(key=lambda s: s[0])
    out, prev = [], float('-inf')
    for bnd, lines in stops + [(float('inf'), [])]:
        for side in column_names(len(gutters)):
            out += [make_line(ws, page_no, side, height) for b, c, ws in segs if c == side and prev <= b < bnd]
        out += lines
        prev = bnd
    return out


def mask_opacity(im):
    """The share of an image its soft mask leaves opaque (0-1), or None: no mask, or one that can't
    be read (then the caller says so)."""
    mask = im['stream'].attrs.get('SMask')
    if mask is None:
        return None
    try:
        import io
        from PIL import Image
        m = mask.resolve()
        filters = m.attrs.get('Filter')
        filters = [f.name if hasattr(f, 'name') else str(f) for f in
                   (filters if isinstance(filters, list) else [filters])]
        if any(f.strip('/').strip("'") in ('DCTDecode', 'JPXDecode') for f in filters):
            img = Image.open(io.BytesIO(m.get_rawdata())).convert('L')
        else:
            w, h = m.attrs['Width'], m.attrs['Height']
            img = Image.frombytes('L', (w, h), m.get_data()[:w * h])
        hist = img.histogram()
        return sum(hist[128:]) / max(1, sum(hist))
    except Exception:  # noqa: BLE001 - reported by the caller
        return None


def text_runs_over(box, words, page_no, notes, page_size=None):
    """True when the page's text runs over the box's side edges rather than sitting inside it: a
    panel's text has a margin, but a picture's rectangle can lie under the text flowing past it.
    Such a box (a quarter or more of its lines with a word across an edge, or carrying on into it
    from a word space away) is set aside, and listed in
    `notes`. A box that bleeds off two or more edges of the page is a backdrop laid under part of
    the page, not a panel set in it: one line across its edge is enough to set it aside."""
    x0, top, x1, bottom = box
    inside = [w for w in words if top <= (w['top'] + w['bottom']) / 2 <= bottom and
              x0 <= (w['x0'] + w['x1']) / 2 <= x1]
    rows = {round(w['baseline']) for w in inside}
    ids = {id(w) for w in inside}
    level = [w for w in words if top <= (w['top'] + w['bottom']) / 2 <= bottom]
    crossing = {round(w['baseline']) for w in level if any(w['x0'] < e - 1 and w['x1'] > e + 1 for e in (x0, x1))}
    # ...or a line of the page carries on into it, a word space from its edge.
    crossing |= {round(w['baseline']) for w in words if id(w) not in ids and round(w['baseline']) in rows and
                 (0 <= x0 - w['x1'] < RUN_ON_GAP or 0 <= w['x0'] - x1 < RUN_ON_GAP)}
    bleeds = page_size is not None and sum((x0 <= 0.5, top <= 0.5, x1 >= page_size[0] - 0.5,
                                            bottom >= page_size[1] - 0.5)) >= 2
    if rows and len(crossing) >= (1 if bleeds else max(1, RUN_OVER_SHARE * len(rows))):
        if notes is not None:
            notes.append({'page': page_no, 'bbox': [round(v, 1) for v in box],
                          'note': f'text runs over its edges ({len(crossing)} of {len(rows)} lines)'
                                  f'{", and it bleeds off the page" if bleeds else ""}: not a box'})
        return True
    return False


def find_boxes(page, page_no, notes=None):
    """Boxed panels: background images that don't fill the page (sidebars, tables), clipped to the
    page (the caller drops a box inside another: `outermost`). A picture cut out with a soft
    mask (an illustration: mostly see-through outside the figure) is not a panel, though its
    rectangle may run over the text beside it; a panel is opaque. Each image set aside, and each
    mask that couldn't be read (kept as a box), goes in `notes`."""
    area = page.width * page.height
    boxes = []
    for im in page.images:
        x0, top = max(0.0, im['x0']), max(0.0, im['top'])
        x1, bottom = min(page.width, im['x1']), min(page.height, im['bottom'])
        w, h = x1 - x0, bottom - top
        if w < BOX_MIN[0] or h < BOX_MIN[1] or w * h > 0.8 * area:
            continue
        where = {'page': page_no, 'bbox': [round(v, 1) for v in (x0, top, x1, bottom)]}
        if 'SMask' in im['stream'].attrs:
            opaque = mask_opacity(im)
            if opaque is None:
                if notes is not None:
                    notes.append(dict(where, note='image mask could not be read: kept as a box'))
            elif opaque < PANEL_OPAQUE:
                if notes is not None:
                    notes.append(dict(where, note=f'illustration ({opaque:.0%} opaque): not a box'))
                continue
        boxes.append((x0, top, x1, bottom))
    # A panel can also be a frame drawn round it: an outline with no fill of its own (a tint
    # under it is drawn separately), whatever its corners (square, cut off, rounded).
    for shape in list(page.rects) + list(page.curves):
        if not shape.get('stroke') or shape.get('fill'):
            continue
        x0, top = max(0.0, shape['x0']), max(0.0, shape['top'])
        x1, bottom = min(page.width, shape['x1']), min(page.height, shape['bottom'])
        w, h = x1 - x0, bottom - top
        if w < BOX_MIN[0] or h < BOX_MIN[1] or w * h > 0.8 * area:
            continue
        boxes.append((x0, top, x1, bottom))
    return sorted(set(boxes), key=lambda b: (b[1], b[0]))


def banded_panels(page):
    """Tables set on a panel of their own with some rows tinted: a filled rectangle, smaller than
    the page, with thick strokes of tint lying inside it (the tinted rows). Such a table can be
    wider than a column of the page; its rows are single lines right across it."""
    area = page.width * page.height
    bands = [l for l in page.lines if abs(l['top'] - l['bottom']) < 1 and (l.get('linewidth') or 0) > RULE_MAX_WIDTH]
    out = []
    for r in page.rects:
        if not r.get('fill'):
            continue
        w, h = r['x1'] - r['x0'], r['bottom'] - r['top']
        if w < BOX_MIN[0] or h < BOX_MIN[1] or w * h > 0.8 * area:
            continue
        # the bands run the panel's whole width (the page's own white ground holds bands too,
        # those of tables set in its columns, but they are far narrower than it)
        if any(abs(b['x0'] - r['x0']) <= 4 and abs(b['x1'] - r['x1']) <= 4 and r['top'] <= b['top'] <= r['bottom']
               for b in bands):
            out.append((max(0.0, r['x0']), max(0.0, r['top']), min(page.width, r['x1']), min(page.height, r['bottom'])))
    return out


def table_rows(page, words, boxes):
    """Words in the rows of a table set across the page, outside any box: the table's tinted rows
    are thick strokes, three or more one above another, each wider than half the page. Its rows,
    from a few lines above the first stroke (its title, header and first group) to a line below
    the last, are read as whole lines, so the gaps between its columns are not taken for the
    page's gutters. Returns the ids of those words."""
    bands = [l for l in page.lines if abs(l['top'] - l['bottom']) < 1 and (l.get('linewidth') or 0) > RULE_MAX_WIDTH
             and l['x1'] - l['x0'] > 0.5 * page.width and
             not any(b[0] - 2 <= l['x0'] and l['x1'] <= b[2] + 2 and b[1] <= l['top'] <= b[3] for b in boxes)]
    stacks = collections.defaultdict(list)
    for b in bands:
        stacks[(round(b['x0'] / 4), round(b['x1'] / 4))].append(b)
    out, regions = set(), []
    for stack in stacks.values():
        if len(stack) < 3:
            continue
        x0, x1 = min(b['x0'] for b in stack), max(b['x1'] for b in stack)
        sizes = sorted(max(c['size'] for c in w['chars']) for w in words) or [10]
        line = 1.2 * sizes[len(sizes) // 2]
        top = min(b['top'] for b in stack) - (b_w := max(b.get('linewidth') or 0 for b in stack)) - 4 * line
        bottom = max(b['bottom'] for b in stack) + b_w + line
        out |= {id(w) for w in words if x0 - 2 <= (w['x0'] + w['x1']) / 2 <= x1 + 2 and top <= w['baseline'] <= bottom}
        regions.append((x0, x1, bottom, line, max(b['bottom'] for b in stack) + b_w / 2))
    return out, regions


def across(ws, g):
    """True when a line's words run across the gutter at `g`: a word over it, or words either side
    of it only a word space apart."""
    ws = sorted(ws, key=lambda w: w['x0'])
    return any(w['x0'] < g - 1 and w['x1'] > g + 1 for w in ws) or \
        any(a['x1'] <= g <= b['x0'] and b['x0'] - a['x1'] < 0.8 * word_size(a) for a, b in zip(ws, ws[1:]))


def below_the_rows(words, regions, gutters, taken):
    """Of the words `table_rows` took, those on the last lines under a table's last stroke that
    read as the page's columns, not as an untinted last row: they run across none of the page's
    gutters, and in each column their words are a word space apart (a row's cells are set
    further apart). A "Notes" heading level with the next column's text is one. Only lines below
    every row are given back to the columns."""
    out = set()
    if not gutters:
        return out
    rows = collections.defaultdict(list)
    for w in words:
        if id(w) in taken:
            rows[round(w['baseline'])].append(w)
    edges = [float('-inf')] + list(gutters) + [float('inf')]

    def prose(ws):
        if any(across(ws, g) for g in gutters):
            return False
        for i in range(len(edges) - 1):
            part = sorted((w for w in ws if edges[i] <= (w['x0'] + w['x1']) / 2 < edges[i + 1]), key=lambda w: w['x0'])
            if any(b['x0'] - a['x1'] >= 0.8 * word_size(a) for a, b in zip(part, part[1:])):
                return False
        return True

    for x0, x1, bottom, line, last in regions:
        for b in sorted((b for b in rows if last < b <= bottom), reverse=True):
            if not prose(rows[b]):
                break
            out |= {id(w) for w in rows[b]}
    return out


def under_tables(words, regions, taken):
    """For each table set across the page, the lines directly under its last row, each no further
    below the one before than a line and a half: [(baseline, words)] per table."""
    rows = collections.defaultdict(list)
    for w in words:
        if id(w) not in taken:
            rows[round(w['baseline'])].append(w)
    runs = []
    for x0, x1, bottom, line, _ in regions:
        run, last = [], bottom
        for b, ws in sorted(rows.items()):
            if b <= bottom - line:
                continue
            # (a line with nothing at the table's left edge is the page's columns again: a note,
            # or a heading over them, starts there, or carries on from a line that did)
            if b - last > 1.6 * line or not any(w['x0'] < x0 + 2 * line for w in ws):
                break
            run.append((b, ws))
            last = b
        runs.append(run)
    return runs


def table_notes(words, regions, gutters, taken):
    """The notes under each table set across the page: the lines directly under its last row
    (each no further below the one before than a line and a half) that are set across the page's
    gutters. A line that crosses none is a note's short last line when it ends the block (a wider
    gap or nothing follows) or the next line crosses again; two such lines in a row are the
    columns starting. Returns [(words, gutters)], one per table that has notes, for
    `order_lines`' blocks: the notes may be set in columns of their own, which their words show."""
    out = []
    for (x0, x1, _, _, _), run in zip(regions, under_tables(words, regions, taken)):
        # (a page of tables shows no gutters: whatever lies under a table is its notes)
        crosses = [not gutters or any(across(ws, g) for g in gutters) for _, ws in run]
        ws_in = []
        for i, (b, ws) in enumerate(run):
            if not crosses[i] and not (i + 1 == len(run) or crosses[i + 1]):
                break
            ws_in += ws
        if ws_in:
            out.append((ws_in, find_gutters(ws_in, x1 - x0, x0, three=False)))
    return out


def panel_notes(page, box, words):
    """The notes under a table on a tinted panel of its own: the panel's lines under its last
    stripe of tint (but an untinted last row), for `order_lines`' blocks, read with the columns
    their own words show. Returns [] when the panel has fewer than three stripes."""
    px0, ptop, px1, pbottom = box
    bands = [l for l in page.lines if abs(l['top'] - l['bottom']) < 1 and (l.get('linewidth') or 0) > RULE_MAX_WIDTH
             and px0 - 2 <= l['x0'] and l['x1'] <= px1 + 2 and ptop <= l['top'] <= pbottom]
    if len(bands) < 3 or not words:
        return []
    sizes = sorted(max(c['size'] for c in w['chars']) for w in words)
    line = 1.2 * sizes[len(sizes) // 2]
    b_w = max(b.get('linewidth') or 0 for b in bands)
    x0, x1 = min(b['x0'] for b in bands), max(b['x1'] for b in bands)
    last = max(b['bottom'] for b in bands) + b_w / 2
    region = [(x0, x1, last + b_w / 2 + line, line, last)]
    taken = {id(w) for w in words if w['baseline'] <= region[0][2]}
    below = [w for w in words if w['baseline'] > last]
    taken -= below_the_rows(words, region, find_gutters(below, x1 - x0, x0, three=False) if below else [], taken)
    return table_notes(words, region, [], taken)


def outermost(boxes):
    """The boxes that lie inside no other. Asked once the boxes that are no panels (text running
    over their edges) are gone, so that a panel on a backdrop outlives the backdrop."""
    return [b for b in boxes if not any(o != b and o[0] <= b[0] and o[1] <= b[1] and o[2] >= b[2] and
                                        o[3] >= b[3] for o in boxes)]


def merge_near(values, tol=2.0):
    out = []
    for v in sorted(values):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


def read_table(page, box, lines):
    """A ruled table inside `box`, or None. Rows are separated by horizontal rules and by the edges
    of shaded row bands; the header is the line just above the first rule, and the last row runs
    down from the last rule while its lines stay inside the table's width. Columns come from
    vertical rules, or from the header's word positions where there are none. Cells hold plain
    text, their words in reading order."""
    x0, top, x1, bottom = box
    inside = lambda o: o['x0'] >= x0 - 2 and o['x1'] <= x1 + 2 and o['top'] >= top - 2 and o['bottom'] <= bottom + 2
    # A table may be set a little wider than the panel behind it: its rules count while they
    # start or end within RULE_SLACK of the panel's sides.
    about = lambda o: o['x0'] >= x0 - RULE_SLACK and o['x1'] <= x1 + RULE_SLACK and o['top'] >= top - 2 and \
        o['bottom'] <= bottom + 2
    # A stroke thicker than a rule is paint, not a rule: a panel's graded tint can be drawn as a
    # stack of thick strokes lying edge to edge.
    hl = [l for l in page.lines if about(l) and abs(l['top'] - l['bottom']) < 1 and l['x1'] - l['x0'] > 20 and
          (l.get('linewidth') or 0) <= RULE_MAX_WIDTH]
    # ...however thin the strokes: rules stand a line of text apart, and strokes that touch the
    # next one (no further off than their own width, or so) are a tint laid in bands.
    tops = sorted(l['top'] for l in hl)

    def banded(l):
        near = max(RULE_MIN_APART, 1.5 * (l.get('linewidth') or 0))
        return any(0 < abs(t - l['top']) <= near for t in tops)

    hl = [l for l in hl if not banded(l)]
    vl = [l for l in page.lines if inside(l) and abs(l['x0'] - l['x1']) < 1 and l['bottom'] - l['top'] > 6]
    bands = [r for r in page.rects if inside(r) and r['x1'] - r['x0'] > 15 and 4 < r['bottom'] - r['top'] < 60]
    rules = merge_near([l['top'] for l in hl] + [r['top'] for r in bands] + [r['bottom'] for r in bands])
    if len(rules) < 2:
        return None
    tx0 = min([l['x0'] for l in hl] + [r['x0'] for r in bands])
    tx1 = max([l['x1'] for l in hl] + [r['x1'] for r in bands])
    within = [l for l in lines if l['x0'] >= tx0 - 3 and l['x1'] <= tx1 + 3]
    above = sorted((l for l in within if l['baseline'] <= rules[0] + 1), key=lambda l: -l['baseline'])
    # The header: bold lines just above the first rule, gathered upwards while they stay close
    # together. Lines above it that aren't bold are a first data row (a table continued from the
    # page before has no header).
    header, first_row = [], []
    for l in above:
        prev = (header or first_row)[-1] if (header or first_row) else None
        if prev and prev['baseline'] - l['baseline'] > 1.8 * l['size']:
            break
        if header and l['size'] > header[0]['size'] + 0.5:     # the table's title, set larger
            break
        if not all(sp['bold'] for sp in l['spans']):
            if header:
                break
            if vl and l['baseline'] < min(v['top'] for v in vl):
                break            # above the column rules: a note printed over the table, not a row
            first_row.append(l)
            continue
        header.append(l)
    if not header and not first_row and not any(rules[0] < l['baseline'] <= rules[-1] for l in within):
        return None
    # The last row: lines below the last rule, while they stay within the table and close together.
    tail, prev = [], rules[-1]
    for l in sorted((l for l in lines if l['baseline'] > rules[-1]), key=lambda l: l['baseline']):
        if l['x0'] < tx0 - 3 or l['x1'] > tx1 + 3 or l['top'] - prev > 1.8 * l['size']:
            break
        tail.append(l)
        prev = l['baseline']
    end = (tail[-1]['baseline'] + 2) if tail else rules[-1]
    edges = ([min(l['baseline'] for l in first_row) - 1] if first_row else []) + \
        [rules[0] - 0.01] + rules[1:] + ([end] if tail else [])
    if vl:
        cols = merge_near([l['x0'] for l in vl], 3)
    else:
        starts, last = [], None
        for t, a, b in sorted((w for l in (header or first_row) for w in l['words']), key=lambda w: w[1]):
            if last is None or a - last > 8:
                starts.append(a - 2)
            last = b
        cols = starts[1:]
    bounds = [tx0 - 3] + [c for c in cols if tx0 < c < tx1] + [tx1 + 3]
    ncol = len(bounds) - 1
    hdr_cells = [[] for _ in range(ncol)]
    rows = [[[] for _ in range(ncol)] for _ in range(len(edges) - 1)]
    used = set()
    seen = set()
    note_from = None
    for l in sorted(within + tail, key=lambda l: (l['baseline'], l['x0'])):
        if id(l) in seen:
            continue
        seen.add(id(l))
        if l in header:
            target = hdr_cells
        else:
            r = next((i for i in range(len(edges) - 1) if edges[i] < l['baseline'] <= edges[i + 1] + 0.5), None)
            if r is None:
                continue
            target = rows[r]
        if target is not hdr_cells and r == len(rows) - 1 and l['text'].lstrip().startswith('*'):
            note_from = l['baseline']         # a footnote under the last row, with no rule between,
                                              # or in a ruled row of its own at the foot of the table
        if note_from is not None and l['baseline'] >= note_from:
            continue
        used.add(id(l))
        for t, a, b in l['words']:
            c = next((i for i in range(ncol) if bounds[i] <= (a + b) / 2 < bounds[i + 1]), ncol - 1)
            target[c].append((l['baseline'], a, b, t))
    rows = [[cell_text(c) for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    return {'bbox': [round(tx0, 1), round(min([h['top'] for h in header + first_row] + [rules[0]]), 1),
                     round(tx1, 1), round(end, 1)],
            'columns': [cell_text(c) for c in hdr_cells], 'rows': rows, 'line_ids': used}


def cell_text(words):
    """A cell's words, (baseline, x0, x1, text), in reading order. Words set a little above or
    below the line (a small "2H" inside brackets) read where they stand in it, touching what they
    touch, not as a line of their own."""
    out, line = [], []
    for w in sorted(words):
        if line and w[0] - line[0][0] > 3.0:
            out.append(sorted(line, key=lambda x: x[1]))
            line = []
        line.append(w)
    out.append(sorted(line, key=lambda x: x[1]))
    text = ''
    for line in out:
        for k, (_, x0, _, t) in enumerate(line):
            # A word set off the line, touching a bracket it sits in, has no space of its own.
            raised = k and abs(line[k - 1][0] - line[k][0]) > 0.5 and x0 - line[k - 1][2] < 0.6
            held = raised and (line[k - 1][3][-1] in '([' or t[0] in ')]')
            text += ('' if not text or held else ' ') + t
    return text


def titled_tables(page, box, lines):
    """A box holding several ruled tables, each under its own title (a line set well larger than
    the box's text), split into one part per table: [(sub-box,
    its lines)]. A box that isn't split this way, or whose parts don't each read as a table, is
    one part."""
    sizes = collections.Counter(l['size'] for l in lines)
    if not sizes:
        return [(box, lines)]
    body = sizes.most_common(1)[0][0]
    titles = sorted((l for l in lines if l['size'] >= body + 3),
                    key=lambda l: l['top'])
    cuts = [t['top'] - 2 for t in titles if t['top'] - box[1] > 3 * body]   # not the box's own heading
    if not cuts or len(titles) < 2:
        return [(box, lines)]
    edges = [box[1]] + cuts + [box[3]]
    parts = []
    for y0, y1 in zip(edges, edges[1:]):
        sub = (box[0], y0, box[2], y1)
        sl = [l for l in lines if y0 <= l['top'] < y1]
        if not sl or not read_table(page, sub, sl):
            return [(box, lines)]
        parts.append((sub, sl))
    return parts


def icon_words(page, words, icon_text, marks_here, shapes_here, alone=False):
    """Words standing in for icons printed inline in the text, for icons --icon-text names: a glyph
    in a named font, or a drawing with a given number of points ("pts:57"). Each sits on the
    baseline of the text beside it; one with no text beside it is left out."""
    out = []

    def glyph_text(m):
        """The text for one glyph: "Font:GLYPH=TEXT" for that glyph of a font whose glyphs mean
        different things, else "Font=TEXT" for any glyph of the font."""
        fonts = [k for k in icon_text if not k.startswith('pts:')]
        for k in fonts:
            font, sep, glyph = k.rpartition(':')
            if sep and font.lower() in m['font'].lower() and glyph == m['text']:
                return icon_text[k]
        return icon_text.get(next((k for k in fonts if ':' not in k and k.lower() in m['font'].lower()), None))

    items = [(m, glyph_text(m)) for m in marks_here if not m['text'].isspace()]
    items += [(sh, icon_text.get(f'pts:{sh["pts"]}')) for sh in shapes_here]
    # Left to right, so an icon standing after another icon finds that one beside it.
    for it, text in sorted(items, key=lambda x: (round(x[0]['top']), x[0]['x0'])):
        if not text:
            continue
        cy = (it['top'] + it['bottom']) / 2
        near = [w for w in list(words) + out if w['top'] - 2 <= cy <= w['bottom'] + 2 and
                (abs(w['x0'] - it['x1']) < 12 or abs(it['x0'] - w['x1']) < 12)]
        if not near:
            # With `alone`, an icon glyph on a line by itself (a heading's icons, turned over to
            # the line below its last word) is a word of that line, at the size it is printed.
            if not alone or 'font' not in it or not words:
                continue
            size = round(it['bottom'] - it['top'], 1)
            c = dict(words[0]['chars'][0], text=text, x0=it['x0'], x1=it['x1'], top=it['top'], bottom=it['bottom'],
                     size=size, fontname='Icon', matrix=None)
            out.append({'text': text, 'x0': it['x0'], 'x1': it['x1'], 'top': it['top'], 'bottom': it['bottom'],
                        'baseline': it['bottom'], 'chars': [c]})
            continue
        ref = min(near, key=lambda w: min(abs(w['x0'] - it['x1']), abs(it['x0'] - w['x1'])))
        c = dict(ref['chars'][0], text=text, x0=it['x0'], x1=it['x1'], fontname='Icon', matrix=None)
        out.append({'text': text, 'x0': it['x0'], 'x1': it['x1'], 'top': ref['top'], 'bottom': ref['bottom'],
                    'baseline': ref['baseline'], 'chars': [c]})
    return out


def page_lines(page, page_no, icon_fonts=(), marks=None, shapes=None, regions=None, icon_text=None,
               notes=None, drops=None, aside_fonts=(), usual=None, used_usual=None, icons_alone=False):
    """One page -> (lines in reading order, gutter x or None). Icon glyphs go to `marks`, small
    drawings to `shapes`, when those lists are given. With `regions` (a list), boxed panels are
    read as regions of their own: their lines follow the page's body lines, tagged with the box,
    and each box and ruled table is added to `regions`."""
    chars, marks_here, shapes_here, tilted = [], [], [], []
    for c in page.chars:
        f = font_name(c.get('fontname', ''))
        if icon_fonts and any(k.lower() in f.lower() for k in icon_fonts):
            marks_here.append({'page': page_no, 'x0': round(c['x0'], 1), 'x1': round(c['x1'], 1),
                               'top': round(c['top'], 1), 'bottom': round(c['bottom'], 1),
                               'font': f, 'text': c['text']})
            continue
        if tilt(c):
            tilted.append(c)
            continue
        if c['text'] in REPLACE_CHARS:
            CHARS_REPLACED[c['text']] += 1
            c = dict(c, text=REPLACE_CHARS[c['text']])
        elif UNMAPPED_GLYPH.match(c['text']):
            UNMAPPED.setdefault((c['text'], f), []).append(page_no)
        chars.append(c)
    for cv in page.curves:
        if cv['x1'] - cv['x0'] < SHAPE_MAX and cv['bottom'] - cv['top'] < SHAPE_MAX and cv.get('fill'):
            shapes_here.append({'page': page_no, 'x0': round(cv['x0'], 1), 'x1': round(cv['x1'], 1),
                                'top': round(cv['top'], 1), 'bottom': round(cv['bottom'], 1),
                                'pts': len(cv.get('pts') or [])})
    if marks is not None:
        marks += marks_here
    if shapes is not None:
        shapes += shapes_here
    # Text set apart in a face of its own (a pull quote: words of the body repeated large across
    # the columns) is taken out before the columns are found, so it neither joins the lines beside
    # it nor cuts the columns in two. Its lines follow the page's, marked `aside`.
    is_aside = lambda c: any(font_name(c.get('fontname', '')) == f and abs(c['size'] - z) < 0.3 for f, z in aside_fonts)
    aside_chars = [c for c in chars if is_aside(c)] if aside_fonts else []
    if aside_chars:
        chars = [c for c in chars if not is_aside(c)]
    words = make_words(chars, page.height, page_no, drops)
    if icon_text:
        words += icon_words(page, words, icon_text, marks_here, shapes_here, icons_alone)
    boxes = find_boxes(page, page_no, notes) if regions is not None else []
    panels = set(banded_panels(page)) if regions is not None else set()
    boxes = sorted(set(boxes) | panels, key=lambda b: (b[1], b[0]))
    gone = [b for b in boxes if text_runs_over(b, words, page_no, notes, (page.width, page.height))]
    within = lambda b, o: o != b and o[0] <= b[0] and o[1] <= b[1] and o[2] >= b[2] and o[3] >= b[3]
    holds = lambda b: any(b[0] <= (w['x0'] + w['x1']) / 2 <= b[2] and b[1] <= (w['top'] + w['bottom']) / 2 <= b[3]
                          for w in words)
    # A box on a backdrop that was set aside outlives it only if it holds text (a panel); an empty
    # one was part of the picture.
    boxes = outermost([b for b in boxes if b not in gone and (holds(b) or not any(within(b, o) for o in gone))])
    in_box = {}
    for w in words:
        cx, cy = (w['x0'] + w['x1']) / 2, (w['top'] + w['bottom']) / 2
        for i, (x0, top, x1, bottom) in enumerate(boxes):
            if f'{page_no}.{i + 1}' in NOT_BOXES:      # a frame the plan says is no panel: its words are the page's
                continue
            if x0 <= cx <= x1 and top <= cy <= bottom:
                in_box[id(w)] = i
                break
    # Running heads and footers often cross the middle, and a large title can sit off-centre;
    # only the body's text, at its usual sizes, decides the gutter.
    body = [w for w in words if id(w) not in in_box]
    sizes = sorted(c['size'] for w in body for c in w['chars'])
    usual_size = sizes[len(sizes) // 2] * 1.4 if sizes else 0
    # A table set across the page hides the gutters with its rows; the text around it shows them.
    # Its notes, under it, cross them too, so the lines directly under a table are left out of
    # the search; which of them are notes is settled once the gutters are known.
    full_rows, table_regions = table_rows(page, body, boxes)
    hidden = full_rows | {id(w) for run in under_tables(body, table_regions, full_rows) for _, ws in run for w in ws}
    gutters = gutters_under_a_standfirst([w for w in body if id(w) not in hidden and w['top'] >= page.height * MARGIN_TOP and
                                          w['bottom'] <= page.height * (1 - MARGIN_BOTTOM) and
                                          max(c['size'] for c in w['chars']) <= usual_size], page.width)
    if page_no in SET_GUTTERS:
        # A page of tables side by side, whose columns' blanks look like gutters: the plan says
        # where its columns are.
        gutters = list(SET_GUTTERS[page_no])
    elif usual and len(gutters) < len(usual):
        # The book's usual gutters, where this page's own body words leave each one clear (a
        # crossing line or so allowed, as when a gutter is found) and stand on both sides of one.
        sized = [w for w in body if id(w) not in hidden and w['top'] >= page.height * MARGIN_TOP and
                 w['bottom'] <= page.height * (1 - MARGIN_BOTTOM) and max(c['size'] for c in w['chars']) <= usual_size]
        rows = len({round(w['baseline']) for w in sized})
        crossing = [sum(1 for w in sized if w['x0'] < g - 1 and w['x1'] > g + 1) for g in usual]
        edges = [float('-inf')] + list(usual) + [float('inf')]
        filled = sum(1 for i in range(len(usual) + 1)
                     if any(edges[i] <= (w['x0'] + w['x1']) / 2 < edges[i + 1] for w in sized))
        # Lines across a gutter are allowed too when they all lie above the columns: an opening
        # set across the page, longer than a standfirst, over columns that start lower down. They
        # are then read as full-width lines over the columns.
        across = [w for w in sized if any(w['x0'] < g - 1 and w['x1'] > g + 1 for g in usual)]
        later = [w for w in sized if (w['x0'] + w['x1']) / 2 >= usual[-1] and w not in across]
        opening = bool(across) and bool(later) and max(w['baseline'] for w in across) < min(w['baseline'] for w in later)
        if sized and (max(crossing) <= max(1, rows // 50) or opening) and filled >= 2:
            gutters = list(usual)
            if used_usual is not None:
                used_usual.append(True)
    full_rows = full_rows - below_the_rows(body, table_regions, gutters, full_rows)
    out = order_lines(body, gutters, page_no, page.height, full_rows,
                      table_notes(body, table_regions, gutters, full_rows))
    keep_run_on(out, page_no, page.height)
    if aside_chars:
        asides = order_lines(make_words(aside_chars, page.height), (), page_no, page.height)
        for l in asides:
            l['aside'] = True
            l['furniture'] = False
        out += asides
    out += tilted_lines(tilted, page_no, page.width, page.height)
    for i, box in enumerate(boxes):
        bw = [w for w in words if in_box.get(id(w)) == i]
        if not bw:
            continue
        bid = f'{page_no}.{i + 1}'
        # A box is one or two columns; a table's columns inside it are not text columns.
        # ...and a table on a tinted panel has no text columns at all: each row is one line.
        inner = () if box in panels else find_gutters(bw, box[2] - box[0], box[0], three=False)
        if not inner and box not in panels:
            # A box's columns can sit under a lead-in set across it, as a page's can: columns of
            # three lines or more on each side, not a short last line beside a blank.
            g = gutters_under_a_standfirst(bw, box[2] - box[0], box[0], three=False)
            if g:
                by_line = collections.defaultdict(list)
                for w in bw:
                    by_line[round(w['baseline'])].append(w)
                clear = [ws for ws in by_line.values() if not any(w['x0'] < g[0] < w['x1'] for w in ws)]
                lefts = sum(1 for ws in clear if any(w['x1'] <= g[0] for w in ws))
                rights = sum(1 for ws in clear if any(w['x0'] >= g[0] for w in ws))
                if lefts >= 3 and rights >= 3:
                    inner = g
        bl = order_lines(bw, inner, page_no, page.height, blocks=panel_notes(page, box, bw) if box in panels else ())
        parts = titled_tables(page, box, bl)
        for k, (sub, sl) in enumerate(parts):
            sid = bid if len(parts) == 1 else f'{bid}.{k + 1}'
            for l in sl:
                l['box'] = sid
                # A panel reaching into the page's foot margin is still content: its last lines
                # are not a running foot. (The page's own number stays furniture, and so does a
                # running head a tall panel is drawn behind.)
                if (l['furniture'] and l['text'].strip() != str(page_no) and
                        l['top'] >= page.height * MARGIN_TOP):
                    l['furniture'] = False
            region = {'id': sid, 'kind': 'box', 'page': page_no, 'bbox': [round(v, 1) for v in sub]}
            if box in panels:
                region['bands'] = True        # a table with tinted rows: its lines are its rows
            table = read_table(page, sub, sl)
            if table:
                for l in sl:
                    if id(l) in table['line_ids']:
                        l['table'] = sid
                region.update(kind='table', table_bbox=table['bbox'], columns=table['columns'],
                              rows=table['rows'])
            regions.append(region)
            out += sl
    return out, gutters


def keep_run_on(lines, page_no, height):
    """A column's last line that dips into the foot margin is still body text, not a running
    foot: it sits one line below the line before it, at the same size, from the same left edge (or
    indented under it, as a bullet's second line is)."""
    for prev, l in zip(lines, lines[1:]):
        if (l['furniture'] and not prev['furniture'] and l['text'].strip() != str(page_no) and
                l['top'] > height / 2 and l['column'] == prev['column'] and l['size'] == prev['size'] and
                -2 <= l['x0'] - prev['x0'] <= 2 * l['size'] and
                0 < l['baseline'] - prev['baseline'] <= 1.5 * l['size']):
            l['furniture'] = False


def assign_headings(lines):
    sizes = collections.Counter()
    for l in lines:
        if not l['furniture'] and not l.get('aside'):
            for s in l['spans']:
                sizes[s['size']] += len(s['text'])
    if not sizes:
        return sizes, None
    body = sizes.most_common(1)[0][0]
    # A size larger than the body's is a heading size only when it is rare: a size set as often as
    # a fifth of the body text (a sidebar's text, a quote) is text, not headings.
    larger = sorted((s for s in sizes if s > body + 0.4 and sizes[s] < max(HEADING_SHARE * sizes[body], 200)), reverse=True)
    # Nor is the size a box's text is mostly set in (its body), however few boxes the pages have.
    per_box = collections.defaultdict(collections.Counter)
    for l in lines:
        if l.get('box') and not l.get('table') and not l['furniture']:
            for s in l['spans']:
                per_box[l['box']][s['size']] += len(s['text'])
    # (A box holding little but its title, over a table, has no body to go by.)
    box_bodies = {c.most_common(1)[0][0] for c in per_box.values() if c and c.most_common(1)[0][1] >= 200}
    larger = [s for s in larger if all(abs(s - b) > 0.4 for b in box_bodies)]
    level = {s: i + 1 for i, s in enumerate(larger)}
    for l in lines:
        if l['furniture'] or l.get('aside'):
            continue
        # A heading that runs on in smaller type ("Bell Ringing (Str) basic") is set by its lead:
        # a bold span at a heading size, a word or more long (not a drop capital).
        lead = l['spans'][0] if l['spans'] else None
        if (lead and lead['bold'] and lead['size'] in level and lead['size'] > l['size'] and
                len(re.findall(r'[^\W\d_]', lead['text'])) >= 3):
            l['size'] = lead['size']
        if l['size'] in level:
            l['heading'] = level[l['size']]
    return sizes, body


def set_gutters(specs):
    """--set-gutters values -> {printed page: [gutter x...]}: "297-304=305", "300=296,420",
    "305=none" (no gutters: the page is read whole)."""
    out = {}
    for s in specs:
        pages, _, xs = s.partition('=')
        if not xs:
            sys.exit(f'--set-gutters {s}: write PAGES=X,X (or PAGES=none)')
        first, _, last = pages.partition('-')
        gutters = [] if xs == 'none' else [float(x) for x in xs.split(',')]
        for p in range(int(first), int(last or first) + 1):
            out[p] = gutters
    return out


def read(pdf_path, first, last, offset, icon_fonts=(), boxes=False, icon_text=None, margin_lines=(),
         aside_fonts=(), icons_alone=False, replace_chars=None, not_boxes=(), usual_gutters=None, set_gutters=None):
    CASE_FIXED.clear()
    NOT_BOXES.clear()
    NOT_BOXES.update(not_boxes)
    SET_GUTTERS.clear()
    SET_GUTTERS.update(set_gutters or {})
    REPLACE_CHARS.clear()
    REPLACE_CHARS.update(replace_chars or {})
    CHARS_REPLACED.clear()
    UNMAPPED.clear()
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        if first + offset < 1 or last + offset > n:
            sys.exit(f'printed pages {first}-{last} with offset {offset} are PDF pages '
                     f'{first + offset}-{last + offset}, outside the PDF\'s 1-{n}')
        def one(p, usual=None):
            """A page read on its own: everything it adds, kept apart so it can be read again."""
            CASE_FIXED.clear()
            r = {'marks': [], 'shapes': [], 'regions': [], 'notes': [], 'drops': [], 'usual': []}
            r['lines'], r['gutters'] = page_lines(pdf.pages[p + offset - 1], p, icon_fonts, r['marks'], r['shapes'],
                                                  r['regions'] if boxes else None, icon_text, r['notes'],
                                                  r['drops'], aside_fonts, usual, r['usual'], icons_alone)
            r['case'] = collections.Counter(CASE_FIXED)
            return r

        pages = {p: one(p) for p in range(first, last + 1)}
        # The book's usual columns: the gutters most of these pages show. A page that shows fewer
        # (a panel or a picture fills most of a column, so too few words stand in it to count)
        # is read again with the usual ones, where its own words leave them clear.
        counts = collections.Counter(len(r['gutters']) for r in pages.values())
        most = counts.most_common(1)[0][0] if counts else 0
        gutter_notes = []
        if usual_gutters:
            # given (--usual-gutters): a chapter too short to show them on most of its pages
            most = max(len(g) for g in usual_gutters.values())
        if most and (usual_gutters or counts[most] >= max(3, 0.5 * len(pages))):
            # Left- and right-hand pages are often set as mirror images, their columns shifted by
            # the difference between the inner and outer margins: each side has its own usual.
            usual_of = dict(usual_gutters or {})
            for side in (0, 1):
                if side in usual_of:
                    continue
                with_most = [r['gutters'] for p, r in pages.items() if len(r['gutters']) == most and p % 2 == side]
                if with_most:
                    usual_of[side] = [sorted(g[i] for g in with_most)[len(with_most) // 2] for i in range(most)]
            for p, r in pages.items():
                if len(r['gutters']) < most and p % 2 in usual_of and p not in SET_GUTTERS:
                    again = one(p, usual_of[p % 2])
                    if again['usual']:
                        gutter_notes.append({'page': p, 'found': [round(g, 1) for g in r['gutters']],
                                             'read_with': [round(g, 1) for g in again['gutters']],
                                             'note': 'fewer columns found than the book usually has; read with its '
                                                     'usual gutters, which this page\'s words leave clear'})
                        pages[p] = again
        lines, marks, shapes, empty, gutters, regions, notes, drops = [], [], [], [], {}, [], [], []
        CASE_FIXED.clear()
        for p, r in pages.items():
            gutters[str(p)] = [round(g, 1) for g in r['gutters']] or None
            if not r['lines']:
                empty.append(p)
            for l in r['lines']:           # a handout set to the page's edges: its title, its last line
                if l['furniture'] and l['text'] in margin_lines:
                    l['furniture'] = False
            lines += r['lines']
            marks += r['marks']
            shapes += r['shapes']
            regions += r['regions']
            notes += r['notes']
            drops += r['drops']
            CASE_FIXED.update(r['case'])
    sizes, body = assign_headings(lines)
    return {'pages': f'{first}-{last}', 'page_offset': offset, 'body_size': body,
            'icon_fonts': list(icon_fonts),
            'fonts': [{'size': s, 'chars': c} for s, c in sorted(sizes.items(), reverse=True)],
            'gutters': gutters, 'gutter_notes': gutter_notes, 'pages_without_text': empty, 'lines': lines,
            'marks': marks, 'shapes': shapes,
            'regions': regions, 'image_notes': notes, 'drop_capitals': drops, 'case_fixed': dict(CASE_FIXED),
            'chars_replaced': {f'{k}={REPLACE_CHARS[k]}': n for k, n in CHARS_REPLACED.items()},
            'unmapped_glyphs': [{'glyph': g, 'font': f, 'count': len(ps), 'first_page': ps[0]}
                                for (g, f), ps in sorted(UNMAPPED.items())]}


def text_view(doc):
    out = []
    for l in doc['lines']:
        tag = ('F' if l['furniture'] else 'T' if l.get('table') else f'H{l["heading"]}' if l.get('heading') else
               'B' if l.get('box') else '  ')
        style_ = ('B' if l['bold'] else ' ') + ('I' if l['italic'] else ' ')
        out.append(f'p{l["page"]:<4} {l["column"][0].upper()} {tag:>3} {l["size"]:>5} {style_} {l["text"]}')
    return '\n'.join(out) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdf')
    ap.add_argument('--pages', required=True, help='printed page range, e.g. 30-109 or 87')
    ap.add_argument('--page-offset', type=int, default=0)
    ap.add_argument('--icon-fonts', nargs='*', default=[], help='fonts whose glyphs are icons, not text')
    ap.add_argument('--boxes', action='store_true', help='read boxed panels and their ruled tables as regions')
    ap.add_argument('--icon-text', nargs='*', default=[], metavar='ICON=TEXT',
                    help='put TEXT in the line where an icon is printed inline: FONT=TEXT for a glyph in an '
                         '--icon-fonts font, pts:N=TEXT for a drawing with N points')
    ap.add_argument('--margin-lines', nargs='*', default=[], metavar='TEXT',
                    help='lines printed in a page margin that are text, not page furniture, each given '
                         'whole (a handout set to the edges of its page: its title, its last line)')
    ap.add_argument('--replace-chars', nargs='*', default=[], metavar='READ=PRINTED',
                    help='a character the PDF gives wrongly and the one the page prints, for a font whose '
                         'encoding misnames a glyph (a multiplication sign read as a yen sign); each is counted '
                         'in `chars_replaced`')
    ap.add_argument('--not-boxes', nargs='*', default=[], metavar='PAGE.N',
                    help='boxes, by the id a first reading gave them, that are no panels (a frame drawn round a '
                         'picture that text runs past): their words are read with the page')
    ap.add_argument('--usual-gutters', nargs='*', default=[], metavar='SIDE=X,X',
                    help='the book\'s usual gutters, for a chapter too short to show them on most of its pages: '
                         'even=214.5,379.5 odd=232.5,397.5 (a page showing fewer is read again with them, '
                         'where its words leave them clear)')
    ap.add_argument('--set-gutters', nargs='*', default=[], metavar='PAGES=X,X',
                    help='the gutters of pages whose own blanks mislead (tables side by side, their columns\' '
                         'blanks looking like gutters), by printed page or range: 297-304=305 or 305=none')
    ap.add_argument('--icons-alone', action='store_true',
                    help='with --icon-text: an icon glyph with no text beside it makes a line of its own '
                         '(icons turned over to the line under a heading); otherwise it is left out of the text')
    ap.add_argument('--aside-fonts', nargs='*', default=[], metavar='FONT@SIZE',
                    help='a face that sets text apart from the columns (a pull quote), by its font name and '
                         'size: its lines are read on their own, after those of the page, and carry `aside`')
    ap.add_argument('--out', help='write the layout JSON here')
    ap.add_argument('--text', action='store_true', help='print a readable view instead of JSON')
    a = ap.parse_args(argv)
    first, last = parse_pages(a.pages)
    icon_text = dict(x.split('=', 1) for x in a.icon_text)
    aside_fonts = []
    for x in a.aside_fonts:
        font, at, size = x.rpartition('@')
        try:
            aside_fonts.append((font, float(size)))
        except ValueError:
            at = ''
        if not at or not font:
            sys.exit(f'--aside-fonts {x}: write FONT@SIZE, e.g. Garamond-Italic@14')
    doc = read(a.pdf, first, last, a.page_offset, a.icon_fonts, a.boxes, icon_text, a.margin_lines, aside_fonts,
               a.icons_alone, dict(x.split('=', 1) for x in a.replace_chars), a.not_boxes,
               {('even', 'odd').index(k): [float(v) for v in x.split(',')]
                for k, x in (u.split('=', 1) for u in a.usual_gutters)},
               set_gutters(a.set_gutters))
    if doc['pages_without_text']:
        print('no text layer on printed pages ' + ', '.join(map(str, doc['pages_without_text'])) +
              ': look at the page images, and ask before running OCR', file=sys.stderr)
    if a.text:
        sys.stdout.write(text_view(doc))
    elif a.out:
        with open(a.out, 'w', encoding='utf-8') as f:
            json.dump(doc, f, ensure_ascii=False, indent=0)
            f.write('\n')
        print(f'{len(doc["lines"])} lines, {len(doc["marks"])} marks, {len(doc["shapes"])} shapes, '
              f'body size {doc["body_size"]} -> {a.out}', file=sys.stderr)
        for font, k in doc['case_fixed'].items():
            print(f'font {font}: {k} capitals its character map read as lower case, kept as capitals',
                  file=sys.stderr)
        for n in doc['image_notes']:
            print(f'p{n["page"]} image {n["bbox"]}: {n["note"]}', file=sys.stderr)
        for n in doc['drop_capitals']:
            print(f'p{n["page"]}: {n["note"]}', file=sys.stderr)
    else:
        json.dump(doc, sys.stdout, ensure_ascii=False, indent=0)
        sys.stdout.write('\n')


if __name__ == '__main__':
    main()
