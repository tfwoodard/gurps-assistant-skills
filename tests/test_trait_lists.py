"""Tests for trait_lists.py: a book's summary tables of its traits, one row a trait, read across the
halves of a page and over a header printed again at the top of each. Everything here is invented.

Run: python -m unittest discover tests
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts'))
sys.path.insert(0, HERE)
import convert_traits  # noqa: E402
from test_text_tables import line  # noqa: E402


def at(l, column, page=10, heading=None):
    l.update(column=column, page=page)
    if heading:
        l['heading'] = heading
    return l


def chapter():
    """A list of lamps in two halves: left at x 60, right at x 320."""
    L, R = 0, 260
    ls = [at(line(80.0, [(200, 'LAMPS')]), 'full', heading=2),
          at(line(95.0, [(60, 'Kind tells whether a lamp burns oil or gas.')]), 'full', heading=5),
          at(line(110.0, [(60 + L, 'Lamp'), (150 + L, 'Kind'), (190 + L, 'Cost'), (230 + L, 'Page')]), 'left', heading=5),
          at(line(121.0, [(60, 'Tide Lamp'), (152, 'O'), (190, '5'), (232, '12')]), 'left'),
          at(line(132.0, [(60, 'Long Harbour'), (152, 'G'), (190, '10'), (232, '13')]), 'left'),
          at(line(143.0, [(66, 'Beacon')]), 'left'),                                     # its name, set in
          at(line(154.0, [(60, 'Reed Lamp'), (152, 'O'), (190, '-1 or'), (232, '14')]), 'left'),
          at(line(165.0, [(190, '-5')]), 'left'),                                          # its cost runs on
          at(line(176.0, [(60, 'Storm Lantern'), (150, 'O or G'), (190, '8'), (232, '15')]), 'left'),
          at(line(110.0, [(60 + R, 'Lamp'), (150 + R, 'Kind'), (190 + R, 'Cost'), (230 + R, 'Page')]), 'right', heading=5),
          at(line(121.0, [(60 + R, 'Wick Lamp'), (152 + R, 'G'), (190 + R, '2'), (232 + R, '16, 17')]), 'right'),
          at(line(132.0, [(60 + R, 'Moon Lamp'), (152 + R, 'O'), (190 + R, '3'), (232 + R, '18')]), 'right')]
    # "Glass Lamp" printed with its kind run on, no space ("LampG"), reaching over the Kind column
    glass = at(line(143.0, [(60 + R, 'Glass Lamp'), (190 + R, '4'), (232 + R, '19')]), 'right')
    glass['words'][1] = ['LampG', glass['words'][1][1], 152 + R + 4.75]
    glass['text'] = 'Glass LampG 4 19'
    ls.append(glass)
    # a second list, whose header has a line over it naming one column further
    ls += [at(line(200.0, [(200, 'WICKS')]), 'full', heading=2),
           at(line(213.0, [(150, 'Burn')]), 'left', heading=5),
           at(line(222.0, [(60, 'Wick'), (150, 'Hours'), (230, 'Page')]), 'left', heading=5),
           at(line(233.0, [(60, 'Cotton'), (152, '4'), (232, '20')]), 'left'),
           at(line(244.0, [(60, 'Flax'), (152, '6'), (232, '21')]), 'left'),
           at(line(255.0, [(60, 'Reed Pith'), (152, '2'), (232, '22')]), 'left')]
    return {'lines': ls, 'regions': []}


PLAN = {'source': 'ML', 'chapter': 'lists', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
        'lists': [{'heading': 'Lamps', 'page': 10, 'header_starts': 'Lamp', 'name': 'Lamps Table',
                   'about': 'Every lamp: kind, cost, page', 'values': {'Kind': ['O', 'G', 'O or G']},
                   'cells': [{'page': 10, 'text': 'O or G', 'column': 'Kind', 'why': 'wider than its column'}]},
                  {'heading': 'Wicks', 'page': 10, 'header_starts': 'Wick', 'name': 'Wicks Table'}]}


def convert(plan=None, doc=None):
    return convert_traits.convert_chapter(doc or chapter(), json.loads(json.dumps(plan or PLAN)))


class TraitListsTest(unittest.TestCase):
    def test_a_list_is_read_across_the_halves_of_a_page_into_one_table(self):
        entries, report = convert()
        self.assertEqual(report['errors'], [])
        by = {e['slug']: e for _, e in entries}
        e = by['lamps-table']
        self.assertEqual((e['name'], e['fields']), ('Lamps Table', {'printed_name': 'Lamps',
                                                                    'about': 'Every lamp: kind, cost, page'}))
        self.assertEqual(e['content'][0]['text'], 'Kind tells whether a lamp burns oil or gas.')
        table = e['content'][1]
        self.assertEqual(table['columns'], ['Lamp', 'Kind', 'Cost', 'Page'])
        self.assertEqual(table['rows'], [['Tide Lamp', 'O', '5', '12'], ['Long Harbour Beacon', 'G', '10', '13'],
                                         ['Reed Lamp', 'O', '-1 or -5', '14'], ['Storm Lantern', 'O or G', '8', '15'],
                                         ['Wick Lamp', 'G', '2', '16, 17'], ['Moon Lamp', 'O', '3', '18'],
                                         ['Glass Lamp', 'G', '4', '19']])
        self.assertEqual(report['words_split'][0]['into'], ['Lamp', 'G'])
        self.assertEqual(report['folded_keys'][0]['cells'], ['Lamp', 'Kind', 'Cost', 'Page'])

    def test_a_line_over_the_header_names_its_column_further(self):
        entries, report = convert()
        e = next(e for _, e in entries if e['slug'] == 'wicks-table')
        self.assertEqual(e['content'][0]['columns'], ['Wick', 'Burn Hours', 'Page'])
        self.assertEqual(e['content'][0]['rows'][2], ['Reed Pith', '2', '22'])

    def test_a_value_the_plan_does_not_give_a_column_refuses_the_list(self):
        plan = json.loads(json.dumps(PLAN))
        plan['lists'][0]['values']['Kind'] = ['O', 'G']
        entries, report = convert(plan)
        self.assertNotIn('lamps-table', [e['slug'] for _, e in entries])
        self.assertTrue(any("'Storm Lantern': 'O or G'" in e for e in report['errors']), report['errors'])

    def test_a_cell_the_plan_places_wrongly_or_a_row_that_ends_in_no_page_refuses_the_list(self):
        plan = json.loads(json.dumps(PLAN))
        plan['lists'][0]['cells'][0]['page'] = 11
        doc = chapter()
        doc['lines'][-2]['words'][-1][0] = 'twenty'          # Flax's page, misread
        entries, report = convert(plan, doc)
        self.assertEqual([e['slug'] for _, e in entries], [])
        self.assertTrue(any("'O or G' on p11 is in no row" in e for e in report['errors']), report['errors'])
        self.assertTrue(any("the row 'Flax' ends 'twenty', not a page" in e for e in report['errors']), report['errors'])


if __name__ == '__main__':
    unittest.main()
