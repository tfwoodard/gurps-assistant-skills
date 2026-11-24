"""pdf_layout.py: a space in the text layer that the next glyph is printed over takes no room on
the page and doesn't part two words ("lantern" / " " / "light", left where a line was broken once and
set again); a space that takes its room does. The page is invented and drawn here.

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
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
    HAVE_LIBS = True
except ImportError:  # pragma: no cover
    HAVE_LIBS = False

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'skills', 'gurps-import', 'scripts')


def draw_page(path):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setFont('Helvetica', 9)
    # "Lantern " and then "light" printed over its space: one word
    c.drawString(60, h - 100, 'The lantern')
    x = 60 + stringWidth('The lantern', 'Helvetica', 9)
    c.drawString(x, h - 100, ' ')
    c.drawString(x, h - 100, 'light fades.')
    # a hyphen printed over the space after a word: the word and its hyphen, as at a line's end
    c.drawString(60, h - 111, 'Keep the wick')
    x = 60 + stringWidth('Keep the wick', 'Helvetica', 9)
    c.drawString(x, h - 111, ' ')
    c.drawString(x, h - 111, '-')
    # an ordinary space between words
    c.drawString(60, h - 122, 'Trim it daily.')
    c.showPage()
    c.save()


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class OverprintedSpaceTest(unittest.TestCase):
    def test_a_space_printed_over_joins_the_words_either_side_and_a_real_space_parts_them(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, out = os.path.join(d, 'page.pdf'), os.path.join(d, 'layout.json')
            draw_page(pdf)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1',
                                '--out', out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding='utf-8') as f:
                texts = [l['text'] for l in json.load(f)['lines']]
        self.assertEqual(texts, ['The lanternlight fades.', 'Keep the wick-', 'Trim it daily.'])


if __name__ == '__main__':
    unittest.main()
