"""package-skills.py: reproducible zips, and which ones changed since the manifest in Drive."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('package_skills', os.path.join(ROOT, 'scripts', 'package-skills.py'))
pk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pk)


class PackageTest(unittest.TestCase):
    def test_every_skill_is_assigned_and_the_librarians_are_never_packaged(self):
        self.assertEqual(set(os.listdir(os.path.join(ROOT, 'skills'))), set(pk.PLAYERS + pk.GM + pk.LIBRARIAN))
        with tempfile.TemporaryDirectory() as d:
            m = pk.package(d)
            names = set().union(*(set(x['zips']) for x in m.values()))
            self.assertEqual(names, {s + '.zip' for s in pk.PLAYERS + pk.GM})
            for folder in m:
                self.assertTrue(os.path.exists(os.path.join(d, folder, 'README.md')))

    def test_zips_are_reproducible(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(pk.package(a), pk.package(b))

    def test_compare_and_collect(self):
        with tempfile.TemporaryDirectory() as d:
            m = pk.package(os.path.join(d, 'dist'))['players']
            same = os.path.join(d, 'same.json')
            with open(same, 'w') as f:
                json.dump(m, f)
            self.assertEqual(pk.changed_zips(m, same), ([], m['version']))
            old = dict(m, version='0.0.1', zips=dict(m['zips'], **{'gurps-rules-lookup.zip': 'x'}))
            older = os.path.join(d, 'old.json')
            with open(older, 'w') as f:
                json.dump(old, f)
            self.assertEqual(pk.changed_zips(m, older), (['gurps-rules-lookup.zip'], '0.0.1'))
            self.assertEqual(pk.changed_zips(m, os.path.join(d, 'none.json')), (list(m['zips']), None))
            up = os.path.join(d, 'up')
            names = pk.collect(os.path.join(d, 'dist'), 'players', ['gurps-rules-lookup.zip'], up)
            self.assertEqual(sorted(os.listdir(os.path.join(up, 'players'))), sorted(names))
            self.assertEqual(sorted(names), ['README.md', 'gurps-rules-lookup.zip', 'manifest.json'])
            self.assertEqual(pk.collect(os.path.join(d, 'dist'), 'players', [], up), [])
            self.assertFalse(os.path.exists(os.path.join(up, 'players')))

    def test_the_hash_is_of_the_contents_and_a_zip_beside_the_manifest_is_checked(self):
        import zipfile

        def rezip(src, dst, level, change=None):
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED, compresslevel=level) as b:
                for info in a.infolist():
                    data = a.read(info)
                    if change and info.filename.endswith('SKILL.md'):
                        data += change
                    b.writestr(info, data, compresslevel=level)

        with tempfile.TemporaryDirectory() as d:
            m = pk.package(os.path.join(d, 'dist'))['players']
            z = 'gurps-rules-lookup.zip'
            built = os.path.join(d, 'dist', 'players', z)
            drive = os.path.join(d, 'drive')
            os.makedirs(drive)
            rezip(built, os.path.join(drive, z), 1)          # same files, other bytes
            with open(os.path.join(drive, z), 'rb') as f, open(built, 'rb') as g:
                self.assertNotEqual(f.read(), g.read())
            self.assertEqual(pk.contents_sha(os.path.join(drive, z)), m['zips'][z])
            manifest = os.path.join(drive, 'manifest.json')
            with open(manifest, 'w') as f:                    # an old manifest, hashing the zip's bytes
                json.dump(dict(m, zips=dict(m['zips'], **{z: 'bytes'})), f)
            self.assertEqual(pk.changed_zips(m, manifest), ([], m['version']))
            rezip(built, os.path.join(drive, z), 1, change=b'\nInvented extra line.\n')
            self.assertEqual(pk.changed_zips(m, manifest), ([z], m['version']))

    def test_the_command_line_refuses_an_unknown_folder(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'package-skills.py'), '--compare', 'dm=x.json'],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('players=<manifest> or gm=<manifest>', r.stderr)


if __name__ == '__main__':
    unittest.main()
