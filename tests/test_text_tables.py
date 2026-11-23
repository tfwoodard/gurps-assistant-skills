"""Tests for the tables a book sets in its text without rules (entry_text.with_text_tables): a
bold-italic header line, then rows. Every table here is invented.

Run: python -m unittest discover tests
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts'))
import entry_text  # noqa: E402

SIZE = 9.5


def line(y, cells, bold_italic=False, column='left', page=10):
    """A line whose words are given with their left edges: [(x0, 'text'), ...]. A word is half
    its type size wide per letter."""
    words = []
    for x, text in cells:
        for w in text.split(' '):
            words.append([w, x, x + 0.5 * SIZE * len(w)])
            x += 0.5 * SIZE * (len(w) + 1)
    text = ' '.join(w[0] for w in words)
    return {'page': page, 'column': column, 'baseline': y, 'top': y - SIZE, 'x0': words[0][1], 'x1': words[-1][2],
            'text': text, 'size': SIZE, 'bold': bold_italic, 'italic': bold_italic, 'font': 'Test',
            'spans': [{'text': text, 'size': SIZE, 'bold': bold_italic, 'italic': bold_italic}],
            'words': words, 'furniture': False}


def right(x1, text):
    """(x0, text) for text set to end at x1."""
    return (x1 - 0.5 * SIZE * len(text), text)


def table(rows, header, y=200.0):
    return [line(y, header, True)] + [line(y + 11 * (i + 1), r) for i, r in enumerate(rows)]


class TextTableTest(unittest.TestCase):
    def read(self, lines):
        report = {'errors': [], 'questions': []}
        out = entry_text.with_text_tables(lines, report, 'advantages/tide-sense')
        return out, report

    def test_two_columns_the_second_set_to_end_together(self):
        body = [line(170.0, [(60, 'The cost depends on the reach:')])]
        t = table([[(70, '1 mile'), right(190, '2 points')],
                   [(70, '10 miles'), right(190, '5 points')],
                   [(70, '100 miles'), right(190, '10 points')]],
                  [(70, 'Reach'), (160, 'Cost')])
        after = [line(250.0, [(72, 'Further reach costs more.')])]
        out, report = self.read(body + t + after)
        self.assertEqual(report['errors'], [])
        self.assertEqual([bool(l.get('block')) for l in out], [False, True, False])
        block = out[1]['block']
        self.assertEqual((block['type'], block['columns']), ('table', ['Reach', 'Cost']))
        self.assertEqual(block['rows'], [['1 mile', '2 points'], ['10 miles', '5 points'], ['100 miles', '10 points']])
        self.assertEqual(block['data'][2], {'reach': '100 miles', 'cost': '10 points'})
        self.assertEqual(out[1]['text'].split()[:2], ['Reach', 'Cost'])                # its words stay countable
        self.assertEqual(report['tables'], [{'entry': 'advantages/tide-sense', 'page': 10, 'header': 'Reach Cost',
                                             'columns': ['Reach', 'Cost'], 'rows': block['rows'], 'failures': []}])

    def test_a_header_of_several_words_goes_to_the_column_each_stands_over(self):
        t = table([[(90, '2'), (120, '4'), right(200, '-10%')],
                   [(90, '5'), (120, '10'), right(200, '-20%')]],
                  [(80, 'Fog'), (112, 'Tide Rise'), (168, 'Modifier')])
        out, report = self.read(t)
        self.assertEqual(out[0]['block']['columns'], ['Fog', 'Tide Rise', 'Modifier'])
        self.assertEqual(out[0]['block']['rows'], [['2', '4', '-10%'], ['5', '10', '-20%']])
        self.assertEqual(out[0]['block']['data'][0], {'fog': 2, 'tide_rise': 4, 'modifier': '-10%'})

    def test_figures_set_to_end_together_before_their_units_line_up(self):
        t = table([[(82, 'None'), right(190, '-10')],
                   [(82, '8 seconds'), right(190, '-2')],
                   [(82 - 0.5 * SIZE, '15 seconds'), right(190, '-1')],
                   [(82 - 0.5 * SIZE, '30 seconds'), right(190, '0')]],
                  [(70, 'Time'), (160, 'Roll')])
        out, report = self.read(t)
        self.assertEqual(report['errors'], [])
        self.assertEqual(out[0]['block']['rows'][2], ['15 seconds', '-1'])

    def test_a_header_set_over_several_lines_names_each_column_downwards(self):
        lines = [line(189.0, [(70, 'Self-Control'), (150, 'Cost of')], True),
                 line(200.0, [(78, 'Number'), (152, 'Living')], True),
                 line(211.0, [(150, 'Increase')], True),
                 line(222.0, [(95, '6'), right(190, '80%')]),
                 line(233.0, [(95, '9'), right(190, '40%')]),
                 line(244.0, [(95 - 0.5 * SIZE, '12'), right(190, '20%')])]
        out, report = self.read(lines)
        self.assertEqual(report['errors'], [])
        self.assertEqual(out[0]['block']['columns'], ['Self-Control Number', 'Cost of Living Increase'])
        self.assertEqual(out[0]['block']['rows'], [['6', '80%'], ['9', '40%'], ['12', '20%']])
        self.assertEqual(report['tables'][0]['header'], 'Self-Control Cost of / Number Living / Increase')

    def test_a_long_name_over_a_column_of_short_figures_is_its_name_not_a_banner(self):
        lines = [line(200.0, [(60, 'Self-Control Number'), (175, 'Bonus')], True),
                 line(211.0, [(100, '6'), right(200, '+4')]),
                 line(222.0, [(100, '9'), right(200, '+3')])]
        out, report = self.read(lines)
        self.assertEqual(out[0]['block']['columns'], ['Self-Control Number', 'Bonus'])
        self.assertNotIn('banners', out[0]['block'])

    def test_a_phrase_over_several_columns_is_a_banner_over_them(self):
        lines = [line(200.0, [(60, 'Rarity of'), (135, 'Wounding Tide Multiplier')], True),
                 line(211.0, [(60, 'Fog'), (140, 'x2'), (185, 'x3'), (230, 'x4')], True),
                 line(222.0, [(60, 'Rare'), (140, '-10'), (185, '-15'), (230, '-20')]),
                 line(233.0, [(60, 'Common'), (140, '-30'), (185, '-45'), (230, '-60')])]
        out, report = self.read(lines)
        self.assertEqual(report['errors'], [])
        block = out[0]['block']
        self.assertEqual(block['columns'], ['Rarity of Fog', 'x2', 'x3', 'x4'])
        self.assertEqual(block['banners'], [{'text': 'Wounding Tide Multiplier', 'columns': [2, 4]}])
        self.assertEqual(block['data'][0], {'rarity_of_fog': 'Rare', 'x2': -10, 'x3': -15, 'x4': -20})

    def test_a_banner_runs_on_over_unnamed_columns_which_take_their_names_from_it(self):
        lines = [line(200.0, [(60, 'Level'), (110, 'Aging [Frequency of Rolls]')], True),
                 line(211.0, [(60, '0'), (110, '50 years'), (200, '70 years'), (290, '90 years')]),
                 line(222.0, [(60, '1'), (110, '25 years'), (200, '35 years'), (290, '45 years')])]
        out, report = self.read(lines)
        self.assertEqual(report['errors'], [])
        block = out[0]['block']
        self.assertEqual((block['columns'], block['banners']),
                         (['Level', '', '', ''], [{'text': 'Aging [Frequency of Rolls]', 'columns': [2, 4]}]))
        self.assertEqual(list(block['data'][0]), ['level', 'aging_frequency_of_rolls_1', 'aging_frequency_of_rolls_2', 'aging_frequency_of_rolls_3'])

    def test_a_header_line_with_a_sign_from_another_font_is_still_a_header(self):
        l = line(200.0, [(60, 'Fog'), (130, 'x2')], True)
        l['spans'] = [{'text': 'Fog', 'size': SIZE, 'bold': True, 'italic': True},
                      {'text': '×', 'size': SIZE, 'bold': False, 'italic': False},
                      {'text': '2', 'size': SIZE, 'bold': True, 'italic': True}]
        self.assertTrue(entry_text.is_table_header(l))
        self.assertFalse(entry_text.is_table_header(line(200.0, [(60, 'Fog 2')])))

    def test_a_cell_that_lines_up_with_nothing_fails_the_table_and_leaves_its_lines(self):
        t = table([[(70, '1 mile'), right(190, '2 points')],
                   [(70, '10 miles'), right(190, '5 points')],
                   [(70, '100 miles'), right(171, '10 points')]],             # out of line
                  [(70, 'Reach'), (160, 'Cost')])
        out, report = self.read(t)
        self.assertEqual(len(out), 4)
        self.assertFalse(any(l.get('block') for l in out))
        self.assertEqual(len(report['errors']), 1)
        self.assertIn("advantages/tide-sense (p10): the table under 'Reach Cost' was not read", report['errors'][0])
        self.assertIn("in column 2 (Cost), '10 points' does not line up with the other cells", report['errors'][0])
        self.assertEqual(len(report['tables'][0]['failures']), 1)

    def test_a_row_with_an_empty_cell_and_rows_with_no_blank_between_columns_fail(self):
        t = table([[(70, '1 mile'), right(190, '2 points')],
                   [(70, '10 miles')],
                   [(70, '100 miles'), right(190, '10 points')]],
                  [(70, 'Reach'), (160, 'Cost')])
        _, report = self.read(t)
        self.assertIn("row 2 has nothing in column 2: '10 miles'", report['errors'][0])
        t = table([[(70, 'one two three four')], [(70, 'five six seven eight')]], [(70, 'Reach'), (160, 'Cost')])
        _, report = self.read(t)
        self.assertIn('its rows leave no blank column between them', report['errors'][0])

    def test_a_header_with_no_words_over_a_column_fails(self):
        t = table([[(70, '1 mile'), right(190, '2 points')], [(70, '10 miles'), right(190, '5 points')]],
                  [(70, 'Reach and cost')])
        _, report = self.read(t)
        self.assertIn('its header has no words over column 2', report['errors'][0])

    def test_the_table_ends_at_a_wider_gap_a_heading_or_the_columns_end(self):
        t = table([[(70, '1 mile'), right(190, '2 points')], [(70, '10 miles'), right(190, '5 points')]],
                  [(70, 'Reach'), (160, 'Cost')])
        after = [line(t[-1]['baseline'] + 17, [(72, 'Add 1 point       for fog.')]),
                 line(t[-1]['baseline'] + 28, [(60, 'And so on.')])]
        out, report = self.read(t + after)
        self.assertEqual([bool(l.get('block')) for l in out], [True, False, False])
        self.assertEqual(len(out[0]['block']['rows']), 2)

    def test_a_bold_italic_line_with_fewer_than_two_rows_under_it_is_text(self):
        lines = [line(200.0, [(70, 'A Word of Warning')], True), line(211.0, [(60, 'The tide waits for nobody.')]),
                 line(240.0, [(60, 'Nor does the fog.')])]
        out, report = self.read(lines)
        self.assertEqual(len(out), 3)
        self.assertEqual(report.get('tables', []), [])


if __name__ == '__main__':
    unittest.main()
