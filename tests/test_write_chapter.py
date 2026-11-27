"""Tests for write_chapter.py: a converted chapter goes into a library folder only when it is fit
to, and a re-import replaces what the chapter had. Uses test_convert_traits' invented chapter.

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
sys.path.insert(0, HERE)
from test_convert_traits import PLAN, chapter  # noqa: E402


class WriteChapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.lib = os.path.join(d, 'library')
        os.makedirs(os.path.join(self.lib, 'library-data', 'advantages'))
        self.dump(os.path.join(self.lib, 'library.json'), {
            'gurps_library': True, 'layout_version': 1, 'edition': '4e', 'sources': [
                {'code': 'ML', 'title': 'Marsh Lamps', 'edition': '4e', 'chapters': [
                    {'id': 'ch1', 'title': 'One', 'pages': '1-9', 'status': 'not-imported', 'date': None, 'notes': ''},
                    {'id': 'ch2', 'title': 'Two', 'pages': '10-11', 'status': 'not-imported', 'date': None, 'notes': ''}]}]})
        self.dump(os.path.join(self.lib, 'library-data', '_import-log.json'), [])
        self.dump(os.path.join(self.lib, 'library-data', 'advantages', '_index.json'), [
            {'slug': 'old-gift', 'name': 'Old Gift', 'source': 'ML', 'chapter': 'ch1', 'page': 3, 'edition': '4e'}])
        self.layout, self.plan, self.out = os.path.join(d, 'layout.json'), os.path.join(d, 'plan.json'), os.path.join(d, 'out')
        self.convert(chapter())

    def tearDown(self):
        self.tmp.cleanup()

    def dump(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def read(self, *rel):
        with open(os.path.join(self.lib, *rel), encoding='utf-8') as f:
            return json.load(f)

    def convert(self, doc):
        self.dump(self.layout, doc)
        self.dump(self.plan, PLAN)
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'convert_traits.py'), self.layout, '--plan', self.plan,
                            '--out', self.out], capture_output=True, text=True, encoding='utf-8')
        return r

    def write(self, *extra):
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, 'write_chapter.py'), self.out, '--library', self.lib,
                               '--layout', self.layout, '--source', 'ML', '--chapter', 'ch2', '--notes', 'Gifts and flaws.',
                               '--date', '2026-01-02', *extra], capture_output=True, text=True, encoding='utf-8')

    def test_entries_indexes_the_log_and_the_chapters_status_are_written(self):
        r = self.write()
        self.assertEqual(r.returncode, 0, r.stderr)
        summary = json.loads(r.stdout)
        self.assertEqual({c: v['entries'] for c, v in summary['categories'].items()}, {'advantages': 4, 'modifiers': 2, 'rules': 4})
        self.assertEqual(self.read('library-data', 'advantages', 'tide-sense.json')['fields']['cost'], '5 points/level')
        self.assertTrue(os.path.exists(os.path.join(self.lib, 'library-data', 'advantages', 'tide-sense.md')))
        index = self.read('library-data', 'advantages', '_index.json')
        self.assertEqual([x['slug'] for x in index], ['eel-speech', 'marsh-rank', 'old-gift', 'tide-sense', 'webbed-hands'])
        self.assertEqual((index[3]['edition'], index[3]['cost'], '_category' in index[3]), ('4e', '5 points/level', False))
        self.assertEqual([x['slug'] for x in self.read('library-data', 'modifiers', '_index.json')],
                         ['moonlit-only', 'tide-sense-limitation'])
        log = self.read('library-data', '_import-log.json')
        self.assertEqual([(x['category'], x['added'], x['chapter'], x['notes']) for x in log],
                         [('advantages', 4, 'ch2', 'Gifts and flaws.'), ('modifiers', 2, 'ch2', 'Gifts and flaws.'),
                          ('rules', 4, 'ch2', 'Gifts and flaws.')])
        chapters = self.read('library.json')['sources'][0]['chapters']
        self.assertEqual((chapters[1]['status'], chapters[1]['date'], chapters[1]['notes']), ('imported', '2026-01-02', 'Gifts and flaws.'))
        self.assertEqual(chapters[0]['status'], 'not-imported')

    def test_a_dry_run_writes_nothing(self):
        r = self.write('--dry-run')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.lib, 'library-data', 'advantages', 'tide-sense.json')))
        self.assertEqual(self.read('library.json')['sources'][0]['chapters'][1]['status'], 'not-imported')
        self.assertEqual(self.read('library-data', '_import-log.json'), [])

    def test_importing_again_replaces_the_chapters_entries_and_removes_what_it_no_longer_has(self):
        self.write()
        doc = chapter()
        i = next(k for k, l in enumerate(doc['lines']) if l['text'].startswith('Eel Speech'))
        j = next(k for k, l in enumerate(doc['lines']) if l['text'] == 'FLAWS')
        doc['lines'][i:j] = []                                           # Eel Speech is gone from the chapter
        self.assertEqual(self.convert(doc).returncode, 0)
        r = self.write()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['categories']['advantages']['removed'], ['eel-speech'])
        self.assertEqual([x['slug'] for x in self.read('library-data', 'advantages', '_index.json')],
                         ['marsh-rank', 'old-gift', 'tide-sense', 'webbed-hands'])
        self.assertFalse(os.path.exists(os.path.join(self.lib, 'library-data', 'advantages', 'eel-speech.json')))
        self.assertFalse(os.path.exists(os.path.join(self.lib, 'library-data', 'advantages', 'eel-speech.md')))

    def test_a_slug_another_chapter_holds_stops_the_write_before_any_file_is_touched(self):
        # Chapter 1 already holds rules/gift-list, which chapter 2 would write too.
        rules = os.path.join(self.lib, 'library-data', 'rules')
        os.makedirs(rules)
        self.dump(os.path.join(rules, '_index.json'), [
            {'slug': 'gift-list', 'name': 'Gift List', 'source': 'ML', 'chapter': 'ch1', 'page': 4, 'edition': '4e'}])
        with open(os.path.join(rules, 'gift-list.json'), 'w', encoding='utf-8') as f:
            f.write('chapter one')
        r = self.write()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("slug 'gift-list' already belongs to ML ch1", r.stderr)
        self.assertIn('nothing written', r.stderr)
        with open(os.path.join(rules, 'gift-list.json'), encoding='utf-8') as f:
            self.assertEqual(f.read(), 'chapter one')
        self.assertEqual(sorted(os.listdir(rules)), ['_index.json', 'gift-list.json'])
        self.assertFalse(os.path.exists(os.path.join(self.lib, 'library-data', 'advantages', 'tide-sense.json')))
        self.assertEqual(self.read('library-data', '_import-log.json'), [])

    def test_a_chapter_with_converter_errors_or_lost_words_is_not_written(self):
        report = os.path.join(self.out, '_report.json')
        with open(report, encoding='utf-8') as f:
            data = json.load(f)
        data['errors'] = ['p10: something is wrong']
        self.dump(report, data)
        r = self.write()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('the converter reported 1 errors; nothing written', r.stderr)
        data['errors'] = []
        self.dump(report, data)
        os.remove(os.path.join(self.out, 'advantages--webbed-hands.json'))
        os.remove(os.path.join(self.out, 'advantages--webbed-hands.md'))
        r = self.write()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('words of the pages are in no entry; nothing written', r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.lib, 'library-data', 'advantages', 'tide-sense.json')))

    def test_an_entry_written_over_a_linked_one_keeps_its_gca_links(self):
        self.assertEqual(self.write().returncode, 0)
        links = [{'item': 'AD:Tide Sense', 'file': 'Marsh Lamps 4e.gdf'}]
        path = os.path.join(self.lib, 'library-data', 'advantages', 'tide-sense.json')
        entry = self.read('library-data', 'advantages', 'tide-sense.json')
        entry['gca'] = links
        self.dump(path, entry)
        r = self.write()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['gca_carried_over'], 1)
        again = self.read('library-data', 'advantages', 'tide-sense.json')
        self.assertEqual(again['gca'], links)
        self.assertEqual(list(again).index('gca'), list(again).index('fields') + 1)
        with open(path[:-5] + '.md', encoding='utf-8') as f:
            self.assertIn('gca: [{"item": "AD:Tide Sense"', f.read())
        rec = next(x for x in self.read('library-data', 'advantages', '_index.json') if x['slug'] == 'tide-sense')
        self.assertEqual(rec['gca'], links)
        self.assertNotIn('gca', self.read('library-data', 'advantages', 'webbed-hands.json'))


if __name__ == '__main__':
    unittest.main()
