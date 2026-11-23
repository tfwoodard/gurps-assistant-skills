"""pdf_layout.py sets a pull quote aside (--aside-fonts) so it neither joins the lines beside it nor
cuts the columns, and puts a word for each icon glyph, by glyph, where a heading prints two icons
in a row (--icon-text FONT:GLYPH=TEXT). The page is invented and drawn here.

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


def draw_page(path):
    """Three columns of body text. A two-line quote in large oblique type lies across the left and
    middle columns, in a gap in their text; the right column runs on beside it, one of its lines on
    the quote's own baseline. Below, a heading in the left column ends in two icon glyphs."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    cols = (50, 220, 390)

    def body(x, rows, text):
        c.setFont('Helvetica', 9)
        for k in rows:
            c.drawString(x, h - 100 - 11 * k, text)

    body(cols[0], range(0, 6), 'Keepers trim the wicks at dusk.')
    body(cols[1], range(0, 6), 'Gulls circle the tower all day.')
    body(cols[2], range(0, 30), 'The bell rings on in the fog.')
    c.setFont('Helvetica-Oblique', 14)
    c.drawString(60, h - 100 - 11 * 8, 'The lamp is usually lit, but it is')        # baseline of the right column's row 8
    c.drawString(60, h - 100 - 11 * 8 - 17, 'not always the keeper who lights it.')
    body(cols[0], range(13, 20), 'Keepers trim the wicks at dusk.')
    body(cols[1], range(13, 30), 'Gulls circle the tower all day.')
    c.setFont('Helvetica-Bold', 14)
    c.drawString(cols[0], h - 100 - 11 * 22, 'Storm Lamp')
    c.setFont('Courier-Bold', 14)                                           # stands in for an icon font
    c.drawString(cols[0] + 86, h - 100 - 11 * 22, '3')                             # one icon
    c.drawString(cols[0] + 100, h - 100 - 11 * 22, '1')                            # another, straight after it
    body(cols[0], range(23, 30), 'Light both lamps at the bell.')
    c.showPage()
    c.save()


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class AsideAndIconTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pdf = os.path.join(cls.tmp.name, 'page.pdf')
        draw_page(cls.pdf)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def layout(self, *extra):
        out = os.path.join(self.tmp.name, 'layout.json')
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), self.pdf, '--pages', '1',
                            '--out', out, *extra], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding='utf-8') as f:
            return json.load(f)

    def test_a_pull_quote_set_aside_leaves_the_columns_whole(self):
        doc = self.layout('--aside-fonts', 'Helvetica-Oblique@14')
        asides = [l['text'] for l in doc['lines'] if l.get('aside')]
        self.assertEqual(asides, ['The lamp is usually lit, but it is', 'not always the keeper who lights it.'])
        self.assertFalse(any(l.get('heading') for l in doc['lines'] if l.get('aside')))
        rest = [l for l in doc['lines'] if not l.get('aside')]
        right = [l['text'] for l in rest if l['column'] == 'right']
        self.assertEqual(right, ['The bell rings on in the fog.'] * 30)       # the row on the quote's baseline too
        order = [l['column'] for l in rest]
        self.assertEqual(order, sorted(order, key=['left', 'middle', 'right'].index))   # each column read through

    def test_without_the_option_the_quote_takes_a_line_of_the_right_column_with_it(self):
        doc = self.layout()
        self.assertTrue(any('lit, but it is The bell rings' in l['text'] for l in doc['lines']))

    def test_two_icons_in_a_row_each_get_their_own_word(self):
        doc = self.layout('--aside-fonts', 'Helvetica-Oblique@14', '--icon-fonts', 'Courier',
                          '--icon-text', 'Courier:3=[square]', 'Courier:1=[disc]')
        self.assertIn('Storm Lamp [square] [disc]', [l['text'] for l in doc['lines']])
        self.assertEqual(sorted(m['text'] for m in doc['marks']), ['1', '3'])

    def test_a_character_the_fonts_give_wrongly_is_replaced_and_counted(self):
        doc = self.layout('--replace-chars', 'K=C', 'G=B')
        texts = {l['text'] for l in doc['lines']}
        self.assertIn('Ceepers trim the wicks at dusk.', texts)
        self.assertIn('Bulls circle the tower all day.', texts)
        self.assertEqual(doc['chars_replaced'], {'K=C': 13, 'G=B': 23})
        self.assertEqual(self.layout()['chars_replaced'], {})

    def test_a_badly_written_aside_font_is_refused(self):
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), self.pdf, '--pages', '1',
                            '--aside-fonts', 'Helvetica-Oblique'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('FONT@SIZE', r.stderr)


def draw_quote_with_source(path):
    """A pull quote in large oblique type across the left and middle columns, its speaker under it,
    and its story's title on two lines in large bold oblique, the first reaching well past the
    quote's right edge, level with a right-column line. The same bold oblique face heads a section
    lower down."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4

    def body(x, rows, text):
        c.setFont('Helvetica', 9)
        for k in rows:
            c.drawString(x, h - 100 - 11 * k, text)

    body(50, range(0, 6), 'Keepers trim the wicks at dusk.')
    body(220, range(0, 6), 'Gulls circle the tower all day.')
    body(390, range(0, 40), 'The bell rings on in the fog.')
    c.setFont('Helvetica-Oblique', 14)
    c.drawString(80, h - 100 - 11 * 8, 'Keep the lamp lit.')
    c.drawString(100, h - 100 - 11 * 8 - 16, '- The Old Keeper,')
    c.setFont('Helvetica-BoldOblique', 14)
    c.drawString(100, h - 100 - 11 * 8 - 32, 'The Tower at the End of')    # wider than the quote
    c.drawString(100, h - 100 - 11 * 8 - 48, 'the World')
    body(50, range(16, 24), 'Keepers trim the wicks at dusk.')
    body(220, range(16, 40), 'Gulls circle the tower all day.')
    c.setFont('Helvetica-BoldOblique', 14)
    c.drawString(50, h - 100 - 11 * 26, 'Storm Watch')
    body(50, range(28, 40), 'Light both lamps at the bell.')
    c.showPage()
    c.save()


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class QuoteSourceTest(unittest.TestCase):
    def test_the_source_under_a_quote_goes_with_it_and_the_face_elsewhere_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, out = os.path.join(d, 'page.pdf'), os.path.join(d, 'layout.json')
            draw_quote_with_source(pdf)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1',
                                '--out', out, '--aside-fonts', 'Helvetica-Oblique@14'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding='utf-8') as f:
                doc = json.load(f)
        asides = [l['text'] for l in doc['lines'] if l.get('aside')]
        self.assertEqual(asides, ['Keep the lamp lit.', '- The Old Keeper,', 'The Tower at the End of', 'the World'])
        rest = [l['text'] for l in doc['lines'] if not l.get('aside')]
        self.assertIn('Storm Watch', rest)
        self.assertEqual(rest.count('The bell rings on in the fog.'), 40)


if __name__ == '__main__':
    unittest.main()
