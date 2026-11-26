---
name: gurps-import
description: Import GURPS game material (advantages, disadvantages, skills, spells, modifiers, templates, equipment, creatures, rules, tables, settings) from a source into the private Google Drive library — a rulebook or supplement PDF, an adventure, a Google Doc or homebrew document, or pasted text — and add GURPS Character Assistant data files (.gdf), link entries to their GCA definitions, or generate a data file for a book that has none. Use when the user asks to add a source or a data file, import a chapter, check what's been imported, or re-import after errata; or when another GURPS skill reports missing entries.
---

# Import

Read `references/library-layout.md` first, especially §3 (sources), §4
(entries), §6 (importing) and §12 (GCA data). Follow its formats exactly: the
other skills depend on them.

**Before any import work, check for an unfinished import.** A session can stop
partway (a usage limit, a closed laptop) and resume with no memory of what it
did. Run `python scripts/import_journal.py show` (it finds the journal itself;
keep scratch in `scratch/` under the working directory). If the repo's hook is
set up (`.claude/settings.json`), the journal is already in front of you. If an
import is open, finish it before starting anything new (§7 below). Do this
before replying to every message while an import is open.

A book is imported in three parts, in any order, and isn't finished until all
three are done:

1. its **chapters**, from the PDF, into entries (§3–§5);
2. its **data files**, from GCA, into `gca/` (§6);
3. the **links** between the two (§6).

## 1. Work out what's being imported

- **Which source?** Match the user's words to a `code` or `title` in
  `library.json` → `sources`, or in the active campaign's `campaign_sources`.
  If it's new, go to **Add a source** first.
- **Library or campaign?** Library sources are imported by the Librarian.
  Campaign sources (adventures, the GM's homebrew) are imported by that
  campaign's GM, into the campaign's `library-data/`, or `gm/library-data/` for
  GM-only material. If there's no edit access to the target folder, stop and
  say who can import it.
- **Which chapter?** One chapter per run, from the source's chapter list.
- **Already imported?** If the chapter's status is `imported` or `problems`,
  confirm this is a re-import (errata or a better extraction) and ask why, for
  the log.

## 2. Add a source

1. Agree on a `code` (layout §3: unique across the library and all campaign
   sources). For a published book, use GCA's code for it: look the title up in
   `bookcodes.xml` in `gca_system_path`. A book not listed there gets a code
   the Librarian chooses, checked against the codes that are. Homebrew is
   `HB-<NAME>`. Then the title and the edition (`4e` unless the book says
   otherwise; `dfrpg` for the Dungeon Fantasy Roleplaying Game).
2. For a PDF, put it (or check it's) in `sources/<code>/` in the library and
   read the chapter list from its bookmarks:

   ```
   python scripts/pdf_outline.py "<local folder>/sources/B/<file>.pdf" --depth 2 --out scratch/chapters.json
   ```

   It reports the page offset (printed page 1's PDF page) from the PDF's page
   labels; if it can't, find printed page 1 in the PDF and pass
   `--page-offset`. Show the list beside the book's contents page, drop
   bookmarks that aren't chapters (cover, credits, index, adverts), and fix
   titles to match the contents. A book in two volumes with one run of page
   numbers (the Basic Set: *Characters* to p. 336, *Campaigns* from p. 337) is
   one source with two `files`, each with its own pages and `page_offset`;
   read each volume's outline and join the lists.
   A Google Doc, file or pasted source: its top-level headings, or a single
   `all` chapter if it's short.
3. Every chapter starts as `not-imported`. Write the source to `library.json`
   (library sources) or `campaign.json` → `campaign_sources` (campaign
   sources). For a campaign source, also add its code to the front of the
   campaign's `sources`, unless the GM says otherwise.
4. Look for the source's data files (§6) and say which exist.
5. Show the chapter list and suggest where to start. For a new library, the
   Basic Set's chapters on attributes, advantages, disadvantages and skills
   come first, with its data file: lookups and characters need them.

## 3. Read the chapter

### PDF (`kind: pdf`)

PDFs import only where the whole file is on disk (layout §6, docs/adr/0001):
Claude Code with the library's local folder, or a cloud session linked to the
Librarian's computer with the folder connected (copy the PDF into scratch with
the device tools). If neither is available, say so and stop. Never copy the
PDF or anything read from it into the repo.

1. Read the chapter's pages by layout into scratch. A chapter that has a plan
   is read with the options the plan records under `layout`:

   ```
   python scripts/read_chapter.py "<library>/sources/B/plans/ch2.json" --library <library> --out scratch/ch2-layout.json
   ```

   For a first look at a new book, call the reader directly:

   ```
   python scripts/pdf_layout.py BOOK.pdf --pages 32-118 --page-offset 2 --out scratch/ch2-layout.json
   python scripts/pdf_layout.py BOOK.pdf --pages 43 --page-offset 2 --text    # look at a page
   ```

   It orders each page's lines by column, marks page furniture (running heads,
   page numbers) and gives heading levels from type size. `--boxes` finds boxed
   panels, ruled tables, and tables set on a tinted panel of their own.
   `check_coverage.py` prints every line set aside as `page furniture`: read
   them each time, because a body line there is a fault to fix, not a line to
   leave out. If it reports pages with no text layer, look at the page images
   and ask before running OCR. Things to look for in a new book, each of which
   has an option once found:
   - its type icons (`--icon-fonts`, `--icon-text`, `--icons-alone`);
   - pull quotes, which repeat the text in a face of their own (`--aside-fonts`); a
     quotation's source set under it at its size in another face (a film's title in bold
     italics) goes with it;
   - a character its fonts give wrongly: list the chapter's non-ASCII characters
     once (`--replace-chars`). A glyph a font gives no character for reads
     "(cid:129)"; the layout lists each in `unmapped_glyphs`, and the coverage
     check (so `write_chapter.py`) refuses the chapter until `--replace-chars`
     says what the page prints there (`(cid:129)=•`);
   - `gutter_notes`: pages read with the book's usual columns because a picture
     or panel hid one.
   - a frame that is no panel (drawn round a picture that text runs past): a box
     with a line or two of unrelated text and no title (`--not-boxes PAGE.N`).
   - a short chapter whose pages hide the book's columns (a box or a picture fills
     most of a column on half its pages, or tables across the page fill the rest):
     give the columns the book shows elsewhere (`--usual-gutters even=X,X odd=X,X`,
     the plan's `usual_gutters`).
   - pages of tables side by side, whose columns' blanks are taken for gutters: give
     each page's gutters (`--set-gutters 297=312 298=296 305-306=none`, the plan's
     `set_gutters`).
   - a panel or picture across the page with columns over it and under it: a band
     with more columns than the page shows is read in its own (the layout's
     `image_notes` says so); where the columns are the same but the text above runs
     on from the last page and the text below starts a new section, name the page
     (`--band-pages 554`, the plan's `band_pages`) so the band above is read first.
   - a table set across the page on stripes of tint (stacked thick strokes): its
     rows, and the notes under it, are read as whole lines (notes set in two columns
     of their own are read in those), and the page's gutters are found from the
     text around it.
2. Check it's the chapter it should be: its first heading matches the chapter
   list. If not, say so and stop.
3. Look at a few pages with `--text` and at the page images where the layout is
   unusual (trait headings with their point costs, margin sidebars, weapon
   tables). Write the chapter's **plan**: which heading level starts an entry,
   which sections hold which category, what's left out (art credits, the
   index), and every same-name decision (§4). Keep it in Drive beside the
   source (`sources/<code>/plans/<chapter>.json`), never in the repo.
4. Convert with the converter for that kind of chapter, then check coverage:

   ```
   python scripts/check_coverage.py scratch/ch2-layout.json scratch/out-ch2
   ```

   Always give a converter the library's entries (`--library-data <library>/library-data`):
   a name another source holds in the same category becomes a `version-of` it, and a name
   another chapter of the same book holds is an error until the plan's `entries` gives the new
   one a `slug` (and a relation). `write_chapter.py` checks the same again before it writes
   anything.

   Converters so far:

   | Kind | Script | Plan says |
   |---|---|---|
   | Trait write-ups (advantages, disadvantages, perks, quirks, talents, enhancements and limitations, skills and techniques, spells, **templates and meta-traits**): a name with its type icons, a line under it (a cost; a skill's attribute and difficulty; a spell's class and what resists it; a template's points), then text | `convert_traits.py` | the type sizes of a trait's name and of its cost line (`name_size`, `cost_size`); the icon words; the `sections` that are lists of traits, by heading and page, with their category and kind (every other section becomes a `rules` entry, and so does each box; a frame holding two sidebars, the second headed as large as the first, gives two); `intro` (a name for text before the first heading, and `standfirst`, how many of the first lines are an opening set large that the layout reads as a heading); `boxes` (`leave_out` with the reason, or `adds_to` an entry, or a `name`); `into` (and `under` a heading or `after_text` a paragraph's opening words, `title_lines`, `lead_lines`, `after_lines`, `fold` (side-by-side parts; a later part may be shorter), and `empty_cells` for cells the page prints blank) for a table on a tinted panel, naming the entry it belongs to; a list's `category: "by-cost"` (with `categories` for exceptions) for advantages and disadvantages listed together; an `entries` key with `@PAGE` for one of several entries of one name (a running example's parts); `trait_ends` for a heading that hands the text after it back to the section; `split_labelled` for labelled paragraphs that are entries of their own; a list's `fields_from` (`start`, `end`) for where its own labelled lines are; a list's `line` (`skill`, `technique`), `marks` after a name and `labels` of paragraphs that are fields too; `rename` for two different traits of one name in one category, or (with `slug` and `relation`) for one trait the book prints twice; `starred` to make a field of the asterisk after a cost; `no_cost_line` and `name_size` for a list whose traits print no cost (perks, quirks); `not_traits` and `leave_out_lines` for name-sized lines that aren't traits; `entries` for an entry's relations, extra fields or audience, and for a section that is a reference table, its `category: "tables"` with `fields` `about` and `roll` and the table's own `name` (the heading over it is kept as `printed_name`); a box's `continues` for a panel carried on under its title again on the next page; `hanging_lists` for entries whose items are set with hanging indents and no label style (a summary list of modifiers). A table's rows may hold group headings (a bold line over the rows of one kind): they become its `groups`. Traits are found by their headings, not listed: a name with no cost line under it is an error. Read the pages with `--boxes`, the book's type icons as words (`--icon-fonts`, `--icon-text FONT:GLYPH=[word]`, `--icons-alone`), its pull quotes set aside (`--aside-fonts FONT@SIZE`) and any character its fonts give wrongly put right (`--replace-chars READ=PRINTED`: the Basic Set's multiplication sign reads as a yen sign; list the chapter's non-ASCII characters once to find these); the plan's `layout` records the options used. Check the layout's `gutter_notes` (pages read with the book's usual columns) and the report's `tables` (every table set in a trait's text, read and checked: see **Tables** below), `table_like` (lines spaced like table rows that were not read as one), `not_tables` (bold-italic lines over prose, left as text), and how it settled the words broken at a line's end: `dehyphenated` and `hyphens_kept`, each with why. Give it the book's word list (`--words`, made once per book with `book_words.py BOOK.pdf --out sources/<code>/plans/words.txt`); give it English words too (`--dictionary english-words`, which needs `pip install english-words`), for the broken words the book prints nowhere else; read the `hyphens_kept` whose reason is "both halves are words, and the book prints neither form elsewhere" (the one case decided without evidence) and put the ones that are one word in the plan's `whole_words`. |
   | Equipment tables (weapons, armor, shields, vehicles): a title, groups under bold headings (a skill with its defaults, or a kind), an italic header row starting `TL`, rows, then numbered notes (under a `Notes` line or none) | `convert_traits.py` with the plan's `equipment_tables` (read by `equipment_tables.py`) | each table's `title`, the `page` it starts on and the `kind` of its items (`melee-weapon`, `armor`…); where it differs from the Basic Set's, `header_starts` (the header's first word), `group_size` (the group headings' type size) and `name_column` (which column names the item); `until` (`page`, `text`) when it ends at something other than a heading or another box; `section` and `about` for its `tables` entry; `notes_below` when a panel's table has its notes printed under the panel, on the page. A table becomes a `tables` entry and one `equipment` entry per item (an item in several tables, or in two groups of one, is one entry; a name one group prints at two TLs is two items, named with their TLs, as GCA gives them). A group heading set in capitals names the skill its items are used with: each item's `skills` points at that skill's entry, with the specialty in the case the skill's entry prints it, and a heading naming a skill or specialty the library's skills don't have fails its table (run with `--library-data`; without it, `skills_not_linked` says no skill was linked). Each is checked as text tables are, and a table that fails is an error and writes nothing. The report's `equipment_tables` counts each one's groups, rows and notes; `columns_split_by_row` lists the header words that shared a column and were split row by row; `names_over_two_lines` the names run on to a second line; `named_with_tl` the names told apart by TL. Show the Librarian the first three tables a new book's tables give (as for any new reader), then only failures. |
   | Creatures: a name, a description, then a stat block (`ST 4; DX 14; …` lines, the characteristic names in bold, then labelled lines: `Traits:`, `Skills:`, `Cost:`), perhaps grouped under a larger heading with text of its own ("Otters") | `convert_traits.py` with a section's `creatures` (read by `creatures.py`) | the section's `kind` (`animal`, `monster`), the type sizes of a creature's name (`name_size`) and of a group's (`group_size`). A creature becomes a `creatures` entry: its description, then a `profile` block; its `attributes` are the characteristics in printed order, and each labelled line is a field too. A heading at the group size with no stat line is a group, an entry the creatures under it `adds-to`; one with a stat line (a creature headed like a group: "Herons") stands alone and closes the group. A heading at the name size with no stat line, or a part of a stat line that is no characteristic and no weight, is an error. Check the report's `creature_groups` (each group's members) and `stat_lines` (a part read otherwise than as printed: a comma for a semicolon). |

   A chapter of another kind needs a converter built first: a script that
   reads the layout JSON and a plan and writes each entry's `.json` and `.md`
   (`render_entry.py`), `_records.json` (index records) and `_report.json`
   (errors, left-out text, questions), with tests on invented pages in
   `tests/`, in its own pull request. Look at the real pages before designing
   one. The kinds the Basic Set still needs:

   | Kind | What the pages look like |
   |---|---|
   | Equipment descriptions | gear lists and descriptions keyed to table rows (the tables themselves are read: above) |
   | Rules prose | sections, sidebars, tables; the WFRP Assistant's `convert_rules.py` is the model to carry over |

   The WFRP Assistant's converters (github.com/tfwoodard/wfrp-assistant-skills,
   `skills/wfrp-import/scripts/convert_*.py`) are the patterns to follow, and
   its `convert_rules.py`, `items.py` and `creatures.py` are worth carrying
   over rather than rewriting when the first rules chapter is imported.
5. The report must have no errors, and `check_coverage.py` must account for
   every word: in an entry, or on the report's `left_out` list. Look at
   anything it reports missing.
   Then `check_names.py <library-data> <out>/_records.json` must find a
   relation (layout §4) on every new entry that shares a name with another,
   in any category; propose the role in the plan's `relations`, and the
   Librarian confirms.

When a table or stat line can't be read from the text (drawn as art, or its
cells out of order), transcribe it from the page image, keeping every word,
show the Librarian, and say so in the chapter's notes.

### Google Doc, file, or pasted text

Read it through the connector, or from the conversation for `pasted`. For a
pasted source, also save the text as a file in the right `sources/` folder, so
it can be re-imported later.

### Homebrew document (layout §3)

The group's own homebrew is written in its homebrew document
(docs/adr/0003). When someone wants a homebrew trait, spell or item added or
changed:

1. Draft the entry with them in the books' style. Ask about every gap a ruling
   would otherwise fill and write the answer into the text, so the entry needs
   no ruling at the table.
2. Write the change into the document and save it.
3. Import the chapter like any other source.
4. If the group builds characters with it, give it a GCA definition (§6).

## 4. Build entries

**Entries that share a name.** When an entry shares its name with one already
in the library or in the same chapter (pass every category's `_index.json`
with `--taken`), the two are related (layout §4). An entry that takes another
source's entry's name in the same category is by default a **version** of it
(`version-of`): the same thing as this source prints it, which each campaign's
source order chooses between (docs/adr/0007). The plan's `relations` state
only the exceptions: `adds-to`, `distinct-from`, `updated-by`, and a
`version-of` between entries whose names or categories differ. Read both
entries before writing one, and ask the Librarian whenever it isn't certain.

A slug's suffix (`broadsword-lt`) keeps files apart and nothing more: nobody
using the library sees it. That is enough when the two entries are read
together (`adds-to`, `version-of`, `reprint-of`). When they are different
things in one category (`distinct-from`), change the **name** in the plan so
people can tell them apart; the slug follows.

**Rules that change another entry.** A relation isn't only for shared names.
When a section changes how something elsewhere in the library works, give it
`adds-to` that entry, whatever either is called: a supplement's new
enhancements for an advantage add to the advantage; a box of optional rules
for a maneuver adds to the maneuver. A lookup of the entry then brings them
up. Without the relation they are only found by someone who already knows to
look.

**Specialties.** A skill or advantage that takes a specialty is one entry when
the book writes it up once and lists the specialties, which go in its `fields`
(layout §4). A specialty with a write-up of its own is an entry under its full
name that `adds-to` the trait's entry.

**What the book prints goes in `fields` as printed**: a cost of "5 points/level",
a default of "IQ-5, or Naturalist-3". They are for lookups and for checking a
data file against the book. Don't turn them into numbers a character could be
built from; that is the data file's job.

**GM-only material.** Mark it `audience: "gm"` in the plan: adventures, and the
secrets of a setting. Traits, spells, equipment and the rules a player uses
stay unmarked. Ask the Librarian about anything else that reads as the GM's.

**A source of an older edition** (layout §8 "Editions"): its plan also lists
every rule it holds (advantage, skill, spell, creature) with the 4e entry that
updated it, if any, under the same name or another. Show the Librarian that
list and import only after they confirm it; each match becomes an
`updated-by` relation.

**Tables.** The tool that reads a table checks it; the Librarian does not
confirm each one (layout §6). Take every number from the source, never from
memory.

- A reader lists every table it found in the report's `tables`, with its
  header, rows and `failures`. A table with a failure is not written: the
  converter stops with an error that says which check failed.
- To put the page in front of the Librarian, open it: `python scripts/open_page.py B 37 44`
  opens the source's PDF at each printed page in a browser window.
- When a reader is new, or is used on a kind of table it hasn't read before,
  show the Librarian the first three tables it produced, whole, beside their
  page numbers, and ask whether they read as the page prints them. After
  that, don't show tables that pass.
- When a table fails, look at the page. Either the reader is wrong (fix it,
  add a test on an invented table, convert again) or the page is unusual. Ask
  the Librarian only when the reader has to change and it isn't clear how the
  table should read.
- The report's `table_like` lists lines spaced like table rows that no reader
  took: look at each on the page. They are either tables the reader missed
  (fix the reader) or text that happens to be widely spaced (say so).
- A table printed as a flowchart or picture is transcribed by hand, keeping
  every word, shown, and noted in the chapter's notes.

Readers so far: `entry_text.with_text_tables` (a table set in the text without
rules: one or more bold-italic header lines, then rows; a header phrase over
several columns is a banner; a last column set flush right, whose long cells
leave no blank down the table, is read row by row after each row's wide gap;
a line under the rows starting with a note's mark (`*`, `†`) ends them and stays
text; a cell carried on to the next line after a slash joins it with no space;
`convert_traits.py` uses it, for tables in the
columns and for those on a tinted panel of their own) and `pdf_layout.py
--boxes` (a ruled table in a box, not yet used by a converter).

To correct an entry's fields or relations after an import, use
`scripts/edit_entry.py --library <root> <category>/<slug> --set FIELD=VALUE
--relation ROLE:TARGET --plan sources/<SRC>/plans/<chapter>.json`. It rewrites
the `.json`, renders the `.md` again, changes only that entry's line in
`_index.json`, and gives the plan the same fields and relations in its own
layout, so a re-import keeps them. An entry's `gca` is not set this way (§6).

## 5. Write

**Settle every question before the bookkeeping.** Gather every open question
(same-name decisions, tables that failed a check, hand transcriptions to show), settle
them with the Librarian, apply the answers, then merge and write the
bookkeeping once per chapter. Entry files can be written as soon as they're
ready.

1. Write entry files to the target `library-data/<category>/` in batches of
   10–20, and record each batch in the journal.
2. Merge with `scripts/merge_import.py` from the current files (don't rebuild
   them by hand):

   ```
   # after each batch: index only
   python scripts/merge_import.py --out scratch/new --index <index> \
       --records scratch/out-ch2/_records.json --edition 4e --slugs <this batch's slugs>

   # at the end: index, log record, chapter status
   python scripts/merge_import.py --out scratch/new --index <index> \
       --records scratch/out-ch2/_records.json --edition 4e --log <import log> --library <library.json> \
       --source B --chapter ch2 --category advantages \
       --log-notes "<what was imported, what was left out>" --chapter-notes "<short summary>" [--failed N]
   ```

   A chapter whose entries span several categories has one `_records.json`;
   each record carries `_category`. Merge it into each category's index in
   turn. For a campaign target, `--library` expects `library.json`'s layout, so
   update `campaign.json` by hand.
3. Write the merged `_index.json` files, then `_import-log.json`, then
   `library.json` last.
4. For a re-import, overwrite each entry, carrying its `gca` over from the
   entry it replaces, and trash entry files the merge says the chapter no
   longer has.

### Writing to the library

**Local folder first.** When the library's local folder can be reached
(layout §1), write straight into it, over the old files, and let Drive sync. In
a cloud session linked to the Librarian's computer, connect the folder once,
stage the files in the session's outputs folder, and copy them over in batches
with the device tools (`scripts/drive_bridge.py` in the repo keeps the ledger).
Give every staged file a path not used before in the session (a new folder per
batch). Then list the folder and check every file's size against the local
copy, and stage each bookkeeping file (`library.json`, indexes, the log) back
and compare it byte for byte.

**Through the connector** (only when the folder can't be reached): print files
with `scripts/print_upload.py <files> --list`, then `--part 1`, `--part 2`…,
and upload the text between the markers exactly, with
`disableConversionToGoogleType: true` and `contentMimeType` `text/markdown` or
`application/json`. If the header says the file ends with a newline, the upload
must too; a `fileSize` one byte short means it was dropped. Check each upload's
size, and check content with a download and `scripts/compare_download.py`. The
connector can't edit in place: write the new file and trash the old one.

## 6. GCA data

Layout §12 and docs/adr/0005 say what is kept and why.

### Add a data file

Data files are read where they are on disk: GCA's own folders
(`gca_system_path`/`books` for the published ones, `gca_user_path`/`books` for
the user's) or the library's local folder.

1. Read it and look at the report (`--dry-run` writes nothing):

   ```
   python scripts/add_data_file.py --library <root> \
       "<path>/GURPS Basic Set 4th Ed.--Characters.gdf" --source B --dry-run
   ```

   It gives the number of definitions in each section, the files it
   `Requires` and whether the library has them, what changed since the file
   was last read, and `problems`: lines it could not read as a definition,
   each with its line number and why. Published files have a few (a tag typed with a space before
   its bracket, a missing comma). Show them; they go in the data file's
   `notes`, and the file's status is `problems` only if a definition the
   library needs is among them. Never correct a published file.
2. Say which source it belongs to (its `page()` tags name the book codes it
   draws on; the description says what it covers). A file that only changes
   other files (a house rules file of `#ReplaceTags` commands) belongs to no
   source, or to the group's homebrew document.
3. Run it again without `--dry-run`. It copies the file, unchanged and under
   its own name, to `gca/books/` (`--folder` for a campaign's own), writes the
   parsed JSON to `gca/parsed/<file-slug>.json`, replaces the file's records
   in `gca/parsed/_index.json`, and adds or replaces its record in
   `library.json` → `data_files` and its name in its source's `data_files`.
4. Say what it `Requires` and whether those files are in the library.

GCA's updater replaces published files. When a file's SHA-256 no longer
matches the library's record, read it again and report what changed
(definitions added, removed and altered, by `item`).

### Link entries to definitions

Run after a chapter's entries are written and its source's data file is in the
library. For each entry, propose the definitions that build it:

- the same name (and name extension) in the section for the entry's category
  (layout §12's table), whose `page()` tag names the entry's source and page;
- for a trait with specialties, every definition of that name with a name
  extension;
- nothing, for rules prose, tables and settings.

Exact matches on name and page are written without asking. Everything else is
shown to the Librarian in three lists, every time, none of them left out:

1. **entries with no definition** (the data file doesn't cover it, or names it
   differently);
2. **definitions with no entry** (GCA's helper items such as `_New Skill`,
   variants GCA splits out, traits from a chapter not imported yet);
3. **pairs whose costs differ**: the entry's printed cost against the
   definition's.

Write the confirmed links to each entry's `gca`, render its `.md` again, and
update its index line.

`scripts/link_gca.py` does this (its docstring has the details):

```
python scripts/link_gca.py --library <root> --source B --report scratch/link-report.json
python scripts/link_gca.py --library <root> --source B --write
```

The first run writes nothing: it prints counts, the three lists and what
couldn't be compared, and the report holds every entry's links and
proposals. Each proposal has a kind (`runs-on`, `singular`, `pointer`,
`other-page`, `no-page`, `other-section`, `on-page`). Show the Librarian a
few of each kind beside the pages they cite, and record what they confirm
in `sources/<code>/plans/links.json`: `links` for an entry's definitions,
`none` for an entry with none (and why), `not_entries` for a definition with
no entry (and why), and `accept` for a kind confirmed as a whole. Then run
with `--write`. A links file naming an entry or definition that isn't there
stops the run with nothing written.

Pairs whose costs differ are faults in the data file, the book or the
import: check each against the page, and keep the data file's ones in a list
for its maintainers (layout §12); never correct the published file.

Writing a chapter again (`write_chapter.py`) keeps each entry's links. Run
the linker again afterwards: an entry whose name changed may need new ones.

### Generate a data file

For a source with no data file (layout §12, "Generated data files"):

1. Read the *GCA Data File Reference Guide* sections for the kind of trait
   first, and look at how a published file defines a similar trait
   (`gdf.py show <file> "AD:<name>"`). GCA's installed copy of the tag
   definitions is `tagdefs.xml` in `gca_system_path`.
2. Write each definition on its entry, as a `define` in the entry's `gca`.
   Propose it beside the entry's text, one trait at a time, and set it only
   after the Librarian confirms: it is a reading of the text, and the text
   stays the authority. Never write definitions in bulk or unasked.
3. Generate:

   ```
   python scripts/gdf.py write --library-data <library-data> --source HB-RIFT \
       --title "Rift Delvers" --requires "GURPS Basic Set 4th Ed.--Characters.gdf" \
       --out "<library>/gca/generated/Rift Delvers.gdf"
   ```

   It refuses a definition GCA would misread (brackets or quotes that don't
   pair up, a double quote in a name, a name without its section's prefix) and
   reads its own output back before writing it.
4. Add it to the library like any data file, with `origin: generated` and
   status `problems`, and ask the Librarian to load it in GCA and build a
   character with it. Set it to `imported` when they have, and note what GCA
   said.

Never edit a generated file: correct the entry and generate again.

## 7. Recording progress

Record every finished step in the journal **as it happens**, with
`scripts/import_journal.py --dir scratch` (`--help` lists every command):

| When | Run |
|---|---|
| Before any step that writes or takes a while | `doing "writing advantage entries, batch 2 of 6"` |
| You ask the Librarian a question | `waiting "the question, in a line"` |
| The Librarian answers | `answered "the decision, in a line"` (first, before acting on it) |
| You push a branch or open a pull request | `repo BRANCH --pr N`; when merged, `repo BRANCH --status merged` |
| The pages are read | `start b-ch2 --source B --category advantages --pages 32-118 --page ch2-layout.json` |
| The report and coverage are checked | `phase b-ch2 converted --out out-ch2` |
| A hand edit, or anything a resumed session must know | `note b-ch2 "..."` |
| After each write batch | `uploaded b-ch2 slug=ID:SIZE ...` (refuses a size that doesn't match the converter's file) |
| All entries written | `phase b-ch2 uploaded`, then after the merge `phase b-ch2 merged` |
| Each bookkeeping file written | `bookkeeping advantages/_index.json NEWID:SIZE` |
| The chapter is finished | `phase b-ch2 bookkeeping`, `clean b-ch2`, then `done b-ch2` |

In the local folder, use the file's path for its ID.

### Resuming after an interruption

Read `show` first. **Waiting:** the Librarian's message may answer that
question; record it with `answered` before doing anything. **Step under way:**
it may be half done; check its result before redoing it. **Entries not yet
written:** the last one may have reached Drive unrecorded; look for it first.
**Phase `uploaded`:** re-run the merge from the current bookkeeping files.
**Phase `merged`:** check each bookkeeping file before writing. Tell the
Librarian you resumed an interrupted import and what was left.

## 8. Report

Give counts (added, updated, skipped, failed), list every failure with its
section and page, say how many of the chapter's entries are linked to GCA
definitions, and name the next `not-imported` chapter.

## Import status

When asked what's been imported, list each source with its chapters and
statuses (from `library.json` and the active campaign's `campaign_sources`),
each data file with its status and counts, counts per category from the
`_index.json` files with how many entries are linked, and the last few log
records.

## Rules

- Write only inside the library's Drive folder. Never write source content to
  the repo, an artifact, or anywhere shared. That includes data files and
  anything read from them. Scratch files in the session workspace are fine;
  delete them at the end (`import_journal.py clean`).
- Never write to GCA's own folders.
- GM-only campaign sources and their entries stay in `gm/`.
- Keep the source's exact wording. Don't paraphrase, summarise or fix it.
- Build a converter before importing a kind of chapter with more than about ten
  entries: a script with tests on an invented PDF (drawn in the test with
  reportlab), in its own pull request, never with source text in the repo.
  Build smaller one-offs (a single table) by hand, show them, and check them.
  Before writing a one-off script for a chapter, ask whether the problem is a
  pattern: if another chapter or book could print it the same way, fix the
  converter or `pdf_layout.py`, with a test, and give the plan an option.
- No silent exceptions in checks. A check, including a throwaway scratch
  script, that skips or excuses anything says so in its output.
- Do repeated work with the repo's scripts rather than inline code written
  fresh each time. If a step keeps needing one-off code, it needs a script.
