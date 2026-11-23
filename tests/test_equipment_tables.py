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

    def test_a_title_the_page_does_not_have_is_an_error(self):
        _, entries, report = self.take(lamp_table(), {'equipment_tables': [{'title': 'Candle Table', 'page': 10, 'kind': 'lamp'}]})
        self.assertEqual(entries, {})
        self.assertEqual(report['errors'], ["plan equipment table 'Candle Table': no such title on p10"])


if __name__ == '__main__':
    unittest.main()
