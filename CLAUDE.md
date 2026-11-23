# GURPS Assistant Skills

Claude skills for GURPS (4th edition), backed by a private Google Drive library
imported from the group's own PDFs and GURPS Character Assistant (GCA) data
files. Sister project to tfwoodard/wfrp-assistant-skills and
tfwoodard/dnd-assistant-skills; the structure and most of the tooling come
from the WFRP one.

## Repo rules

- Never commit copyrighted or private content: sources (PDFs, homebrew), GCA
  data files (`.gdf`) or anything read from them, anything imported, chapter
  plans, campaign files, character files (`.gca5`), session notes, or
  transcripts. They live in Drive (and in GCA's own folders) only.
- Test fixtures must be invented. Never commit real book text or a real data
  file's definitions, even a line, even in a test or a commit message. Generate
  fixture PDFs in the test itself (reportlab) from invented words, and write
  fixture data files and characters from invented traits.
- Use the terms in `CONTEXT.md`.
- `gurps-library.config.json` is gitignored and must stay that way. The
  library's Drive folder ID and local paths go there or in the claude.ai
  Project's instructions, never in a tracked file.
- `shared/library-layout.md` is the source of truth for the library format, and
  `shared/scripts/` for the library reader and excerpt tool the players' skills
  use. Edit those, never a skill's copy. After editing anything in `shared/`,
  run `./scripts/sync-shared.sh` and commit the synced `skills/*/references/`
  and `skills/*/scripts/` copies. `./scripts/sync-shared.sh --check` verifies them.
- Bump `version` in `.claude-plugin/plugin.json` when skills change.
- Player and GM skills are shared as zips in the library's Drive (layout §7);
  the Librarian's skills (`gurps-library-setup`, `gurps-import`) stay in the
  repo. `scripts/package-skills.py` says which skill goes where. Whenever you
  pull a `main` that changed, run
  `python scripts/package-skills.py --compare players=<the library's skills/manifest.json> --upload <dir>`.
  It says which zips' contents changed and puts them in `<dir>/players/` with
  that folder's `README.md` and `manifest.json`: copy those to the library's
  `skills/`. Then tell the Librarian which skills changed, so the group can
  re-upload them.
- Run the tests with `python -m unittest discover tests` before pushing. CI
  (`.github/workflows/tests.yml`) runs them with ResourceWarning as an error,
  `sync-shared.sh --check`, the packaging, and fails a pull request that changes
  `skills/` or `shared/` without a version bump.
- On the Librarian's Windows computer, use Python 3.12, installed for the user
  (`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`): it has pdfplumber,
  reportlab and Pillow. Since 2026-10 `python` and `python3` on the PATH are a
  3.15 without them, under which the PDF tests skip or fail to import. Run the
  `.sh` scripts from Git Bash.

## GCA on this computer

- GCA's shared data folder (`gca_system_path` in the config) holds the
  published data files (`books/`), the character schema (`gca5.xsd`), GCA's
  book codes (`bookcodes.xml`) and tag definitions (`tagdefs.xml`), and a
  sample character. Read from it freely; **never write to it**.
- The user's GCA folder (`gca_user_path`) holds their own data files, GCA
  library files and characters. Read from it; write only when asked.
- The public guide to the data file format is the *GCA Data File Reference
  Guide* (misersoft.com/gca5/downloads). Read the section for a kind of trait
  before writing a definition of that kind. The character file has no guide:
  `gca5.xsd` and its revision notes are the reference.
- The Librarian hopes to have data files the library generates, and corrections
  to published ones, accepted officially. So follow the published files' own
  conventions (book codes, categories, tag usage, header and author block)
  rather than inventing new ones, and report faults found in published files
  in a form that could be sent to their maintainers; never patch a published
  file.
- Before trusting a reading of either format, try it on the real files:
  `gdf.py parse` on a published data file, `gca5.py read` on a real character.
  Report results as counts and problems; never paste their content into the
  repo, a test or a commit message.

## Library operations

- At the start of a session, read `handoff.md` at the library's root: where the
  work stands, the Librarian's standing decisions, the campaigns and their
  characters, and open items. Before the session ends, bring it up to date and
  save it. It stays in Drive, never in the repo.
- Prefer the library's local folder (layout §1) over the connector whenever it
  can be reached: PDFs and data files need it, and a chapter's hundreds of
  files go through it in seconds.
- During imports and bulk updates, treat Drive reads and writes as trivial.
  When a library file needs checking or correcting, read it and fix it; don't
  weigh whether the transfer is worth it. Bulk reads that would crowd the
  conversation can go to a background agent.
- In claude.ai, files go to and from the library's local folder through the
  device bridge. Use `scripts/drive_bridge.py`: `record` each
  `device_stage_files` result, `push --batch NAME FILE...` to get the
  `device_commit_files` list with every file's `expectedMtimeMs`, then download
  the batch again and `verify`. Never commit from memory of a file's time.
- During an import, these are expected and authorized by the Librarian; don't
  stop to ask about them:
  - writing files to the library's Drive folders;
  - moving a library file to the Drive trash once its replacement is written
    and its size verified;
  - deleting the import's own scratch files (`import_journal.py clean`);
  - pushing a feature branch and opening a pull request (never merging
    unasked; when asked to merge, delete the branch as well);
  - copying packaged skills to the library's skill folders.

## Lessons carried over from the DnD and WFRP Assistants

These cost real time there; don't relearn them.

- **Read structure, don't guess it.** Flattened page text lost headings and ran
  table columns together, and every chapter needed heuristics that kept
  breaking. Read PDFs with positions and fonts (`pdf_layout.py`) and build the
  entries from that (docs/adr/0002).
- **A converter per kind of chapter, with tests.** Before importing a kind of
  chapter with more than about ten entries (advantages, skills, spells, an
  equipment table), write a converter with tests on an invented page, in its
  own pull request. One-offs (a single table) are done by hand, shown, and
  checked.
- **Count every word.** A chapter's coverage check accounts for every word on
  its pages: in an entry, or on the left-out list (art credits, page furniture).
- **No silent exceptions in checks.** A check that skips or excuses a case says
  so in its output. `gdf.py` lists every line it could not read; linking lists
  every entry and definition it could not match.
- **Journal every step as it happens.** Sessions stop mid-import (usage limits,
  closed laptops). `import_journal.py` records progress and conversation state,
  and the hook in `.claude/settings.json` shows it at every prompt.
- **Settle questions before bookkeeping.** Gather every open question, settle it,
  then merge indexes, the log and `library.json` once (`merge_import.py`).
- **Never retype a file.** Write generated files unchanged, check each size, and
  compare downloads with `compare_download.py`.
- **Slugs are for the tools; names are for people.** A slug's suffix
  (`broadsword-lt`) only keeps two files apart, and no player or GM sees it.
  When two entries of one name are different things, rename the new one; a
  different slug is not a fix.
- **Records point at rules; they don't copy them.** An entry points at its GCA
  definitions (docs/adr/0005); a sheet cites pages. Nothing is copied to where
  it can go stale.
- **The builder never encodes rules.** Here that is settled by not having one:
  GCA calculates, from data files (docs/adr/0006). Don't write code that works
  out a cost or a level.
- **Show the Librarian a reading before it is written.** A generated
  definition, a link that isn't an exact match: each is shown beside the text
  it reads and written only once confirmed.
- **Tables are verified by the tool, not by the Librarian** (decided
  2026-11-22: there are too many to confirm by hand). A table reader checks
  every table it reads and refuses one that fails. The Librarian sees the
  first three a reader produces, then only a failure that needs the reader
  changed. Put the effort into the checks.

## What is and isn't built

Built and tested: the library layout; the PDF layout and outline readers, entry
text helpers, renderer, coverage and name checks, merge, journal, entry editor
(all from WFRP); the library reader, lookup and excerpt tools; the data file
reader and writer (`gdf.py`, run against every data file on this computer) and
`add_data_file.py`; the character file reader and sheet (`gca5.py`); the trait
converter (`convert_traits.py`: traits, skills, spells, templates and
meta-traits), which reads and checks the tables set in a trait's text, and with
`equipment_tables.py` the weapon, armor and shield tables.

Not built: converters for rules prose (beyond what the trait converter makes of
a chapter's other sections), equipment descriptions and creatures; linking
entries to definitions; writing to character files. `skills/gurps-import/SKILL.md` and
`skills/gurps-character-sheet/references/character-files.md` say what each
needs first.

## Agent skills

### Issue tracker

Issues live in GitHub Issues on tfwoodard/gurps-assistant-skills, via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
