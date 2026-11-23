"""Tests for read_chapter.py: a plan's layout options become pdf_layout.py's arguments.

Run: python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'skills', 'gurps-import', 'scripts'))
import read_chapter  # noqa: E402


class ReadChapter(unittest.TestCase):
    def test_every_option_is_passed_and_notes_are_passed_over(self):
        layout = {'file': 'sources/ML/Marsh Lamps.pdf', 'pages': '10-20', 'page_offset': 2, 'boxes': True,
                  'icons_alone': True, 'icon_fonts': ['MarshIcons'], 'icon_text': ['MarshIcons:1=[wet]'],
                  'aside_fonts': ['Reed-Italic@14'], 'replace_chars': ['K=C'], 'replace_chars_why': 'a note'}
        args = read_chapter.command(layout, 'L', 'out.json')
        self.assertEqual(args[0], os.path.join('L', 'sources', 'ML', 'Marsh Lamps.pdf'))
        self.assertEqual(args[1:], ['--pages', '10-20', '--page-offset', '2', '--boxes', '--icons-alone',
                                    '--icon-fonts', 'MarshIcons', '--icon-text', 'MarshIcons:1=[wet]',
                                    '--aside-fonts', 'Reed-Italic@14', '--replace-chars', 'K=C', '--out', 'out.json'])

    def test_the_least_a_layout_needs_and_a_negative_offset(self):
        self.assertEqual(read_chapter.command({'file': 'a.pdf', 'pages': '343-361', 'page_offset': -335}, 'L', 'o')[1:],
                         ['--pages', '343-361', '--page-offset', '-335', '--out', 'o'])

    def test_an_unknown_option_and_a_missing_file_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'does not know: boxs'):
            read_chapter.command({'file': 'a.pdf', 'pages': '1', 'boxs': True}, 'L', 'o')
        with self.assertRaisesRegex(ValueError, 'has no `file`'):
            read_chapter.command({'pages': '1'}, 'L', 'o')


if __name__ == '__main__':
    unittest.main()
