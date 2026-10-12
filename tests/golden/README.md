# Golden corpus (R8.1, R8.1a)

Hand-picked Polish pages from the **pinned dump**, with the output extraction must
produce for each. Tests run against these and never need a dump.

| Path | What | Edited by |
|---|---|---|
| `pages.toml` | the list: one `[[page]]` per title, with `why` it is in the set | hand |
| `pages/<slug>.wiki` | the page's full raw wikitext, every language, verbatim | `make golden-pull` |
| `manifest.json` | dump pin, page/revision ids and sha1 of each fixture | `make golden-pull` |
| `expected/<slug>.json` | the page's P3 `Word` as indented JSON; `null` for no record; `"TODO"` until blessed | `pytest --update-golden` |
| `store.sqlite.zst` | the fixtures plus exactly the Template/Module pages their expansion touched | `tools/golden.py snapshot` (M4) |

The slug is the title with spaces as underscores (`dzień_dobry`).

- **Adding a page:** add it to `pages.toml`, run `make golden-pull` (needs
  `data/pages.sqlite` from `polwikt scan`), and commit the new `.wiki`, the manifest and
  its `"TODO"` expectation. Then rebuild the snapshot (from M4).
- **Blessing:** `uv run pytest tests/test_golden.py --update-golden` rewrites every
  expectation from the current extractor, including the `"TODO"` ones. Review the
  diff; it is the test.
- **Never edit `pages/` or `store.sqlite.zst` by hand.** `test_fixture_is_intact`
  checks each fixture's sha1 against the manifest.
- Folding (`kotów`, `mamy` produce no record) is P4's job. The per-page expectation
  is still the P3 `Word` with its `form_of` senses; the corpus-level check over the
  whole set arrives with P4 (M11).
- `inspect --golden <title>` shows a fixture's wikitext and parse tree without a dump.
