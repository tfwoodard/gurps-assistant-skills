"""pdf_layout.py on a page set in three columns with a table across it: the table's rows (on thick
strokes of tint) hide the gutters, so the gutters are found from the text around it; the table's
notes, set in two columns of their own under it, are read as their own columns; and a framed box
whose two columns sit under a lead-in set across it is read in its columns. The page is invented
and drawn here.

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


def draw_table(c, h):
    """Columns of text, then a table across the page on stripes of tint; its rows end at h - 304."""
    c.setFont('Helvetica', 9)
    for k in range(10):                                          # three columns above the table
        for x, t in zip(COLS, ('Keepers trim the wicks.', 'Gulls circle the tower.', 'Fog rolls in at dusk.')):
            c.drawString(x, h - 80 - 11 * k, t)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, h - 230, 'Harbour Lamp Table')
    c.setFont('Helvetica-Oblique', 9)
    c.drawString(55, h - 245, 'Lamp')
    c.drawString(195, h - 245, 'Reach')
    c.drawString(300, h - 245, 'Oil')
    c.drawString(420, h - 245, 'Cost')
    names = ('Brass Lamp of the Quay', 'Tin Lantern of the Mole', 'Glass Beacon of the Point',
             'Copper Lamp of the Pier', 'Iron Brazier of the Wall')
    for k, name in enumerate(names):
        y = h - 260 - 11 * k
        c.setLineWidth(8)
        c.setStrokeColorRGB(0.85, 0.9, 0.95)
        c.line(50, y + 3, 545, y + 3)
        c.setFont('Helvetica', 9)
        c.drawString(55, y, name)
        c.drawString(195, y, f'{k + 2} yards')
        c.drawString(300, y, f'{k + 1} pints a night')
        c.drawString(420, y, f'${10 * (k + 1)}')


def draw_table_page(path):
    """The table's notes in two columns of their own, then three columns of text."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    draw_table(c, h)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(50, h - 320, 'Notes')
    c.setFont('Helvetica', 9)
    left = ['[1] Smokes badly when the wick is left long, so the', 'keepers trim it every hour of the night or else',
            'the glass goes black.', '[2] Needs a second keeper on stormy nights, to hold', 'the shutter open against the wind.']
    right = ['[3] Seen from the far side of the bay on a clear', 'night, and from the cliffs above the town when',
             'the fog is thin.', '[4] Burns driftwood as well as oil, but the smoke', 'drifts over the town and the harbour.']
    for k, (a, b) in enumerate(zip(left, right)):
        c.drawString(50, h - 331 - 11 * k, a)
        c.drawString(300, h - 331 - 11 * k, b)
    for k in range(12):                                          # three columns below it
        for x, t in zip(COLS, ('Ropes hang by the door.', 'Bells ring the hours.', 'Boats come in at noon.')):
            c.drawString(x, h - 420 - 11 * k, t)
    c.showPage()
    c.save()


def draw_notes_in_columns_page(path):
    """The table's notes in the page's own left column, their heading a line under the last row
    and level with the other columns' text."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    draw_table(c, h)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(50, h - 318, 'Notes')
    c.setFont('Helvetica', 9)
    for k in range(10):
        y = h - 318 - 11 * k
        if k:
            c.drawString(50, y, f'[{k}] Lamp note number {k}.')
        c.drawString(220, y, 'Ropes hang by the door.')
        c.drawString(390, y, 'Bells ring the hours.')
    c.showPage()
    c.save()


def draw_panel_page(path):
    """A table on a tinted panel of its own (a filled rectangle with stripes its full width),
    its notes set in two columns at the panel's foot."""
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    x0, x1, top, bottom = 60, 540, h - 200, h - 420
    c.setFillColorRGB(0.97, 0.95, 0.9)
    c.rect(x0, bottom, x1 - x0, top - bottom, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(70, top - 20, 'Signal Lamp Table')
    c.setFont('Helvetica-Oblique', 9)
    for x, t in ((70, 'Lamp'), (250, 'Reach'), (420, 'Cost')):
        c.drawString(x, top - 36, t)
    for k in range(5):
        y = top - 50 - 11 * k
        if k % 2 == 0:
            c.setLineWidth(8)
            c.setStrokeColorRGB(0.85, 0.9, 0.95)
            c.line(x0, y + 3, x1, y + 3)
        c.setFont('Helvetica', 9)
        c.drawString(70, y, f'Signal lamp number {k + 1}')
        c.drawString(250, y, f'{k + 2} miles')
        c.drawString(420, y, f'${10 * (k + 1)}')
    c.setFont('Helvetica-Bold', 9)
    c.drawString(70, top - 120, 'Notes')
    c.setFont('Helvetica', 9)
    left = ['[1] Seen only on a clear night, and then', 'only from the cliffs above the harbour.']
    right = ['[2] Needs a keeper to work the shutter', 'all night, in fog as well as in storms.']
    for k, (a, b) in enumerate(zip(left, right)):
        c.drawString(70, top - 132 - 11 * k, a)
        c.drawString(310, top - 132 - 11 * k, b)
    c.showPage()
    c.save()


def draw_box_page(path):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    x0, x1, top, bottom = 60, 540, h - 120, h - 330
    c.setLineWidth(1)
    c.setStrokeColorRGB(0, 0.47, 0.7)
    c.rect(x0, bottom, x1 - x0, top - bottom, stroke=1, fill=0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(w / 2, top - 22, 'Storm Shutters')
    c.setFont('Helvetica', 9)
    c.drawString(x0 + 14, top - 40, 'The following fittings are kept on every tower of the coast, and are checked each month by')
    c.drawString(x0 + 14, top - 51, 'the inspector when the supply boat comes in:')
    for k in range(9):
        c.drawString(x0 + 14, top - 70 - 11 * k, 'A shutter on each window pane.')
        c.drawString(310, top - 70 - 11 * k, 'A bar to hold the door shut.')
    c.showPage()
    c.save()


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class TablesAcrossThePageTest(unittest.TestCase):
    def layout(self, draw, *extra):
        with tempfile.TemporaryDirectory() as d:
            pdf, out = os.path.join(d, 'page.pdf'), os.path.join(d, 'layout.json')
            draw(pdf)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1',
                                '--out', out, '--boxes', *extra], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding='utf-8') as f:
                return json.load(f)

    def test_the_gutters_are_found_round_a_table_across_the_page(self):
        doc = self.layout(draw_table_page)
        self.assertEqual(len(doc['gutters']['1']), 2)
        lines = [(l['column'], l['text']) for l in doc['lines']]
        rows = [c for c, t in lines if 'yards' in t]
        self.assertEqual(rows, ['full'] * 5)
        self.assertEqual({c for c, t in lines if t.startswith(('Keepers', 'Gulls', 'Fog', 'Ropes', 'Bells', 'Boats'))},
                         {'left', 'middle', 'right'})

    def test_its_notes_are_read_in_their_own_columns_between_the_table_and_the_text_below(self):
        doc = self.layout(draw_table_page)
        texts = [l['text'] for l in doc['lines']]
        first = texts.index('Notes')
        self.assertEqual(texts[first + 1:first + 11], [
            '[1] Smokes badly when the wick is left long, so the', 'keepers trim it every hour of the night or else',
            'the glass goes black.', '[2] Needs a second keeper on stormy nights, to hold', 'the shutter open against the wind.',
            '[3] Seen from the far side of the bay on a clear', 'night, and from the cliffs above the town when',
            'the fog is thin.', '[4] Burns driftwood as well as oil, but the smoke', 'drifts over the town and the harbour.'])
        self.assertLess(max(i for i, t in enumerate(texts) if ' of the ' in t and 'yards' in t), first)
        self.assertGreater(min(i for i, t in enumerate(texts) if t.startswith('Ropes')), first + 10)

    def test_a_notes_heading_level_with_the_next_columns_text_is_read_in_its_column(self):
        doc = self.layout(draw_notes_in_columns_page)
        lines = [(l['column'], l['text']) for l in doc['lines']]
        self.assertEqual([c for c, t in lines if 'yards' in t], ['full'] * 5)
        at = lines.index(('left', 'Notes'))
        self.assertEqual(lines[at + 1:at + 4], [('left', '[1] Lamp note number 1.'), ('left', '[2] Lamp note number 2.'),
                                                ('left', '[3] Lamp note number 3.')])
        self.assertEqual({c for c, t in lines if t.startswith(('Ropes', 'Bells'))}, {'middle', 'right'})

    def test_notes_in_two_columns_on_a_tinted_panel_are_read_in_their_columns(self):
        doc = self.layout(draw_panel_page)
        boxed = [l['text'] for l in doc['lines'] if l.get('box')]
        self.assertTrue(all(any(t.startswith(f'Signal lamp number {k}') and 'miles' in t for t in boxed) for k in range(1, 6)))
        at = boxed.index('Notes')
        self.assertEqual(boxed[at + 1:], ['[1] Seen only on a clear night, and then', 'only from the cliffs above the harbour.',
                                          '[2] Needs a keeper to work the shutter', 'all night, in fog as well as in storms.'])

    def test_a_box_with_a_lead_in_across_it_is_read_in_its_columns(self):
        doc = self.layout(draw_box_page)
        boxed = [(l['column'], l['text']) for l in doc['lines'] if l.get('box')]
        self.assertIn(('left', 'A shutter on each window pane.'), boxed)
        self.assertIn(('right', 'A bar to hold the door shut.'), boxed)
        self.assertFalse(any('pane. A bar' in t for _, t in boxed))


if __name__ == '__main__':
    unittest.main()
