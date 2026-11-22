# A plan is only for importing; the campaign's source order chooses between versions

Carried over from the WFRP Assistant (its ADR 0006), where both points were
learned the slow way.

1. **A plan holds only what the import needs to read the source**: which
   headings are entries, where a table's columns fall, which box belongs to
   which section. It lives in Drive beside the source because it is the book's
   outline. It takes no part in anything at runtime, and content decisions are
   not kept in it. An entry's `gca` links and definitions live on the entry and
   are carried over when a chapter is imported again.

2. **Which books are used, and which come first, are campaign settings.**
   `campaign.json`'s `sources` lists the sources in play, highest precedence
   first. When a later book prints something again with changes (a weapon's new
   table line, a longer skill write-up), both entries are kept, joined by
   `version-of`, and each campaign uses the one whose source it lists first.

3. **A shared name is a version by default.** An entry that takes another
   source's entry's exact name in its category is written as a `version-of` it
   without a line in the plan; plans state only the exceptions (`adds-to`,
   `distinct-from`, `updated-by`).

4. **The same holds for data files.** Which data files a campaign loads, and in
   what order, is the campaign's setting (`gca.data_files`), as it is in GCA.
