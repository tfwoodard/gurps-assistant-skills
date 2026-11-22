"""Tests for gca5.py, the GCA character file reader. The character here is invented.

Run: python -m unittest discover tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, '..', 'skills', 'gurps-character-sheet', 'scripts', 'gca5.py')
sys.path.insert(0, os.path.dirname(SCRIPT))
import gca5  # noqa: E402


def trait(kind, idkey, name, body):
    return f'<trait type="{kind}" idkey="{idkey}"><name>{name}</name>{body}</trait>'


def character(name, player='Sam'):
    attributes = (
        trait('Attributes', 1, 'ST', '<points>10</points><score>11</score><ref><mainwin>1</mainwin></ref>') +
        trait('Attributes', 2, 'DX', '<points>20</points><score>11</score><ref><mainwin>2</mainwin></ref>') +
        trait('Attributes', 3, '----------', '<points>0</points><score>0</score>') +
        trait('Attributes', 4, 'Lifting ST', '<points>0</points><score>11</score><hide>-1</hide>'))
    advantages = trait('Advantages', 10, 'Tide Sense', '''<points>8</points><level>2</level>
        <ref><page>ML12</page></ref>
        <modifiers count="1"><modifier idkey="11"><name>Moonlit Only</name><group>Tide Sense</group>
          <cost>-20%</cost><level>1</level><premodsvalue>-20%</premodsvalue><value>-20%</value><valuenum>-20</valuenum>
        </modifier></modifiers>''')
    skills = trait('Skills', 20, 'Reed Weaving', '''<nameext>Baskets</nameext><points>2</points><type>IQ/A</type>
        <step>-1</step><stepoff>IQ</stepoff><level>9</level><ref><page>ML21</page></ref>''')
    new_weapon = trait('Equipment', 30, 'Eel Spear', '''<cost>40</cost><count>1</count><weight>4</weight>
        <attackmodes count="2">
          <attackmode><name>Thrust</name><chardamage>1d+2</chardamage><chardamtype>imp</chardamtype>
            <charreach>1,2</charreach><charskillused>"SK:Spear"</charskillused><charskillscore>12</charskillscore></attackmode>
          <attackmode><name>Thrown</name><chardamage>1d+3</chardamage><chardamtype>imp</chardamtype>
            <charrangehalfdam>11</charrangehalfdam><charrangemax>16</charrangemax>
            <charskillused>"SK:Thrown Weapon (Spear)"</charskillused><charskillscore>10</charskillscore></attackmode>
        </attackmodes>''')
    old_weapon = trait('Equipment', 31, 'Mud Sling', '''<cost>20</cost><count>2</count><weight>0.5</weight>
        <weaponmodesdata><damage>sw</damage><chardamage>1d</chardamage><chardamtype>pi</chardamtype>
          <charskillused>"SK:Sling"</charskillused><charskillscore>8</charskillscore></weaponmodesdata>''')
    return f'''<character>
      <author><version>GCA5Engine, Version=5.0.0.1</version></author>
      <library><name>%user%\\marsh.gds</name><book>%sys%\\Marsh Basics.gdf</book><book>%user%\\Marsh Lamps.gdf</book></library>
      <name>{name}</name><player>{player}</player><bodytype>Humanoid</bodytype>
      <vitals><race>Marshfolk</race><age>30</age></vitals>
      <notes>Owes the ferryman.</notes>
      <traits>
        <attributes count="4">{attributes}</attributes>
        <advantages count="1">{advantages}</advantages>
        <skills count="1">{skills}</skills>
        <equipment count="2">{new_weapon}{old_weapon}</equipment>
      </traits>
      <campaign><name>Marsh Lamps</name><basetl>3</basetl><basepoints>40</basepoints><loggedpoints>3</loggedpoints>
        <otherpoints>0</otherpoints><totalpoints>43</totalpoints>
        <logentries count="1"><logentry><entrydate>01-02-2026</entrydate><campaigndate />
          <charpoints>3</charpoints><caption>The Drowned Stair</caption><notes /></logentry></logentries>
      </campaign>
    </character>'''


def write(folder, name, *chars):
    path = os.path.join(folder, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<gca5 xmlns="gca5">' + ''.join(chars) + '</gca5>')
    return path


class ReadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = write(self.tmp.name, 'kessa.gca5', character('Kessa of the Reeds'))
        self.rec = gca5.read(gca5.pick(gca5.characters(self.path), None))

    def tearDown(self):
        self.tmp.cleanup()

    def test_who_and_what_it_was_built_with(self):
        self.assertEqual((self.rec['name'], self.rec['player'], self.rec['vitals']),
                         ('Kessa of the Reeds', 'Sam', {'race': 'Marshfolk', 'age': '30'}))
        self.assertEqual(self.rec['built_with'], {'library': '%user%\\marsh.gds',
                                                  'books': ['%sys%\\Marsh Basics.gdf', '%user%\\Marsh Lamps.gdf']})
        self.assertEqual(self.rec['campaign']['basepoints'], 40)
        self.assertEqual(self.rec['log'][0]['points'], 3)

    def test_traits_carry_what_gca_saved(self):
        tide = self.rec['traits']['advantages'][0]
        self.assertEqual((tide['full_name'], tide['points'], tide['level'], tide['page']), ('Tide Sense', 8, 2, 'ML12'))
        self.assertEqual(tide['modifiers'], [{'name': 'Moonlit Only', 'value': '-20%', 'level': 1}])
        weave = self.rec['traits']['skills'][0]
        self.assertEqual((weave['full_name'], weave['type'], weave['level'], weave['relative']),
                         ('Reed Weaving (Baskets)', 'IQ/A', 9, 'IQ-1'))

    def test_attack_modes_in_the_current_and_the_older_layout(self):
        spear, sling = self.rec['traits']['equipment']
        self.assertEqual([m['name'] for m in spear['modes']], ['Thrust', 'Thrown'])
        self.assertEqual(spear['modes'][1]['charrangemax'], '16')
        self.assertEqual(sling['modes'], [{'chardamage': '1d', 'chardamtype': 'pi', 'charskillused': '"SK:Sling"',
                                           'charskillscore': '8'}])

    def test_the_only_sum_is_labelled_as_made_here(self):
        self.assertEqual(self.rec['points_summed_here'], {'attributes': 30, 'advantages': 8, 'skills': 2, 'total': 40})

    def test_the_sheet_shows_main_attributes_and_counts_what_it_leaves_out(self):
        md = gca5.sheet(self.rec)
        self.assertIn('| ST | 11 | 10 |', md)
        self.assertNotIn('Lifting ST', md)
        self.assertIn('2 traits GCA hides or uses only as dividers are not shown.', md)
        self.assertIn('- Tide Sense 2 (Moonlit Only, -20%) [8] (ML12)', md)
        self.assertIn('| Reed Weaving (Baskets) | IQ/A | 9 | IQ-1 | 2 | ML21 |', md)
        self.assertIn('| Eel Spear | Thrown | SK:Thrown Weapon (Spear) | 10 | 1d+3 imp | 11/16 |', md)
        self.assertIn('- 01-02-2026: The Drowned Stair, +3 points', md)
        self.assertIn('Built in GCA with: Marsh Basics.gdf, Marsh Lamps.gdf.', md)


class FileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def run_it(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, encoding='utf-8')

    def test_a_file_of_several_characters_needs_one_named(self):
        path = write(self.tmp.name, 'two.gca5', character('Kessa'), character('Old Bram', 'Jo'))
        self.assertEqual(self.run_it('list', path).stdout.splitlines(), ['Kessa\tSam', 'Old Bram\tJo'])
        r = self.run_it('read', path)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('name one with --character', r.stderr)
        self.assertEqual(json.loads(self.run_it('read', path, '--character', 'old bram').stdout)['player'], 'Jo')

    def test_a_party_file_lists_its_character_files(self):
        path = os.path.join(self.tmp.name, 'marsh.gca5party')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('C:\\chars\\Kessa.gca5\nC:\\chars\\Old Bram.gca5\n<gmconsole>\n  <cards count="2" />\n</gmconsole>\n')
        self.assertEqual(self.run_it('list', path).stdout.splitlines(), ['C:\\chars\\Kessa.gca5', 'C:\\chars\\Old Bram.gca5'])
        r = self.run_it('sheet', path)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('this is a party file', r.stderr)

    def test_sheet_is_written_to_a_file(self):
        path = write(self.tmp.name, 'kessa.gca5', character('Kessa'))
        out = os.path.join(self.tmp.name, 'kessa.md')
        self.assertEqual(self.run_it('sheet', path, '--out', out).returncode, 0)
        with open(out, encoding='utf-8') as f:
            self.assertTrue(f.read().startswith('# Kessa\n'))


if __name__ == '__main__':
    unittest.main()
