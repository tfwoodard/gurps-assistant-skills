"""Tests for convert_traits.py and entry_text.mark_paragraphs(), on an invented chapter given as the
lines pdf_layout.py would read from it.

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
SCRIPTS = os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts')
sys.path.insert(0, SCRIPTS)
import convert_traits  # noqa: E402
import entry_text  # noqa: E402

LEFT, RIGHT = 60.0, 240.0          # the two columns' left edges; each is 160 points wide


class Page:
    """Builds lines the way pdf_layout.py gives them: body lines 11 points apart, a paragraph's
    first line set in by 12."""
    def __init__(self):
        self.lines = []
        self.page, self.column, self.x, self.y, self.box = 10, 'left', LEFT, 80.0, None

    def at(self, page=None, column=None, y=None, box=None):
        if page:
            self.page = page
        if column:
            self.column, self.x = column, {'left': LEFT, 'right': RIGHT}[column]
        if y is not None:
            self.y = y
        self.box = box
        return self

    def line(self, text, size=9.5, heading=None, bold=False, indent=0.0, right=False, gap=None, italic=False,
             **extra):
        width = 0.5 * size * len(text)
        x0 = self.x + 160 - width if right else self.x + indent
        self.y += gap if gap is not None else (11.0 if size < 10 else size + 6)
        words = [[m.group(), round(x0 + 0.5 * size * m.start(), 1), round(x0 + 0.5 * size * m.end(), 1)]
                 for m in re.finditer(r'\S+', text)]
        l = {'page': self.page, 'column': self.column, 'top': self.y - size, 'baseline': self.y, 'x0': x0,
             'x1': x0 + width, 'text': text, 'size': size, 'bold': bold, 'italic': False, 'font': 'Test',
             'spans': [{'text': text, 'size': size, 'bold': bold, 'italic': False}], 'words': words,
             'furniture': False}
        if heading:
            l['heading'] = heading
        if self.box:
            l['box'] = self.box
        l.update(extra)
        self.lines.append(l)
        return l

    def para(self, *texts):
        for i, t in enumerate(texts):
            self.line(t, indent=12.0 if i == 0 else 0.0)

    def name(self, text):
        return self.line(text, size=14.0, heading=3, bold=True)

    def cost(self, text):
        return self.line(text, size=11.0, heading=4, bold=True, right=True, gap=13.0)


def chapter():
    p = Page()
    p.line('Gifts are what the marsh gives.', indent=12.0)             # before any heading
    p.line('MARSH GIFTS', size=20.0, heading=2, bold=True)
    p.para('Every keeper has one or two', 'of these.')
    p.line('GIFT LIST', size=20.0, heading=2, bold=True)
    p.para('The gifts, in order.')
    p.name('Tide Sense [mental]')
    p.cost('5 points/level')
    p.para('You feel the tide turn, wher-', 'ever you are.')
    p.para('Each level adds a mile.')
    p.line('Special Limitations', size=11.0, heading=4, bold=True)        # a heading in the trait's text
    p.para('Moonlit Only: Works by', 'moonlight. -20%.')
    p.name('Webbed Hands')                                               # its icons turned over to a second line
    p.line('[physical] [exotic]', size=14.0, heading=3, gap=15.0)
    p.cost('2 points')
    p.para('You swim well. Row one       3 yards', 'and so on.')
    p.at(column='right', y=80.0)
    p.para('carries on in the next', 'column.')                           # Webbed Hands, across the column break
    p.name('Marsh Rank [social]')
    p.cost('see Rank, p. 29')
    p.name('Eel Speech [mental]/[physical] [supernatural]')
    p.cost('10 points + 2 points per')                                    # a cost set over two lines
    p.cost('eel in the shoal')
    p.para('Eels listen to you.')
    p.line('FLAWS', size=20.0, heading=2, bold=True)
    p.name('Moonlit Only [attack]')
    p.cost('-20%')
    p.para('The gift works by moonlight.')
    p.name('Tide Sense')                                                 # the same name again, as a flaw
    p.cost('-10%')
    p.para('Only at the turn of the tide.')
    p.line('BOAT', size=14.0, heading=3, bold=True)                      # lettering in a picture
    p.at(box='10.1', y=500.0)
    p.line('Fog Rules', size=20.0, heading=2, bold=True)
    p.para('In fog, every gift is at -2.')
    p.at(box=None)
    p.line('The marsh gives and the marsh', size=14.0, aside=True)        # a pull quote
    return {'lines': p.lines, 'regions': [{'id': '10.1', 'kind': 'box', 'page': 10, 'bbox': [50, 480, 400, 560]}]}


PLAN = {'source': 'ML', 'chapter': 'ch2', 'name_size': 14.0, 'cost_size': 11.0,
        'icons': ['exotic', 'mental', 'physical', 'social', 'supernatural', 'attack'],
        'intro': {'name': 'Gifts'},
        'sections': [{'heading': 'Gift List', 'page': 10, 'traits': {'category': 'advantages', 'kind': 'advantage'}},
                     {'heading': 'Flaws', 'page': 10, 'traits': {'category': 'modifiers', 'kind': 'limitation'}}],
        'rename': [{'page': 10, 'name': 'Tide Sense', 'section': 'Flaws', 'to': 'Tide Sense (Limitation)'}],
        'leave_out_lines': [{'page': 10, 'text': 'BOAT', 'why': 'lettering in the picture'}],
        'boxes': {'10.1': {'adds_to': 'advantages/tide-sense'}}}


class ConvertTest(unittest.TestCase):
    def setUp(self):
        self.entries, self.report = convert_traits.convert_chapter(chapter(), json.loads(json.dumps(PLAN)))
        self.by = {f'{c}/{e["slug"]}': e for c, e in self.entries}

    def test_it_converts_without_errors_and_finds_every_entry(self):
        self.assertEqual(self.report['errors'], [])
        self.assertEqual(sorted(self.by), [
            'advantages/eel-speech', 'advantages/marsh-rank', 'advantages/tide-sense', 'advantages/webbed-hands',
            'modifiers/moonlit-only', 'modifiers/tide-sense-limitation',
            'rules/fog-rules', 'rules/gift-list', 'rules/gifts', 'rules/marsh-gifts'])
        self.assertEqual(self.report['counts'], {'rules': 4, 'advantages': 4, 'modifiers': 2})

    def test_a_trait_has_its_name_types_cost_and_text(self):
        e = self.by['advantages/tide-sense']
        self.assertEqual((e['name'], e['page'], e['section'], e['source'], e['chapter']),
                         ('Tide Sense', 10, 'Gift List', 'ML', 'ch2'))
        self.assertEqual(e['fields'], {'kind': 'advantage', 'types': ['mental'], 'cost': '5 points/level', 'leveled': True})
        self.assertEqual([b['type'] for b in e['content']], ['paragraph', 'paragraph', 'heading', 'paragraph'])
        self.assertEqual(e['content'][1]['text'], 'Each level adds a mile.')
        self.assertEqual(e['content'][2]['text'], 'Special Limitations')
        self.assertEqual(e['content'][3]['text'], 'Moonlit Only: Works by moonlight. -20%.')

    def test_icons_on_a_second_line_and_text_across_a_column_break(self):
        e = self.by['advantages/webbed-hands']
        self.assertEqual(e['fields'], {'kind': 'advantage', 'types': ['physical', 'exotic'], 'cost': '2 points', 'leveled': False})
        self.assertEqual([b['text'] for b in e['content']],
                         ['You swim well. Row one       3 yards and so on.', 'carries on in the next column.'])

    def test_a_pointer_a_two_line_cost_and_either_or_types(self):
        self.assertEqual(self.by['advantages/marsh-rank']['fields'], {'kind': 'advantage', 'types': ['social'], 'see': 'see Rank, p. 29'})
        self.assertEqual(self.by['advantages/marsh-rank']['content'], [])
        eel = self.by['advantages/eel-speech']['fields']
        self.assertEqual(eel['cost'], '10 points + 2 points per eel in the shoal')
        self.assertEqual((eel['types'], eel['types_printed']),
                         (['mental', 'physical', 'supernatural'], '[mental]/[physical] [supernatural]'))

    def test_a_renamed_trait_keeps_its_printed_name(self):
        e = self.by['modifiers/tide-sense-limitation']
        self.assertEqual((e['name'], e['fields']['printed_name'], e['fields']['kind'], e['fields']['cost']),
                         ('Tide Sense (Limitation)', 'Tide Sense', 'limitation', '-10%'))

    def test_sections_the_intro_and_a_box_are_rules_entries(self):
        self.assertEqual(self.by['rules/gifts']['content'][0]['text'], 'Gifts are what the marsh gives.')
        self.assertEqual(self.by['rules/marsh-gifts']['content'][0]['text'], 'Every keeper has one or two of these.')
        self.assertEqual(self.by['rules/gift-list']['content'][0]['text'], 'The gifts, in order.')
        fog = self.by['rules/fog-rules']
        self.assertEqual((fog['name'], fog['fields'], fog['relations']),
                         ('Fog Rules', {'box': True}, [{'role': 'adds-to', 'to': 'advantages/tide-sense'}]))

    def test_what_is_left_out_is_listed_with_why(self):
        self.assertEqual([(x['text'], x['why']) for x in self.report['left_out']],
                         [('The marsh gives and the marsh', 'pull quote'), ('BOAT', 'lettering in the picture'),
                          ('FLAWS', 'a heading with nothing under it but other entries')])

    def test_a_line_spaced_like_a_table_row_and_a_word_joined_across_a_line_end_are_reported(self):
        self.assertEqual([(t['entry'], t['text']) for t in self.report['table_like']],
                         [('advantages/webbed-hands', 'You swim well. Row one       3 yards')])
        self.assertEqual(self.report['questions'], [])
        self.assertEqual(self.report['dehyphenated'], [{'entry': 'advantages/tide-sense', 'from': 'wher-ever',
                                                        'to': 'wherever', 'why': 'a half is not a word by itself'}])
        self.assertEqual(self.by['advantages/tide-sense']['content'][0]['text'], 'You feel the tide turn, wherever you are.')

    def test_the_plans_whole_words_and_the_books_word_list_settle_broken_words(self):
        p = Page()
        p.line('GIFT LIST', size=20.0, heading=2, bold=True)
        p.para('The gifts.')
        p.name('Far Call')
        p.cost('Variable')
        p.para('Even the mail-', 'room clerk hears a near-', 'perfect call, mean-', 'ing yours, at second-', 'hand.')
        plan = {'source': 'ML', 'chapter': 'ch2', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
                'whole_words': ['mailroom'], 'hyphenated_words': ['second-hand'],
                'sections': [{'heading': 'Gift List', 'page': 10, 'traits': {'category': 'advantages', 'kind': 'advantage'}}]}
        doc = {'lines': p.lines, 'regions': []}
        entries, report = convert_traits.convert_chapter(doc, plan, None, {'mail', 'room', 'near', 'perfect', 'meaning'},
                                                         {'secondhand'})
        e = next(e for c, e in entries if e['slug'] == 'far-call')
        self.assertEqual(e['content'][0]['text'],
                         'Even the mailroom clerk hears a near-perfect call, meaning yours, at second-hand.')
        self.assertEqual(report['questions'], [])

    def test_a_name_with_no_cost_and_plan_lines_that_match_nothing_are_errors(self):
        doc = chapter()
        doc['lines'] = [l for l in doc['lines'] if l['text'] != '2 points']
        plan = json.loads(json.dumps(PLAN))
        plan['sections'].append({'heading': 'Curses', 'page': 12, 'traits': {'category': 'disadvantages', 'kind': 'disadvantage'}})
        plan['boxes']['11.1'] = {'leave_out': 'x'}
        plan['rename'].append({'page': 10, 'name': 'Mud Sense', 'to': 'Mud Sense (Flaw)'})
        _, report = convert_traits.convert_chapter(doc, plan)
        text = '\n'.join(report['errors'])
        self.assertIn("p10: 'Webbed Hands' has no cost line under its name", text)
        self.assertIn("plan section 'Curses' (p12) matches no heading", text)
        self.assertIn('plan box 11.1 is not a box in the layout', text)
        self.assertIn("plan rename: no trait 'Mud Sense' on p10", text)

    def test_two_traits_of_one_name_in_one_category_are_an_error_until_one_is_renamed(self):
        plan = json.loads(json.dumps(PLAN))
        plan['sections'][1]['traits'] = {'category': 'advantages', 'kind': 'advantage'}
        plan['rename'] = []
        _, report = convert_traits.convert_chapter(chapter(), plan)
        self.assertTrue(any('advantages/tide-sense: two entries of this chapter take this slug' in e for e in report['errors']))

    def test_one_name_for_an_enhancement_and_a_limitation_is_kept_and_told_apart_by_kind(self):
        plan = json.loads(json.dumps(PLAN))
        plan['rename'] = []
        plan['sections'].insert(1, {'heading': 'Marsh Gifts', 'page': 10, 'traits': {'category': 'modifiers', 'kind': 'enhancement'}})
        doc = chapter()
        i = next(k for k, l in enumerate(doc['lines']) if l['text'] == 'GIFT LIST')
        extra = Page().at(y=doc['lines'][i - 1]['baseline'])
        extra.name('Tide Sense')
        extra.cost('+10%')
        extra.para('Works at any tide.')
        doc['lines'][i:i] = extra.lines
        entries, report = convert_traits.convert_chapter(doc, plan)
        self.assertEqual(report['errors'], [])
        mods = {e['slug']: e for c, e in entries if c == 'modifiers' and e['name'] == 'Tide Sense'}
        self.assertEqual(sorted(mods), ['tide-sense', 'tide-sense-limitation'])
        self.assertEqual(mods['tide-sense']['fields']['kind'], 'enhancement')
        self.assertEqual(mods['tide-sense-limitation']['relations'], [{'role': 'distinct-from', 'to': 'modifiers/tide-sense'}])
        self.assertEqual(report['same_name'], [{'entry': 'modifiers/tide-sense-limitation', 'same_name_as': 'modifiers/tide-sense',
                                                'told_apart_by': 'kind: limitation / enhancement'}])

    def test_a_name_another_source_holds_is_a_version_of_it(self):
        entries, report = convert_traits.convert_chapter(chapter(), json.loads(json.dumps(PLAN)),
                                                         {'advantages': {'tide-sense': 'XX'}})
        e = next(e for c, e in entries if e['name'] == 'Tide Sense')
        self.assertEqual((e['slug'], e['relations']), ('tide-sense-ml', [{'role': 'version-of', 'to': 'advantages/tide-sense'}]))
        self.assertEqual(report['same_name'], [{'entry': 'advantages/tide-sense', 'held_by': 'XX'}])


class TableInTextTest(unittest.TestCase):
    def test_a_table_in_a_traits_text_says_which_paragraphs_it_is_read_with(self):
        p = Page()
        p.line('GIFT LIST', size=20.0, heading=2, bold=True)
        p.para('The gifts.')
        p.name('Far Call')
        p.cost('Variable')
        p.para('The cost depends on the reach:')
        p.line('Reach            Cost', bold=True, italic=True, gap=17.0)
        p.line('1 mile           2 points')
        p.line('9 miles          5 points')
        p.line('Further reach doubles the cost.', indent=12.0, gap=17.0)
        for l in p.lines:
            if l['text'].startswith('Reach'):
                l['italic'] = True
                l['spans'][0]['italic'] = True
        plan = {'source': 'ML', 'chapter': 'ch2', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
                'sections': [{'heading': 'Gift List', 'page': 10, 'traits': {'category': 'advantages', 'kind': 'advantage'}}]}
        entries, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        self.assertEqual(report['errors'], [])
        e = next(e for c, e in entries if e['slug'] == 'far-call')
        self.assertEqual([b['type'] for b in e['content']], ['paragraph', 'table', 'paragraph'])
        table = e['content'][1]
        self.assertEqual((table['columns'], table['rows'], table['read_with']),
                         (['Reach', 'Cost'], [['1 mile', '2 points'], ['9 miles', '5 points']], ['before', 'after']))
        self.assertEqual(e['content'][2]['text'], 'Further reach doubles the cost.')
        self.assertEqual(report['table_like'], [])


class PrintedTwiceTest(unittest.TestCase):
    def test_a_trait_printed_twice_in_a_chapter_keeps_its_name_and_is_marked_a_reprint(self):
        p = Page()
        for title in ('WET KNACKS', 'DRY KNACKS'):
            p.line(title, size=20.0, heading=2, bold=True)
            p.para('Some knacks.')
            p.line('Small Habit', size=11.0, heading=4, bold=True)
            p.para('You may take a habit as a knack.')
        knack = {'category': 'disadvantages', 'kind': 'quirk', 'no_cost_line': True, 'name_size': 11.0,
                 'fields': {'cost': '-1 point'}}
        plan = {'source': 'ML', 'chapter': 'ch3', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
                'sections': [{'heading': 'Wet Knacks', 'page': 10, 'traits': dict(knack, fields={'cost': '-1 point', 'types': ['wet']})},
                             {'heading': 'Dry Knacks', 'page': 10, 'traits': dict(knack, fields={'cost': '-1 point', 'types': ['dry']})}],
                'rename': [{'page': 10, 'name': 'Small Habit', 'section': 'Dry Knacks', 'slug': 'small-habit-dry',
                            'relation': {'role': 'reprint-of', 'to': 'disadvantages/small-habit'}}]}
        entries, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        self.assertEqual(report['errors'], [])
        habits = {e['slug']: e for c, e in entries if e['name'] == 'Small Habit'}
        self.assertEqual(sorted(habits), ['small-habit', 'small-habit-dry'])
        self.assertEqual(habits['small-habit-dry']['relations'], [{'role': 'reprint-of', 'to': 'disadvantages/small-habit'}])
        self.assertEqual((habits['small-habit']['fields']['types'], habits['small-habit-dry']['fields']['types']), (['wet'], ['dry']))
        self.assertNotIn('printed_name', habits['small-habit-dry']['fields'])


class SkillsTest(unittest.TestCase):
    LABELS = {'Defaults': 'defaults', 'Default': 'defaults', 'Prerequisites': 'prerequisites'}

    def chapter(self):
        p = Page()
        p.line('KNOWLEDGE LIST', size=20.0, heading=2, bold=True)
        p.para('What keepers know.')
        p.name('Lamp Tending/TL†')
        p.cost('IQ/Average')
        p.para('Defaults: IQ-5 or Wick Lore (same)-', '4.')
        p.para('Prerequisites: Wick Lore.')
        p.para('You keep a lamp lit.')
        p.name('Rowing')
        p.cost('DX or HT/Easy')
        p.para('Default: DX-4.')
        p.para('You row.')
        p.name('Oar Craft')
        p.cost('see Rowing, above')
        p.line('TRICKS', size=20.0, heading=2, bold=True)
        p.name('Quick Trim*')
        p.cost('Hard')
        p.para('Default: Lamp Tending-3.')
        p.para('You trim a wick in a second.')
        return {'lines': p.lines, 'regions': []}

    def plan(self):
        return {'source': 'ML', 'chapter': 'ch4', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'sections': [
            {'heading': 'Knowledge List', 'page': 10, 'traits': {'category': 'skills', 'kind': 'skill', 'line': 'skill',
                                                                 'marks': {'†': 'specialties', '/TL': 'tl'}, 'labels': self.LABELS}},
            {'heading': 'Tricks', 'page': 10, 'traits': {'category': 'skills', 'kind': 'technique', 'line': 'technique',
                                                         'marks': {'*': 'starred'}, 'labels': self.LABELS}}]}

    def test_a_skills_line_marks_and_labelled_paragraphs_become_fields(self):
        entries, report = convert_traits.convert_chapter(self.chapter(), self.plan())
        self.assertEqual(report['errors'], [])
        by = {e['slug']: e for c, e in entries if c == 'skills'}
        self.assertEqual(by['lamp-tending']['name'], 'Lamp Tending')
        self.assertEqual(by['lamp-tending']['fields'], {
            'kind': 'skill', 'specialties': True, 'tl': True, 'printed_name': 'Lamp Tending/TL†', 'attribute': 'IQ',
            'difficulty': 'Average', 'defaults': 'IQ-5 or Wick Lore (same)-4.', 'prerequisites': 'Wick Lore.'})
        self.assertEqual([b['text'] for b in by['lamp-tending']['content']],
                         ['Defaults: IQ-5 or Wick Lore (same)-4.', 'Prerequisites: Wick Lore.', 'You keep a lamp lit.'])
        self.assertEqual(by['rowing']['fields'], {'kind': 'skill', 'specialties': False, 'tl': False,
                                                  'attribute': 'DX or HT', 'difficulty': 'Easy', 'defaults': 'DX-4.'})
        self.assertEqual(by['oar-craft']['fields'], {'kind': 'skill', 'specialties': False, 'tl': False, 'see': 'see Rowing, above'})
        self.assertEqual(by['quick-trim']['fields'], {'kind': 'technique', 'starred': True, 'printed_name': 'Quick Trim*',
                                                      'difficulty': 'Hard', 'defaults': 'Lamp Tending-3.'})
        self.assertEqual(report['hyphens_kept'][0]['why'], 'a figure or an abbreviation')

    def test_a_line_that_is_no_attribute_and_difficulty_is_an_error(self):
        doc = self.chapter()
        next(l for l in doc['lines'] if l['text'] == 'IQ/Average')['text'] = 'Quite hard'
        _, report = convert_traits.convert_chapter(doc, self.plan())
        self.assertIn("p10: 'Lamp Tending': the line under its name, 'Quite hard', is not an attribute and a difficulty",
                      report['errors'])


class NoCostLineTest(unittest.TestCase):
    def test_a_list_whose_text_gives_one_cost_for_all_takes_it_from_the_plan(self):
        p = Page()
        p.line('KNACKS', size=20.0, heading=2, bold=True)
        p.para('Every knack costs 1 point.')
        p.line('Dry Feet [physical]', size=11.0, heading=4, bold=True)
        p.para('Your boots never leak.')
        p.line('Loud Whistle', size=11.0, heading=4, bold=True)
        p.para('Heard across the fen.')
        plan = {'source': 'ML', 'chapter': 'ch2', 'name_size': 14.0, 'cost_size': 11.0, 'icons': ['physical'],
                'sections': [{'heading': 'Knacks', 'page': 10, 'traits': {
                    'category': 'advantages', 'kind': 'perk', 'no_cost_line': True, 'name_size': 11.0,
                    'fields': {'cost': '1 point', 'leveled': False}}}]}
        entries, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        self.assertEqual(report['errors'], [])
        by = {f'{c}/{e["slug"]}': e for c, e in entries}
        self.assertEqual(sorted(by), ['advantages/dry-feet', 'advantages/loud-whistle', 'rules/knacks'])
        self.assertEqual(by['advantages/dry-feet']['fields'],
                         {'kind': 'perk', 'types': ['physical'], 'cost': '1 point', 'leveled': False})
        self.assertEqual(by['advantages/loud-whistle']['content'][0]['text'], 'Heard across the fen.')


class CommandTest(unittest.TestCase):
    def test_it_writes_entries_pages_records_and_a_report_that_cover_every_word(self):
        with tempfile.TemporaryDirectory() as d:
            layout, plan, out = os.path.join(d, 'layout.json'), os.path.join(d, 'plan.json'), os.path.join(d, 'out')
            with open(layout, 'w', encoding='utf-8') as f:
                json.dump(chapter(), f)
            with open(plan, 'w', encoding='utf-8') as f:
                json.dump(PLAN, f)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'convert_traits.py'), layout, '--plan', plan,
                                '--out', out], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(r.returncode, 0, r.stderr)
            names = sorted(os.listdir(out))
            self.assertIn('advantages--tide-sense.json', names)
            self.assertIn('advantages--tide-sense.md', names)
            with open(os.path.join(out, '_records.json'), encoding='utf-8') as f:
                rec = next(x for x in json.load(f) if x['slug'] == 'tide-sense')
            self.assertEqual((rec['_category'], rec['kind'], rec['cost'], rec['types']),
                             ('advantages', 'advantage', '5 points/level', ['mental']))
            with open(os.path.join(out, 'advantages--tide-sense.md'), encoding='utf-8') as f:
                md = f.read()
            self.assertIn('cost: 5 points/level', md)
            self.assertIn('# Tide Sense', md)
            c = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'check_coverage.py'), layout, out],
                               capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(c.returncode, 0, c.stdout)
            self.assertIn('every word of', c.stdout)


class ParagraphTest(unittest.TestCase):
    def marks(self, build):
        p = Page()
        build(p)
        return [(l['text'], l['para']) for l in entry_text.mark_paragraphs(p.lines)]

    def test_an_indented_first_line_starts_a_paragraph(self):
        def build(p):
            p.para('The tide comes in', 'at dusk.')
            p.para('It goes out', 'at dawn.')
        self.assertEqual(self.marks(build), [('The tide comes in', True), ('at dusk.', False),
                                             ('It goes out', True), ('at dawn.', False)])

    def test_one_line_paragraphs_one_after_another(self):
        def build(p):
            p.para('Row softly.')
            p.para('Row quickly.')
            p.para('Row on, and on,', 'and on.')
        self.assertEqual([m for _, m in self.marks(build)], [True, True, True, False])

    def test_lines_stepping_round_a_picture_are_not_paragraphs(self):
        def build(p):
            p.line('The lamp stands on the')
            p.line('rock, and the keeper', indent=12.0)        # set in, but the sentence runs on
            p.line('climbs to it by a')
            p.line('ladder.')
        self.assertEqual([m for _, m in self.marks(build)], [False, False, False, False])

    def test_a_column_that_opens_without_an_indent_carries_on(self):
        def build(p):
            p.para('The keeper climbs the', 'stair and trims the')
            p.at(column='right', y=80.0)
            p.line('wick before dusk.')
            p.para('Then the bell rings.')
        self.assertEqual([m for _, m in self.marks(build)], [True, False, False, True])


if __name__ == '__main__':
    unittest.main()
