# GURPS Assistant Skills

Claude skills for running **GURPS, 4th edition** at the table. They import game
material from **sources you own** (Steve Jackson Games PDFs, your own homebrew,
and GURPS Character Assistant data files) into a private library, then use it
to:

| Skill | What it does |
|---|---|
| `gurps-library-setup` | Creates, connects, upgrades, and checks your private library in Google Drive; creates campaigns and sets up sharing |
| `gurps-import` | Imports traits, spells, equipment, rules and tables from a source, one chapter at a time; adds GCA data files, links entries to their GCA definitions, and generates a data file for a book that has none |
| `gurps-rules-lookup` | Answers rules questions mid-session, citing chapter, section and page |
| `gurps-character-sheet` | Reads GURPS Character Assistant characters and builds a readable sheet from them |
| `gurps-session-notes` | Turns your notes or transcripts into session notes, then searches them, writes "previously on…" recaps, and tracks open threads and character points |

Words like *source*, *entry*, *chapter*, *data file*, *definition*, *Librarian*,
and *GM* have specific meanings here; see [`CONTEXT.md`](CONTEXT.md).

**Status: a new project.** The library format, the shared tooling, the GCA data
file reader and writer and the character file reader are built and tested. No
first converter (trait write-ups) is built and runs clean on the Basic Set's
advantages chapter; tables set inside a trait's text, entry-to-GCA linking and
writing to character files are not built yet.

## Working with GURPS Character Assistant

[GURPS Character Assistant 5](https://www.sjgames.com/gurps/characterassistant/)
(GCA) already builds GURPS characters, from data files that cover most of the
line. These skills work beside it rather than replacing it:

- **Books and data files are both imported.** The PDF gives the rules in the
  book's words, to look up and cite. The data file gives what a character is
  built with. Entries point at their GCA definitions
  ([ADR 0005](docs/adr/0005-gca-data-files-are-imported-beside-the-books.md)).
- **GCA does the arithmetic.** A character is its GCA file; the skills read
  what GCA saved and never work out a cost or a level themselves
  ([ADR 0006](docs/adr/0006-the-gca-file-is-the-character-record-and-gca-does-the-sums.md)).
- **Books GCA has no data file for can get one**, generated from definitions
  the Librarian confirms one trait at a time.

You don't need GCA to look up rules or keep session notes. You need it to build
and change characters.

## No copyrighted content lives in this repo

This repository contains **only skill instructions and tooling**. Your sources,
GCA's data files, everything imported from them, and your campaigns live in a
**Google Drive folder you control**, shared only with your group. The skills
read and write that folder through Google Drive for desktop or Claude's Google
Drive connector.

`.gitignore` blocks the local config file, PDFs, data files, character files,
transcripts, and the library's folder names, in case something lands in a clone
by accident. Test fixtures are invented. Please keep it that way in pull
requests.

You need your own legal copies of the books and of GCA.

## How it fits together

```
 GitHub (public)                  Google Drive (private, your group only)
 ┌───────────────────────┐        ┌──────────────────────────────────────────┐
 │ skills/*/SKILL.md     │        │ GURPS Assistant/                         │
 │ shared/library-layout │─reads─▶│  library.json  ← sources, data files     │
 │ (no game content)     │ writes │  sources/      ← PDFs, homebrew docs     │
 └───────────────────────┘        │  gca/          ← data files, read & made │
            ▲                     │  library-data/<category>/ ← entries      │
            │                     │  campaigns/<slug>/campaign.json          │
            │                     │    characters/ ← .gca5 files and sheets  │
            │                     │    sessions/  gca/  sources/             │
            │                     │    gm/         ← the campaign's GM only  │
            │                     └──────────────────────────────────────────┘
 gurps-library.config.json (gitignored): Drive folder, local path, GCA's folders
```

The full folder layout, file formats, and rules are in
[`shared/library-layout.md`](shared/library-layout.md). Design decisions are in
[`docs/adr/`](docs/adr/).

## Roles

- **Librarian:** the one person who maintains the shared library: adds
  sources and data files, imports them, and sets library-wide house rules.
- **GM:** runs one campaign, controls its settings, imports its adventures and
  homebrew, and is the only one who can open its `gm/` folder.
- **Players:** can view the library and edit their campaign's characters and
  sessions.

One person can be both Librarian and GM.

## Setup

### 1. Connect Google Drive

In claude.ai, open **Settings → Connectors** and connect **Google Drive**.
Everyone in the group who uses the skills needs this. The Librarian also
needs **Google Drive for desktop**, so PDFs can be imported from the computer
(see [ADR 0001](docs/adr/0001-import-runs-where-the-whole-source-is-readable.md)),
and Python 3.12 or later with `pdfplumber` and `pypdf`.

### 2. Install the skills

**Claude Code (plugin):**

```
/plugin marketplace add tfwoodard/gurps-assistant-skills
/plugin install gurps-assistant@gurps-assistant-skills
```

**claude.ai (upload):** the Librarian packages the skills and puts them in the
library's Drive:

```bash
python scripts/package-skills.py     # writes dist/players/ (and dist/gm/ when there are GM skills)
```

Players download the zips in the library's `skills/` folder and upload each
under **Settings → Capabilities → Skills**. The Librarian uses library setup
and import from this repo; they aren't packaged.

### 3. Create or connect the library

Ask Claude: *"Set up a new GURPS library in my Drive folder &lt;folder URL&gt;"*
(or *"connect to the GURPS library at &lt;folder URL&gt;"*). Whoever creates it
is the Librarian. Then ask Claude to share it with your group.

### 4. Create a campaign

Ask Claude: *"Create a campaign called Rift Delvers, GM'd by me."* Each
campaign's `campaign.json` holds its sources in play, the GCA data files its
characters are built with, house rules, starting points and limits, bans, the
party and the current in-game date. To change any of these, just ask.

### 5. Import

Importing happens one **chapter** at a time, from where the whole PDF can be
read: Claude Code on the Librarian's computer, or a claude.ai session linked to
it through the Claude desktop app.

1. Put the PDF in the library's `sources/<code>/` folder (for example
   `sources/B/` for the Basic Set) and ask *"add the Basic Set as a source"*.
   Claude reads the chapter list from the PDF's bookmarks and checks it with
   you, and looks for the book's GCA data file.
2. Ask *"add the Basic Set's data file"*. Claude reads it, reports anything in
   it that doesn't parse, and files it in the library.
3. Ask *"import chapter 2 of the Basic Set"*. Claude reads the chapter's pages
   by layout, proposes a plan, converts, checks that every word landed
   somewhere, writes the entries, and links them to their GCA definitions.
4. Ask *"what's left to import?"* at any time.

Entries keep the source's exact wording and are cited by chapter, section and
page, e.g. *(B, ch. 2 › Combat Reflexes, p. 43)*. Tables are checked by the
tool that reads them; you are shown the first few, and after that only one that
fails a check.

**Homebrew** lives in a homebrew document: a Markdown file per library or
campaign, imported a chapter at a time
([ADR 0003](docs/adr/0003-homebrew-is-written-in-a-library-document.md)). House
rules you already keep as a GCA data file are added as a data file.

### 6. Characters

Build characters in GCA and save them in the campaign's `characters/` folder.
Ask *"build Kessa's sheet"* or *"what's Kessa's Stealth?"*. Changes are made in
GCA.

### 7. Record sessions

After each game, give Claude your notes or a transcript:

> *"Add tonight's session from these notes: …"*

The original is saved unedited in `sessions/raw/`. Claude writes a structured
session file (summary, events, NPCs, loot, character points, injuries, rulings,
open threads). Then ask things like *"When did we first meet the smuggler?"* or
*"Give me a previously-on for tonight."* Anything secret goes in the campaign's
`gm/` folder, which players can't open.

## Configuration

The skills look for the library in this order, and use the first one they find:

1. **`gurps-library.config.json`** (Claude Code). Copy the example and fill it in:

   ```json
   {
     "drive_folder_id": "1AbC...xyz",
     "drive_folder_name": "GURPS Assistant",
     "drive_local_path": "I:\\My Drive\\GURPS Assistant",
     "gca_system_path": "C:\\ProgramData\\Steve Jackson Games\\GURPS Character Assistant 5",
     "gca_user_path": "C:\\Users\\<you>\\Documents\\GURPS Character Assistant 5",
     "default_campaign": "rift-delvers",
     "edition": "4e",
     "layout_version": 1
   }
   ```

   - `drive_folder_id`: the last part of the folder's URL,
     `https://drive.google.com/drive/folders/`**`1AbC...xyz`**.
   - `drive_local_path`: where Google Drive for desktop shows the library on
     your computer (backslashes doubled in JSON). Needed for importing PDFs.
   - `gca_system_path`, `gca_user_path` (optional): GCA's shared data folder
     (it holds `gca5.xsd` and the published data files) and your own GCA
     folder. Needed for adding data files.
   - `default_campaign` (optional): the campaign used when you don't name one.

   This file is **gitignored**. Don't commit it.

2. **Project instructions** (claude.ai). Uploaded skills can't read a local
   file, so put lines like these in your claude.ai Project's instructions:

   > GURPS library: https://drive.google.com/drive/folders/1AbC...xyz
   > GURPS library folder: I:\My Drive\GURPS Assistant
   > Default campaign: rift-delvers

3. **Automatic discovery.** If neither is set, the skills search your Drive for
   a `library.json` containing `"gurps_library": true` and ask you to confirm if
   there's more than one.

To check the connection at any time, ask *"check my GURPS library"*.

## Developing

```
.claude-plugin/        plugin + marketplace manifests
.claude/settings.json  hook that shows an unfinished import at every prompt
CONTEXT.md             glossary of the project's terms
docs/adr/              design decisions
docs/agents/           settings for agent skills (issues, labels, domain docs)
shared/                reference files and scripts shared by the skills (edit here)
skills/<name>/         SKILL.md + references/ and scripts/ (some are synced copies)
skills/gurps-import/scripts/gdf.py             GCA data file -> JSON and index; entries' definitions -> a data file
skills/gurps-import/scripts/add_data_file.py   add a GCA data file to the library, or read it again after it changed
skills/gurps-import/scripts/convert_traits.py  trait write-ups (advantages, modifiers...) -> entries
skills/gurps-import/scripts/book_words.py      the words a book prints whole, to settle words broken at a line end
skills/gurps-import/scripts/open_page.py       open a source's PDF at a printed page, to check an import against it
skills/gurps-import/scripts/pdf_outline.py     PDF bookmarks -> chapter list with printed pages
skills/gurps-import/scripts/pdf_layout.py      PDF pages -> lines (by baseline and column) with style, boxes
skills/gurps-import/scripts/entry_text.py      text helpers for converters (styles, hyphens, lists, table data)
skills/gurps-import/scripts/render_entry.py    entry .json -> Markdown
skills/gurps-import/scripts/check_coverage.py  check converted entries lost no words of the pages
skills/gurps-import/scripts/check_names.py     check new entries sharing a name have a relation
skills/gurps-import/scripts/edit_entry.py      correct an entry's fields or relations in place
skills/gurps-import/scripts/merge_import.py    merge index records, log, chapter status
skills/gurps-import/scripts/import_journal.py  progress journal for resuming an import
skills/gurps-import/scripts/print_upload.py    print files for connector uploads
skills/gurps-import/scripts/compare_download.py  check a Drive download against the upload
skills/gurps-character-sheet/scripts/gca5.py   GCA character file -> JSON record and Markdown sheet
skills/gurps-rules-lookup/scripts/find_entry.py  find entries by name for a campaign
shared/scripts/library.py, excerpt.py          the library reader and the exact-wording tool
tests/                 tests; every fixture is invented
scripts/sync-shared.sh copy shared/ into each skill  (--check to verify)
scripts/package-skills.py  zip the player and GM skills for claude.ai
scripts/drive_bridge.py    ledger for moving files through the claude.ai device bridge
```

Run the tests with `python -m unittest discover tests`. The PDF tools need
`pdfplumber` and `pypdf`; the tests also need `reportlab` to generate their
fixture PDFs.

## License

The contents of this repository (skill instructions, the library spec, and
scripts) are released under the [MIT License](LICENSE).

This license covers only what's in this repo. It doesn't cover your sources,
GCA or its data files, anything imported from them, or your group's campaign
files, none of which are, or should ever be, stored here. GURPS is a trademark
of Steve Jackson Games, and GURPS Character Assistant is its product; this
project is unofficial and not affiliated with or endorsed by Steve Jackson
Games.
