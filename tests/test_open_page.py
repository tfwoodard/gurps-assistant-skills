"""Tests for open_page.py: the address of a printed page in a source's PDF. Nothing is opened.

Run: python -m unittest discover tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'skills', 'gurps-import', 'scripts',
                      'open_page.py')


class OpenPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lib = os.path.join(self.tmp.name, 'Marsh Library')
        os.makedirs(os.path.join(self.lib, 'sources', 'ML'))
        for name in ('Marsh Lamps 1.pdf', 'Marsh Lamps 2.pdf'):
            with open(os.path.join(self.lib, 'sources', 'ML', name), 'wb') as f:
                f.write(b'%PDF-1.4\n')
        with open(os.path.join(self.lib, 'library.json'), 'w', encoding='utf-8') as f:
            json.dump({'gurps_library': True, 'sources': [{'code': 'ML', 'files': [
                {'file': 'sources/ML/Marsh Lamps 1.pdf', 'pages': '1-100', 'page_offset': 2},
                {'file': 'sources/ML/Marsh Lamps 2.pdf', 'pages': '101-180', 'page_offset': -99}]}]}, f)

    def tearDown(self):
        self.tmp.cleanup()

    def run_it(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args, '--library', self.lib, '--print'],
                              capture_output=True, text=True, encoding='utf-8')

    def test_the_file_that_holds_the_page_and_its_pdf_page(self):
        out = self.run_it('ml', '37', '120').stdout.splitlines()
        self.assertTrue(out[0].startswith('ml p37 (PDF page 39): file:///'))
        self.assertTrue(out[0].endswith('/Marsh%20Library/sources/ML/Marsh%20Lamps%201.pdf#page=39'))
        self.assertTrue(out[1].endswith('/Marsh%20Lamps%202.pdf#page=21'))

    def test_a_page_no_file_holds_and_an_unknown_source_are_refused(self):
        r = self.run_it('ML', '200')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no file holds printed page 200 (its files hold 1-100, 101-180)', r.stderr)
        r = self.run_it('XX', '3')
        self.assertIn('XX: no source with that code', r.stderr)


if __name__ == '__main__':
    unittest.main()
