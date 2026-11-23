"""Tests for how words broken at a line's end are joined (entry_text.join_lines, known, vocabulary)
and for book_words.py's word list. All words are ordinary English or invented.

Run: python -m unittest discover tests
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'skills', 'gurps-import', 'scripts'))
import book_words  # noqa: E402
import entry_text  # noqa: E402

VOCAB = {'report', 'tune', 'meaning', 'self-aware', 'near', 'perfect', 'noise', 'less', 'mail', 'room', 'man-made',
         'manmade', 'fine', 'keeper', 'lamp', 'the', 'marsh'}


def join(first, second, vocab=VOCAB):
    report = {'questions': []}
    return entry_text.join_lines([first, second], report, 'rules/x', vocab), report


class JoinTest(unittest.TestCase):
    def test_a_word_the_book_prints_whole_loses_its_hyphen(self):
        text, report = join('It has mean-', 'ing here.')
        self.assertEqual(text, 'It has meaning here.')
        self.assertEqual(report['dehyphenated'], [{'entry': 'rules/x', 'from': 'mean-ing', 'to': 'meaning'}])
        self.assertEqual(report['questions'], [])

    def test_a_word_whose_kin_the_book_prints_loses_it_too(self):
        self.assertEqual(join('He was report-', 'ing to the keeper.')[0], 'He was reporting to the keeper.')
        self.assertEqual(join('It needs fine tun-', 'ing first.')[0], 'It needs fine tuning first.')

    def test_a_form_the_book_prints_hyphenated_keeps_it(self):
        text, report = join('She is self-', 'aware now.')
        self.assertEqual(text, 'She is self-aware now.')
        self.assertEqual(report['hyphens_kept'][0]['why'], 'the book prints it hyphenated elsewhere')

    def test_figures_and_abbreviations_keep_it(self):
        for first, second, joined in (('a 12-', 'hour sleep', 'a 12-hour sleep'), ('see pp. 242-', '253 for more', 'see pp. 242-253 for more'),
                                      ('against HT-', '5 is worth', 'against HT-5 is worth')):
            text, report = join(first, second)
            self.assertEqual(text, joined)
            self.assertEqual(report['hyphens_kept'][0]['why'], 'a figure or an abbreviation')

    def test_a_half_that_is_no_word_means_a_broken_word(self):
        text, report = join('a birth cer-', 'tificate and')
        self.assertEqual(text, 'a birth certificate and')
        self.assertEqual(report['dehyphenated'][0]['why'], 'a half is not a word by itself')

    def test_a_second_half_that_is_only_an_ending_means_a_broken_word(self):
        text, report = join('move noise-', 'lessly on')
        self.assertEqual(text, 'move noiselessly on')
        self.assertEqual(report['dehyphenated'][0]['why'], 'the second half is only an ending')

    def test_two_words_the_book_never_joins_or_hyphenates_stay_a_compound_and_say_so(self):
        text, report = join('grants near-', 'perfect sight')
        self.assertEqual(text, 'grants near-perfect sight')
        self.assertEqual(report['hyphens_kept'][0]['why'], 'both halves are words, and the book prints neither form elsewhere')
        self.assertEqual(report['questions'], [])
        text, _ = join('even the mail-', 'room clerk', VOCAB | {'mailroom'})          # the plan's whole_words
        self.assertEqual(text, 'even the mailroom clerk')

    def test_both_forms_printed_keeps_the_hyphen(self):
        text, report = join('any man-', 'made thing')
        self.assertEqual(text, 'any man-made thing')
        self.assertEqual(report['hyphens_kept'][0]['why'], 'the book prints both forms')

    def test_a_dash_standing_by_itself_is_followed_by_a_space(self):
        text, report = join('roll vs. IQ -', 'Complexity to succeed')
        self.assertEqual(text, 'roll vs. IQ - Complexity to succeed')
        self.assertEqual(report['hyphens_kept'][0]['why'], 'a dash standing by itself, not a broken word')

    def test_a_hanging_hyphen_before_a_conjunction_keeps_its_space(self):
        text, report = join('hard to use near-', 'or far-reaching gifts')
        self.assertEqual(text, 'hard to use near- or far-reaching gifts')
        self.assertEqual(report['hyphens_kept'][0]['why'], 'a hanging hyphen before a conjunction')

    def test_a_dictionary_settles_a_word_the_book_prints_nowhere_else(self):
        vocab = entry_text.Vocabulary(VOCAB | {'for', 'got', 'kit', 'tens'})
        self.assertEqual(join('that he for-', 'got to row', vocab)[0], 'that he for-got to row')      # two words: kept
        vocab.dictionary = frozenset({'forgot', 'kitten'})
        text, report = join('that he for-', 'got to row', vocab)
        self.assertEqual(text, 'that he forgot to row')
        self.assertEqual(report['dehyphenated'][0]['why'], 'an English word, by the dictionary')
        self.assertEqual(join('gadgets, kit-', 'tens, and knives', vocab)[0], 'gadgets, kittens, and knives')   # by its kin
        self.assertEqual(join('grants near-', 'perfect sight', vocab)[0], 'grants near-perfect sight')            # no such word

    def test_without_a_vocabulary_every_join_is_asked(self):
        text, report = join('It has mean-', 'ing here.', None)
        self.assertEqual(text, 'It has mean-ing here.')
        self.assertEqual(report['questions'][0]['kind'], 'hyphen-join')


class WordsTest(unittest.TestCase):
    def test_known_allows_one_common_ending(self):
        self.assertTrue(entry_text.known('reporting', VOCAB))
        self.assertTrue(entry_text.known('tuning', VOCAB))
        self.assertTrue(entry_text.known('keeper’s', VOCAB))
        self.assertFalse(entry_text.known('tificate', VOCAB))
        self.assertFalse(entry_text.known('thes', VOCAB))            # too short a stem to go by

    def test_the_two_halves_of_a_broken_word_are_not_words(self):
        lines = [{'text': 'The keeper trims the lan-'}, {'text': 'tern and the wick.'}, {'text': 'Then rests.'}]
        vocab = entry_text.vocabulary(lines)
        self.assertNotIn('lan-', vocab)
        self.assertNotIn('tern', vocab)
        self.assertLessEqual({'the', 'keeper', 'trims', 'and', 'wick', 'then', 'rests'}, vocab)
        self.assertEqual(book_words.words_of('The keeper trims the lan-\ntern and the wick.\n\nSelf-aware eels.'),
                         {'the', 'keeper', 'trims', 'and', 'wick', 'self-aware', 'eels'})


if __name__ == '__main__':
    unittest.main()
