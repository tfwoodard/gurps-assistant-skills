"""Tests for add_data_file.py. The data file and its traits are invented.

Run: python -m unittest discover tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts', 'add_data_file.py')

FIRST = '''Encoding=UTF-8
Version=3
Description=Invented traits for Marsh Lamps.
Requires="Marsh Basics.gdf", "Fen Gear.gdf"

[Advantages]
<Mental Advantages>
Tide Sense, 5/10, page(ML12)
Lamp Lore, 2, page (ML13)

[Skills]
<Boating>
Punting, DX/E, page(ML20)
'''
SECOND = FIRST.replace('Tide Sense, 5/10', 'Tide Sense, 6/12').replace('Punting, DX/E, page(ML20)\n',
                                                                       'Sculling, DX/A, page(ML21)\n')


class AddDataFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = os.path.join(self.tmp.name, 'library')
        os.makedirs(os.path.join(self.lib, 'gca', 'parsed'))
        self.write_json('library.json', {'gurps_library': True, 'layout_version': 1, 'sources': [
            {'code': 'ML', 'title': 'Marsh Lamps', 'chapters': []}], 'data_files': [
            {'file': 'Marsh Basics.gdf', 'folder': 'gca/books', 'sha256': 'x', 'notes': ''}]})
        self.write_json('gca/parsed/_index.json', [{'item': 'SK:Rowing', 'file': 'Marsh Basics.gdf', 'line': 4}])
        self.gdf = os.path.join(self.tmp.name, 'Marsh Lamps 4e.gdf')
        self.write_gdf(FIRST)

    def tearDown(self):
        self.tmp.cleanup()

    def write_json(self, rel, data):
        with open(os.path.join(self.lib, *rel.split('/')), 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def read_json(self, rel):
        with open(os.path.join(self.lib, *rel.split('/')), encoding='utf-8') as f:
            return json.load(f)

    def write_gdf(self, text):
        with open(self.gdf, 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(text)

    def run_it(self, *extra):
        r = subprocess.run([sys.executable, SCRIPT, self.gdf, '--library', self.lib, '--date', '2026-01-02', *extra],
                           capture_output=True, text=True, encoding='utf-8')
        return r, (json.loads(r.stdout) if r.returncode == 0 else None)

    def test_the_file_is_copied_read_indexed_and_recorded(self):
        r, report = self.run_it('--source', 'ML')
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.gdf, 'rb') as a, open(os.path.join(self.lib, 'gca', 'books', 'Marsh Lamps 4e.gdf'), 'rb') as b:
            self.assertEqual(a.read(), b.read())
        parsed = self.read_json('gca/parsed/marsh-lamps-4e.json')
        self.assertEqual([i['item'] for s in parsed['sections'] for i in s['items']],
                         ['AD:Tide Sense', 'AD:Lamp Lore', 'SK:Punting'])
        self.assertEqual([(x['file'], x['item']) for x in self.read_json('gca/parsed/_index.json')],
                         [('Marsh Basics.gdf', 'SK:Rowing'), ('Marsh Lamps 4e.gdf', 'AD:Tide Sense'),
                          ('Marsh Lamps 4e.gdf', 'AD:Lamp Lore'), ('Marsh Lamps 4e.gdf', 'SK:Punting')])
        library = self.read_json('library.json')
        rec = library['data_files'][1]
        self.assertEqual((rec['file'], rec['folder'], rec['origin'], rec['source'], rec['status'], rec['date']),
                         ('Marsh Lamps 4e.gdf', 'gca/books', 'official', 'ML', 'imported', '2026-01-02'))
        self.assertEqual((rec['requires'], rec['counts'], rec['problems']),
                         (['Marsh Basics.gdf', 'Fen Gear.gdf'], {'Advantages': 2, 'Skills': 1}, 1))
        self.assertEqual(library['sources'][0]['data_files'], ['Marsh Lamps 4e.gdf'])

    def test_the_report_names_unread_lines_and_required_files_not_in_the_library(self):
        _, report = self.run_it()
        self.assertEqual([(p['line'], p['text']) for p in report['problems']], [(9, 'Lamp Lore')])
        self.assertEqual(report['requires'], [{'file': 'Marsh Basics.gdf', 'in_library': True},
                                              {'file': 'Fen Gear.gdf', 'in_library': False}])
        self.assertIsNone(report['changes'])

    def test_reading_a_changed_file_again_says_what_changed_and_keeps_its_source(self):
        self.run_it('--source', 'ML', '--notes', 'from the marsh')
        self.write_gdf(SECOND)
        _, report = self.run_it()
        self.assertFalse(report['same_as_before'])
        self.assertEqual(report['changes'], {'added': ['Skills/SK:Sculling'], 'removed': ['Skills/SK:Punting'],
                                             'altered': ['Advantages/AD:Tide Sense']})
        library = self.read_json('library.json')
        self.assertEqual(len(library['data_files']), 2)
        self.assertEqual((library['data_files'][1]['source'], library['data_files'][1]['notes']), ('ML', 'from the marsh'))
        self.assertEqual([x['item'] for x in self.read_json('gca/parsed/_index.json') if x['file'] == 'Marsh Lamps 4e.gdf'],
                         ['AD:Tide Sense', 'AD:Lamp Lore', 'SK:Sculling'])
        self.assertEqual(library['sources'][0]['data_files'], ['Marsh Lamps 4e.gdf'])

    def test_a_dry_run_writes_nothing_and_an_unknown_source_is_refused(self):
        r, report = self.run_it('--dry-run')
        self.assertEqual(report['definitions'], 3)
        self.assertFalse(os.path.exists(os.path.join(self.lib, 'gca', 'books')))
        self.assertEqual(len(self.read_json('library.json')['data_files']), 1)
        r, _ = self.run_it('--source', 'ZZ')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no source with that code', r.stderr)


if __name__ == '__main__':
    unittest.main()
