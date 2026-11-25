"""Tests for equipment_tables.take_tables: weapon and armor tables as the books print them (a
title, groups under bold headings, an italic header row, rows, numbered notes). Every table here is
invented.

Run: python -m unittest discover tests
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts'))
import equipment_tables  # noqa: E402
from test_text_tables import SIZE, line  # noqa: E402

COLS = (60, 80, 170, 220, 260)          # TL, item, light, cost, notes


def styled(l, size=None, bold=None, italic=None, heading=None):
    for k, v in (('size', size), ('bold', bold), ('italic', italic)):
        if v is not None:
            l[k] = v
            for s in l['spans']:
                s[k] = v
    if heading:
        l['heading'] = True
    return l


def title(y, text):
    return styled(line(y, [(60, text)]), size=13.0, bold=True, heading=True)


def group(y, text):
    return styled(line(y, [(60, text)]), size=11.0, bold=True)


def header(y, names, cols=COLS):
    return styled(line(y, list(zip(cols, names))), italic=True)


def row(y, cells, cols=COLS):
    return line(y, [(x, c) for x, c in zip(cols, cells) if c])


def lamp_table(y=100.0, light_of_lantern='5 yd'):
    return [title(y, 'Lamp Table'),
            group(y + 16, 'LAMPS (DX-4)'),
            header(y + 28, ['TL', 'Lamp', 'Light', 'Cost', 'Notes']),
            row(y + 39, ['1', 'Oil Lamp', '2 yd', '$10', '[1]']),
            row(y + 50, ['2', 'Glass Lantern', light_of_lantern, '$40', '']),
            row(y + 61, ['', 'or', '1 yd', '', '']),
            group(y + 76, 'TORCHES (DX)'),
            row(y + 88, ['0', 'Pitch Torch', '1 yd', '$2', '[1, 2]']),
            row(y + 99, ['', '', 'or less', '', '']),
            group(y + 114, 'Notes'),
            line(y + 126, [(60, '[1] Smokes indoors.')]),
            line(y + 137, [(60, '[2] Burns for an hour, then')]),
            line(y + 148, [(60, 'must be lit again.')])]


def thrown_table(y=300.0):
    cols = (60, 80, 170, 220)
    return [title(y, 'Thrown Lamp Table'),
            group(y + 16, 'THROWING (DX-3)'),
            header(y + 28, ['TL', 'Lamp', 'Range', 'Notes'], cols),
            row(y + 39, ['1', 'Oil Lamp', '10 yd', ''], cols),
            row(y + 50, ['1', 'Clay Pot', '8 yd', ''], cols)]


PLAN = {'equipment_tables': [{'title': 'Lamp Table', 'page': 10, 'kind': 'lamp'},
                             {'title': 'Thrown Lamp Table', 'page': 10, 'kind': 'lamp'}]}


class EquipmentTablesTest(unittest.TestCase):
    def take(self, lines, plan=PLAN):
        report = {'errors': [], 'questions': []}
        rest, entries = equipment_tables.take_tables(lines, plan, report, None, 'ML', 'ch8')
        return rest, dict(((c, e['slug']), e) for c, e in entries), report

    def test_a_table_becomes_a_tables_entry_and_an_entry_per_item(self):
        after = [title(400.0, 'Lamp Care'), line(416.0, [(60, 'Trim the wicks.')])]
        rest, entries, report = self.take(lamp_table() + thrown_table() + after)
        self.assertEqual(report['errors'], [])
        self.assertEqual([l['text'] for l in rest], ['Lamp Care', 'Trim the wicks.'])
        self.assertEqual(sorted(entries), [('equipment', 'clay-pot'), ('equipment', 'glass-lantern'),
                                           ('equipment', 'oil-lamp'), ('equipment', 'pitch-torch'),
                                           ('tables', 'lamp-table'), ('tables', 'thrown-lamp-table')])
        table = entries[('tables', 'lamp-table')]
        self.assertEqual([b['type'] for b in table['content']], ['heading', 'table', 'heading', 'table', 'heading', 'list'])
        self.assertEqual(table['content'][1]['columns'], ['TL', 'Lamp', 'Light', 'Cost', 'Notes'])
        self.assertEqual(table['content'][3]['rows'], [['0', 'Pitch Torch', '1 yd or less', '$2', '[1, 2]']])
        self.assertEqual(table['content'][5]['keys'], ['1', '2'])
        self.assertEqual(table['content'][5]['items'][1], '[2] Burns for an hour, then must be lit again.')
        self.assertEqual([(t['title'], t['groups'], t['rows'], t['notes']) for t in report['equipment_tables']],
                         [('Lamp Table', 2, 4, 2), ('Thrown Lamp Table', 1, 2, 0)])

    def test_an_items_fields_are_its_first_row_and_its_modes_every_row(self):
        _, entries, _ = self.take(lamp_table() + thrown_table())
        lantern = entries[('equipment', 'glass-lantern')]['fields']
        self.assertEqual(lantern, {'kind': 'lamp', 'group': ['LAMPS (DX-4)'], 'tl': '2', 'light': '5 yd', 'cost': '$40',
                                   'modes': [{'tl': '2', 'lamp': 'Glass Lantern', 'light': '5 yd', 'cost': '$40'},
                                             {'lamp': 'or', 'light': '1 yd'}]})
        self.assertNotIn('modes', entries[('equipment', 'clay-pot')]['fields'])

    def test_an_item_in_two_tables_is_one_entry_its_modes_keyed_by_each_tables_columns(self):
        _, entries, _ = self.take(lamp_table() + thrown_table())
        lamp = entries[('equipment', 'oil-lamp')]
        self.assertEqual(lamp['fields']['group'], ['LAMPS (DX-4)', 'THROWING (DX-3)'])
        self.assertEqual(lamp['fields']['modes'], [
            {'tl': '1', 'lamp': 'Oil Lamp', 'light': '2 yd', 'cost': '$10', 'notes': '[1]', 'table': 'Lamp Table'},
            {'tl': '1', 'lamp': 'Oil Lamp', 'range': '10 yd', 'table': 'Thrown Lamp Table'}])
        self.assertEqual([b.get('text') or b['type'] for b in lamp['content']],
                         ['LAMPS (DX-4)', 'table', 'THROWING (DX-3)', 'table', 'list'])
        self.assertEqual(lamp['content'][-1], {'type': 'list', 'ordered': False, 'items': ['[1] Smokes indoors.'],
                                               'keys': ['1']})

    def test_a_cell_out_of_line_fails_the_table_and_writes_nothing_of_it(self):
        lines = lamp_table()
        lines[4] = row(150.0, ['2', 'Glass Lantern', '5 yd', '$40', ''], (60, 80, 175, 220, 260))   # 5 points right
        _, entries, report = self.take(lines, {'equipment_tables': PLAN['equipment_tables'][:1]})
        self.assertEqual(entries, {})
        self.assertEqual(len(report['errors']), 1)
        self.assertIn("equipment table 'Lamp Table' (p10) was not read", report['errors'][0])
        self.assertIn('does not line up with the other cells', report['errors'][0])

    def test_a_group_heading_carried_onto_a_second_line_is_one_heading(self):
        lines = lamp_table()
        lines[1:2] = [group(116.0, 'LAMPS (DX-4, Torch-2,'), styled(line(127.0, [(90, 'or Lantern-1)')]), size=11.0, bold=True)]
        _, entries, report = self.take(lines, {'equipment_tables': PLAN['equipment_tables'][:1]})
        self.assertEqual(report['errors'], [])
        self.assertEqual(entries[('tables', 'lamp-table')]['content'][0]['text'], 'LAMPS (DX-4, Torch-2, or Lantern-1)')
        self.assertEqual(entries[('equipment', 'oil-lamp')]['fields']['group'], ['LAMPS (DX-4, Torch-2, or Lantern-1)'])

    def test_a_group_with_no_rows_fails_the_table(self):
        lines = lamp_table()
        lines[6:9] = [group(176.0, 'TORCHES (DX)')]                     # its rows gone, the notes follow
        _, entries, report = self.take(lines, {'equipment_tables': PLAN['equipment_tables'][:1]})
        self.assertEqual(entries, {})
        self.assertIn("the group 'TORCHES (DX)' has no rows", report['errors'][0])

    def test_numbered_notes_after_the_rows_with_no_notes_line_are_the_notes(self):
        lines = lamp_table()
        del lines[9]                                                # the "Notes" line
        _, entries, report = self.take(lines, {'equipment_tables': PLAN['equipment_tables'][:1]})
        self.assertEqual(report['errors'], [])
        self.assertEqual(entries[('tables', 'lamp-table')]['content'][-1]['keys'], ['1', '2'])

    def test_a_name_run_on_to_a_second_line_is_one_row_and_one_item(self):
        lines = lamp_table()
        # the name's second line set in under the first, the row's cells on it
        lines[4:5] = [row(150.0, ['2', 'Glass', '', '', '']), line(161.0, [(90, 'Lantern'), (170, '5 yd'), (220, '$40')])]
        _, entries, report = self.take(lines, {'equipment_tables': PLAN['equipment_tables'][:1]})
        self.assertEqual(report['errors'], [])
        self.assertIn(('equipment', 'glass-lantern'), entries)
        self.assertEqual(entries[('tables', 'lamp-table')]['content'][1]['rows'][1], ['2', 'Glass Lantern', '5 yd', '$40', ''])
        self.assertEqual(report['names_over_two_lines'], ['Lamp Table: Glass Lantern'])

    def test_a_header_word_in_brackets_names_one_column_with_the_word_before_it(self):
        cols = (60, 80, 170, 230)
        lines = [title(100.0, 'Kite Table'), group(116.0, 'KITE FLYING (DX-4)'),
                 header(128.0, ['TL', 'Kite', 'Lift', '(G)', 'Cost'], (60, 80, 170, 200, 230)),
                 row(139.0, ['1', 'Box Kite', '3/9 (1G)', '$5'], cols),
                 row(150.0, ['2', 'Delta Kite', '4/12 (2G)', '$9'], cols)]
        _, entries, report = self.take(lines, {'equipment_tables': [{'title': 'Kite Table', 'page': 10, 'kind': 'kite'}]})
        self.assertEqual(report['errors'], [])
        self.assertEqual(entries[('tables', 'kite-table')]['content'][1]['columns'], ['TL', 'Kite', 'Lift (G)', 'Cost'])
        self.assertEqual(entries[('equipment', 'box-kite')]['fields']['lift_g'], '3/9 (1G)')

    def test_a_name_one_group_prints_at_two_tls_is_two_items_named_with_their_tls(self):
        lines = lamp_table()
        lines[3] = row(139.0, ['1', 'Glass Lantern', '2 yd', '$10', '[1]'])
        _, entries, report = self.take(lines, {'equipment_tables': PLAN['equipment_tables'][:1]})
        self.assertEqual(report['errors'], [])
        old, new = entries[('equipment', 'glass-lantern-tl1')], entries[('equipment', 'glass-lantern-tl2')]
        self.assertEqual((old['name'], new['name']), ('Glass Lantern (TL1)', 'Glass Lantern (TL2)'))
        self.assertNotIn('relations', old)
        self.assertEqual(new['relations'], [{'role': 'distinct-from', 'to': 'equipment/glass-lantern-tl1'}])
        self.assertEqual(report['named_with_tl'], [{'table': 'Lamp Table', 'item': 'glass-lantern', 'tls': ['1', '2']}])

    def test_a_name_printed_in_two_groups_of_one_table_is_one_item(self):
        lines = lamp_table()
        lines[7] = row(188.0, ['2', 'Glass Lantern', '1 yd', '$40', ''])       # in TORCHES as well
        _, entries, report = self.take(lines, {'equipment_tables': PLAN['equipment_tables'][:1]})
        self.assertEqual(report['errors'], [])
        self.assertEqual(entries[('equipment', 'glass-lantern')]['fields']['group'], ['LAMPS (DX-4)', 'TORCHES (DX)'])
        self.assertNotIn('named_with_tl', report)

    def test_notes_printed_under_a_tables_panel_in_two_columns_are_its_notes(self):
        lines = [dict(l, box='10.1') for l in lamp_table()[:9]]   # a panel's lines follow the page's
        below = [line(300.0, [(60, '[1] Smokes indoors.')]),
                 line(311.0, [(60, 'Keep a window open.')]),
                 line(300.0, [(320, '[2] Burns for an hour.')], column='right'),
                 dict(line(700.0, [(320, '10 LAMPS')], column='right'), furniture=True)]
        regions = [{'id': '10.1', 'page': 10, 'kind': 'box', 'bbox': [50, 90, 560, 280]}]
        plan = {'equipment_tables': [dict(PLAN['equipment_tables'][0], notes_below=True)]}
        report = {'errors': [], 'questions': []}
        rest, entries = equipment_tables.take_tables(below + lines, plan, report, None, 'ML', 'ch8', regions)
        self.assertEqual(report['errors'], [])
        self.assertEqual([l['text'] for l in rest], ['10 LAMPS'])
        notes = dict(((c, e['slug']), e) for c, e in entries)[('tables', 'lamp-table')]['content'][-1]
        self.assertEqual(notes['items'], ['[1] Smokes indoors. Keep a window open.', '[2] Burns for an hour.'])

    def test_text_under_a_panel_that_opens_no_note_fails_the_table(self):
        lines = [dict(l, box='10.1') for l in lamp_table()[:9]]   # a panel's lines follow the page's
        below = [line(300.0, [(60, 'The lamps above burn oil.')])]
        regions = [{'id': '10.1', 'page': 10, 'kind': 'box', 'bbox': [50, 90, 560, 280]}]
        plan = {'equipment_tables': [dict(PLAN['equipment_tables'][0], notes_below=True)]}
        report = {'errors': [], 'questions': []}
        rest, entries = equipment_tables.take_tables(below + lines, plan, report, None, 'ML', 'ch8', regions)
        self.assertEqual(entries, [])
        self.assertIn('opens no note', report['errors'][0])
        self.assertEqual([l['text'] for l in rest], ['The lamps above burn oil.'])

    def test_a_title_the_page_does_not_have_is_an_error(self):
        _, entries, report = self.take(lamp_table(), {'equipment_tables': [{'title': 'Candle Table', 'page': 10, 'kind': 'lamp'}]})
        self.assertEqual(entries, {})
        self.assertEqual(report['errors'], ["plan equipment table 'Candle Table': no such title on p10"])


# invented skills entries: (name, text)
SKILLS = {'lamps': ('Lamps', 'Lamps\nTending lamps of every kind.'),
          'torches': ('Torches', 'Torches\nCarrying a torch.'),
          'kite-flying': ('Kite Flying', 'Kite Flying/TL\nYou must specialize: Box, Delta, or RC (a radio-'
                                         'controlled kite). Flying a box kite is the easiest.'),
          'rowing': ('Rowing', 'Rowing'), 'swimming': ('Swimming', 'Swimming')}


class GroupSkillsTest(unittest.TestCase):
    def skills(self, heading):
        return equipment_tables.group_skills(heading, SKILLS.get)

    def test_a_skill_and_its_defaults(self):
        self.assertEqual(self.skills('LAMPS (DX-4, Torch-2, or Lantern-1)'),
                         ([{'name': 'Lamps', 'to': 'skills/lamps', 'defaults': 'DX-4, Torch-2, or Lantern-1'}], None))
        self.assertEqual(self.skills('TORCHES (DX)'), ([{'name': 'Torches', 'to': 'skills/torches', 'defaults': 'DX'}], None))

    def test_a_specialty_takes_its_case_from_the_skills_entry(self):
        box, _ = self.skills('KITE FLYING/TL (BOX) (DX-4, or other Kite Flying at -2)')
        self.assertEqual(box, [{'name': 'Kite Flying/TL (Box)', 'to': 'skills/kite-flying', 'specialty': 'Box',
                                'defaults': 'DX-4, or other Kite Flying at -2'}])
        rc, _ = self.skills('KITE FLYING/TL (RC)')
        self.assertEqual(rc, [{'name': 'Kite Flying/TL (RC)', 'to': 'skills/kite-flying', 'specialty': 'RC'}])

    def test_several_skills_at_a_penalty_or_an_attribute(self):
        self.assertEqual(self.skills('ROWING-2, SWIMMING-2, or DX-2'), ([
            {'name': 'Rowing', 'to': 'skills/rowing', 'modifier': '-2', 'defaults': 'DX-2'},
            {'name': 'Swimming', 'to': 'skills/swimming', 'modifier': '-2', 'defaults': 'DX-2'}], None))

    def test_a_heading_in_upper_and_lower_case_names_no_skill(self):
        self.assertEqual(self.skills('Hand Lamps'), (None, None))

    def test_an_unknown_skill_or_specialty_is_a_failure(self):
        self.assertIn('no skills/candles entry', self.skills('CANDLES (DX-4)')[1])
        self.assertIn("prints no specialty 'GLIDER'", self.skills('KITE FLYING/TL (GLIDER) (DX-4)')[1])


class TableSkillsTest(unittest.TestCase):
    def take(self, lines, skills=SKILLS):
        report = {'errors': [], 'questions': []}
        plan = {'equipment_tables': PLAN['equipment_tables'][:1]}
        _, entries = equipment_tables.take_tables(lines, plan, report, None, 'ML', 'ch8', (), skills.get)
        return dict(((c, e['slug']), e) for c, e in entries), report

    def test_an_item_links_the_skill_its_group_names(self):
        entries, report = self.take(lamp_table())
        self.assertEqual(report['errors'], [])
        self.assertNotIn('skills_not_linked', report)
        self.assertEqual(entries[('equipment', 'oil-lamp')]['fields']['skills'],
                         [{'name': 'Lamps', 'to': 'skills/lamps', 'defaults': 'DX-4'}])

    def test_an_item_in_two_groups_has_both_skills_and_each_mode_its_own(self):
        lines = lamp_table()
        lines[7] = row(188.0, ['2', 'Glass Lantern', '1 yd', '$40', ''])       # in TORCHES as well
        entries, report = self.take(lines)
        fields = entries[('equipment', 'glass-lantern')]['fields']
        self.assertEqual([s['name'] for s in fields['skills']], ['Lamps', 'Torches'])
        self.assertEqual([m['skill'] for m in fields['modes']], ['Lamps', 'Lamps', 'Torches'])

    def test_a_group_naming_no_skills_entry_fails_the_table(self):
        entries, report = self.take(lamp_table(), {'lamps': SKILLS['lamps']})
        self.assertEqual(entries, {})
        self.assertIn('no skills/torches entry', report['errors'][0])

    def test_without_library_skills_the_report_says_none_were_linked(self):
        report = {'errors': [], 'questions': []}
        _, entries = equipment_tables.take_tables(lamp_table(), {'equipment_tables': PLAN['equipment_tables'][:1]},
                                                  report, None, 'ML', 'ch8')
        self.assertEqual(report['skills_not_linked'], ['Lamp Table: no library skills given'])
        self.assertTrue(all('skills' not in e['fields'] for _, e in entries))


if __name__ == '__main__':
    unittest.main()
