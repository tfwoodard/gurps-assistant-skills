# GURPS Assistant: layout and lookup contract (layout_version 1)

This file is the single source of truth for how the skills find, read, and
write the private library. It is copied into each skill's `references/` folder
by `scripts/sync-shared.sh` so every skill stays self-contained when uploaded to
claude.ai. Edit it here, then run the script.

The library holds copyrighted material and the group's private play. It lives
in a Google Drive folder that only the group can open. **Nothing from the
library is ever written to the git repo.**

Terms used here (import, source, entry, chapter, Librarian, GM, trait, data
file, …) are defined in the repo's `CONTEXT.md`.

## 1. Locating the library

Resolve the library root folder in this order and stop at the first hit:

1. **Config file.** `gurps-library.config.json` in the current working directory
   or plugin root (Claude Code). Use `drive_folder_id`, and `drive_local_path`
   if it's set (below).
2. **Conversation / Project context.** A Drive folder ID or URL the user gave in
   this conversation, or in the Project's instructions or docs. A folder URL
   looks like `https://drive.google.com/drive/folders/<FOLDER_ID>` (an account
   segment such as `/u/2/` may come before `folders`).
3. **Drive search.** Search Google Drive for a file named `library.json` whose
   contents contain `"gurps_library": true`. Its parent folder is the root. If
   several match, list them and ask which to use.

If none resolve, stop and tell the user how to configure it (README >
Configuration). Do not guess.

After resolving, read `library.json` and check `layout_version`. If it is
higher than the version this file describes, warn that the skills may be out of
date. If it is lower, suggest running `gurps-library-setup` to upgrade it.

Then resolve the **active campaign** (§8) when the task involves one:
characters, session notes, or rules questions at the table.

### Local folder or connector

Google Drive for desktop can show the library as a folder on a computer
(`drive_local_path`: in the config file, or a line in the Project's
instructions such as "GURPS library folder: I:\My Drive\GURPS Assistant"). When
the session can reach that folder, read and write library files there
directly; Drive syncs them. A session can reach it when it is Claude Code on
that computer, or a cloud session linked to that computer through the Claude
desktop app with the folder connected (ask for access to the folder once, if it
isn't). Before using the folder, check that it holds `library.json` with
`"gurps_library": true`.

Otherwise, and on phones, use the Google Drive connector. Both reach the same
files, so a skill can switch between them at any time.

Never copy library content into the repo, a public artifact, or any shared
location outside the library.

### GURPS Character Assistant's folders

On a computer with GURPS Character Assistant 5 (GCA) installed, the config file
may also give `gca_system_path` (GCA's shared data folder, which holds the
official data files in `books/`, the character schema `gca5.xsd`, and
`bookcodes.xml`) and `gca_user_path` (the user's own GCA folder: their data
files, libraries and characters). The Librarian's skills read data files from
there when adding them as sources (§12). Nothing is ever written to
`gca_system_path`.

## 2. Folder structure

```
<Library root>/
├── library.json                 manifest and library source list (§3)
├── handoff.md                   where the work stands, for the next session
├── skills/                      player skill zips to upload to claude.ai (§7)
├── sources/                     files for library sources
│   └── <code>/                  the source's PDFs or documents
│       └── plans/               per-chapter import plans (§6)
├── gca/                         GCA data files (§12)
│   ├── books/                   data files as published or as the group wrote them (.gdf)
│   ├── generated/               data files the library generates from its entries
│   ├── parsed/                  each data file read into JSON, and `_index.json`
│   └── libraries/               GCA library files (.gds): which data files load, in what order
├── library-data/                entries imported from library sources (§4)
│   ├── _import-log.json
│   ├── rules/                   rules prose, maneuvers, conditions, glossary, optional rules
│   ├── tables/                  reference tables (size and speed/range, hit locations, reactions…)
│   ├── attributes/              basic attributes and secondary characteristics
│   ├── advantages/              advantages, perks, languages, cultural familiarities, features
│   ├── disadvantages/           disadvantages and quirks
│   ├── skills/                  skills and techniques
│   ├── spells/                  spells, and the abilities of other magic systems
│   ├── modifiers/               enhancements and limitations
│   ├── templates/               racial and occupational templates, meta-traits, lenses
│   ├── equipment/               weapons, armor, shields, gear, vehicles
│   ├── creatures/               animals, monsters, and NPC write-ups
│   └── lore/                    settings: places, organisations, history
└── campaigns/
    └── <campaign-slug>/
        ├── campaign.json        campaign config (§8)
        ├── characters/          GCA character files and their readable sheets (§9)
        ├── sessions/            session notes (§10)
        │   ├── _index.json
        │   ├── <yyyy-mm-dd>-s<NN>.md
        │   └── raw/             original notes and transcripts, unedited
        ├── sources/             files for player-visible campaign sources
        ├── gca/                 the campaign's own data files and its GCA library file (§12)
        ├── library-data/        entries from player-visible campaign sources
        └── gm/                  shared with the campaign's GM only (§7)
            ├── skills/          GM skill zips to upload to claude.ai (§7)
            ├── sources/         files for GM-only campaign sources (adventures)
            ├── library-data/    entries from GM-only campaign sources
            ├── npcs/            NPCs the players haven't met (GCA files or notes)
            └── sessions/        GM-only notes, one file per session
```

Every `library-data/` folder has the same category subfolders and the same
`_import-log.json`. Create missing category folders as needed.

The categories follow the way GCA sorts traits (§12), so an entry and its GCA
definition are found in the same place.

## 3. Sources

### `library.json`

```json
{
  "gurps_library": true,
  "layout_version": 1,
  "name": "GURPS Assistant",
  "edition": "4e",
  "sources": [
    {
      "code": "B",
      "title": "GURPS Basic Set",
      "kind": "pdf",
      "edition": "4e",
      "files": [
        { "file": "sources/B/GURPS Basic Set - Characters.pdf", "pages": "1-336", "page_offset": 2 },
        { "file": "sources/B/GURPS Basic Set - Campaigns.pdf", "pages": "337-576", "page_offset": -335 }
      ],
      "data_files": ["GURPS Basic Set 4th Ed.--Characters.gdf"],
      "chapters": [
        { "id": "ch2", "title": "Chapter 2: Advantages", "pages": "32-118",
          "status": "imported", "date": "2026-11-22", "notes": "" }
      ]
    }
  ],
  "data_files": [],
  "house_rules": []
}
```

Each source has:

| Field | Meaning |
|---|---|
| `code` | Short unique code, used in citations and entry `source` fields. Unique across the library **and** all campaign sources. For a published book, use the code GCA knows it by (`bookcodes.xml`: `B` Basic Set, `M` Magic, `MA` Martial Arts, `P` Powers, `LT` Low-Tech, `HT` High-Tech, `UT` Ultra-Tech…), so a data file's `page(B34)` and the library's citation name the same book. A book GCA doesn't list takes the code its data file uses in its `page()` tags, and failing that one the Librarian chooses. Homebrew: `HB-<NAME>`. Some codes hold a colon or a slash (`LT:IA`, `M:LoS`, `P3/51` for a Pyramid issue): the code is used as it is in citations and `source` fields, without any colon GCA puts at its end, and with each colon or slash as a hyphen wherever it names a folder or part of a slug (`sources/LT-IA/`, `buckler-lt-ia`). `sources/README.md` lists every folder with its code, book and data files. |
| `title` | Full title. |
| `edition` | What the source was written for: `4e`, `3e`, or `dfrpg` (the Dungeon Fantasy Roleplaying Game). §8 says how editions mix in a campaign. |
| `kind` | `pdf`, `gdoc` (Google Doc), `file` (other text file, including a homebrew document), or `pasted` (text given in the conversation). |
| `files` | The source's files, each with its path in Drive (relative to the folder holding `sources/`), the **printed** pages it holds, and its `page_offset`: the PDF page number minus the printed page number, which is what the tools take as `--page-offset` (2 when a cover and a blank come before printed page 1; negative for a second volume whose PDF starts at 1 but whose printed pages carry on from the first). A book printed as two volumes with one run of page numbers (the Basic Set) is one source with two files. `pages` and entry `page` fields are always printed page numbers; tools add the offset to find the PDF page. Not used for `pasted`. |
| `data_files` | The GCA data files that define this source's traits, by file name (§12). Empty or left out when there is none yet. |
| `chapters` | The source's table of contents, recorded when the source is added. `pages` is the printed page range. `status` is `not-imported`, `imported`, or `problems` (imported, but some entries failed checks: `notes` says which). `date` is the last import. |

A source with no chapters (a one-page homebrew doc) is treated as a single
chapter with `id` `all`.

The library's own `data_files` lists every data file added to the library, with
its status (§12).

### Homebrew documents

Homebrew the group writes itself lives in a **homebrew document**: one Markdown
file per scope (the library, a campaign, or a campaign's GM-only material) in
that scope's `sources/` folder, with `kind: file` and a code like `HB-RIFT`
(docs/adr/0003). It is the master copy: to change an entry, edit the document
and import that chapter again.

- Each `#` heading is a chapter (`Advantages`, `Skills`, `Spells`…); chapter ids
  are the heading's slug. Text before the first `#` is a note to editors.
- Entries are written the way the books write them (a trait's name and point
  cost on its heading line, a skill's attribute/difficulty and defaults, a
  spell's Duration/Cost/Time to cast/Prerequisites lines), so the import finds
  the same fields as for the books.
- A line `Table: <title>` above a table titles it.

A group that already keeps its house rules as a GCA data file adds that file as
a data file (§12); a homebrew document then holds only the wording.

`house_rules` is a list of short strings that apply to every campaign.

### Campaign sources

A campaign's own sources are listed in its `campaign.json` (§8) under
`campaign_sources`, with the same fields plus:

| Field | Meaning |
|---|---|
| `visibility` | `players` (files in the campaign's `sources/`, entries in its `library-data/`) or `gm` (files in `gm/sources/`, entries in `gm/library-data/`). A published adventure is a `gm` campaign source. |

## 4. Entries

Each category folder in a `library-data/` holds:

- **`_index.json`**: a JSON array with one compact record per entry. Skills
  filter on it first, then open only the entries they need. Each record has at
  least `slug`, `name`, `source`, `edition` (its source's, §3), `chapter`,
  `section`, `page`, the entry's `relations`, `audience` and `gca` (§12) when it
  has them, plus category fields:

  | Category      | Extra index fields |
  |---------------|--------------------|
  | rules         | `kind` (maneuver, condition, procedure, glossary, optional), `aliases` |
  | tables        | `about` (one line), `roll` (`3d`, `1d`…, when it is a roll table); `kind: cross-reference` on a cross-reference, `kind: equipment` on a weapon, armor or shield table whose items are `equipment` entries |
  | attributes    | `kind` (basic, secondary), `abbreviation` (ST, HP…), `cost` (as printed: "±10 points/level") |
  | advantages    | `kind` (advantage, perk, talent, language, cultural-familiarity, feature), `types` (as printed: mental, physical, social; exotic, supernatural), `cost` (as printed: "15 points", "5 points/level", "Variable"), `leveled` (true/false), `see` (for a pointer to another trait, as printed) |
  | disadvantages | `kind` (disadvantage, quirk), `types`, `cost` (as printed, its asterisk too), `self_control` (true when the cost carries the asterisk that marks a self-control number) |
  | skills        | `kind` (skill, technique), `attribute` (as printed: DX, IQ, "DX or IQ"; a technique has none), `difficulty` (as printed: Easy, Average, Hard, Very Hard, Varies), `defaults` and `prerequisites` (as printed), `tl` (true for a /TL skill), `specialties` (true when the list marks the skill as taking a specialty), `printed_name` when the list prints marks after the name, `starred` (a technique whose name carries an asterisk) |
  | spells        | `kind` (spell, or the system's own word), `college`, `class` (as printed: Regular, Area, "Information; Area"…), `resisted` (as printed: "Resisted by HT"), `duration`, `cost`, `base_cost` (an Area spell's), `time_to_cast`, `prerequisites`, `modifiers` (each as printed, from the spell's labelled lines), `very_hard` (true for a spell printed with "(VH)"), `printed_name` when it is |
  | modifiers     | `kind` (enhancement, limitation), `cost` (as printed: "+50%", "−10%/level"), `applies_to` (the traits it is printed for, when it isn't general) |
  | templates     | `kind` (racial, occupational, meta-trait, lens), `points` (as printed: "100 points", "Variable"), `types` when the book marks them, and its labelled lists as printed (`attributes`, `secondary_characteristics`, `attribute_modifiers`, `secondary_characteristic_modifiers`, `advantages`, `disadvantages`, `primary_skills`, `secondary_skills`, `background_skills`, `features`). A meta-trait the book describes inside a group entry ("Body of Air" under Elemental Meta-Traits) is an entry of its own that `adds-to` the group |
  | equipment     | `kind` (melee-weapon, ranged-weapon, firearm, heavy-weapon, grenade, armor, shield, gear, vehicle, …), `group` (each table group it is printed in, as printed: a skill with its defaults, or a kind of armor), `skills` (the skills those groups name, each `{"name", "to", "specialty"?, "modifier"?, "defaults"?}`: `{"name": "Kite Flying (Box)", "to": "skills/kite-flying", "specialty": "Box", "defaults": "DX-4"}`, with `modifier` for a group that names a skill at a penalty, "-2"), and its first table row's cells, keyed by the table's column names as printed (`tl`, `cost`, `weight`, `lc`, `damage`, `reach`, `parry`, `st`, `acc`, `range`, `rof`, `shots`, `bulk`, `rcl`, `dr`, `location`, `notes`…), with `modes` when it has more than one row |
  | creatures     | `kind` (animal, monster, npc), `attributes` (the stat line as printed, in its order: ST, DX, IQ, HT, and whatever else it gives, each value as printed: `"Move": "5 (Water Move 8)"`, and the weight printed without a name as `Weight`), and each labelled line of the stat block under its label (`traits`, `skills`, `traits_and_skills`, `cost`), as printed. A group the book describes its creatures under ("Otters", over two kinds of otter) is an entry of its own, with no `attributes`, that each of them `adds-to` |
  | lore          | `kind` (place, organisation, history, other) |

- **`<slug>.json`**: the entry's data, for tools.
- **`<slug>.md`**: the same entry for reading, generated from the `.json`
  (`gurps-import/scripts/render_entry.py`) and never edited by hand: correct the
  `.json` and render again. YAML front matter repeats the index fields, then
  the entry's content in the source's exact wording. Tables are Markdown
  tables, which render in chat; never HTML tables. Sidebars are block quotes
  with a bold title.

### The entry `.json`

```json
{
  "slug": "combat-reflexes", "name": "Combat Reflexes", "source": "B", "chapter": "ch2",
  "section": "Combat Reflexes", "page": 43,
  "fields": { "kind": "advantage", "types": ["mental"], "cost": "15 points", "leveled": false },
  "gca": [ { "item": "AD:Combat Reflexes", "file": "GURPS Basic Set 4th Ed.--Characters.gdf" } ],
  "level": 3,
  "content": [ blocks ]
}
```

`relations` (when present) says how the entry relates to other entries, as
`[{"role": ..., "to": "<category>/<slug>"}]`:

| Role | Meaning | Using it |
|---|---|---|
| `adds-to` | adds to that entry (more detail, optional rules, a new specialty, new modifiers for an advantage) | use both: that entry first, then this one |
| `version-of` | the same thing as that entry, as this source prints it (a supplement's revised weapon table line, an expanded skill write-up, errata) | of the versions whose sources are in play, a campaign uses the one whose source comes first in its `sources` (§8), whichever way the mark points, and says the others exist. Between versions it ranks the same, and with no campaign, the one carrying the mark (the later import) |
| `reprint-of` | the same text printed again (a worldbook repeating a Basic Set advantage) | use either; cite the one whose source comes first in play |
| `distinct-from` | a different thing that could be taken for that entry: the same name in another category (the *Luck* advantage, a *Luck* spell if any), or a near name in the same one | never combine them |
| `updated-by` | an older edition's rules for this were updated by that entry | in a campaign of the newer edition this entry doesn't exist (§8) |
| `counts-as` | for rules, also counts as that entry (a homebrew sword that counts as a Broadsword) | use this entry's own stats; any rule naming that entry applies to this one too |

Every pair of entries that share a name (allowing for plurals, "The", and
parenthetical words) has a relation on the later entry. One that takes the
other's exact name in its category is a `version-of` it unless the plan says
otherwise, and the import writes that itself; for a near name, or a name shared
across categories, the import refuses the entry until the plan says how the
two relate. A skill or advantage that takes a specialty (`Guns (Pistol)`,
`Talent (Animal Friend)`) is one entry for the trait (`guns`, `talent`) when the
book writes it up once and lists the specialties, which then go in its
`fields`; a specialty the book gives a write-up of its own is an entry under
its full name that `adds-to` the trait's entry. `adds-to` also ties a rule to
the entry it changes when they share no name: whoever reads an entry reads
what adds to it.

`audience` is `"gm"` for an entry only the GM should see (an adventure's
secrets). Without it, the entry is for everyone. Only use a `gm` entry for the
campaign's GM (§8), or when there's no campaign and the user says they're the
GM.

`fields` holds the index fields and any other values a tool needs, taken from
the source's words: a skill's `prerequisites`, a weapon's table line (`damage`,
`reach`, `parry`, `st`, or `acc`, `range`, `rof`, `shots`, `bulk`, `rcl`, each
as printed), an armor's `dr` and `location`, a template's trait lists as
printed. An item printed in several rows (a weapon's attack modes, a spear in
the melee and the thrown tables) has every row under `modes`, each keyed by its
own table's columns, with `table` naming the table when they come from more
than one, and `skill` naming the skill a row is used with when the item is in
more than one group (a sword's one-handed and two-handed rows); a row that only gives another mode leaves the item's cells empty, so
a mode lacks the keys it doesn't print. The `notes` cell cites the table's
numbered notes ("[1, 3]"); the entry's content lists the notes it cites, with
their numbers as `keys`. The table itself is a `tables` entry (`kind:
equipment`): each group a heading and a table, then the notes.

`gca` links the entry to its GCA definitions (§12). The numbers a character is
built with come from there, not from `fields`: `fields` records what the book
prints, for lookups and for checking the data file against the book.

`level` is the heading level of the entry's own title on the page.

`content` is a list of blocks, in the source's order. Text keeps the source's
wording, with bold and italic as Markdown marks:

| Block | Fields |
|---|---|
| `heading` | `level`, `text` |
| `paragraph` | `text` |
| `list` | `ordered`, `items` (strings, or `{"text", "items"}` for an item with a sublist), and `keys` for a list of results keyed by a roll ("3 – …", "5-6 – …"): each item's key, as printed |
| `fields` | `title`, `items`: `[{"label", "text"}]` (a spell's "Duration: 1 minute" lines, a skill's "Defaults:" line) |
| `table` | `title`, `columns`, `rows` (cells as printed), `groups` (`{"before": row, "text"}` for rows that head the rows below), `footnotes`, `data`, and `read_with` for a table set in an entry's text (below) |
| `sidebar` | `title`, `content` (blocks) |
| `profile` | `name`, `characteristics` (the stat line, in the printed order), `lines` (`[{"label": "Traits", "text": "…"}]`, as printed) — a creature's or NPC's stat block |

A table set inside an entry's text is not the whole of what the book says
about it. The paragraph before it says what it is a table of, and the one
after it often carries it on past its last row ("further levels continue to
double"), says what to do between two rows ("use the higher"), or closes it
("this table is not open-ended"). Those paragraphs stay where the book prints
them, as the blocks on either side, and the table's `read_with` (`"before"`,
`"after"`, or both) says which are there. Whoever shows a table, quotes it, or
works anything out from its `data` takes those paragraphs with it: a table's
rows alone are never the rule.

A table's `data` has one object per row, keyed by its column headers in words
(`"weapon"`, `"roll"`). "—" is `null`; plain, "+N" and "−N" numbers are
numbers; a roll range ("3–4") is `{"min": 3, "max": 4}` under the roll
column; anything else is the printed text. A row under a group row carries it
as `"group"`.

`chapter` is the chapter `id` from the source's chapter list. `section` is the
heading the entry sits under, as printed. `page` is the printed page the entry
starts on.

Slugs are lowercase, hyphenated, ASCII: `combat-reflexes`, `fast-draw`,
`broadsword`. Each source's entries keep their own files even when names match:
if a slug is already taken by another source, add the source code
(`broadsword-lt`).

A slug is the tools' own handle: it keeps files apart, and no player or GM ever
sees it. What people see is the `name`. Two entries of one name are usually
meant to be read together (a supplement's longer write-up of a skill, a
reprint), and then a suffix on the slug is all they need. Two different things
of one name in one category must be something a reader can tell apart. Where
the book itself gives both the one name and tells them apart by their `kind`
(the enhancement *Armor Divisor* and the limitation *Armor Divisor*, as the
data files also have them), both keep the book's name, the later one's slug
takes its kind (`armor-divisor-limitation`), each is `distinct-from` the other,
and whoever shows one says its kind. Otherwise the later one gets a different
name, and the slug follows the name.

### `_import-log.json`

A JSON array, newest last, one record per import run:
`{"date", "source", "chapter", "category", "added", "updated", "skipped", "failed", "notes"}`.
`updated` counts entries a re-import overwrote; `notes` says why (errata,
better extraction).

## 5. Citing

Cite every rule or entry by source, chapter, section and page:
`(B, ch. 2 › Combat Reflexes, p. 43)`. Use the chapter's number or short title,
whichever the source uses. Where space is short (a character sheet, a list),
the usual GURPS form is enough: the code and the page, `B43`.

If something came from a house rule, say so instead, and say whether it is a
library or a campaign house rule.

### Exact wording

The skills are for help at the table, where a ruling can turn on a rule's exact
words. The goal: anyone in the group gets the library's wording at once,
without asking for it in a particular way, and without the book's text being
written out in Claude's reply (Claude doesn't reproduce book text in its own
words, however the copy is owned).

So whenever an answer depends on exact wording (the user asks for it, or the
ruling turns on a phrase), Claude sends the wording as a file, by default and
without asking first, and its reply paraphrases and cites:

- With a library folder a script can read (§1, or a copy fetched into one),
  `scripts/excerpt.py <ref> [<ref> …] --library <root> --campaign <slug> --out
  <file>` writes each entry, or a part of one by heading path
  (`rules/success-rolls#Critical Success`), unchanged with its citation, and
  prints only what it wrote. Several refs go in one file.
- Without one, the entry's own `.md` file from the library is the file.

Send it with the surface's file tool so it shows in the conversation. Where a
surface has no way to send a file, give the file's link from the Drive
connector. The same holds for GM-only entries, sent only to the GM.

## 6. Importing

### Who imports where

| Who | Imports | Into |
|---|---|---|
| Librarian | library sources and data files | `library-data/`, `gca/` |
| A campaign's GM | that campaign's campaign sources and data files | the campaign's `library-data/` or `gm/library-data/`, and its `gca/` |

Nobody else writes entries. If the connector reports no edit access to the
target folder, stop and say who can import it.

### Where it runs

Importing runs wherever the whole source can be read (docs/adr/0001):

- `gdoc`, `pasted`, and small `file` sources: through the connector, anywhere.
- `pdf` sources and data files: from the local folder (§1): Claude Code on the
  Librarian's computer, or a cloud session linked to it, so the whole file is
  on disk. A rulebook PDF is far past what the connector returns. If neither is
  available, say so and stop.
- A whole book writes hundreds of files, so write them to the local folder
  when it can be reached; through the connector, every file's text passes
  through the conversation.

### PDFs are read by layout, not as flat text

GURPS books are two- and three-column pages with sidebars in the margins,
boxed text, trait write-ups headed by a name and a point cost, and long
equipment tables. Flat text extraction runs columns and table cells together
(docs/adr/0002). The import reads each page's text spans with their position,
font, size and weight (`gurps-import/scripts/pdf_layout.py`), orders them by
column, and finds headings from font size and weight. Each chapter's **plan**
says how the chapter splits into entries (which heading level is an entry,
which section holds which category) and lives in Drive beside the source
(`sources/<code>/plans/<chapter>.json`), never in the repo: it is the book's
outline.

When text extraction garbles a page (a table drawn as art), look at the page
image and transcribe it, and say so in the chapter's notes. If the PDF is
scanned (no text layer), ask before running OCR.

### Entries are written automatically, except tables

Write entries in batches, checking each one: required fields present, no
truncated text, every word of the chapter in an entry or the left-out list.
Report every failure with its chapter and section, and set the chapter's
status to `problems`.

**Tables** are checked by the tool that reads them, not one by one by a
person: characters and play depend on their numbers, and a book has too many
to show each. A table is written only when it passes every check its reader
makes (each row has a cell in each column, the header names each column, each
column's cells line up on the page). The importer is shown the first three
tables a reader produces for a kind of table, to confirm the reader reads them
as the page prints them; after that, only a table that fails a check. A failed
table is never written on a guess: the reader is corrected, with a test, and
the chapter converted again. A table the tools cannot read at all (drawn as a
picture, a flowchart) is transcribed by hand and shown.

### Cross-references

A **cross-reference** is a table the Librarian builds rather than one a source
prints. It lives in `tables/` with `kind: cross-reference` in its front matter
and index record, so no one takes it for source text. Every row says where its
information appears (source, chapter, section, page). Like any table, it's
shown to the Librarian before it's written.

### Re-importing

Re-importing a chapter overwrites its entries: in the local folder (§1), write
over each file; through the connector, write the new file and move the old one
to the Drive trash. Record the count in `updated` with the reason in `notes`.
An entry's `gca` links are carried over from the entry it replaces. No versions
are kept; Drive's revision history covers the rare need.

## 7. Access

- **Library root**: the Librarian edits; everyone else in the group can view.
- **`campaigns/<slug>/`**: the campaign's GM and players can edit.
- **`campaigns/<slug>/gm/`**: shared with that campaign's GM only, with
  inherited access turned off (`inheritedPermissionsDisabled`), so players
  can't open it even though they can edit the rest of the campaign.

Skills never move GM-only material out of `gm/`, and never include it in
answers unless the user is that campaign's GM.

The skills themselves are shared the same way, as zips to upload in claude.ai
(Settings → Capabilities → Skills), each folder with a `README.md` and a
`manifest.json` (version and each zip's SHA-256):

- **`skills/`** at the library root: the player skills (rules lookup, character
  sheets, session notes). Everyone who can view the library can download them.
- **`campaigns/<slug>/gm/skills/`**: GM-only skills, when there are any. GMs
  also use the player skills.
- The Librarian's skills (library setup, import) aren't shared: the Librarian
  uses them from the repo.

## 8. Campaigns

Each folder in `campaigns/` is one campaign, configured by its `campaign.json`:

```json
{
  "name": "Rift Delvers",
  "slug": "rift-delvers",
  "gm": "",
  "edition": "4e",
  "sources": ["HB-RIFT", "MA", "M", "B"],
  "campaign_sources": [],
  "gca": {
    "library": "gca/Rift Delvers.gds",
    "data_files": [
      "GURPS Basic Set 4th Ed.--Characters.gdf",
      "GURPS Magic 4e.gdf",
      "GURPS Martial Arts 4e.gdf",
      "Rift Delvers.gdf"
    ]
  },
  "house_rules": [],
  "creation": {
    "starting_points": 150,
    "disadvantage_limit": -75,
    "quirk_limit": -5,
    "tech_level": 3,
    "notes": ""
  },
  "allowed": {
    "advantages": { "exclude": [] },
    "templates": "all"
  },
  "party": [
    { "character": "characters/kessa-of-the-reeds.gca5", "player": "Sam" }
  ],
  "in_game_date": "",
  "notes": ""
}
```

| Field | Meaning |
|---|---|
| `slug` | Must match the folder name. |
| `gm` | Name or email of the campaign's GM. |
| `edition` | What the campaign plays by: `4e` or `dfrpg`. Left out means the library's `edition`. |
| `sources` | The **sources in play**, highest precedence first: library source codes and this campaign's source codes. Only entries from these sources may be used, and where two of them have versions of one thing (§4, `version-of`) the campaign uses the version from the source listed first. |
| `campaign_sources` | This campaign's own sources (§3). |
| `gca` | How the campaign's characters are built in GCA (§12): its GCA library file, when the group keeps one in Drive, and the data files it loads, in GCA's load order (later files change earlier ones). Every source in play that has data files should have them here; the health check says which don't. |
| `house_rules` | Added to the library's `house_rules`. Where they conflict, the campaign's win. Each is a short string, or `{ "id", "text", "from", "data_file" }` when a data file in `gca.data_files` puts it into effect, so a reader knows GCA already applies it. |
| `creation` | How new characters are made: the starting point total, the limits on points from disadvantages and quirks, the campaign's tech level, and anything else in words. |
| `allowed.<category>` | `"all"`, or `{ "include": [slugs] }` (only these), or `{ "exclude": [slugs] }` (all but these). Applied after the `sources` filter. Categories left out mean `"all"`. |
| `party` | The current party. `character` is a path to the character's GCA file, relative to the campaign folder. |
| `in_game_date` | The current date in the setting, as the GM writes it. |
| `notes` | Free text for the GM: setting, tone, things to keep in mind. |

When a campaign is created, campaign sources go first in `sources`, then the
library's sources newest first, so the GM's material and later books' revisions
take precedence unless the GM reorders them. Ask the GM whether that is the
order they play by.

**Choosing the active campaign**, in this order:

1. A campaign the user names in the conversation (match `name` or `slug`).
2. `default_campaign` in `gurps-library.config.json`, or a campaign named in the
   Project's instructions or docs.
3. If `campaigns/` contains exactly one campaign, use it and say so.
4. Otherwise ask. If the user wants no campaign, use all library sources, with
   only the library's house rules.

**Finding entries for a campaign:**

1. Gather candidates from the library's `library-data/`, the campaign's
   `library-data/`, and, only if the user is the GM, the campaign's
   `gm/library-data/`.
2. Keep entries whose `source` is in `sources`, then apply `allowed`. Drop
   entries with `audience: gm` unless the user is the campaign's GM. Drop
   entries of another edition that are `updated-by` an entry.
3. Entries that share a name follow their `relations` (§4): an entry that
   adds to another is used with it, after it; of versions of one thing
   (`version-of`), the one whose source comes first in `sources` is used and the
   others aren't offered; of a reprint and its original, cite the one whose
   source comes first in `sources`; distinct entries are kept apart (say which
   one you mean when the question could be either).
4. If a filter removes everything the user asked for, say which rule removed it
   rather than quietly widening the search. If the source is in play but the
   relevant chapter isn't imported yet (§3 chapter status), say that instead of
   "not found".

**Editions.** A campaign plays by one edition's rules. A source of an older
edition in its `sources` contributes only what the campaign's edition didn't
update: settings, places, adventures, and creatures read through the campaign's
edition's rules. An entry that's `updated-by` a newer one is never offered.
Which entries were updated is a judgment call; each chapter's import plan
proposes them and the Librarian confirms.

## 9. Characters

A character lives in the campaign's `characters/` folder:

- `<slug>.gca5`: the **character file**, written by GURPS Character Assistant
  and the source of truth (docs/adr/0006). GCA works out every point cost,
  skill level and bonus from the data files loaded when the character was
  built. The file's format follows GCA's own schema, `gca5.xsd`.
- `<slug>.md`: the readable sheet, built from the character file by
  `gurps-character-sheet`. Rebuild it whenever the file changes. Never edit it
  by hand.
- `<name>.gca5party`: a GCA party file, when the group keeps one.

The skills read a character file freely. Writing is not built yet (until it
is, changes are made in GCA); when it is, they write to it only what is not
calculated: what happens to a character in play (points earned and unspent,
hit points and fatigue lost, money, notes, possessions gained and lost) and
changes the group asks for. After any change that GCA must work out (a trait
added, a level raised), the file is marked as needing GCA and the calculated
numbers in it aren't relied on until someone has opened and saved it there.
`gurps-character-sheet`'s references give the details.

Never copy into a session note or a sheet a number the skills worked out
themselves in place of GCA's.

## 10. Sessions

Session notes live in `campaigns/<slug>/sessions/`. They hold the group's
words and the GM's secrets, so they stay in Drive only.

### Session file: `<yyyy-mm-dd>-s<NN>.md`

`NN` is the session number, zero-padded to two digits (`s07`; `s112` past 99).

```markdown
---
session: 7
date: 2026-11-14
title: "The Drowned Stair"
in_game_date: ""
attendees: [Sam, Alex, Jo]
gm: Tom
raw:
  - raw/2026-11-14-s07-transcript.vtt
speakers:
  "Speaker 1": { player: Sam, character: Kessa }
  "Speaker 4": { role: gm }
summary: "One or two sentences."
npcs: []
locations: []
factions: []
items: []
quests: []
tags: []
---

## Summary
## Events
## NPCs
## Loot and rewards
## Advancement
- Character points awarded, and to whom; what they were spent on.
## Injuries and conditions
- Wounds, crippling injuries, afflictions and anything else that carries forward.
## Rulings
## Open threads
- ~~A thread this session resolved~~ (resolved: what happened)
## Open questions
```

Leave out sections that would be empty, except Summary.

### GM-only session notes

Secrets, prep, and anything the players haven't seen go in
`gm/sessions/<same file name>.md`, never in the shared session file. A raw
source that contains GM secrets (the GM's prep notes) is saved in
`gm/sessions/raw/` instead of `sessions/raw/`.

### `sessions/_index.json`

A JSON array with one record per session, sorted by `session`:

```json
{
  "session": 7, "date": "2026-11-14", "file": "2026-11-14-s07.md",
  "title": "The Drowned Stair", "in_game_date": "",
  "summary": "One or two sentences.",
  "npcs": [], "locations": [], "factions": [], "items": [], "quests": [], "tags": [],
  "points_awarded": 3,
  "open_threads": [], "resolved_threads": []
}
```

The index only describes the shared file. `gm/sessions/` has its own
`_index.json` with the same shape, for GM-only searches.

Use the same spelling for a name across all sessions. If a session file or
folder is missing, create it rather than failing.

## 11. Writing

| Writes to | Who |
|---|---|
| `library.json`, `sources/` (files), `gca/`, `library-data/` | Librarian, through `gurps-library-setup` and `gurps-import` |
| a campaign's `campaign.json`, `sources/`, `gca/`, `library-data/`, `gm/` | that campaign's GM |
| a campaign's `characters/`, `sessions/` | the campaign's GM and players |

Files in `sessions/raw/` and `gm/sessions/raw/` are never edited after they're
saved. Update an `_index.json` in the same pass as the files it describes, so
it never points at missing files. In the local folder (§1), change a file by
writing over it; Drive keeps its revision history. The connector can't edit
file contents in place: to change a file through it, write the new version and
move the old one to the Drive trash.

Before writing over a character file, keep the copy it replaces beside it as
`<slug>.<yyyymmdd-hhmmss>.bak.gca5` until the group has opened the new one in
GCA.

## 12. GCA data

GURPS Character Assistant builds characters from **data files** (`.gdf`): plain
text, one trait definition per line, as the *GCA Data File Reference Guide*
describes. The library keeps them alongside its entries (docs/adr/0005): an
entry holds what the book says, in the book's words; a data file holds how GCA
builds the trait. Each is imported from its own original and neither is derived
from the other, except in generated files (below).

### Data files

`library.json` → `data_files` lists every data file in the library:

```json
{ "file": "GURPS Basic Set 4th Ed.--Characters.gdf", "folder": "gca/books",
  "origin": "official", "source": "B", "description": "", "requires": [], "taboo": [],
  "sha256": "", "status": "imported", "date": "2026-11-22",
  "counts": { "Advantages": 0, "Skills": 0 }, "notes": "" }
```

| Field | Meaning |
|---|---|
| `file` | The file's name, exactly as GCA knows it: other data files name it in their `Requires=` and `Taboo=` lines, and a GCA library file lists it by name. Never rename one. |
| `folder` | `gca/books` (as published or as the group wrote it) or `gca/generated` (made by the library, below); for a campaign's own, the campaign's `gca/`. |
| `origin` | `official` (shipped with GCA or its updates), `community` (someone else's, say whose in `notes`), `homebrew` (the group's own), or `generated`. |
| `source` | The source whose traits it defines, when there is one. One file may serve several sources (the Basic Set file covers both volumes) and one source may have several files. |
| `requires`, `taboo`, `description` | The file's own header lines. |
| `sha256` | Of the file as imported, to tell when GCA's updater has replaced it. |
| `status` | `not-imported`, `imported`, or `problems`. |

Each data file is read once into `gca/parsed/<file-slug>.json`
(`gurps-import/scripts/gdf.py`): its header, and each section's items in file
order with their category, name, name extension, the values before the first
tag (an advantage's cost, a skill's type), every tag, and the line they came
from. (Comments and line breaks are not kept: the copy in `gca/books/` is the
file itself.) Data file commands
(`#ReplaceTags`, `#Clone`, `#Delete`…) are kept as commands, not applied: what
a trait finally looks like depends on which files a campaign loads and in what
order.

`gca/parsed/_index.json` has one record per trait definition:
`{"item": "AD:Combat Reflexes", "file", "section", "category", "name", "nameext", "page", "line"}`.
`item` is the trait's name with GCA's prefix for its kind:

| Prefix | GCA section | Library category |
|---|---|---|
| `ST:` | Attributes | attributes |
| `AD:` `PE:` `LA:` `CU:` `FE:` | Advantages, Perks, Languages, Cultures, Features | advantages |
| `DI:` `QU:` | Disadvantages, Quirks | disadvantages |
| `SK:` | Skills (techniques included) | skills |
| `SP:` | Spells | spells |
| `TE:` | Templates | templates |
| `EQ:` | Equipment | equipment |
| (none) | Modifiers, by group | modifiers |

### Linking entries to definitions

An entry's `gca` is a list of the definitions that build it:

```json
"gca": [
  { "item": "SK:Guns (Pistol)", "file": "GURPS Basic Set 4th Ed.--Characters.gdf" },
  { "item": "SK:Guns (Rifle)",  "file": "GURPS Basic Set 4th Ed.--Characters.gdf" }
]
```

One entry often has several (a skill's specialties, an advantage GCA splits
into variants) and some have none (rules prose; a trait no data file covers
yet). The link is proposed by matching names and the definition's `page()` tag
against the entry's page, and anything not matched exactly is shown to the
Librarian. Three lists come out of every linking run and are reported, never
hidden: entries with no definition, definitions with no entry, and pairs whose
printed cost and data file cost disagree.

To use a definition, read it from `gca/parsed/` and then apply the commands of
the campaign's later data files (§8 `gca.data_files`) that name it. Say so
when a campaign's data file changes a trait from what the book prints.

### Generated data files

A source with no data file can be given one. Its definitions are written on
its entries, one at a time, each a reading of the entry's text that the
Librarian confirms beside the text it reads:

```json
"gca": [
  { "item": "AD:Tide Sense", "define": {
      "section": "Advantages", "category": ["Mental Advantages"],
      "values": ["5/10"],
      "tags": { "page": "HB-RIFT12", "mods": "Tide Sense", "gives": "+1 to SK:Boating (Unpowered)" } } }
]
```

`gurps-import/scripts/gdf.py write` gathers a source's `define`s into
`gca/generated/<source title>.gdf`, with a header that names the files it
requires and an `[Author]` section saying it was generated by the library, from
which source, and when. The entries are the master copy: correct the entry and
generate again; never edit a generated file. A generated file is tested by
loading it in GCA and building a character with it before a campaign uses it;
its `status` stays `problems` until someone has.

### GCA library files

A GCA library file (`.gds`) is GCA's own list of data files to load, in order.
A campaign that keeps one in Drive (`gca/<name>.gds`) gives every player the
same data: they copy it and the campaign's data files into their GCA folder.
`campaign.json` → `gca.data_files` repeats the list so the skills know it
without the file.

### Character files

Character files (`.gca5`) are XML, described by GCA's schema `gca5.xsd` in
`gca_system_path` (§1). A character records the library file and data files it
was built with; when those differ from the campaign's `gca.data_files`, say so
before relying on its numbers. §9 says what the skills may write.
