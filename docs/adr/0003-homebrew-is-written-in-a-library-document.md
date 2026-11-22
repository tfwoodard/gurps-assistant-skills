# Homebrew is written in a library document

Carried over from the DnD and WFRP Assistants. The master copy of a group's
homebrew is a **homebrew document**: one Markdown file per scope (the library,
a campaign, or a campaign's GM-only material), kept in that scope's `sources/`
folder in Drive and imported like any other source. Each `#` heading is a
chapter (Advantages, Skills, Spells…), and entries are written the way the
books write them, so the same converters and checks apply. Changing a homebrew
entry means editing the document and importing that chapter again.

A group that already keeps house rules as a GCA data file keeps doing so: the
data file is added to the library as a data file (ADR 0005) and the homebrew
document holds the wording. Homebrew with no data file can have one generated
from its entries.

## Considered Options

- **Write the entries' JSON directly, with no source document.** Rejected:
  every other entry traces back to a source, the import's checks would be
  skipped, and editing JSON by hand is error-prone for a GM.
- **The data file is the homebrew's only copy.** Rejected: it says how GCA
  builds a trait, not what the trait means at the table, and nobody can look a
  ruling up in it.
