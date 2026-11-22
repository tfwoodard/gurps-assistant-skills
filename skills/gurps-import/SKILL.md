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

1. Read the chapter's pages by layout into scratch:

   ```
   python scripts/pdf_layout.py BOOK.pdf --pages 32-118 --page-offset 0 --out scratch/ch2-layout.json
   python scripts/pdf_layout.py BOOK.pdf --pages 43 --page-offset 0 --text    # look at a page
   ```

   It orders each page's lines by column, marks page furniture (running heads,
   page numbers) and gives heading levels from type size. `--boxes` finds boxed
   panels and ruled tables. `check_coverage.py` prints every line set aside as
   `page furniture`: read them each time, because a body line there is a fault
   to fix, not a line to leave out. If it reports pages with no text layer,
   look at the page images and ask before running OCR.
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

   Converters so far:

   | Kind | Script | Plan says |
   |---|---|---|
   | Trait write-ups (advantages, disadvantages, perks, quirks, enhancements and limitations): a name with its type icons, a cost line under it, then text | `convert_traits.py` | the type sizes of a trait's name and of its cost line (`name_size`, `cost_size`); the icon words; the `sections` that are lists of traits, by heading and page, with their category and kind (every other section becomes a `rules` entry, and so does each box); `intro` (a name for text before the first heading); `boxes` (`leave_out` with the reason, or `adds_to` an entry, or a `name`); `rename` for two different traits of one name in one category; `not_traits` and `leave_out_lines` for name-sized lines that aren't traits; `entries` for an entry's relations, extra fields or audience. Traits are found by their headings, not listed: a name with no cost line under it is an error. Read the pages with `--boxes`, the book's type icons as words (`--icon-fonts`, `--icon-text FONT:GLYPH=[word]`, `--icons-alone`) and its pull quotes set aside (`--aside-fonts FONT@SIZE`); the plan's `layout` records the options used. Check the layout's `gutter_notes` (pages read with the book's usual columns) and the report's `table_like` (lines spaced like table rows: tables set in a trait's text, **not read as tables yet**) and `questions` (words joined across a line end that it could not settle). |

   A chapter of another kind needs a converter built first: a script that
   reads the layout JSON and a plan and writes each entry's `.json` and `.md`
   (`render_entry.py`), `_records.json` (index records) and `_report.json`
   (errors, left-out text, questions), with tests on invented pages in
   `tests/`, in its own pull request. Look at the real pages before designing
   one. The kinds the Basic Set still needs:

   | Kind | What the pages look like |
   |---|---|
   | Skills | name, attribute/difficulty, defaults and prerequisites lines, then prose and specialty lists |
   | Spells (*Magic*) | name, class, then prose and Duration, Cost, Time to cast, Prerequisites, Item lines |
   | Tables in a trait's text | cost and level tables set in the columns without rules (Allies, Warp, Contacts): to be added to `convert_traits.py` |
   | Templates | point total, then attribute, advantage, disadvantage and skill lists with choices |
   | Equipment | long ruled tables by weapon skill or gear kind, with footnotes, and descriptions keyed to table rows |
   | Rules prose | sections, sidebars, tables; the WFRP Assistant's `convert_rules.py` is the model to carry over |
   | Creatures | stat lines and trait paragraphs |

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

**Tables.** Show each table to the importer and write it only after they
confirm it. Take every number from the source, never from memory. Show each
one's rows (or, for a long table, its size and first and last rows, offering
the rest) and compare its row count with the page image. A table printed as a
flowchart or picture is transcribed by hand, keeping every word, shown, and
noted in the chapter's notes.

To correct an entry's fields or relations after an import, use
`scripts/edit_entry.py --library <root> <category>/<slug> --set FIELD=VALUE
--relation ROLE:TARGET --plan sources/<SRC>/plans/<chapter>.json`. It rewrites
the `.json`, renders the `.md` again, changes only that entry's line in
`_index.json`, and gives the plan the same fields and relations in its own
layout, so a re-import keeps them. An entry's `gca` is not set this way (§6).

## 5. Write

**Settle every question before the bookkeeping.** Gather every open question
(same-name decisions, tables to confirm, hand transcriptions to show), settle
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

There is no script for this yet: it needs real entries to be built against.
Build it (`link_gca.py`, with tests on invented entries and an invented data
file) when the first chapter of traits is imported.

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
