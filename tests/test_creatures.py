"""Tests for convert_traits.py's creature sections (creatures.py), on an invented chapter of marsh
beasts given as the lines pdf_layout.py would read from it.

Run: python -m unittest discover tests
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_convert_traits import SCRIPTS, Page, convert_traits  # noqa: E402
import creatures  # noqa: E402

STAT_NAME = re.compile(r'^(ST|DX|IQ|HT|Will|Per|Speed|Dodge|Move|SM)$')
SECTIONS = {'creatures': {'kind': 'animal', 'name_size': 10.9, 'group_size': 13.9}}


def stat(p, text, indent=0.0):
    """A stat line, its characteristic names in bold."""
    l = p.line(text, indent=indent)
    l['spans'] = [{'text': w, 'size': 9.5, 'bold': bool(STAT_NAME.match(w)), 'italic': False} for w in text.split()]
    return l


def label(p, name, rest):
    """A labelled line set flush, its label in bold italic."""
    l = p.line(f'{name}: {rest}')
    l['spans'] = [{'text': f'{name}:', 'size': 9.5, 'bold': True, 'italic': True},
                  {'text': f' {rest}', 'size': 9.5, 'bold': False, 'italic': False}]
    return l


def beast(p, name, size=10.9, about=(), st='ST 4; DX 14; IQ 4; HT 12.', will='Will 10; Per 12; Speed 6.5; Dodge 9;'):
    p.line(name, size=size, heading=3 if size > 12 else 4, bold=True)
    if about:
        p.para(*about)
    stat(p, st)
    stat(p, will)
    stat(p, 'Move 5 (Water Move 8).', indent=12.0)
    stat(p, 'SM -2; 20 lbs.')


def chapter():
    p = Page()
    p.line('MARSH BEASTS', size=20.0, heading=2, bold=True)
    p.para('Beasts of the marsh, for', 'any keeper to meet.')
    p.line('Otters', size=13.9, heading=3, bold=True)                    # a group
    p.para('Otters fish in pairs and', 'whistle to each other.')
    beast(p, 'River Otter', about=('A small, quick otter.',))
    label(p, 'Traits', 'Night Vision 2; Sharp Teeth (Fishing;')       # a semicolon inside brackets
    p.line('Small, -10%); Wild Animal.', indent=12.0)
    label(p, 'Skills', 'Swimming-15.')
    beast(p, 'Sea Otter', will='Will 10; Per 12; Speed 6, Dodge 9;')  # a comma for a semicolon
    label(p, 'Traits and Skills', 'As river otter.')
    p.para('Sea otters float on their', 'backs to eat.')                 # the creature's text, after its stats
    beast(p, 'Herons', size=13.9, about=('A tall wading bird.',))      # a creature headed like a group
    label(p, 'Cost', '$50.')
    beast(p, 'Marsh Frog')                                             # after Herons: in no group
    label(p, 'Traits', 'Wild Animal.')
    return {'lines': p.lines, 'regions': []}


def plan(**creature_spec):
    return {'source': 'ML', 'chapter': 'ch16', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
            'sections': [{'heading': 'Marsh Beasts', 'page': 10,
                          'creatures': dict(SECTIONS['creatures'], **creature_spec)}]}


class CreatureSectionTest(unittest.TestCase):
    def setUp(self):
        self.entries, self.report = convert_traits.convert_chapter(chapter(), plan())
        self.by = {f'{c}/{e["slug"]}': e for c, e in self.entries}

    def test_it_finds_the_sections_text_its_groups_and_its_creatures(self):
        self.assertEqual(self.report['errors'], [])
        self.assertEqual(sorted(self.by), ['creatures/herons', 'creatures/marsh-frog', 'creatures/otters',
                                           'creatures/river-otter', 'creatures/sea-otter', 'rules/marsh-beasts'])
        self.assertEqual(self.report['creature_groups'],
                         [{'group': 'Otters', 'page': 10, 'members': ['River Otter', 'Sea Otter']}])

    def test_a_creature_has_its_description_then_its_stats_in_printed_order(self):
        e = self.by['creatures/river-otter']
        self.assertEqual(e['section'], 'Otters')
        self.assertEqual(e['relations'], [{'role': 'adds-to', 'to': 'creatures/otters'}])
        attrs = {'ST': '4', 'DX': '14', 'IQ': '4', 'HT': '12', 'Will': '10', 'Per': '12', 'Speed': '6.5',
                 'Dodge': '9', 'Move': '5 (Water Move 8)', 'SM': '-2', 'Weight': '20 lbs.'}
        self.assertEqual(list(e['fields']['attributes'].items()), list(attrs.items()))
        self.assertEqual(e['fields']['kind'], 'animal')
        self.assertEqual(e['fields']['traits'], 'Night Vision 2; Sharp Teeth (Fishing; Small, -10%); Wild Animal.')
        self.assertEqual(e['fields']['skills'], 'Swimming-15.')
        self.assertEqual([b['type'] for b in e['content']], ['paragraph', 'profile'])
        prof = e['content'][1]
        self.assertEqual((prof['name'], prof['characteristics']), ('River Otter', attrs))
        self.assertEqual([l['label'] for l in prof['lines']], ['Traits', 'Skills'])

    def test_a_comma_between_two_characteristics_is_read_as_a_semicolon_and_reported(self):
        e = self.by['creatures/sea-otter']
        self.assertEqual((e['fields']['attributes']['Speed'], e['fields']['attributes']['Dodge']), ('6', '9'))
        self.assertEqual(self.report['stat_lines'], [{'entry': 'creatures/sea-otter', 'text': 'Speed 6, Dodge 9',
                                                      'read': 'a comma between two characteristics, read as the '
                                                              'semicolon the others print'}])
        self.assertEqual(e['fields']['traits_and_skills'], 'As river otter.')
        self.assertEqual(e['content'][-1], {'type': 'paragraph', 'text': 'Sea otters float on their backs to eat.'})

    def test_a_creature_headed_like_a_group_stands_alone_and_closes_the_group(self):
        herons, frog = self.by['creatures/herons'], self.by['creatures/marsh-frog']
        self.assertEqual((herons['section'], herons['fields']['cost']), ('Marsh Beasts', '$50.'))
        self.assertNotIn('relations', herons)
        self.assertNotIn('relations', frog)
        self.assertNotIn('attributes', self.by['creatures/otters']['fields'])

    def test_a_creature_heading_with_no_stat_line_is_an_error(self):
        doc = chapter()
        doc['lines'] = [l for l in doc['lines'] if not (l['text'].startswith(('ST ', 'Will ', 'Move ', 'SM ')) and
                                                        l['baseline'] > [x for x in doc['lines']
                                                                         if x['text'] == 'Marsh Frog'][0]['baseline'])]
        _, report = convert_traits.convert_chapter(doc, plan())
        self.assertTrue(any("'Marsh Frog' has no stat line" in e for e in report['errors']), report['errors'])

    def test_a_part_of_a_stat_line_that_is_no_characteristic_is_an_error(self):
        report = {'errors': []}
        self.assertIsNone(creatures.read_stats('ST 4; DX 14; Wings 2; 20 lbs.', report, 'creatures/x'))
        self.assertTrue(any("'Wings 2'" in e for e in report['errors']), report['errors'])
        report = {'errors': []}
        self.assertIsNone(creatures.read_stats('ST 4; DX 14. ST 5.', report, 'creatures/x'))
        self.assertTrue(any('ST is printed twice' in e for e in report['errors']), report['errors'])

    def test_it_writes_profiles_that_render_and_cover_every_word(self):
        with tempfile.TemporaryDirectory() as d:
            layout, plan_path, out = os.path.join(d, 'layout.json'), os.path.join(d, 'plan.json'), os.path.join(d, 'out')
            with open(layout, 'w', encoding='utf-8') as f:
                json.dump(chapter(), f)
            with open(plan_path, 'w', encoding='utf-8') as f:
                json.dump(plan(), f)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'convert_traits.py'), layout, '--plan', plan_path,
                                '--out', out], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(os.path.join(out, 'creatures--river-otter.md'), encoding='utf-8') as f:
                md = f.read()
            self.assertIn('| ST | DX | IQ | HT | Will | Per | Speed | Dodge | Move | SM | Weight |', md)
            self.assertIn('**Traits:** Night Vision 2;', md)
            self.assertEqual(md.count('# River Otter'), 1)             # the profile is the entry's own
            c = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'check_coverage.py'), layout, out],
                               capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(c.returncode, 0, c.stdout)


if __name__ == '__main__':
    unittest.main()
