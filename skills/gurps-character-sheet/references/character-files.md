# GCA character files

A character is a GURPS Character Assistant 5 file, `<slug>.gca5`, in the
campaign's `characters/` folder (library layout §9). This note says how the
file is laid out, what `scripts/gca5.py` reads from it, and what the skills may
write. The authority on the format is GCA's own schema, `gca5.xsd`, in GCA's
shared data folder (`gca_system_path` in the config file); it has a revision
history at its head, which is the place to look when a file from a newer GCA
holds something this note doesn't mention.

## Layout

The file is XML in the namespace `gca5`. Its root, `gca5`, holds one or more
`character` elements. In each:

| Element | Holds |
|---|---|
| `author` | which version of GCA saved the file |
| `system` | `lastkey`: the highest `idkey` given out so far. Every trait and modifier has a unique `idkey` |
| `library` | the GCA library file and each data file (`book`) the character was built with; `%sys%` and `%user%` stand for GCA's two folders |
| `settings` | rule switches (rule of 20, and so on) |
| `name`, `player`, `bodytype`, `vitals`, `description`, `notes` | who the character is |
| `traits` | the traits, grouped by kind: `attributes`, `cultures`, `languages`, `advantages`, `disadvantages`, `quirks`, `perks`, `features`, `skills`, `spells`, `equipment`, `templates` |
| `loadouts`, `transforms` | which equipment is carried in which loadout; alternate forms |
| `campaign` | `basepoints`, `disadlimit`, `quirklimit`, `basetl`, `loggedpoints`, `otherpoints`, `totalpoints`, money, and `logentries`: the campaign log, one `logentry` per award (`entrydate`, `campaigndate`, `charpoints`, `charmoney`, `caption`, `notes`) |
| `basicdamages`, `damagebreaks`, `skilltypes`, `body`, `hitlocationtable`, … | tables copied in from the data files, so the file stands alone |

Each `trait` (`type` and `idkey` attributes) has:

- `name`, `nameext` (the specialty or other name extension), `cat` (GCA's
  categories), `parentkey` and `childkeylist` (traits filed under a parent, such
  as a template's components);
- what GCA worked out: `points`, `level`, `score` (attributes), `type`
  (a skill's `DX/A`), `step` and `stepoff` (a skill's level relative to its
  attribute), `count`, `cost`, `weight` (equipment);
- `calcs`: how it got there (base levels, bonus levels, costs before and after
  modifiers);
- `ref`: the data file tags the trait was built from (`page`, `needs`, `gives`,
  `default`, `mods`, …) and the user's own `usernotes`;
- `attackmodes`: one `attackmode` per weapon mode, with the mode as the data
  file gives it (`damage`, `reach`, …) and as worked out for this character
  (`chardamage`, `charskillscore`, …). Files from before schema revision 28
  have a single `weaponmodesdata` block instead, with several modes' values run
  together with `|`;
- `armordata`, `modifiers` (each a `modifier` with `name`, `group`, `cost`,
  `level`, `value`), `bonuses` and `conditionals` (what the trait gives).

## What the reader gives

`gca5.py read` returns, per trait: `id`, `name`, `nameext`, `full_name`, and
whichever of `points`, `score`, `level`, `type`, `relative`, `count`, `cost`,
`weight`, `page`, `usernotes`, `notes`, `mainwin`, `parent`, `hidden`,
`modifiers`, `modes` the file has. Everything is as GCA saved it.
`points_summed_here` is the one thing the script adds up itself.

It has been checked against the sample character GCA installs (saved by an
early GCA 5, in the older attack mode layout) and against characters saved by
GCA 5.0.202 (the current `attackmodes` layout). In the sample and in the one
current character compared, the points on the traits add up to the campaign's
base points plus the points in its log.

## What may be written (when writing is built)

Decided in docs/adr/0006; none of it is built.

| Change | Needs GCA afterwards? |
|---|---|
| A campaign log entry (points or money awarded) and the `campaign` totals it changes | to be proved: whether GCA recomputes the totals from the log on load |
| `usernotes` on a trait; the character's `notes` and `description` | no |
| Current injury, fatigue and other play state | to be decided: GCA has no field for most of it, so it may belong in the session notes and on the sheet instead |
| Equipment gained, lost or spent (`count`) | yes: weight and cost totals are calculated |
| A trait added, removed or raised | yes: everything about it is calculated |

Rules for any write:

1. Keep the file being replaced as `<slug>.<yyyymmdd-hhmmss>.bak.gca5` until the
   new one has been opened in GCA.
2. Change only the elements the edit is about; leave every other byte of the
   file as GCA wrote it.
3. New traits and modifiers take `idkey`s above `system/lastkey`, and `lastkey`
   is raised.
4. Check the result against `gca5.xsd` before it replaces the file.
5. When the change needs GCA, say so in the reply and on the rebuilt sheet, and
   don't show calculated numbers as current until the file has been opened and
   saved in GCA.
