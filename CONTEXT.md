# GURPS Assistant

Skills that help a group run GURPS (4th edition) at the table, using game material the group owns, kept in a private library, alongside GURPS Character Assistant.

## Language

### Importing

**Import**:
Turning a source into entries in the library data, or a data file into the library's GCA data.
_Avoid_: Ingest, extract, parse

**Source**:
A document that entries are imported from: a rulebook or supplement PDF, an adventure, or a homebrew document. A data file is not a source; it belongs to one.
_Avoid_: Book (when homebrew is meant)

**Library source**:
A source imported by the Librarian into the shared library, available to any campaign that puts it in play.

**Campaign source**:
A source imported by a campaign's GM into that campaign only, such as a published adventure or the GM's own homebrew. Other campaigns never see it.
_Avoid_: Private source

**Sources in play**:
The ordered list of sources a campaign uses.
_Avoid_: Enabled books, allowed books

**Code**:
A source's short name in citations (`B` for the Basic Set, `MA` for Martial Arts). For a published book it is the code GCA uses, so a data file's page reference and the library's citation name the same book.
_Avoid_: Abbreviation, book ID

**Edition**:
What a source was written for (4e, 3e, or the Dungeon Fantasy Roleplaying Game), and what a campaign plays by.
_Avoid_: Version, ruleset

**Chapter**:
One part of a source, as listed in its table of contents, with its printed page range. A chapter is imported in one go and tracked as not imported, imported, or imported with problems.
_Avoid_: Section, page (as the unit of import)

**Plan**:
How the import reads one chapter: which headings start entries and which category each section holds. A helper for importing only: nothing reads it at runtime. Kept in Drive beside the source.
_Avoid_: Config, mapping

**Entry**:
One imported game item, such as an advantage, skill, spell, piece of equipment, rule, or table, in the source's own words, along with the source, chapter, section and page it came from.
_Avoid_: Record, item

**Version**:
One of two or more entries for the same thing in different sources (a weapon as the Basic Set prints it and as Low-Tech revises it), joined by a *version-of* mark. A campaign uses the version from the source that comes first in its sources.
_Avoid_: Override, duplicate

**Relation**:
How an entry relates to another: it *adds to* it, is a *version of* it, is a *reprint of* it, or is *distinct from* it. An older edition's entry can be *updated by* a newer edition's. An entry can also *count as* another for rules purposes.
_Avoid_: Override (as the general term), duplicate

**Audience**:
Who an entry is for: everyone, or only the GM.
_Avoid_: Visibility (that's for campaign sources)

**Homebrew document**:
A Markdown source the group writes in Drive to hold its own homebrew, one per scope (the library, a campaign, or a campaign's GM-only material). It is the master copy of the wording.

**Cross-reference**:
A table the Librarian builds to link names or entries across sources, citing where each one appears. It belongs to no source.

**Library data**:
All the entries imported into the library.

### GCA

**GCA**:
GURPS Character Assistant 5, the program the group builds characters with. It does every calculation.
_Avoid_: The builder, the app

**Trait**:
Anything a character has that GCA tracks: an attribute, advantage, perk, disadvantage, quirk, skill, technique, spell, template or piece of equipment. The word is GCA's and the books'.
_Avoid_: Ability, feature (a feature is one kind of trait), stat

**Data file**:
A GCA file (`.gdf`) of definitions, usually for one book. Published ones come with GCA; a group may write its own.
_Avoid_: GDF (in prose), book file, data set

**Definition**:
One trait as a data file defines it: its name, the values before its tags (a cost, a skill type) and its tags. An entry says what a trait means; a definition says how GCA builds it.
_Avoid_: Record, item, entry (an entry is the book's text)

**Item name**:
A definition's name as GCA refers to it, with the prefix for its kind: `AD:Combat Reflexes`, `SK:Guns (Pistol)`.
_Avoid_: ID, key

**Tag**:
One `name(value)` pair in a definition: `page(B43)`, `gives(+1 to ST:Basic Speed)`.
_Avoid_: Field, attribute, property

**Command**:
A line in a data file that changes what an earlier file defined (`#ReplaceTags`, `#Clone`, `#Delete`). Kept as written at import; applied only in a campaign's load order.
_Avoid_: Directive (GCA uses that word for something else), patch

**Link**:
An entry's pointer to the definitions that build it. Proposed by matching names and pages, confirmed by the Librarian where the match isn't exact.
_Avoid_: Mapping, binding

**Generated data file**:
A data file the library writes from definitions kept on a source's entries, for a source that has no published one. The entries are the master copy.
_Avoid_: Export, compiled file

**Load order**:
The data files a campaign's characters are built with, in the order GCA loads them. Later files change earlier ones.

**GCA library file**:
GCA's own list of data files to load (`.gds`). Not the library.
_Avoid_: Library (alone, when this is meant)

### People

**Librarian**:
The one person who maintains the library: imports library sources and data files, corrects entries, and sets library-wide house rules.
_Avoid_: Owner, admin, GM (when the library role is meant)

**GM**:
The Game Master of one campaign, who controls that campaign's configuration, campaign sources, and GM-only notes.
_Avoid_: DM, owner

**Player**:
A member of the group who plays a character in a campaign.
_Avoid_: User

### Characters

**Character file**:
The GCA file (`.gca5`) that is a character's record. GCA writes it and works out every number in it.
_Avoid_: Character record (there is no second record), save file

**Sheet**:
The readable page built from a character file. Generated, never edited.
_Avoid_: Character file (when the generated page is meant)

**Character points**:
What characters are built with and awarded in play.
_Avoid_: XP, experience

**Campaign log**:
The list of awards (points and money) GCA keeps in a character file.

**Template**:
A package of traits taken together: a racial template, an occupational template, a meta-trait, or a lens that changes another template.
_Avoid_: Class, race (as the general term), package

**Modifier**:
An enhancement or limitation applied to a trait, changing its cost by a percentage.
_Avoid_: Mod (in prose), option

**Specialty**:
The particular field a skill or advantage is taken in (`Guns (Pistol)`); GCA calls it the name extension.
_Avoid_: Specialisation, subtype
