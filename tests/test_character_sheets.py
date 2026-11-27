"""Tests for character_sheets.py and the sheet pages of pdf_layout.py: a filled-in character sheet
read by its words' places and fonts. The character, its values and the page drawn here are invented;
the form's labels stand where the reader expects them.

Run: python -m unittest discover tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    HAVE_LIBS = True
except ImportError:  # pragma: no cover
    HAVE_LIBS = False

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts')
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)
import character_sheets as cs  # noqa: E402
import convert_traits  # noqa: E402

HAND = 'FletchersHand'


def word(text, x0, top, font='NewAster-Bold', size=9.5):
    return {'page': 50, 'text': text, 'x0': x0, 'x1': x0 + 0.5 * size * len(text), 'top': top, 'bottom': top + size,
            'size': size, 'font': font}


def hand(text, x0, top, size=9.5, font=HAND):
    """Written words, one per space, from x0."""
    out = []
    for t in text.split():
        out.append(word(t, x0, top, font, size))
        x0 += 0.5 * size * (len(t) + 1)
    return out


def sheet_words(skills_on_left=False):
    """A form with its labels in place and an invented lamplighter written in."""
    ws = [word(t, x, y) for t, x, y in cs.ANCHORS]
    ws += [word('TL:', 389, 153), word('Cultural', 389, 164), word('DR', 349, 153), word('PARRY', 341, 193),
           word('BLOCK', 340, 245), word('Reaction', 448, 208), word('Status', 388, 234),
           word('[', 135, 92, 'NewAster', 20), word(']', 158, 92, 'NewAster', 20)]
    ws += [word('DISADVANTAGES', 392, 280), word('ADVANTAGES', 137, 349), word('SKILLS', 443, 480),
           word('Relative', 497, 495)]
    ws += hand('Wicklow Fenn', 238, 21, 14) + hand('125', 553, 22, 11) + hand('Soot-streaked and cheerful', 262, 56)
    ws += hand('11', 107, 99, 13) + hand('10', 140, 99, 13) + hand('11', 228, 98, 13) + hand('0', 300, 98, 13)
    ws += hand('Lampspeech (Native)', 336, 96, 10) + hand('0', 574, 96, 10)
    ws += hand('3', 406, 152, 10) + hand('0', 574, 152, 10) + hand('Marsh Towns', 406, 178, 10) + hand('0', 574, 178, 10)
    ws += hand('2', 345, 170, 16) + hand('9', 346, 210, 16) + hand('(Torch)', 335, 226)
    ws += hand('+1 from other keepers,', 422, 235, 10) + hand('+2 at dusk', 389, 248, 10)
    ws += hand('Night Vision 2', 69, 363) + hand('2', 305, 363)
    ws += hand('Lamp Sense (Oil; Smoke', 69, 376) + hand('Only, -20%)', 79, 389) + hand('8', 305, 389)
    ws += hand('Fear of Deep Water', 334, 293, 9) + hand('-10', 566, 293, 9)
    ws += hand('Wick Trimming/TL3', 333, 507, 9) + hand('(Oil Lamps)', 343, 518, 9) + hand('12', 473, 518, 9) + \
        hand('IQ+1', 514, 518, 9) + hand('4', 573, 518, 9)
    ws += hand('* +1 from Lamp Sense.', 333, 700, 9)
    ws += [word('ICONIC LAMPLIGHTERS 50', 240, 757, 'NewAster-Black', 12)]
    ws[-1]['furniture'] = True
    return ws


class ReadSheetTest(unittest.TestCase):
    def setUp(self):
        self.sheet, self.labels, self.failures = cs.read_sheet(sheet_words())

    def test_the_header_attributes_and_boxes_are_read_from_their_places(self):
        self.assertEqual(self.failures, [])
        s = self.sheet
        self.assertEqual((s['name'], s['point_total'], s['appearance']), ('Wicklow Fenn', '125', 'Soot-streaked and cheerful'))
        self.assertEqual(s['attributes'], {'ST': {'value': '11', 'points': '10'}, 'HP': {'value': '11', 'points': '0'}})
        self.assertEqual((s['tl'], s['tl_points'], s['dr'], s['parry']), ('3', '0', '2', '9 (Torch)'))
        self.assertEqual(s['languages'], [{'name': 'Lampspeech (Native)', 'points': '0'}])
        self.assertEqual(s['cultural_familiarities'], [{'name': 'Marsh Towns', 'points': '0'}])
        self.assertEqual(s['reaction_modifiers'], [{'label': 'Status', 'text': '+1 from other keepers, +2 at dusk'}])

    def test_list_rows_carry_on_over_lines_set_in_and_notes_are_kept_apart(self):
        s = self.sheet
        self.assertEqual(s['advantages'], [{'name': 'Night Vision 2', 'points': '2'},
                                           {'name': 'Lamp Sense (Oil; Smoke Only, -20%)', 'points': '8'}])
        self.assertEqual(s['disadvantages'], [{'name': 'Fear of Deep Water', 'points': '-10'}])
        self.assertEqual(s['skills'], [{'name': 'Wick Trimming/TL3 (Oil Lamps)', 'level': '12', 'relative_level': 'IQ+1',
                                        'points': '4'}])
        self.assertEqual(s['notes'], ['* +1 from Lamp Sense.'])
        self.assertIn('ADVANTAGES', [w['text'] for w in self.labels])
        self.assertNotIn('ICONIC LAMPLIGHTERS 50', [w['text'] for w in self.labels])   # the running foot

    def test_italic_handwriting_keeps_its_emphasis(self):
        ws = sheet_words()
        ws += hand('Lamps', 69, 402) + [word('(', 100, 402, HAND)] + hand('lit', 103, 402, font=HAND + 'Italic') + \
            hand(')', 112, 402) + hand('1', 305, 402)
        sheet, _, failures = cs.read_sheet(ws)
        self.assertEqual(failures, [])
        self.assertEqual(sheet['advantages'][-1], {'name': 'Lamps (*lit*)', 'points': '1'})

    def test_a_written_word_in_no_field_or_a_missing_label_refuses_the_sheet(self):
        _, _, failures = cs.read_sheet(sheet_words() + hand('stray', 20, 400))
        self.assertTrue(any("'stray'" in f for f in failures), failures)
        _, _, failures = cs.read_sheet([w for w in sheet_words() if w['text'] != 'ENCUMBRANCE'])
        self.assertTrue(any("'ENCUMBRANCE'" in f for f in failures), failures)


class PointsSummaryTest(unittest.TestCase):
    def test_categories_and_spaced_figures_are_read_into_rows(self):
        def line(top, x, words):
            return {'top': top, 'x0': x, 'words': words}
        lines = [line(628, 86, [['POINTS', 86, 120], ['SUMMARY', 123, 169]]),
                 line(641, 86, [['Attributes/Secondary', 86, 173], ['Characteristics', 176, 237]]),
                 line(654, 86, [['Advantages/Perks/TL/Languages/', 86, 221]]),
                 line(667, 92, [['Cultural', 92, 126], ['Familiarity', 128, 174]]),
                 line(680, 86, [['Other', 86, 110]]),
                 line(641, 242, [['[', 242, 245], ['4', 247, 252], ['5', 252, 257], [']', 266, 270]]),
                 line(667, 242, [['[1', 242, 249], [',', 249, 251], ['2', 251, 256], ['0', 256, 261], ['0', 261, 266],
                                 [']', 266, 270]]),
                 line(680, 242, [['[', 242, 245], [']', 266, 269]])]
        rows, joins, failures = cs.read_points_summary(lines)
        self.assertEqual(failures, [])
        self.assertEqual(rows, [['Attributes/Secondary Characteristics', '45'],
                                ['Advantages/Perks/TL/Languages/Cultural Familiarity', '1,200'], ['Other', '']])
        self.assertEqual(joins, [('[ 4 5 ]', '45'), ('[1 , 2 0 0 ]', '1,200')])


class AttachTest(unittest.TestCase):
    def test_a_sheet_goes_into_the_entry_the_plan_names_and_its_form_is_left_out(self):
        from test_convert_traits import Page
        p = Page()
        p.line('WICKLOW FENN', size=20.0, heading=2, bold=True)
        p.para('Wicklow trims the lamps of the', 'marsh towns.')
        layout = {'lines': p.lines, 'regions': [], 'sheets': [{'page': 50, 'words': sheet_words()}]}
        plan = {'source': 'ML', 'chapter': 'lamplighters', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
                'entries': {'rules/wicklow-fenn': {'category': 'creatures', 'fields': {'kind': 'npc'}}},
                'sheets': [{'page': 50, 'entry': 'creatures/wicklow-fenn'}]}
        entries, report = convert_traits.convert_chapter(layout, plan)
        self.assertEqual(report['errors'], [])
        cat, e = entries[0]
        self.assertEqual((cat, e['fields']['kind'], e['fields']['sheet_page']), ('creatures', 'npc', 50))
        self.assertEqual(e['fields']['sheet']['name'], 'Wicklow Fenn')
        titles = [b.get('title') or b.get('text') for b in e['content'] if b['type'] in ('heading', 'table')]
        self.assertEqual(titles[0], 'Character Sheet')
        self.assertIn('Advantages and Perks', titles)
        self.assertIn("the character sheet's printed form", report['left_out'][-1]['why'])
        # every word of the sheet is counted, and accounted for: its values in the entry, its form left out
        with tempfile.TemporaryDirectory() as d:
            for name, data in (('layout.json', layout), ('plan.json', plan)):
                with open(os.path.join(d, name), 'w', encoding='utf-8') as f:
                    json.dump(data, f)
            out = os.path.join(d, 'out')
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'convert_traits.py'), os.path.join(d, 'layout.json'),
                                '--plan', os.path.join(d, 'plan.json'), '--out', out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'check_coverage.py'), os.path.join(d, 'layout.json'),
                                out], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn('every word of', r.stdout)
        plan['sheets'] = []
        _, report = convert_traits.convert_chapter(json.loads(json.dumps(layout)), plan)
        self.assertIn('sheet page p50 is read into no entry', ' '.join(report['errors']))


@unittest.skipUnless(HAVE_LIBS, 'reportlab is needed to draw the fixture PDF')
class SheetPagesTest(unittest.TestCase):
    def test_a_sheet_page_gives_its_words_with_their_fonts_and_none_of_its_lines(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, 'sheet.pdf')
            c = canvas.Canvas(pdf, pagesize=letter)
            w, h = letter
            c.setFont('Helvetica-Bold', 9.5)
            c.drawString(209, h - 30, 'Name ______________')
            c.setFont('Times-Italic', 14)
            c.drawString(238, h - 30, 'Wicklow')              # written over the printed rule
            c.showPage()
            c.save()
            out = os.path.join(d, 'layout.json')
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'pdf_layout.py'), pdf, '--pages', '1',
                                '--sheet-pages', '1', '--out', out], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding='utf-8') as f:
                doc = json.load(f)
        self.assertEqual(doc['lines'], [])
        got = sorted((x['text'], x['font']) for x in doc['sheets'][0]['words'])
        self.assertEqual(got, [('Name', 'Helvetica-Bold'), ('Wicklow', 'Times-Italic'),
                               ('______________', 'Helvetica-Bold')])


if __name__ == '__main__':
    unittest.main()
