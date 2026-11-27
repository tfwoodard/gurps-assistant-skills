"""Tests for link_gca.py: a source's entries are linked to the definitions of its data files, exact
matches at once and the rest as proposals the links file confirms. The book, its data file and its
traits are invented.

Run: python -m unittest discover tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts')

GDF = '''Encoding=UTF-8
Version=3
Description=Invented traits for Marsh Lamps.

[Advantages]
<_New Advantages>
_New Advantage, 0
<Mental Advantages>
Tide Sense, 15/45, page(ML12)
Lamp Lore, 5/10, page(ML13)
Reed Friend, 5/10, page(ML14)
Fog Sight, 10, page(ML15)
Wick Craft, 8, page(ML16)
Keeper Rank, 5/10, page(ML9)
Gull Speech, 10, page(OT30)

[Skills]
<Boating>
Punting, DX/E, page(ML20)
Lantern (Oil), IQ/A, page(ML21)
Lantern (Gas), IQ/A, page(ML21)
Lantern (Glass), IQ/E, page(ML21)

[Modifiers]
<_General>
Bright, +20%, page(ML40)
Bright: Dim glow, +20%, page(ML40)
Steady, +10%/+20%, page(ML41)
<Tide Sense>
Bright, +10%, page(ML12)
'''

ENTRIES = {
    'advantages': [
        ('tide-sense', 'Tide Sense', 12, {'cost': '15 points'}),
        ('lamp-lore', 'Lamp Lore', 13, {'cost': '5 points/level'}),
        ('reed-friends', 'Reed Friends', 14, {'cost': '5 points/level'}),
        ('fog-sight', 'Fog Sight', 14, {'cost': '10 points'}),
        ('wick-craft', 'Wick Craft', 16, {'cost': '10 points'}),
        ('keeper-rank', 'Keeper Rank', 20, {'see': 'Keeper Rank, p. 9'}),
    ],
    'skills': [
        ('punting', 'Punting', 20, {'attribute': 'DX', 'difficulty': 'Easy'}),
        ('lantern', 'Lantern', 21, {'attribute': 'IQ', 'difficulty': 'Average', 'specialties': True}),
        ('lantern-gas', 'Lantern (Gas)', 21, {'attribute': 'IQ', 'difficulty': 'Average'}),
    ],
    'modifiers': [
        ('bright', 'Bright', 40, {'cost': '+20%'}),
        ('steady', 'Steady', 41, {'cost': '+10%/level'}),
    ],
}
FILE = 'Marsh Lamps 4e.gdf'


class LinkGca(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = os.path.join(self.tmp.name, 'library')
        os.makedirs(os.path.join(self.lib, 'gca', 'parsed'))
        os.makedirs(os.path.join(self.lib, 'sources', 'ML', 'plans'))
        self.dump('library.json', {'gurps_library': True, 'layout_version': 1, 'edition': '4e', 'sources': [
            {'code': 'ML', 'title': 'Marsh Lamps', 'edition': '4e', 'chapters': [], 'data_files': []}], 'data_files': []})
        gdf = os.path.join(self.tmp.name, FILE)
        with open(gdf, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(GDF)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'add_data_file.py'), gdf, '--library', self.lib,
                            '--source', 'ML'], capture_output=True, text=True, encoding='utf-8')
        assert r.returncode == 0, r.stderr
        for cat, entries in ENTRIES.items():
            os.makedirs(os.path.join(self.lib, 'library-data', cat))
            records = []
            for slug, name, page, fields in entries:
                self.dump(f'library-data/{cat}/{slug}.json', {
                    'slug': slug, 'name': name, 'source': 'ML', 'chapter': 'ch2', 'section': name, 'page': page,
                    'fields': fields, 'level': 3, 'content': [{'type': 'paragraph', 'text': 'Invented words.'}]}, indent=1)
                records.append({'slug': slug, 'name': name, 'source': 'ML', 'chapter': 'ch2', 'section': name,
                                'page': page, **fields, 'edition': '4e'})
            with open(os.path.join(self.lib, 'library-data', cat, '_index.json'), 'w', encoding='utf-8') as f:
                f.write('[\n' + ',\n'.join('  ' + json.dumps(r) for r in records) + '\n]\n')

    def tearDown(self):
        self.tmp.cleanup()

    def dump(self, rel, data, indent=None):
        with open(os.path.join(self.lib, *rel.split('/')), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent)
            if indent is not None:
                f.write('\n')

    def read(self, rel):
        with open(os.path.join(self.lib, *rel.split('/')), encoding='utf-8') as f:
            return f.read()

    def run_it(self, links=None, *extra):
        if links is not None:
            self.dump('sources/ML/plans/links.json', links)
        out = os.path.join(self.tmp.name, 'report.json')
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'link_gca.py'), '--library', self.lib, '--source', 'ML',
                            '--report', out, *extra], capture_output=True, text=True, encoding='utf-8')
        with open(out, encoding='utf-8') as f:
            return r, json.load(f)

    def test_exact_matches_link_and_the_rest_are_proposed_by_kind(self):
        r, rep = self.run_it()
        self.assertEqual(r.returncode, 0, r.stderr)
        items = lambda ref: [x['item'] for x in rep['links'][ref]]
        self.assertEqual(items('advantages/tide-sense'), ['AD:Tide Sense'])
        self.assertEqual(rep['links']['advantages/tide-sense'], [{'item': 'AD:Tide Sense', 'file': FILE}])
        # a skill that takes specialties gets each of them, but not one another entry is named for
        self.assertEqual(items('skills/lantern'), ['SK:Lantern (Oil)', 'SK:Lantern (Glass)'])
        self.assertEqual(items('skills/lantern-gas'), ['SK:Lantern (Gas)'])
        # a modifier's link names its group, and the same name in another group is not taken; a variant
        # named "Bright: Dim glow" is the modifier's as "Bright (Dim glow)" would be
        self.assertEqual(rep['links']['modifiers/bright'], [{'item': 'Bright', 'group': '_General', 'file': FILE},
                                                            {'item': 'Bright: Dim glow', 'group': '_General', 'file': FILE}])
        proposed = {x['entry']: [(p['kind'], p['item']) for p in x['proposals']] for x in rep['no_definition']}
        self.assertEqual(proposed, {'advantages/reed-friends': [('singular', 'AD:Reed Friend')],
                                    'advantages/fog-sight': [('runs-on', 'AD:Fog Sight')],
                                    'advantages/keeper-rank': [('pointer', 'AD:Keeper Rank')]})
        self.assertEqual(rep['counts']['advantages'], {'entries': 6, 'exact': 3, 'unlinked': 3})

    def test_definitions_with_no_entry_and_costs_that_differ_are_reported(self):
        _, rep = self.run_it()
        self.assertEqual(sorted((x['item'], x.get('group', ''), x['why']) for x in rep['no_entry']),
                         [('AD:Fog Sight', '', 'cites ML'), ('AD:Gull Speech', '', 'cites no page of ML'),
                          ('AD:Keeper Rank', '', 'cites ML'), ('AD:Reed Friend', '', 'cites ML'),
                          ('Bright', 'Tide Sense', "in a modifier group no entry's definition is in")])
        self.assertEqual(rep['helpers'], 1)
        self.assertEqual(rep['costs_differ'], [
            {'entry': 'advantages/wick-craft', 'item': 'AD:Wick Craft', 'printed': '10 points', 'data_file': '8'},
            {'entry': 'skills/lantern', 'item': 'SK:Lantern (Glass)', 'printed': 'IQ/Average', 'data_file': 'IQ/E'}])
        # "15 points" against "15/45", "5 points/level" against "5/10" and "+10%/level" against "+10%/+20%" agree;
        # nothing here is left uncompared
        self.assertEqual(rep['not_compared'], {})

    def test_the_links_file_confirms_links_by_entry_or_by_kind(self):
        r, rep = self.run_it({'links': {'advantages/keeper-rank': ['AD:Keeper Rank']},
                              'accept': ['runs-on', 'singular'],
                              'not_entries': {'AD:Gull Speech': 'from another book'}})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rep['how']['advantages/keeper-rank'], 'confirmed')
        self.assertEqual((rep['how']['advantages/fog-sight'], rep['how']['advantages/reed-friends']), ('accepted', 'accepted'))
        self.assertEqual(rep['no_definition'], [])
        self.assertEqual([x['item'] for x in rep['no_entry']], ['Bright'])
        self.assertEqual(rep['no_entry_known'][0]['why'], 'from another book')

    def test_an_accepted_pointer_takes_only_definitions_no_other_entry_holds(self):
        r, rep = self.run_it({'accept': ['pointer']})
        self.assertEqual((rep['how']['advantages/keeper-rank'], rep['pointers_to_linked']), ('accepted', []))
        # the write-up the pointer points to, in another chapter, takes the definition first
        index = self.read('library-data/advantages/_index.json').rstrip().rstrip(']').rstrip()
        rec = {'slug': 'keeper-rank-write-up', 'name': 'Keeper Rank', 'source': 'ML', 'chapter': 'ch1',
               'section': 'Keeper Rank', 'page': 9, 'cost': '5 points/level', 'edition': '4e'}
        with open(os.path.join(self.lib, 'library-data', 'advantages', '_index.json'), 'w', encoding='utf-8') as f:
            f.write(index + ',\n  ' + json.dumps(rec) + '\n]\n')
        r, rep = self.run_it({'accept': ['pointer']})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rep['how']['advantages/keeper-rank-write-up'], 'exact')
        self.assertEqual(rep['how']['advantages/keeper-rank'], 'pointer')
        self.assertEqual(rep['pointers_to_linked'], [{'entry': 'advantages/keeper-rank', 'items': ['AD:Keeper Rank']}])
        self.assertNotIn('advantages/keeper-rank', [x['entry'] for x in rep['no_definition']])
        self.assertEqual(rep['claimed_twice'], [])

    def test_a_links_file_naming_what_isnt_there_is_an_error_and_nothing_is_written(self):
        r, rep = self.run_it({'links': {'advantages/no-such': ['AD:Tide Sense'], 'skills/punting': ['SK:Sculling']},
                              'none': {'skills/punting': 'x'}, 'accept': ['nearby']}, '--write')
        self.assertEqual(r.returncode, 1)
        self.assertEqual(len(rep["errors"]), 4, rep["errors"])
        self.assertIn('nothing written', r.stdout)
        self.assertNotIn('"gca"', self.read('library-data/advantages/tide-sense.json'))

    def test_write_sets_gca_on_the_entry_its_markdown_and_its_index_line_and_takes_it_off_again(self):
        r, _ = self.run_it({'links': {'advantages/keeper-rank': ['AD:Keeper Rank']}}, '--write')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('wrote 9 entries', r.stdout)
        entry = json.loads(self.read('library-data/advantages/keeper-rank.json'))
        self.assertEqual(list(entry), ['slug', 'name', 'source', 'chapter', 'section', 'page', 'fields', 'gca', 'level', 'content'])
        self.assertEqual(entry['gca'], [{'item': 'AD:Keeper Rank', 'file': FILE}])
        self.assertIn('gca: [{"item": "AD:Keeper Rank"', self.read('library-data/advantages/keeper-rank.md'))
        index = self.read('library-data/advantages/_index.json').splitlines()
        rec = json.loads(next(l for l in index if '"keeper-rank"' in l).strip().rstrip(','))
        self.assertEqual(list(rec)[-2:], ['gca', 'edition'])
        self.assertNotIn('gca', json.loads(next(l for l in index if '"fog-sight"' in l).strip().rstrip(',')))
        # run again with the confirmation gone: the link comes off; a run that changes nothing writes nothing
        r, _ = self.run_it({}, '--write')
        self.assertIn('wrote 1 entries', r.stdout)
        self.assertNotIn('gca', json.loads(self.read('library-data/advantages/keeper-rank.json')))
        r, _ = self.run_it({}, '--write')
        self.assertIn('wrote 0 entries', r.stdout)


if __name__ == '__main__':
    unittest.main()
