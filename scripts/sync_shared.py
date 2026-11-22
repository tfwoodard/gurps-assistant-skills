#!/usr/bin/env python3
"""Copy shared files into the skills so each skill is self-contained (required for
claude.ai uploads): shared/*.md into every skill's references/ folder, and
shared/scripts/*.py into the scripts/ folder of each skill listed for it below.

    python scripts/sync_shared.py            # copy
    python scripts/sync_shared.py --check    # fail if any copy is out of date

Run after editing anything in shared/. Works the same on Windows, macOS and Linux;
scripts/sync-shared.sh is a wrapper for it.
"""
import glob
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# shared scripts and the skills that carry a copy
SCRIPTS = {
    'library.py': ('gurps-character-sheet', 'gurps-rules-lookup'),
    'excerpt.py': ('gurps-character-sheet', 'gurps-rules-lookup'),
}


def pairs():
    """(shared file, its copy) for every copy there should be."""
    out = []
    for skill in sorted(os.listdir(os.path.join(ROOT, 'skills'))):
        if not os.path.isdir(os.path.join(ROOT, 'skills', skill)):
            continue
        for f in sorted(glob.glob(os.path.join(ROOT, 'shared', '*.md'))):
            out.append((f, os.path.join(ROOT, 'skills', skill, 'references', os.path.basename(f))))
    for name, skills in SCRIPTS.items():
        for skill in skills:
            out.append((os.path.join(ROOT, 'shared', 'scripts', name), os.path.join(ROOT, 'skills', skill, 'scripts', name)))
    return out


def same(a, b):
    if not os.path.exists(b):
        return False
    with open(a, 'rb') as fa, open(b, 'rb') as fb:
        return fa.read() == fb.read()


def main(argv=None):
    check = '--check' in (argv if argv is not None else sys.argv[1:])
    stale = []
    for src, dest in pairs():
        if check:
            if not same(src, dest):
                stale.append(os.path.relpath(dest, ROOT).replace(os.sep, '/'))
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
    for d in stale:
        print(f'out of date: {d}')
    if check and not stale:
        print('shared references are in sync')
    return 1 if stale else 0


if __name__ == '__main__':
    sys.exit(main())
