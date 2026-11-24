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

    def test_a_name_another_chapter_of_the_book_holds_is_an_error_until_the_plan_gives_a_slug(self):
        taken = {'rules': {'gift-list': ('ML', 'ch1')}, 'advantages': {'tide-sense': ('ML', 'ch2')}}
        _, report = convert_traits.convert_chapter(chapter(), json.loads(json.dumps(PLAN)), taken)
        self.assertEqual([e for e in report['errors'] if 'already has' in e],
                         ["rules/gift-list (p10): ML ch1 already has an entry rules/gift-list; give this one a `slug` in the "
                          "plan's entries (and a relation, if the two are read together)"])
        plan = json.loads(json.dumps(PLAN))
        plan['entries'] = {'rules/gift-list': {'slug': 'gift-list-ch2', 'relations': [{'role': 'distinct-from', 'to': 'rules/gift-list'}]}}
        entries, report = convert_traits.convert_chapter(chapter(), plan, taken)
        self.assertEqual(report['errors'], [])                   # tide-sense is this chapter's own: no error
        e = next(e for c, e in entries if e['name'] == 'Gift List')
        self.assertEqual((e['slug'], e['relations']), ('gift-list-ch2', [{'role': 'distinct-from', 'to': 'rules/gift-list'}]))

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


class SpellsTest(unittest.TestCase):
    LABELS = {'Duration': 'duration', 'Cost': 'cost', 'Base Cost': 'base_cost', 'Time to cast': 'time_to_cast',
              'Prerequisite': 'prerequisites', 'Duration, Cost, and Time to cast': ['duration', 'cost', 'time_to_cast']}

    def chapter(self):
        p = Page()
        p.line('FOG SPELLS', size=20.0, heading=2, bold=True)
        p.name('Thicken Fog')
        p.cost('Area')
        p.para('The fog grows thick over', 'the marsh.')
        p.para('Duration: 1 minute, or', 'until dawn.')
        p.para('Base Cost: 2. Cannot be', 'maintained.')
        p.name('Lift Fog (VH)')
        p.cost('Regular; Resisted by')
        p.cost('the fog’s Will')
        p.para('The fog lifts from the', 'water.')
        p.para('Duration, Cost, and Time to', 'cast: As for Thicken Fog.')
        p.para('Prerequisite: Thicken Fog', 'and Magery 1.')
        p.name('Fog Song')
        p.cost('Loud')
        p.para('You sing.')
        return {'lines': p.lines, 'regions': []}

    def plan(self):
        return {'source': 'ML', 'chapter': 'ch5', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'sections': [
            {'heading': 'Fog Spells', 'page': 10, 'traits': {'category': 'spells', 'kind': 'spell', 'line': 'spell',
                                                             'marks': {' (VH)': 'very_hard'}, 'labels': self.LABELS,
                                                             'fields': {'college': 'Fog'}, 'fields_from': 'end'}}]}

    def test_a_spells_class_what_resists_it_and_its_labelled_lines(self):
        entries, report = convert_traits.convert_chapter(self.chapter(), self.plan())
        self.assertEqual(report['errors'], ["p10: 'Fog Song': the line under its name, 'Loud', is not a spell class (and what resists it)"])
        by = {e['slug']: e for c, e in entries if c == 'spells'}
        self.assertEqual(by['thicken-fog']['fields'], {'kind': 'spell', 'very_hard': False, 'class': 'Area', 'college': 'Fog',
                                                       'duration': '1 minute, or until dawn.', 'base_cost': '2. Cannot be maintained.'})
        lift = by['lift-fog']['fields']
        self.assertEqual((lift['very_hard'], lift['printed_name'], lift['class'], lift['resisted']),
                         (True, 'Lift Fog (VH)', 'Regular', 'Resisted by the fog’s Will'))
        self.assertEqual((lift['duration'], lift['cost'], lift['time_to_cast'], lift['prerequisites']),
                         ('As for Thicken Fog.',) * 3 + ('Thicken Fog and Magery 1.',))


class TemplatesAndTalentsTest(unittest.TestCase):
    LABELS = {'Attributes': 'attributes', 'Advantages': 'advantages', 'Defaults': 'defaults'}

    def label_line(self, p, label, rest, gap=None):
        l = p.line(f'{label}: {rest}', gap=gap)
        l['spans'] = [{'text': f'{label}:', 'size': 9.5, 'bold': True, 'italic': True},
                      {'text': f' {rest}', 'size': 9.5, 'bold': False, 'italic': False}]
        return l

    def test_a_templates_points_and_its_flush_labelled_lines_with_hanging_lines_under_them(self):
        p = Page()
        p.line('SAMPLE KEEPERS', size=20.0, heading=2, bold=True)
        p.para('Some keepers.')
        p.name('Lamp Keeper')
        p.cost('60 points')
        p.para('You keep the lamp lit and', 'the boats safe.')
        self.label_line(p, 'Attributes', 'ST 10 [0]; DX 11')
        p.line('[20]; IQ 12 [40].', indent=12.0)
        self.label_line(p, 'Advantages', 'Night Vision 2 [2];')
        p.line('Lamp Sense [5].', indent=12.0)
        self.label_line(p, 'Note', 'Choose one more, or')
        p.line('two.', indent=12.0)
        plan = {'source': 'ML', 'chapter': 'ch7', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'sections': [
            {'heading': 'Sample Keepers', 'page': 10, 'traits': {'category': 'templates', 'kind': 'occupational',
                                                                 'line': 'points', 'labels': self.LABELS, 'fields_from': 'end'}}]}
        entries, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        self.assertEqual(report['errors'], [])
        e = next(e for c, e in entries if e['slug'] == 'lamp-keeper')
        self.assertEqual(e['fields'], {'kind': 'occupational', 'points': '60 points', 'attributes': 'ST 10 [0]; DX 11 [20]; IQ 12 [40].',
                                       'advantages': 'Night Vision 2 [2]; Lamp Sense [5].'})
        self.assertEqual(len(e['content']), 4)

    def test_a_heading_that_ends_a_trait_hands_what_follows_back_to_the_section(self):
        p = Page()
        p.line('FOG SIGHT', size=20.0, heading=2, bold=True)
        p.para('Seeing through fog.')
        p.name('Fog Sight Talent')
        p.cost('5 points/level')
        p.para('You see through fog.')
        p.name('Fog Sight Abilities')
        p.para('Fog Sight abilities: Lamp Sense.')
        plan = {'source': 'ML', 'chapter': 'ch6', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
                'sections': [{'heading': 'Fog Sight', 'page': 10, 'traits': {'category': 'advantages', 'kind': 'talent'}}],
                'trait_ends': [{'page': 10, 'text': 'Fog Sight Abilities'}]}
        entries, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        self.assertEqual(report['errors'], [])
        by = {e['slug']: e for c, e in entries}
        self.assertEqual([b.get('text') for b in by['fog-sight-talent']['content']], ['You see through fog.'])
        self.assertEqual([b.get('text') for b in by['fog-sight']['content']],
                         ['Seeing through fog.', 'Fog Sight Abilities', 'Fog Sight abilities: Lamp Sense.'])
        plan['trait_ends'].append({'page': 11, 'text': 'Nothing'})
        _, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        self.assertIn("plan trait_ends: no heading 'Nothing' on p11 after a trait", report['errors'])

    def test_labelled_paragraphs_split_into_entries_of_their_own(self):
        p = Page()
        p.line('SAMPLE KEEPERS', size=20.0, heading=2, bold=True)
        p.para('Some keepers.')
        p.name('Marsh Bodies')
        p.cost('Variable')
        p.para('Your body is marsh stuff,', 'all of it.')
        self.label_line(p, 'Body of Mud', 'Your body is mud,')
        p.line('wet mud.')
        p.para('It squelches when', 'you walk.')
        self.label_line(p, 'Body of Reed', 'Your body is reeds,')
        p.line('dry reeds.')
        self.label_line(p, 'Note', 'Rare, and')
        p.line('strange.')
        plan = {'source': 'ML', 'chapter': 'ch7', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [],
                'sections': [{'heading': 'Sample Keepers', 'page': 10, 'traits': {'category': 'templates', 'kind': 'meta-trait'}}],
                'split_labelled': {'templates/marsh-bodies': {'fields': {'kind': 'meta-trait'}, 'except': ['Note']}}}
        entries, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        self.assertEqual(report['errors'], [])
        by = {e['slug']: e for c, e in entries}
        self.assertEqual([b['text'] for b in by['marsh-bodies']['content']],
                         ['Your body is marsh stuff, all of it.', '***Note***:  Rare, and strange.'])
        self.assertEqual([b['text'] for b in by['body-of-mud']['content']], ['Your body is mud, wet mud.', 'It squelches when you walk.'])
        self.assertEqual((by['body-of-reed']['fields'], by['body-of-reed']['relations']),
                         ({'kind': 'meta-trait'}, [{'role': 'adds-to', 'to': 'templates/marsh-bodies'}]))
        self.assertEqual(report['split'], [{'entry': 'templates/marsh-bodies', 'into': ['Body of Mud', 'Body of Reed']}])

    def test_a_skills_own_labels_open_its_text_and_a_specialtys_are_passed_over(self):
        p = Page()
        p.line('KNOWLEDGE LIST', size=20.0, heading=2, bold=True)
        p.para('What keepers know.')
        p.name('Rowing')
        p.cost('DX/Easy')
        self.label_line(p, 'Defaults', 'DX-4 or Swimming-')
        p.line('4.')
        p.para('You row, with oars,', 'on water.')
        self.label_line(p, 'Punts', 'Flat boats moved')
        p.line('with a pole.')
        self.label_line(p, 'Defaults', 'Rowing-2 or')
        p.line('DX-5.')
        plan = {'source': 'ML', 'chapter': 'ch4', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'sections': [
            {'heading': 'Knowledge List', 'page': 10, 'traits': {'category': 'skills', 'kind': 'skill', 'line': 'skill',
                                                                 'labels': self.LABELS}}]}
        entries, report = convert_traits.convert_chapter({'lines': p.lines, 'regions': []}, plan)
        e = next(e for c, e in entries if e['slug'] == 'rowing')
        self.assertEqual(e['fields']['defaults'], 'DX-4 or Swimming-4.')
        self.assertEqual(report['labels_passed_over'], [{'entry': 'skills/rowing', 'labels': ['Defaults']}])


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

    def test_a_hanging_labelled_line_carries_on_over_a_column_turn_past_a_box(self):
        def labelled(p, label, rest, indent=0.0):
            l = p.line(f'{label}: {rest}', indent=indent)
            l['spans'] = [{'text': f'{label}:', 'size': 9.5, 'bold': True, 'italic': True},
                          {'text': f' {rest}', 'size': 9.5, 'bold': False, 'italic': False}]

        def build(p):
            p.line('A keeper of the marsh lamps.', indent=12.0)
            labelled(p, 'Attributes', 'ST 10 [0]; DX 11')
            p.line('[20]; IQ 10 [0]; HT', indent=12.0)
            p.line('11 [10]; Will', indent=12.0)                # breaks off mid-list at the column's foot
            p.at(column='left', y=300.0, box='10.1')
            p.line('A box set at the foot of the page.')
            p.line('Its own lines, in reading order here.')
            p.at(column='right', y=80.0)
            p.line('10 [0]; Per 10 [0].', indent=12.0)          # the hanging line, carried over
            labelled(p, 'Advantages', 'Lamp Sense [5].')
        self.assertEqual([m for _, m in self.marks(build)], [True, True, False, False, False, False, False, True])

    @staticmethod
    def styled(p, spans, indent=0.0):
        """A line of (text, bold, italic) runs."""
        l = p.line(' '.join(t for t, _, _ in spans), indent=indent)
        l['spans'] = [{'text': t, 'size': 9.5, 'bold': b, 'italic': i} for t, b, i in spans]
        return l

    def test_a_ladder_of_dash_labels_with_labels_of_another_style_inside_its_items(self):
        def build(p):
            p.para('How the lamps are rated:')
            self.styled(p, [('2 –', True, False), ('Dim.', False, True), ('Lit at dusk', False, False)])
            p.line('and put out at dawn.', indent=12.0)
            self.styled(p, [('Oil:', False, True), ('A pint a', False, False)], indent=12.0)   # inside the item
            p.line('night.', indent=12.0)
            self.styled(p, [('-1 –', True, False), ('Out.', False, True), ('Not lit.', False, False)])
            p.para('Keepers mark the rating', 'on the door.')                 # a paragraph after the ladder
        self.assertEqual([m for _, m in self.marks(build)], [True, True, False, False, False, True, True, False])

    def test_an_indented_label_of_the_items_own_style_starts_another_item(self):
        def build(p):
            self.styled(p, [('Default:', False, True), ('Rowing-2.', False, False)])
            self.styled(p, [('Punt:', False, True), ('Any flat boat.', False, False)], indent=12.0)
            self.styled(p, [('Skiff:', False, True), ('Any small boat', False, False)], indent=12.0)
            p.line('with oars.')
        self.assertEqual([m for _, m in self.marks(build)], [True, True, True, False])


class TwoSidebarsInOneFrameTest(unittest.TestCase):
    def test_a_heading_as_large_as_the_boxs_title_starts_another_entry(self):
        def l(text, baseline, size=9.5, heading=None):
            d = {'page': 10, 'column': 'full', 'box': '10.1', 'text': text, 'size': size, 'baseline': baseline,
                 'top': baseline - size, 'x0': 60.0, 'x1': 300.0, 'bold': bool(heading), 'italic': False, 'font': 'T',
                 'furniture': False, 'words': [[w, 60.0, 70.0] for w in text.split()],
                 'spans': [{'text': text, 'size': size, 'bold': bool(heading), 'italic': False}]}
            if heading:
                d['heading'] = heading
            return d
        doc = {'pages': [10], 'body_size': 9.5, 'gutters': {}, 'lines': [
            l('Gulls', 100.0, 14.0, 3), l('Gulls steal the keepers’ bread.', 116.0),
            l('Nesting', 130.0, 11.0, 4), l('They nest on the gallery rail.', 144.0),
            l('Fog Bells', 160.0, 14.0, 3), l('Ring the bell every minute in fog.', 176.0)],
            'regions': [{'id': '10.1', 'kind': 'box', 'page': 10, 'bbox': [50, 80, 320, 190]}]}
        plan = {'source': 'ML', 'chapter': 'ch3', 'name_size': 20.0, 'cost_size': 11.0, 'icons': [], 'indent': False}
        entries, report = convert_traits.convert_chapter(doc, plan)
        self.assertEqual(report['errors'], [])
        boxes = {e['slug']: e for c, e in entries if e['fields'].get('box')}
        self.assertEqual(sorted(boxes), ['fog-bells', 'gulls'])
        self.assertEqual([b.get('text') for b in boxes['gulls']['content']],
                         ['Gulls steal the keepers’ bread.', 'Nesting', 'They nest on the gallery rail.'])
        self.assertEqual([b.get('text') for b in boxes['fog-bells']['content']], ['Ring the bell every minute in fog.'])


def mini_line(text, baseline, size=9.5, heading=None, page=10, box=None):
    d = {'page': page, 'column': 'left', 'text': text, 'size': size, 'baseline': baseline, 'top': baseline - size,
         'x0': 60.0, 'x1': 200.0, 'bold': bool(heading), 'italic': False, 'font': 'T', 'furniture': False,
         'words': [[w, 60.0, 70.0] for w in text.split()],
         'spans': [{'text': text, 'size': size, 'bold': bool(heading), 'italic': False}]}
    if heading:
        d['heading'] = heading
    if box:
        d['box'] = box
    return d


class MixedListTest(unittest.TestCase):
    def doc(self):
        return {'pages': [10], 'body_size': 9.5, 'gutters': {}, 'regions': [], 'lines': [
            mini_line('LAMP FEATURES', 60.0, 20.0, 2),
            mini_line('Keepers differ in what they bring to the tower.', 80.0),
            mini_line('Lamp Sense', 100.0, 14.0, 3), mini_line('5 points', 114.0, 11.0, 4),
            mini_line('You know when a lamp is about to fail.', 128.0),
            mini_line('Fog Blindness', 150.0, 14.0, 3), mini_line('-10 points', 164.0, 11.0, 4),
            mini_line('You cannot see a lamp through fog.', 178.0),
            mini_line('Tower Height', 200.0, 14.0, 3), mini_line('0 points', 214.0, 11.0, 4),
            mini_line('Your tower is unusually tall.', 228.0)]}

    def test_a_list_of_both_sorts_takes_each_traits_category_from_its_cost(self):
        plan = {'source': 'ML', 'chapter': 'ch1', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'indent': False,
                'sections': [{'heading': 'Lamp Features', 'page': 10,
                              'traits': {'category': 'by-cost', 'kind': 'trait',
                                         'categories': {'Tower Height': 'disadvantages'}}}]}
        entries, report = convert_traits.convert_chapter(self.doc(), plan)
        self.assertEqual(report['errors'], [])
        got = {e['slug']: (c, e['fields']['kind']) for c, e in entries if c != 'rules'}
        self.assertEqual(got, {'lamp-sense': ('advantages', 'advantage'), 'fog-blindness': ('disadvantages', 'disadvantage'),
                               'tower-height': ('disadvantages', 'disadvantage')})

    def test_a_panels_lines_between_its_title_and_header_go_before_its_table(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_text_tables import line as text_line
        doc = self.doc()
        box = [mini_line('Lamp Table', 300.0, 14.0, box='10.1'), text_line(316.0, [(60, 'Lamps the keepers use.')]),
               text_line(330.0, [(60, 'Lamp'), (150, 'Oil')], True),
               text_line(341.0, [(60, 'Small'), (150, '1 pint')]), text_line(352.0, [(60, 'Great'), (150, '4 pints')])]
        for l in box[1:]:
            l.update(box='10.1', column='full')
        doc['lines'] += box
        doc['regions'] = [{'id': '10.1', 'kind': 'box', 'page': 10, 'bands': True, 'bbox': [50, 285, 300, 360]}]
        plan = {'source': 'ML', 'chapter': 'ch1', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'indent': False,
                'sections': [{'heading': 'Lamp Features', 'page': 10, 'traits': {'category': 'by-cost', 'kind': 'trait'}}],
                'boxes': {'10.1': {'into': 'rules/lamp-features', 'title_lines': 1, 'lead_lines': 1}}}
        entries, report = convert_traits.convert_chapter(doc, plan)
        self.assertEqual(report['errors'], [])
        owner = next(e for c, e in entries if e['slug'] == 'lamp-features')
        self.assertEqual([(b['type'], b.get('text') or b.get('title')) for b in owner['content']][-2:],
                         [('paragraph', 'Lamps the keepers use.'), ('table', 'Lamp Table')])

    def panel(self, boxplan, second=False):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from test_text_tables import line as text_line
        doc = self.doc()
        if second:                        # a second paragraph in the entry, after the one citing the table
            doc['lines'].insert(2, mini_line('Their lamps are of two kinds.', 97.0))
        box = [mini_line('Lamp Table', 300.0, 14.0, box='10.1'),
               text_line(316.0, [(60, 'Lamp'), (110, 'Oil'), (200, 'Keepers')], True),
               text_line(327.0, [(60, 'None'), (110, 'No lamp is lit.')]),
               text_line(338.0, [(60, 'Small'), (110, '1 pint'), (200, '1')]),
               text_line(349.0, [(60, 'Great'), (110, '4 pints'), (200, '2')]),
               text_line(363.0, [(60, 'Or count a pint for each foot of tower.')])]
        for l in box[1:]:
            l.update(box='10.1', column='full')
        doc['lines'] += box
        doc['regions'] = [{'id': '10.1', 'kind': 'box', 'page': 10, 'bands': True, 'bbox': [50, 285, 300, 370]}]
        plan = {'source': 'ML', 'chapter': 'ch1', 'name_size': 14.0, 'cost_size': 11.0, 'icons': [], 'indent': False,
                'sections': [{'heading': 'Lamp Features', 'page': 10, 'traits': {'category': 'by-cost', 'kind': 'trait'}}],
                'boxes': {'10.1': dict({'into': 'rules/lamp-features', 'title_lines': 1}, **boxplan)}}
        entries, report = convert_traits.convert_chapter(doc, plan)
        return next(e for c, e in entries if e['slug'] == 'lamp-features'), report

    def test_a_panels_last_lines_go_after_its_table_and_a_blank_it_prints_is_named(self):
        owner, report = self.panel({'after_lines': 1, 'empty_cells': [[1, 3]]})
        self.assertEqual(report['errors'], [])
        self.assertEqual([(b['type'], b.get('text') or b.get('title')) for b in owner['content']][-2:],
                         [('table', 'Lamp Table'), ('paragraph', 'Or count a pint for each foot of tower.')])
        self.assertEqual(owner['content'][-2]['rows'][0], ['None', 'No lamp is lit.', ''])
        self.assertEqual(report['tables'][0]['blank_as_printed'], [[1, 3]])

    def test_a_panels_table_goes_after_the_paragraph_the_plan_names(self):
        owner, report = self.panel({'after_lines': 1, 'empty_cells': [[1, 3]], 'after_text': 'Keepers differ'}, True)
        self.assertEqual(report['errors'], [])
        self.assertEqual([(b['type'], (b.get('text') or b.get('title'))[:14]) for b in owner['content']],
                         [('paragraph', 'Keepers differ'), ('table', 'Lamp Table'), ('paragraph', 'Or count a pin'),
                          ('paragraph', 'Their lamps ar')])
        self.assertEqual(owner['content'][1]['read_with'], ['before', 'after'])
        _, report = self.panel({'after_lines': 1, 'empty_cells': [[1, 3]], 'after_text': 'No such words'})
        self.assertTrue(any("0 paragraphs opening 'No such words'" in e for e in report['errors']), report['errors'])

    def test_a_blank_not_named_fails_and_so_does_one_named_that_is_not_blank(self):
        _, report = self.panel({'after_lines': 1})
        self.assertTrue(any('row 1 has nothing in column 3' in e for e in report['errors']), report['errors'])
        _, report = self.panel({'after_lines': 1, 'empty_cells': [[1, 3], [2, 3]]})
        self.assertTrue(any("row 2, column 3 is listed as printed blank, but it is not: '1'" in e for e in report['errors']),
                        report['errors'])

    def test_entries_of_one_name_are_told_apart_by_page_in_the_plan(self):
        doc = {'pages': [10, 11], 'body_size': 9.5, 'gutters': {}, 'lines': [
            mini_line('Lamp Log', 60.0, 14.0, 3, box='10.1'), mini_line('Day one: lit at dusk.', 76.0, box='10.1'),
            mini_line('Lamp Log (cont’d)', 60.0, 14.0, 3, page=11, box='11.1'),
            mini_line('Day two: fog.', 76.0, page=11, box='11.1'),
            mini_line('Lamp Log (cont’d)', 300.0, 14.0, 3, page=11, box='11.2'),
            mini_line('Day three: storm.', 316.0, page=11, box='11.2')],
            'regions': [{'id': '10.1', 'kind': 'box', 'page': 10, 'bbox': [50, 40, 300, 90]},
                        {'id': '11.1', 'kind': 'box', 'page': 11, 'bbox': [50, 40, 300, 90]},
                        {'id': '11.2', 'kind': 'box', 'page': 11, 'bbox': [50, 280, 300, 330]}]}
        plan = {'source': 'ML', 'chapter': 'ch1', 'name_size': 20.0, 'cost_size': 11.0, 'icons': [], 'indent': False,
                'entries': {'rules/lamp-log-contd@11': {'slug': 'lamp-log-contd-2', 'relations': [{'role': 'adds-to', 'to': 'rules/lamp-log'}]}}}
        entries, report = convert_traits.convert_chapter(doc, plan)
        self.assertTrue(any('two entries of this chapter take this slug' in e for e in report['errors']))
        # the page alone does not tell two on one page apart: the second takes its own key
        doc['lines'][4]['page'] = doc['lines'][5]['page'] = 12
        doc['regions'][2].update(id='12.1', page=12)
        for l in doc['lines'][4:]:
            l['box'] = '12.1'
        plan['entries']['rules/lamp-log-contd@12'] = {'slug': 'lamp-log-contd-3', 'relations': [{'role': 'adds-to', 'to': 'rules/lamp-log'}]}
        entries, report = convert_traits.convert_chapter(doc, plan)
        self.assertEqual(report['errors'], [])
        got = {e['slug']: e.get('relations') for c, e in entries}
        self.assertEqual(got, {'lamp-log': None, 'lamp-log-contd-2': [{'role': 'adds-to', 'to': 'rules/lamp-log'}],
                               'lamp-log-contd-3': [{'role': 'adds-to', 'to': 'rules/lamp-log'}]})


class HeadingLinesTest(unittest.TestCase):
    def head(self, text, size, baseline):
        return {'page': 10, 'column': 'right', 'text': text, 'size': size, 'baseline': baseline, 'heading': 2,
                'spans': [{'text': text, 'size': size, 'bold': True, 'italic': False}]}

    def runs(self, lines):
        return [(k, [l['text'] for l in run]) for k, run in convert_traits.group_headings(lines, lambda l: bool(l.get('heading')))]

    def test_a_line_of_joining_words_set_smaller_joins_the_lines_either_side(self):
        lines = [self.head('LAMPS', 20.0, 70.0), self.head('AND', 15.0, 90.0), self.head('LANTERNS', 20.0, 110.0)]
        self.assertEqual(self.runs(lines), [('heading', ['LAMPS', 'AND', 'LANTERNS'])])
        self.assertEqual(convert_traits.heading_text(convert_traits.group_headings(lines, lambda l: True)[0][1]),
                         'LAMPS AND LANTERNS')

    def test_a_smaller_heading_of_its_own_stays_apart(self):
        lines = [self.head('LAMPS', 20.0, 70.0), self.head('Wicks', 15.0, 90.0), self.head('LANTERNS', 20.0, 110.0)]
        self.assertEqual(self.runs(lines), [('heading', ['LAMPS']), ('heading', ['Wicks']), ('heading', ['LANTERNS'])])


if __name__ == '__main__':
    unittest.main()
