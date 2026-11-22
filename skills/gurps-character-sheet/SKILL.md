---
name: gurps-character-sheet
description: Read GURPS characters kept as GURPS Character Assistant 5 files (.gca5) in the group's private Google Drive library, and build a readable sheet from them. Use when the user asks what a character has ("what's Kessa's Stealth", "how many points has Bram spent", "what is she carrying"), wants a character's sheet built or refreshed, wants to add an existing GCA character to a campaign, or wants to check a character against the campaign's point limits and data files.
---

# Character sheets

Read `references/library-layout.md` first, especially §8 (campaigns), §9
(characters) and §12 (GCA data), then `references/character-files.md`.

**The character's GCA file is the record, and GCA does every calculation**
(docs/adr/0006). This skill reads what GCA saved. It never works out a point
cost, a skill level, a defense or an encumbrance level, and never shows a
number of its own where GCA's belongs.

## Find the character

Resolve the library and the active campaign (layout §1, §8). The party's
characters are in `campaign.json` → `party`, each a path to a `.gca5` file in
the campaign's `characters/`. Match the name the user gives against the
character names and the players' names.

A GCA file can hold more than one character; a party file (`.gca5party`) holds
none, only the paths of the characters in it:

```
python scripts/gca5.py list <file>
```

## Read a character

With the library as a folder the session can read (layout §1), or a copy of
the file fetched into the session:

```
python scripts/gca5.py read  <file.gca5> [--character NAME] [--out record.json]
python scripts/gca5.py sheet <file.gca5> [--character NAME] [--out <slug>.md]
```

`read` gives everything GCA saved, as JSON: who the character is, the data
files it was built with, the campaign block (base points, limits, logged
points), the campaign log, and every trait by kind with its points, level or
score, page reference, modifiers and, for weapons, attack modes. `sheet` writes
the readable Markdown sheet from the same record.

Answer questions from `read`. For what a trait *does*, look the trait up in
the library (`gurps-rules-lookup`) by its name and page reference and cite the
entry; the character file holds numbers, not rules text.

Before relying on a character's numbers, compare the data files it names
(`built_with`) with the campaign's `gca.data_files`. Say which differ: a
character built without the campaign's house rules file has different costs.

## Build or refresh the sheet

Write `sheet`'s output beside the character file as `<slug>.md`, replacing the
old one. The sheet is generated: never edit it by hand, and rebuild it
whenever the `.gca5` changes (compare the two files' times).

The sheet says at its foot how many traits it left out because GCA hides them
or uses them as dividers. `read` has them all.

## Add an existing character to a campaign

1. Copy the `.gca5` into the campaign's `characters/` under a slug of the
   character's name (`kessa-of-the-reeds.gca5`). Keep the original where it was.
2. Add it to `campaign.json` → `party` with the player's name.
3. Build its sheet.
4. Report the data files it was built with against the campaign's, and its
   points against the campaign's `creation` limits (the campaign block's own
   numbers, and the sum of the points GCA saved on each kind of trait, which
   the script labels as its own sum).

## Changing a character

**Not built yet.** Until it is, changes are made in GCA, and this skill then
rebuilds the sheet. When asked to record a session's points or injuries on a
character, say so, and put them in the session note (`gurps-session-notes`),
which is where the group will find what is still to be entered in GCA.

`references/character-files.md` says what the skill will be allowed to write
when it is built, and what has to be proved against GCA first.

## Don'ts

- Don't calculate. If GCA's saved number looks wrong, say what it is and why
  it looks wrong, and suggest opening the character in GCA.
- Don't copy rules text onto the sheet; cite the page (`B43`).
- Don't show a GM-only NPC's file (`gm/npcs/`) to anyone but the campaign's GM.
