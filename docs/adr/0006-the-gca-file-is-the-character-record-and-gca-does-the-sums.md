# The GCA file is the character's record, and GCA does the sums

The WFRP Assistant keeps each character as its own JSON record and has a
builder that works every number out from the library. That builder is the
largest and most delicate part of that project. GURPS already has one: GCA
evaluates the data files' formulas (point costs, skill levels from defaults,
bonuses that depend on other traits, modifiers that change costs) and saves
the results in the character file (`.gca5`, XML, described by GCA's own schema
`gca5.xsd`).

## Decisions

1. **The `.gca5` file is the character record.** There is no second record to
   keep in step with it. It lives in the campaign's `characters/` folder.

2. **GCA is the only thing that calculates.** The skills read what GCA saved
   and show it. They never work out a cost or a level themselves, and never
   show a number of their own in place of GCA's.

3. **The skills write only what isn't calculated**: what happens in play
   (points awarded, injuries, money, notes, the campaign log) and edits the
   group asks for. When an edit needs GCA's arithmetic (a new trait, a raised
   level), the file is marked as needing GCA, and its calculated numbers aren't
   relied on until someone has opened and saved it there.

4. **Every write keeps the file it replaces** until the new one has been opened
   in GCA.

## Considered Options

- **Our own record and builder, with import from and export to GCA.**
  Rejected: it means writing GCA's formula engine again and keeping it in step
  with every data file feature, to get numbers that would then disagree with
  the sheet the player prints from GCA.
- **Read-only.** Rejected: recording a session's points and injuries on the
  character is most of what the group asks for after a game.

## Consequences

- Building or changing a character needs a computer with GCA. From a phone, a
  character can be read and its play state updated, not rebuilt.
- The character schema is GCA's and changes with its versions; the reader keeps
  to what the schema documents and says what it doesn't know.
- Writing is not built yet. It needs proving against GCA itself: a file the
  skills changed must open there without complaint.
