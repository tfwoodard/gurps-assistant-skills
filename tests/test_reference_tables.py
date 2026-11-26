"""A book's appendix of reference tables: convert_traits.py makes `tables` entries of the plan's
sections (`category`, `name`), carries a panel on into the next page's (`continues`), reads lists
set with hanging indents (`hanging_lists`) and gives each footnote under a panel's table a
paragraph of its own. pdf_layout.py reads a panel nearly as wide as the page in three columns, and
a page whose columns change at a panel across it in bands. Everything here is invented.

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

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts')
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)
import convert_traits  # noqa: E402
from test_convert_traits import Page  # noqa: E402


def chapter():
    p = Page()
    p.line('LAMP HOURS', size=20.0, heading=2, bold=True)
    p.para('How long a lamp burns, by its oil.')
    p.line('WICK MODIFIERS', size=20.0, heading=2, bold=True)
    p.para('When lighting a lamp, figure your', 'roll by:')
    p.line('Weather', size=10.9, heading=10, bold=True)
    p.line('Rain: -2')
    p.line('Wind, strong or gusting: -4 (or')
    p.line('-2 behind glass)', indent=12.0)
    p.line('Fog: -1')
    p.line('Keeper', size=10.9, heading=10, bold=True)
    p.para('A keeper who has trimmed the', 'wick today adds one.')
    p.line('Tired: -1')
    p.at(page=11, column='left', y=60.0, box='11.1')
    p.line('LAMP LOG', size=20.0, heading=2, bold=True)
    p.para('Write each lamp in the log.')
    p.at(page=12, column='left', y=60.0, box='12.1')
    p.line("LAMP LOG (CONT'D)", size=20.0, heading=2, bold=True)
    p.para('Sign the log at dawn.')
    return {'lines': p.lines, 'regions': [{'id': '11.1', 'kind': 'box', 'page': 11},
                                          {'id': '12.1', 'kind': 'box', 'page': 12}]}


PLAN = {'source': 'ML', 'chapter': 'tables', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
        'entries': {'rules/lamp-hours': {'category': 'tables', 'name': 'Lamp Hours Table',
                                         'fields': {'about': 'How long each oil burns', 'roll': '1d'}}},
        'boxes': {'12.1': {'continues': 'rules/lamp-log'}},
        'hanging_lists': ['rules/wick-modifiers']}


class ReferenceTablesTest(unittest.TestCase):
    def setUp(self):
        self.entries, self.report = convert_traits.convert_chapter(chapter(), json.loads(json.dumps(PLAN)))
        self.by = {f'{c}/{e["slug"]}': e for c, e in self.entries}

    def test_a_section_the_plan_names_a_table_is_a_tables_entry_under_the_tables_name(self):
        self.assertEqual(self.report['errors'], [])
        e = self.by['tables/lamp-hours-table']
        self.assertEqual(e['name'], 'Lamp Hours Table')
        self.assertEqual(e['fields'], {'printed_name': 'Lamp Hours', 'about': 'How long each oil burns', 'roll': '1d'})
        self.assertNotIn('rules/lamp-hours', self.by)
        self.assertEqual(self.report['counts'], {'tables': 1, 'rules': 2})

    def test_items_set_with_hanging_indents_are_a_paragraph_each(self):
        e = self.by['rules/wick-modifiers']
        self.assertEqual([b.get('text') for b in e['content']],
                         ['When lighting a lamp, figure your roll by:', 'Weather', 'Rain: -2',
                          'Wind, strong or gusting: -4 (or -2 behind glass)', 'Fog: -1', 'Keeper',
                          'A keeper who has trimmed the wick today adds one.', 'Tired: -1'])

    def test_a_panel_carried_on_goes_on_at_the_end_of_the_entry_and_its_title_is_left_out(self):
        e = self.by['rules/lamp-log']
        self.assertEqual([b['text'] for b in e['content']], ['Write each lamp in the log.', 'Sign the log at dawn.'])
        self.assertNotIn('rules/lamp-log-contd', self.by)
        self.assertEqual([(x['text'], x['why']) for x in self.report['left_out']],
                         [("LAMP LOG (CONT'D)", 'the title of a panel carrying on rules/lamp-log, repeated')])

    def test_plan_options_that_match_nothing_are_errors(self):
        plan = json.loads(json.dumps(PLAN))
        plan['hanging_lists'].append('rules/no-such-list')
        plan['boxes']['12.1']['continues'] = 'rules/no-such-log'
        _, report = convert_traits.convert_chapter(chapter(), plan)
        self.assertIn('plan hanging_lists: rules/no-such-list matches no entry of the chapter', report['errors'])
        self.assertTrue(any('`continues` rules/no-such-log, which is no entry' in e for e in report['errors']))


class PanelFootnotesTest(unittest.TestCase):
    def test_each_footnote_under_a_panels_table_is_a_paragraph_of_its_own(self):
        from test_text_tables import line, table
        doc = chapter()
        rows = table([[(70, 'Dusk'), (130, '2*')], [(70, 'Night'), (130, '4†')]], [(70, 'Hour'), (130, 'Lamps')], y=300.0)
        notes = [line(340.0, [(70, '* Only by day.')]), line(351.0, [(70, '† Twice in a fog, and')]),
                 line(362.0, [(70, 'again at dawn.')])]
        for l in rows + notes:
            l.update(page=13, box='13.1')
        doc['lines'] += rows + notes
        doc['regions'].append({'id': '13.1', 'kind': 'box', 'page': 13, 'bands': True})
        plan = json.loads(json.dumps(PLAN))
        plan['boxes']['13.1'] = {'into': 'rules/lamp-log', 'after_lines': 3}
        entries, report = convert_traits.convert_chapter(doc, plan)
        self.assertEqual(report['errors'], [])
        e = next(e for c, e in entries if e['slug'] == 'lamp-log')
        self.assertEqual([b['type'] for b in e['content']], ['paragraph', 'paragraph', 'table', 'paragraph', 'paragraph'])
        self.assertEqual([b['text'] for b in e['content'][3:]], ['* Only by day.', '† Twice in a fog, and again at dawn.'])


def draw_wide_panel(path):
    """Two columns of body text, and under them a frame nearly as wide as the page holding a title
    and three columns of text."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica', 9)
    for k in range(12):
        c.drawString(60, h - 100 - 11 * k, 'Keepers trim the wicks at dusk.')
        c.drawString(310, h - 100 - 11 * k, 'Gulls circle the tower all day.')
    c.setLineWidth(1)
    c.rect(50, h - 520, 495, 270, stroke=1, fill=0)
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(w / 2, h - 275, 'The Keepers Lamp Log, Kept Nightly')
    c.setFont('Helvetica', 9)
    for k in range(16):
        c.drawString(62, h - 300 - 11 * k, 'First the oil is poured.')
        c.drawString(225, h - 300 - 11 * k, 'Then the wick is trimmed.')
        c.drawString(390, h - 300 - 11 * k, 'Last the glass is wiped.')
    c.showPage()
    c.save()


def draw_banded_page(path, columns_below=2):
    """Three short columns at the top, a frame across the page, and under it `columns_below`
    columns of text."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica', 9)
    for k in range(4):
        c.drawString(60, h - 80 - 11 * k, 'Reeds bend.')
        c.drawString(225, h - 80 - 11 * k, 'Gulls cry.')
        c.drawString(390, h - 80 - 11 * k, 'Fog lifts.')
    c.setLineWidth(1)
    c.rect(50, h - 330, 495, 200, stroke=1, fill=0)
    xs = (60, 310) if columns_below == 2 else (60, 225, 390)
    for k in range(20):
        for n, x in enumerate(xs):
            c.drawString(x, h - 360 - 11 * k, f'Column {n + 1} text below.')
    c.showPage()
    c.save()


def read_layout(pdf, *extra):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, 'layout.json')
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1', '--boxes',
                            '--out', out, *extra], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        with open(out, encoding='utf-8') as f:
            return json.load(f)


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class WidePanelTest(unittest.TestCase):
    def test_a_panel_nearly_as_wide_as_the_page_is_read_in_three_columns(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, 'page.pdf')
            draw_wide_panel(pdf)
            doc = read_layout(pdf)
        boxed = [l for l in doc['lines'] if l.get('box')]
        self.assertEqual(boxed[0]['text'], 'The Keepers Lamp Log, Kept Nightly')
        self.assertEqual([(l['column'], l['text']) for l in boxed[1:]],
                         [('left', 'First the oil is poured.')] * 16 + [('middle', 'Then the wick is trimmed.')] * 16 +
                         [('right', 'Last the glass is wiped.')] * 16)


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class BandedPageTest(unittest.TestCase):
    def test_columns_over_a_panel_more_than_the_pages_are_read_as_their_own_band(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, 'page.pdf')
            draw_banded_page(pdf)
            doc = read_layout(pdf)
        texts = [(l['column'], l['text']) for l in doc['lines'] if not l.get('box')]
        self.assertEqual(texts[:12], [('left', 'Reeds bend.')] * 4 + [('middle', 'Gulls cry.')] * 4 +
                         [('right', 'Fog lifts.')] * 4)
        self.assertEqual(texts[12:], [('left', 'Column 1 text below.')] * 20 + [('right', 'Column 2 text below.')] * 20)
        self.assertTrue(any('read in bands' in n.get('note', '') for n in doc['image_notes']))

    def test_a_page_the_plan_names_is_read_band_by_band_though_its_columns_do_not_change(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, 'page.pdf')
            draw_banded_page(pdf, columns_below=3)
            whole, banded = read_layout(pdf), read_layout(pdf, '--band-pages', '1')
        first = lambda doc: [l['text'] for l in doc['lines'] if not l.get('box')][:6]
        # read as one page, its left column runs down past the frame before the middle starts
        self.assertEqual(first(whole), ['Reeds bend.'] * 4 + ['Column 1 text below.'] * 2)
        # read in bands, the three short columns over the frame come first
        self.assertEqual(first(banded), ['Reeds bend.'] * 4 + ['Gulls cry.'] * 2)


if __name__ == '__main__':
    unittest.main()
