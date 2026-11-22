# GCA data files are imported beside the books, and entries point at them

GURPS has what the DnD and WFRP Assistants had to build for themselves: a
character builder, GURPS Character Assistant 5 (GCA), with a documented data
file format (`.gdf`) and published data files for most of the line. The
Librarian's GCA came with about two hundred of them, holding some 29,000 trait
definitions: costs, prerequisites, defaults, modifiers, bonuses and the page
each comes from.

A book and its data file say different things about the same trait. The book
says what it means and how it plays, in words a ruling can turn on. The data
file says how to build it: what it costs at each level, what it needs, what it
gives. Neither can be derived from the other, and both are needed.

## Decisions

1. **Both are imported, each from its own original.** The PDF becomes entries
   in `library-data/`, in the book's words. The data file is kept whole in
   `gca/books/` and read into `gca/parsed/`, definition by definition.

2. **An entry points at its definitions; it does not copy them.** An entry's
   `gca` lists the definitions that build it by GCA's own name for them
   (`AD:Combat Reflexes`) and the file they are in. What a trait finally looks
   like in a campaign depends on which data files the campaign loads and in
   what order, because later files change earlier ones with commands
   (`#ReplaceTags`, `#Clone`, `#Delete`). A copy on the entry would be wrong for
   every campaign with a house rules file.

3. **The library's categories follow GCA's sections**, and a source's code is
   GCA's code for the book, so an entry and its definition are found the same
   way and cite the same page.

4. **Linking reports what doesn't match.** Entries with no definition,
   definitions with no entry, and pairs whose printed cost and data file cost
   differ are listed every time. A data file is somebody's reading of the book
   and has mistakes; so will the import.

5. **A source with no data file can have one generated**, from definitions
   written on its entries one at a time, each confirmed by the Librarian beside
   the text it reads (as the WFRP Assistant's formulas were). The entries are
   the master copy and the generated file is never edited. It is tested in GCA
   before a campaign uses it.

6. **Data file commands are kept, not applied, at import.** Applying them
   belongs to a campaign's load order.

## Considered Options

- **Books only; generate every data file ourselves.** Rejected: years of other
  people's careful work would be redone worse, and the group's characters are
  already built on the published files.
- **Data files only, as the library.** Rejected: they hold no rules text, no
  rules that aren't traits (combat, tables, settings), and nothing to cite at
  the table.
- **Copy each definition's tags into its entry.** Rejected: decision 2.

## Consequences

- The import has two kinds of original, and a book isn't finished until its
  entries are linked.
- The data files are copyrighted like the books. They live in the library's
  Drive folder and in GCA's own folders, never in the repo; tests use invented
  traits.
- GCA's updater replaces published files. Each data file's hash is recorded so
  a change is noticed and the file read again.
