"""Tests for gdf.py, the GCA data file reader and writer. Every trait here is invented.

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
sys.path.insert(0, SCRIPTS)
import gdf  # noqa: E402

SAMPLE = '''Encoding=UTF-8
Version=3
* a comment in the header
Program=5.0.100
Description=Invented traits for the Marsh Lamps setting. _
\t\tSecond half of the description.
Requires="Marsh Basics.gdf"

[AUTHOR]
****************************
//  Marsh Lamps
//  Written by nobody, for a test

[Advantages]
<Mental Advantages>
Tide Sense, 5/10, page(ML12), mods(Tide Sense), upto(3),_
\tgives(+1 to SK:Punting, +2 to "SK:Eel/Net Fishing"),_
\tdescription(You feel the tide turn, wherever you are (even indoors).)
// a comment between definitions
{Lamp Oil, Blessed}, 1, page(ML13)   // a comment after one
<Physical Advantages>
Webbed Hands (Marshfolk), 2, page(ML14), initmods(Slow, -10%, group(Webbed) |
\tSticky, +5%, group(Webbed))

[Skills]
<Boating>
Punting, DX/E, default(ST:DX - 4, SK:Rowing - 2), page(ML20)
Reed Weaving (Baskets), IQ/A, page(ML21), cat(Craft, Marsh)
#ReplaceTags in "SK:Rowing" with page(ML22)
#Clone "SK:Rowing" as "SK:Sculling"

[Modifiers]
<Tide Sense>
Moonlit Only, -20%, group(Tide Sense), page(ML12)

[Lists]
<Marsh Towns>
Sedgewick, Low Fen, "Upper, Lower and Middle Mire"
'''


class ReadTest(unittest.TestCase):
    def setUp(self):
        self.p = gdf.parse(SAMPLE, 'Marsh Lamps.gdf')

    def section(self, name):
        return [s for s in self.p['sections'] if s['name'] == name][0]['items']

    def test_header_joins_a_continued_line_and_skips_comments(self):
        self.assertEqual(self.p['header']['version'], '3')
        self.assertEqual(self.p['header']['requires'], '"Marsh Basics.gdf"')
        self.assertEqual(self.p['header']['description'],
                         'Invented traits for the Marsh Lamps setting. Second half of the description.')
        self.assertEqual(self.p['problems'], [])

    def test_author_lines_are_kept_as_written(self):
        self.assertEqual([i['text'] for i in self.section('Author')][1:3],
                         ['//  Marsh Lamps', '//  Written by nobody, for a test'])

    def test_a_definition_has_its_name_values_tags_category_and_prefix(self):
        tide = self.section('Advantages')[0]
        self.assertEqual((tide['item'], tide['name'], tide['nameext'], tide['category']),
                         ('AD:Tide Sense', 'Tide Sense', '', 'Mental Advantages'))
        self.assertEqual(tide['values'], ['5/10'])
        self.assertEqual(list(tide['tags']), ['page', 'mods', 'upto', 'gives', 'description'])
        self.assertEqual(tide['tags']['gives'], '+1 to SK:Punting, +2 to "SK:Eel/Net Fishing"')
        self.assertEqual(tide['tags']['description'], 'You feel the tide turn, wherever you are (even indoors).')
        self.assertEqual(tide['line'], 16)

    def test_a_name_with_a_comma_a_name_extension_and_a_line_ending_in_a_pipe(self):
        oil, webbed = self.section('Advantages')[1:]
        self.assertEqual((oil['name'], oil['values'], oil['tags']), ('Lamp Oil, Blessed', ['1'], {'page': 'ML13'}))
        self.assertEqual((webbed['item'], webbed['nameext'], webbed['category']),
                         ('AD:Webbed Hands (Marshfolk)', 'Marshfolk', 'Physical Advantages'))
        self.assertEqual(webbed['tags']['initmods'], 'Slow, -10%, group(Webbed) |Sticky, +5%, group(Webbed)')

    def test_commands_are_kept_and_never_applied(self):
        items = self.section('Skills')
        self.assertEqual([i.get('item') or i['command'] for i in items],
                         ['SK:Punting', 'SK:Reed Weaving (Baskets)', '#ReplaceTags', '#Clone'])
        self.assertEqual(items[2]['text'], 'in "SK:Rowing" with page(ML22)')
        self.assertEqual(gdf.counts(self.p), {'Advantages': 3, 'Skills': 2, 'commands': 2, 'Modifiers': 1})

    def test_modifiers_have_no_prefix_and_lists_keep_their_lines(self):
        self.assertEqual(self.section('Modifiers')[0]['item'], 'Moonlit Only')
        self.assertEqual(self.section('Lists')[0],
                         {'line': 38, 'category': 'Marsh Towns', 'text': 'Sedgewick, Low Fen, "Upper, Lower and Middle Mire"'})

    def test_index_records(self):
        recs = gdf.records(self.p)
        self.assertEqual(len(recs), 6)
        self.assertEqual(recs[3], {'item': 'SK:Punting', 'file': 'Marsh Lamps.gdf', 'section': 'Skills',
                                   'category': 'Boating', 'name': 'Punting', 'nameext': '', 'page': 'ML20', 'line': 27})

    def test_what_cannot_be_read_is_reported_with_its_line(self):
        p = gdf.parse('Version=3\nstray line\n[Skills]\nPunting, DX/E, page (ML20)\nRowing, DX/A, page(ML2\n'
                      '#Wibble "SK:Rowing"\n')
        self.assertEqual([(x['line'], x['why'].split(':')[0]) for x in p['problems']],
                         [(2, 'header line without ='), (4, 'text between tags that is not a tag'),
                          (5, 'brackets or quotes do not pair up'), (6, 'not a data file command the guide lists')])

    def test_a_file_without_the_encoding_line_is_read_as_windows_text(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'old.gdf')
            with open(path, 'wb') as f:
                f.write('Version=3\n[Skills]\nCafé Lore, IQ/E\n'.encode('cp1252'))
            self.assertEqual(gdf.parse(gdf.read_text(path))['sections'][0]['items'][0]['name'], 'Café Lore')

    def test_written_out_and_read_again_it_is_the_same(self):
        def content(p):
            return [[{k: v for k, v in it.items() if k != 'line'} for it in s['items']]
                    for s in p['sections'] if s['name'] != 'Author']
        again = gdf.parse(gdf.serialize(self.p), 'Marsh Lamps.gdf')
        self.assertEqual(content(again), content(self.p))
        self.assertEqual(again['header'], self.p['header'])


class WriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, 'library-data')
        self.entry('advantages', 'tide-sense', 'ML', [
            {'item': 'AD:Tide Sense', 'define': {'section': 'Advantages', 'category': ['Mental Advantages', 'Marsh'],
                                                 'values': ['5/10'], 'tags': {'page': 'ML12', 'upto': '3'}}}])
        self.entry('skills', 'punting', 'ML', [
            {'item': 'SK:Punting', 'define': {'section': 'Skills', 'category': 'Boating', 'values': ['DX/E'],
                                              'tags': {'default': 'ST:DX - 4', 'page': 'ML20'}}},
            {'item': 'SK:Rowing', 'file': 'Marsh Basics.gdf'}])          # a link, not a definition
        self.entry('skills', 'other-book', 'XX', [
            {'item': 'SK:Elsewhere', 'define': {'section': 'Skills', 'values': ['IQ/E'], 'tags': {}}}])

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, category, slug, source, gca):
        os.makedirs(os.path.join(self.data, category), exist_ok=True)
        with open(os.path.join(self.data, category, slug + '.json'), 'w', encoding='utf-8') as f:
            json.dump({'slug': slug, 'name': slug, 'source': source, 'gca': gca}, f)

    def run_write(self, *extra):
        out = os.path.join(self.tmp.name, 'Marsh Lamps.gdf')
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'gdf.py'), 'write', '--library-data', self.data,
                            '--source', 'ML', '--title', 'Marsh Lamps', '--date', '2026-01-02', '--out', out, *extra],
                           capture_output=True, text=True, encoding='utf-8')
        return r, out

    def test_a_sources_definitions_become_a_data_file_gca_can_read(self):
        r, out = self.run_write('--requires', 'Marsh Basics.gdf')
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, 'rb') as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b'Encoding=UTF-8\r\nVersion=3\r\n'))
        p = gdf.parse(gdf.read_text(out), 'Marsh Lamps.gdf')
        self.assertEqual(p['problems'], [])
        self.assertEqual(p['header']['requires'], '"Marsh Basics.gdf"')
        self.assertEqual([r_['item'] for r_ in gdf.records(p)], ['AD:Tide Sense', 'SK:Punting'])
        tide = p['sections'][1]['items'][0]
        self.assertEqual((tide['category'], tide['values'], tide['tags']),
                         ('Mental Advantages', ['5/10'], {'page': 'ML12', 'upto': '3', 'cat': 'Mental Advantages, Marsh'}))
        self.assertIn('* Do not edit this file by hand.', [i['text'] for i in p['sections'][0]['items']])
        self.assertEqual(json.loads(r.stdout)['entries'], ['advantages/tide-sense', 'skills/punting'])

    def test_a_definition_gca_would_misread_is_refused(self):
        self.entry('skills', 'bad', 'ML', [
            {'item': 'SK:Bad', 'define': {'section': 'Skills', 'values': ['IQ/E'], 'tags': {'page': 'ML(9'}}}])
        r, out = self.run_write()
        self.assertEqual(r.returncode, 1)
        self.assertIn('Bad: brackets or quotes do not pair up in page', r.stderr)
        self.assertFalse(os.path.exists(out))

    def test_a_definition_in_the_wrong_section_is_refused(self):
        self.entry('skills', 'bad', 'ML', [
            {'item': 'AD:Punting', 'define': {'section': 'Skills', 'values': ['DX/E'], 'tags': {}}}])
        r, _ = self.run_write()
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not carry the prefix of [Skills] (SK)", r.stderr)


if __name__ == '__main__':
    unittest.main()
