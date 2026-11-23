"""pdf_layout.py reads a table set on a tinted panel wider than a column as rows of its own, and
a display heading standing alone inside one column as heading everything below it. convert_traits
then puts such a table into the entry the plan names. The page and its traits are invented.

Run: python -m unittest discover tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    HAVE_LIBS = True
except ImportError:  # pragma: no cover
    HAVE_LIBS = False

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'skills', 'gurps-import', 'scripts')
sys.path.insert(0, SCRIPTS)
import convert_traits  # noqa: E402

COLS = (50, 220, 390)


def draw_page(path):
    """Three columns. Top: a trait's name and cost in the left column, and beside it, across the
    middle and right columns, its table on a white panel with two rows tinted. Mid-page: a large
    heading that fits inside the middle column, the other columns blank beside it, and text under
    it in all three."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    def text(x, y, s, font='Helvetica', size=9):
        c.setFont(font, size)
        c.drawString(x, h - y, s)

    text(COLS[0], 100, 'Short Reach', 'Helvetica-BoldOblique', 14)
    text(COLS[0] + 90, 114, '-10 points', 'Helvetica-Bold', 11)
    for k in range(12):
        text(COLS[0], 128 + 11 * k, 'Your reach is shorter than most.')
    # the panel: a white ground, two tinted rows as thick strokes, a header and four rows
    px0, px1, ptop, pbot = 215, 545, 86, 150
    c.setFillColorRGB(1, 1, 1)
    c.rect(px0, h - pbot, px1 - px0, pbot - ptop, stroke=0, fill=1)
    c.setLineWidth(12)
    c.setStrokeColorRGB(0.92, 0.88, 0.86)
    for y in (114, 136):
        c.line(px0 + 1, h - y + 3, px1 - 1, h - y + 3)
    c.setFillColorRGB(0, 0, 0)
    text(220, 103, 'Level', 'Helvetica-BoldOblique')
    text(300, 103, 'Reach', 'Helvetica-BoldOblique')
    text(420, 103, 'Throw', 'Helvetica-BoldOblique')
    for k, (a, b, d) in enumerate((('0 (Usual)', '6 feet', '40 yards'), ('1', '5 feet', '30 yards'),
                                   ('2', '4 feet', '20 yards'), ('3', '3 feet', '10 yards'))):
        text(220, 114 + 11 * k, a)
        text(300, 114 + 11 * k, b)
        text(420, 114 + 11 * k, d)
    for k in range(9):
        text(COLS[1], 172 + 11 * k, 'The middle column runs on here.')
        text(COLS[2], 172 + 11 * k, 'The right column runs on here.')
    c.setFont('Helvetica-Bold', 36)
    c.drawString(COLS[1] + 20, h - 330, 'KNACKS')                       # inside the middle column
    for k in range(10):
        text(COLS[0], 360 + 11 * k, 'A knack is a small gift, as the')
        text(COLS[1], 360 + 11 * k, 'marsh folk say, and costs little')
        text(COLS[2], 360 + 11 * k, 'to learn and less to forget.')
    c.showPage()
    c.save()


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class PanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            pdf, out = os.path.join(d, 'page.pdf'), os.path.join(d, 'layout.json')
            draw_page(pdf)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1',
                                '--boxes', '--out', out], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            with open(out, encoding='utf-8') as f:
                cls.doc = json.load(f)

    def test_the_panel_is_a_region_whose_lines_are_its_rows(self):
        regions = self.doc['regions']
        self.assertEqual([(r['id'], r['kind'], r.get('bands')) for r in regions], [('1.1', 'box', True)])
        rows = [l['text'] for l in self.doc['lines'] if l.get('box') == '1.1']
        self.assertEqual(rows, ['Level Reach Throw', '0 (Usual) 6 feet 40 yards', '1 5 feet 30 yards',
                                '2 4 feet 20 yards', '3 3 feet 10 yards'])

    def test_the_columns_beside_and_under_the_panel_are_still_found(self):
        self.assertEqual(len(self.doc['gutters']['1']), 2)
        left = [l['text'] for l in self.doc['lines'] if l['column'] == 'left' and not l.get('box')]
        self.assertEqual(left[:3], ['Short Reach', '-10 points', 'Your reach is shorter than most.'])

    def test_a_display_heading_alone_at_its_height_heads_what_is_below_it(self):
        lines = [l for l in self.doc['lines'] if not l.get('box')]
        texts = [l['text'] for l in lines]
        at = texts.index('KNACKS')
        self.assertEqual(lines[at]['column'], 'full')
        self.assertFalse(any(t.startswith('A knack is') for t in texts[:at]))          # the left column's lower part
        self.assertTrue(all(t in texts[:at] for t in ('Your reach is shorter than most.', 'The right column runs on here.')))
        self.assertEqual(texts[at + 1], 'A knack is a small gift, as the')

    def test_the_converter_puts_the_table_into_the_entry_the_plan_names(self):
        doc = json.loads(json.dumps(self.doc))
        for l in doc['lines']:                                                    # the fixture's faces, as a plan gives them
            l.pop('heading', None)
            if l['size'] == 36.0:
                l['heading'] = 1
            elif l['size'] == 14.0:
                l['heading'] = 2
            elif l['size'] == 11.0:
                l['heading'] = 3
        plan = {'source': 'ML', 'chapter': 'ch3', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'indent': False,
                'boxes': {'1.1': {'into': 'disadvantages/short-reach'}}}
        # a heading over the page's first lines makes them a list of traits
        head = {'page': 1, 'column': 'full', 'top': 40, 'baseline': 60, 'x0': 50, 'x1': 200, 'text': 'FLAW LIST', 'size': 36.0,
                'bold': True, 'italic': False, 'font': 'T', 'spans': [{'text': 'FLAW LIST', 'size': 36.0, 'bold': True, 'italic': False}],
                'words': [['FLAW', 50, 120], ['LIST', 130, 200]], 'furniture': False, 'heading': 1}
        doc['lines'].insert(0, head)
        plan['sections'] = [{'heading': 'Flaw List', 'page': 1, 'traits': {'category': 'disadvantages', 'kind': 'disadvantage',
                                                                          'starred': 'self_control'}}]
        entries, report = convert_traits.convert_chapter(doc, plan)
        self.assertEqual(report['errors'], [])
        e = next(e for c, e in entries if e['slug'] == 'short-reach')
        self.assertEqual(e['fields'], {'kind': 'disadvantage', 'cost': '-10 points', 'leveled': False, 'self_control': False})
        table = e['content'][-1]
        self.assertEqual((table['type'], table['columns']), ('table', ['Level', 'Reach', 'Throw']))
        self.assertEqual(table['rows'][0], ['0 (Usual)', '6 feet', '40 yards'])
        self.assertEqual(table['read_with'], ['before'])
        self.assertEqual(report['tables'][0]['entry'], 'disadvantages/short-reach')

    def test_a_panel_the_plan_gives_no_owner_is_an_error(self):
        doc = json.loads(json.dumps(self.doc))
        plan = {'source': 'ML', 'chapter': 'ch3', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'intro': {'name': 'Flaws'}}
        _, report = convert_traits.convert_chapter(doc, plan)
        self.assertTrue(any('box 1.1 (p1) is a table on a panel of its own' in e and 'with `into`' in e for e in report['errors']))


if __name__ == '__main__':
    unittest.main()
