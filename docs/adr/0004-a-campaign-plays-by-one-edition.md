# A campaign plays by one edition; older books add only what wasn't updated

Carried over from the DnD and WFRP Assistants. Groups mine third edition
worldbooks and adventures for settings while playing fourth edition rules. A
campaign must not mix editions' rules: a 3e advantage or skill that 4e rewrote
is never offered beside the 4e one, but the older book's places, history and
adventure material are still wanted.

So every source and index record carries its `edition` (`4e`, `3e`, or `dfrpg`
for the Dungeon Fantasy Roleplaying Game, which is its own game on the same
engine), a campaign plays by one edition (by default the library's, `4e`), and
an older entry that a newer one updated gets an `updated-by` relation to it,
under the same name or another. In a campaign of the newer edition, that entry
doesn't exist. Everything else from the older source appears, read through the
campaign's edition's rules. Which entries were updated is a judgment call: each
chapter's plan proposes them and the Librarian confirms.

## Considered Options

- **Match by name only.** Rejected: traits were renamed, merged and split
  between editions.
- **Hide everything from older editions.** Rejected: the settings and
  adventures are why the books are in the library.
