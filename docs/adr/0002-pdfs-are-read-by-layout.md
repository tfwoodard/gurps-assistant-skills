# PDFs are read by layout, not as flat text

Carried over from the DnD and WFRP Assistants. The DnD Assistant first
imported from flattened page text. It dropped heading levels, ran table columns
together and couldn't tell a list's last item from the heading after it, so
every chapter needed hand-split tables and heuristics that kept breaking. It
only became reliable once the importer read the source's real structure.

GURPS PDFs are two- and three-column pages with margin sidebars, boxed text,
trait write-ups headed by a name and a point cost, and long equipment tables,
which flat extraction mangles the same way. So the import reads each page as
text spans with position, font, size and weight (`pdf_layout.py`, on
pdfplumber), orders them by column, and finds headings from font size and
weight. Each kind of chapter (advantages, skills, spells, equipment tables)
gets a converter that builds entries from those lines and a plan, with tests on
an invented PDF.

When a page's structure can't be read from its text (a table drawn as art),
Claude looks at the page image, transcribes it, and records that in the
chapter's notes.

## Considered Options

- **Flat text with heuristics.** Rejected: the lesson above.
- **OCR every page.** Rejected: the books have a text layer, and OCR adds
  errors to wording the library must keep exactly. OCR only for scanned PDFs
  (some older books are), and only after asking.
- **Take the text from GCA's data files.** Rejected: a data file's
  `description()` tags are short notes written for GCA, not the book's rules.
  The data files are imported for what they are (ADR 0005).
