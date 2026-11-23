"""pdf_layout.py reads a panel whose frame is drawn (an outline with cut-off corners over a tint
made of thick strokes) as a box, and does not take the tint for a table's rules. The page is
invented and drawn here.

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


def draw_page(path, band=6.5):
    """Two columns of body text, and under them a panel across the page: a tint of thick strokes
    laid edge to edge, an eight-sided outline round it, a title and two columns of text in it."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica', 9)
    for k in range(12):
        c.drawString(60, h - 100 - 11 * k, 'Keepers trim the wicks at dusk.')
        c.drawString(310, h - 100 - 11 * k, 'Gulls circle the tower all day.')
    x0, x1, top, bottom = 60, 540, h - 300, h - 480
    c.setLineWidth(band)
    for k in range(int(178 / band)):                         # the tint: strokes laid edge to edge
        c.setStrokeColorRGB(0.75 + 0.001 * k, 0.84, 0.92)
        y = top - 4 - band * 0.98 * k
        c.line(x0 + 6, y, x1 - 6, y)
    c.setLineWidth(1)
    c.setStrokeColorRGB(0, 0.47, 0.7)
    p = c.beginPath()                                        # the frame, corners cut off
    cut = 10
    p.moveTo(x0 + cut, top)
    for x, y in ((x1 - cut, top), (x1, top - cut), (x1, bottom + cut), (x1 - cut, bottom), (x0 + cut, bottom),
                 (x0, bottom + cut), (x0, top - cut)):
        p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(w / 2, top - 24, 'Storm Lamps')
    c.setFont('Helvetica', 9)
    for k in range(8):
        c.drawString(x0 + 16, top - 50 - 11 * k, 'Light both lamps when the bell rings.')
        c.drawString(310, top - 50 - 11 * k, 'Douse them when the fog lifts.')
    c.showPage()
    c.save()


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class DrawnFrameTest(unittest.TestCase):
    band = 6.5                       # the width of each stroke of the tint

    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            pdf, out = os.path.join(d, 'page.pdf'), os.path.join(d, 'layout.json')
            draw_page(pdf, cls.band)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1',
                                '--boxes', '--out', out], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            with open(out, encoding='utf-8') as f:
                cls.doc = json.load(f)

    def test_the_drawn_frame_is_one_box_and_its_tint_is_not_a_table(self):
        self.assertEqual([(r['id'], r['kind']) for r in self.doc['regions']], [('1.1', 'box')])

    def test_the_lines_inside_it_are_the_boxs_and_the_rest_are_the_pages(self):
        boxed = [l['text'] for l in self.doc['lines'] if l.get('box')]
        self.assertEqual(boxed[0], 'Storm Lamps')
        self.assertEqual(sorted(set(boxed[1:])), ['Douse them when the fog lifts.', 'Light both lamps when the bell rings.'])
        self.assertEqual(len(boxed), 17)
        outside = {l['text'] for l in self.doc['lines'] if not l.get('box')}
        self.assertEqual(outside, {'Keepers trim the wicks at dusk.', 'Gulls circle the tower all day.'})


class ThinBandsTest(DrawnFrameTest):
    """The same panel with its tint laid in strokes as thin as a rule: still a tint, not a table."""
    band = 2.4


if __name__ == '__main__':
    unittest.main()
