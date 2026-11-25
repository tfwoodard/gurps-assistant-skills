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


class KeyedListTest(unittest.TestCase):
    def test_results_keyed_by_a_roll_become_one_list_with_their_keys(self):
        lines = [line(190.0, [(60, 'Roll 3d on the table below.')]),
                 line(201.0, [(60, '3 – The lamp goes out.')]),
                 line(212.0, [(60, '4-5 – The lamp flickers, and the')]),
                 line(223.0, [(72, 'keeper sees shapes.')]),
                 line(234.0, [(60, '6+ – Nothing happens.')]),
                 line(250.0, [(60, 'Then roll again.')])]
        report = {'errors': [], 'questions': []}
        out = entry_text.with_keyed_lists(lines, report, 'rules/lamps')
        self.assertEqual([bool(l.get('block')) for l in out], [False, True, False])
        block = out[1]['block']
        self.assertEqual(block['keys'], ['3', '4-5', '6+'])
        self.assertEqual(block['items'], ['3 – The lamp goes out.', '4-5 – The lamp flickers, and the keeper sees shapes.',
                                          '6+ – Nothing happens.'])
        self.assertEqual(report['keyed_lists'], [{'entry': 'rules/lamps', 'page': 10, 'items': 3, 'keys': ['3', '4-5', '6+']}])

    def test_fewer_than_three_keyed_lines_are_text(self):
        lines = [line(201.0, [(60, '3 – The lamp goes out.')]), line(212.0, [(60, '4 – It is lit again.')])]
        report = {'errors': [], 'questions': []}
        self.assertEqual(entry_text.with_keyed_lists(lines, report, 'rules/lamps'), lines)


class KeyedListKeysAndTurnsTest(unittest.TestCase):
    def test_keys_of_several_numbers_and_an_item_running_on_over_a_column_turn(self):
        def item(y, x, text, para, column='left'):
            l = line(y, [(x, text)], column=column)
            l['para'] = para
            return l
        lines = [item(201.0, 60, '3 – The lamp goes out.', True),
                 item(212.0, 60, '4, 5 – The lamp gutters and', True),
                 item(80.0, 240, 'smokes.', False, 'right'),
                 item(91.0, 240, '6 – Nothing happens.', True, 'right')]
        report = {'errors': [], 'questions': []}
        out = entry_text.with_keyed_lists(lines, report, 'rules/lamps')
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['block']['keys'], ['3', '4, 5', '6'])
        self.assertEqual(out[0]['block']['items'][1], '4, 5 – The lamp gutters and smokes.')


class KeyedListAcrossColumnsTest(unittest.TestCase):
    def test_a_keyed_list_set_as_paragraphs_carries_on_into_the_next_column(self):
        def item(y, x, text, para):
            l = line(y, [(x, text)])
            l['para'] = para
            return l
        lines = [item(201.0, 72, '1 – A match: lights a', True), item(212.0, 60, 'candle.', False),
                 item(223.0, 72, '2 – A torch: lights', True), item(234.0, 60, 'paper.', False)]
        right = [item(80.0, 252, '3 – A forge: melts', True), item(91.0, 240, 'iron.', False),
                 item(102.0, 240, 'Cost to keep it up is the same.', True)]
        for l in right:
            l['column'] = 'right'
        report = {'errors': [], 'questions': []}
        out = entry_text.with_keyed_lists(lines + right, report, 'spells/kindle')
        self.assertEqual([bool(l.get('block')) for l in out], [True, False])
        self.assertEqual(out[0]['block']['items'], ['1 – A match: lights a candle.', '2 – A torch: lights paper.',
                                                    '3 – A forge: melts iron.'])


class FlushRightColumnTest(unittest.TestCase):
    """A two-column table whose second column is set flush right, one long chore reaching past
    where a long time begins, so no blank runs down the table."""

    def lines(self):
        return table([[(60, 'Bake a loaf of bread'), right(300, '1 hr.')],
                      [(60, 'Darn a sock'), right(300, '10 min.')],
                      [(60, 'Sweep the whole of the long front hall'), right(300, '2 min.')],
                      [(60, 'Air a room'), right(300, '5 min. per window (more if')],
                      [right(300, 'it is windy)')],
                      [(60, 'Find a lost thimble in a sewing basket,')],
                      [(68, 'if it is there'), right(300, '2d seconds')]],
                     [(60, 'Chore'), right(300, 'Time')])

    def test_each_rows_last_cell_is_read_after_its_wide_gap(self):
        report = {'errors': [], 'questions': []}
        out = entry_text.with_text_tables(self.lines(), report, 'rules/chores')
        self.assertEqual(report['errors'], [])
        self.assertEqual(len(out), 1)
        block = out[0]['block']
        self.assertEqual(block['columns'], ['Chore', 'Time'])
        self.assertEqual(block['rows'], [['Bake a loaf of bread', '1 hr.'], ['Darn a sock', '10 min.'],
                                         ['Sweep the whole of the long front hall', '2 min.'],
                                         ['Air a room', '5 min. per window (more if it is windy)'],
                                         ['Find a lost thimble in a sewing basket, if it is there', '2d seconds']])

    def test_a_line_that_runs_full_width_from_the_left_is_prose_and_no_such_table(self):
        lines = self.lines()
        lines[3] = line(lines[3]['baseline'], [(60, 'Sweep the whole of the long front hall and the stairs')])
        lines[3]['words'][-1][2] = 300.0                     # justified out to the right edge
        columns, _, _, failures = entry_text.read_text_table(lines[:1], lines[1:])
        self.assertEqual(columns, [])
        self.assertIn('it reads as one column', failures[0])


class TableNoteAndSlashTest(unittest.TestCase):
    def test_a_note_under_the_rows_ends_them_and_stays_text(self):
        t = table([[(70, 'Dusk'), (130, '2*')], [(70, 'Night'), (130, '4')], [(70, 'Fog'), (130, '6')]],
                  [(70, 'Hour'), (130, 'Lamps')])
        notes = [line(t[-1]['baseline'] + 11, [(56, '* Only where the harbour wall is')]),
                 line(t[-1]['baseline'] + 22, [(56, 'lit, and never on a feast day.')])]
        report = {'errors': [], 'questions': []}
        out = entry_text.with_text_tables(t + notes, report, 'rules/lamps')
        self.assertEqual(report['errors'], [])
        self.assertEqual(report.get('not_tables'), None)
        self.assertEqual([bool(l.get('block')) for l in out], [True, False, False])
        self.assertEqual(out[0]['block']['rows'], [['Dusk', '2*'], ['Night', '4'], ['Fog', '6']])
        self.assertEqual(out[1]['text'], '* Only where the harbour wall is')

    def test_a_cell_carried_on_after_a_slash_joins_without_a_space(self):
        t = table([[(70, '3'), (100, 'Lamp Oil'), right(260, '0.2')],
                   [(70, '4'), (100, 'Whale Oil/')],
                   [(110, 'Tallow Blend'), right(260, '0.4')],
                   [(70, '5'), (100, 'Oil w/ wick'), right(260, '0.6')]],
                  [(70, 'TL'), (100, 'Fuel'), right(260, 'Burn')])
        report = {'errors': [], 'questions': []}
        out = entry_text.with_text_tables(t, report, 'rules/lamps')
        self.assertEqual(report['errors'], [])
        self.assertEqual(out[0]['block']['rows'], [['3', 'Lamp Oil', '0.2'], ['4', 'Whale Oil/Tallow Blend', '0.4'],
                                                   ['5', 'Oil w/ wick', '0.6']])


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

    def test_names_set_close_together_each_over_its_columns_cells_are_names_not_a_banner(self):
        lines = [line(200.0, [(60, 'Rank'), (60 + 0.5 * SIZE * 5 + 2, 'Examples'), (180, 'Upkeep')], True),
                 line(211.0, [(60, '3'), (60 + 0.5 * SIZE * 5 + 2, 'Lamp warden, keeper'), right(220, '$900')]),
                 line(222.0, [(60, '2'), (60 + 0.5 * SIZE * 5 + 2, 'Wick trimmer'), right(220, '$30')])]
        out, report = self.read(lines)
        self.assertEqual(report['errors'], [])
        block = out[0]['block']
        self.assertEqual(block['columns'], ['Rank', 'Examples', 'Upkeep'])
        self.assertNotIn('banners', block)

    def test_figures_lined_up_on_their_decimal_point_line_up(self):
        def at_point(x, text):                  # a figure whose whole number ends at x
            whole = text.split('.')[0]
            return (x - 0.5 * SIZE * len(whole), text)
        t = table([[(60, '1'), at_point(150, '0.2')], [(60, '2'), at_point(150, '0.8')],
                   [(60, '5'), at_point(150, '5')], [(60, '9'), at_point(150, '16')], [(60, '10'), at_point(150, '20')]],
                  [(60, 'Reach'), (130, 'Oil')])
        out, report = self.read(t)
        self.assertEqual(report['errors'], [])
        self.assertEqual([r[1] for r in out[0]['block']['rows']], ['0.2', '0.8', '5', '16', '20'])

    def test_names_centred_on_their_columns_under_a_banner_centred_on_them(self):
        lines = [line(189.0, [(60, 'Hour'), (116.25, 'Oil Burned (pints)')], True),
                 line(200.0, [(98, 'Calm (0)'), (140, 'Wind (1)'), (182, 'Gale (2)')], True),
                 line(211.0, [(60, '1'), (110, '1'), (152, '2'), (194, '4')]),
                 line(222.0, [(60, '2'), (110, '2'), (152, '4'), (194, '8')])]
        out, report = self.read(lines)
        self.assertEqual(report['errors'], [])
        block = out[0]['block']
        self.assertEqual(block['columns'], ['Hour', 'Calm (0)', 'Wind (1)', 'Gale (2)'])
        self.assertEqual(block['banners'], [{'text': 'Oil Burned (pints)', 'columns': [2, 4]}])

    def test_a_banner_over_one_columns_cells_is_a_banner_when_it_overhangs_its_name_below(self):
        lines = [line(189.0, [(60, 'Rank'), (116.5, 'Weight by Build')], True),
                 line(200.0, [(100, 'Thin'), (139, 'Plump'), (190, 'Fat')], True),
                 line(211.0, [(60, '1'), (100, '40'), (145, '60'), (190, '80')]),
                 line(222.0, [(60, '2'), (100, '50'), (145, '75'), (190, '100')])]
        out, report = self.read(lines)
        self.assertEqual(report['errors'], [])
        block = out[0]['block']
        self.assertEqual(block['columns'], ['Rank', 'Thin', 'Plump', 'Fat'])
        self.assertEqual(block['banners'], [{'text': 'Weight by Build', 'columns': [2, 4]}])

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

    def test_a_header_set_larger_than_its_rows_is_a_header_though_marked_a_heading(self):
        h = line(200.0, [(60, 'Lamp'), (150, 'Cost'), (200, 'Page')], True)
        h['heading'] = 5
        self.assertTrue(entry_text.is_table_header(h))
        title = line(200.0, [(60, 'Lamps and Lanterns')], True)
        title['heading'] = 5
        self.assertFalse(entry_text.is_table_header(title))

    def test_a_table_set_as_two_side_by_side_is_read_one_after_the_other(self):
        header = [line(200.0, [(60, 'Skill'), (110, 'Chance'), (200, 'Skill'), (250, 'Chance')], True)]
        rows = [line(211.0, [(60, '3'), (110, '1%'), (200, '5'), (250, '5%')]),
                line(222.0, [(60, '4'), (110, '2%'), (200, '6'), (250, '9%')])]
        report = {'errors': [], 'questions': []}
        block = entry_text.table_block(header, rows, report, 'rules/odds', 'The Odds', 2)
        self.assertEqual((block['title'], block['columns']), ('The Odds', ['Skill', 'Chance']))
        self.assertEqual(block['rows'], [['3', '1%'], ['4', '2%'], ['5', '5%'], ['6', '9%']])
        self.assertEqual(report['folded_keys'],
                         [{'region': 'Skill Chance Skill Chance', 'entry': 'rules/odds', 'cells': ['Skill', 'Chance']}])
        self.assertEqual(report['tables'][0]['folded'], 2)
        report = {'errors': [], 'questions': []}
        header = [line(200.0, [(60, 'Skill'), (110, 'Chance'), (200, 'Rank'), (250, 'Chance')], True)]
        self.assertIsNone(entry_text.table_block(header, rows, report, 'rules/odds', '', 2))
        self.assertIn('does not fold into 2 parts with the same column names', report['errors'][0])

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

    def test_a_row_with_an_empty_cell_fails_and_lines_with_no_blank_between_columns_are_text(self):
        t = table([[(70, '1 mile'), right(190, '2 points')],
                   [(70, '10 miles')],
                   [(70, '100 miles'), right(190, '10 points')]],
                  [(70, 'Reach'), (160, 'Cost')])
        _, report = self.read(t)
        self.assertIn("row 2 has nothing in column 2: '10 miles'", report['errors'][0])
        t = table([[(70, 'one two three four')], [(70, 'five six seven eight')]], [(70, 'Reach'), (160, 'Cost')])
        out, report = self.read(t)
        self.assertEqual(report['errors'], [])
        self.assertEqual(len(out), 3)
        self.assertEqual(report['not_tables'], [{'entry': 'advantages/tide-sense', 'page': 10, 'text': 'Reach Cost',
                                                 'why': 'the lines under it read as one column'}])

    def test_a_cell_carried_onto_a_second_line_joins_its_row(self):
        t = table([[(70, 'cut'), (130, 'cutting')],
                   [(70, 'spec.'), (130, 'special – see')],
                   [(136, 'the notes')],
                   [(70, 'tox'), (130, 'toxic')]],
                  [(70, 'Abbr.'), (130, 'Damage Type')])
        out, report = self.read(t)
        self.assertEqual(report['errors'], [])
        self.assertEqual(out[0]['block']['rows'], [['cut', 'cutting'], ['spec.', 'special – see the notes'], ['tox', 'toxic']])

    def test_a_name_set_over_two_lines_with_its_cells_on_the_second_is_one_row(self):
        t = table([[(70, 'Ladder'), right(190, '1 rung')],
                   [(70, 'Rope-down')],
                   [(70, '(no gloves)'), right(190, '2 feet')],
                   [(70, 'Wall'), right(190, '1 foot')]],
                  [(70, 'Climb'), (160, 'Pace')])
        out, report = self.read(t)
        self.assertEqual(report['errors'], [])
        self.assertEqual(out[0]['block']['rows'], [['Ladder', '1 rung'], ['Rope-down (no gloves)', '2 feet'], ['Wall', '1 foot']])

    def test_a_name_set_over_three_lines_hanging_under_its_first_is_one_row(self):
        t = table([[(70, 'Pebble'), right(190, '1 oz')],
                   [(70, 'Basket of')],
                   [(76, 'river stones')],
                   [(76, 'or shells'), right(190, '20 lbs')],
                   [(70, 'Boulder'), right(190, '1 ton')]],
                  [(70, 'Load'), (160, 'Weight')])
        out, report = self.read(t)
        self.assertEqual(report['errors'], [])
        self.assertEqual(out[0]['block']['rows'], [['Pebble', '1 oz'], ['Basket of river stones or shells', '20 lbs'],
                                                   ['Boulder', '1 ton']])

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
