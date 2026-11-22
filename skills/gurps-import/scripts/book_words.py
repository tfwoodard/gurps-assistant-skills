#!/usr/bin/env python3
"""List the words a book prints whole, to settle the words its lines break in two.

    book_words.py BOOK.pdf [MORE.pdf ...] --out words.txt

A converter joins a word broken at a line's end ("mean-" / "ing") and has to decide whether its
hyphen belongs ("self-awareness") or only marks the break ("meaning"). A chapter's own words
settle most; the whole book's settle nearly all the rest. This lists every word the PDFs print
that is not broken at a line's end, in lower case, one to a line: plain words ("meaning") and
hyphenated ones ("self-awareness") alike. A converter given the list (`--words`) drops a
line-end hyphen when the joined word is in it and the hyphenated form is not.

The list is made from the book's text: keep it in Drive beside the source's plans, never in the
repo. Needs pypdf.
"""
import argparse
import re
import sys

WORD = re.compile(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*")


def words_of(text):
    """The words of a page's text that are printed whole: a line's last word is left out when
    the line ends in a hyphen, and so is the first word of the line after it (the two halves of
    a broken word are not words)."""
    out = set()
    after_break = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        broken = line.endswith(('-', '­', '‐'))
        found = WORD.findall(line[:-1] if broken else line)
        if broken and found:
            found = found[:-1]
        if after_break and found:
            found = found[1:]
        out.update(w.lower() for w in found)
        after_break = broken
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pdfs', nargs='+')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    from pypdf import PdfReader
    words, pages = set(), 0
    for path in a.pdfs:
        reader = PdfReader(path)
        for page in reader.pages:
            words |= words_of(page.extract_text() or '')
            pages += 1
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(sorted(words)) + '\n')
    print(f'{len(words)} words from {pages} pages of {len(a.pdfs)} PDF(s) -> {a.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
