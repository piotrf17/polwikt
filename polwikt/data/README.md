# Config tables

Wiktionary convention data, kept out of Python so that convention changes and scope
changes don't need code edits (R10.5). Each table is filled in by the milestone that
first needs it:

| file | contents | milestone |
|---|---|---|
| `pos_headings.toml` | en.wiktionary POS heading → `Pos` enum (R5.3) | M5 |
| `sections.toml` | section heading → handler (Declension, Synonyms, …) (R5.5) | M5 |
| `labels.toml` | `{{lb\|pl\|…}}` label → typed tag, plus aliases (R6.7) | M6 |
| `templates.toml` | expansion policy: expand / capture / both (R4.2) | M4 |

The dump pin and scope knobs (`languages`, `drop_labels`) live in `polwikt.toml` at the
project root, not here.
