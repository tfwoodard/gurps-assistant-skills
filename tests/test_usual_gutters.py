"""pdf_layout.py --usual-gutters: a page whose own words hide a column (a long opening set across
the page, over three columns that start lower down) is read with the book's usual gutters. The page
is invented and drawn here.

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
COLS = (50, 220, 390)


def draw_page(path):
    """Fourteen lines across the left two thirds of the page (a picture would sit to their right),
    then three columns of text, the right one starting lower."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica', 9)
    for k in range(14):
        c.drawString(50, h - 80 - 11 * k, 'The keepers of the marsh lamps tend them all night long, every night.')
    for k in range(20):
        c.drawString(COLS[0], h - 260 - 11 * k, 'Left column words here.')
        c.drawString(COLS[1], h - 260 - 11 * k, 'Middle column words.')
        c.drawString(COLS[2], h - 300 - 11 * k, 'Right column words.')
    c.showPage()
    c.save()


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class UsualGuttersTest(unittest.TestCase):
    def layout(self, *extra):
        with tempfile.TemporaryDirectory() as d:
            pdf, out = os.path.join(d, 'page.pdf'), os.path.join(d, 'layout.json')
            draw_page(pdf)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1',
                                '--out', out, *extra], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding='utf-8') as f:
                return json.load(f)

    def test_the_usual_gutters_read_the_columns_under_a_long_opening(self):
        doc = self.layout('--usual-gutters', 'odd=210,380', 'even=200,370')
        self.assertEqual(doc['gutters']['1'], [210.0, 380.0])
        self.assertEqual([n['page'] for n in doc['gutter_notes']], [1])
        texts = [(l['column'], l['text']) for l in doc['lines']]
        self.assertEqual({c for c, t in texts if t.startswith('The keepers')}, {'full'})
        cols = [c for c, t in texts if not t.startswith('The keepers')]
        self.assertEqual(cols, ['left'] * 20 + ['middle'] * 20 + ['right'] * 20)

    def test_gutters_the_plan_sets_are_the_pages_own(self):
        doc = self.layout('--set-gutters', '1=210')
        self.assertEqual(doc['gutters']['1'], [210.0])
        texts = [(l['column'], l['text']) for l in doc['lines']]
        self.assertIn(('left', 'Left column words here.'), texts)
        self.assertTrue(any(c == 'right' and t.startswith('Middle column words.') for c, t in texts))
        doc = self.layout('--set-gutters', '1=none')
        self.assertIsNone(doc['gutters']['1'])

    def test_without_them_the_columns_run_together(self):
        doc = self.layout()
        self.assertFalse(doc['gutter_notes'])
        self.assertTrue(any('Left column words here. Middle column words.' in l['text'] for l in doc['lines']))


if __name__ == '__main__':
    unittest.main()
