# PLAN.md — implementation milestones

Spec: `REQUIREMENTS.md`. Working rules: `CLAUDE.md`. Requirement IDs (`R3.2`, `R6.6a`)
are cited per milestone so exit criteria trace back to the spec.

**Progress:** M0 ✅ M1 ✅ (both restarted from scratch 2026-10-11) — next is M2.
Plan revised 2026-10-11 after a review against the live wiki, the dump index and the
pinned upstream code (REQUIREMENTS §12, decisions 6–10). The first M0/M1 attempt is in git
history (`6fced42`); its lessons are folded into the M1 notes below, not its code.

**Shape of the plan.** The **proto schema** gates every extractor and is done. The
**dump + P1 scan** gates everything real: golden fixtures come from the pinned dump (not
the live wiki, decision 7), so M3 follows M2. M4 wires up expansion and, as a side
effect, records what each fixture touches — that record becomes the committed golden
store, which is what lets every later milestone test without a dump. After that the
extractors go in dependency order — structure, senses, paradigms — each graded by the
same golden harness. There is no P2 milestone: the subset pass is deferred (decision 6).

```
M0 ─ M1 schema ─────────────────────────────────┐
  └─ M2 dump + P1 ─ M3 fixtures ─ M4 expansion ───┴─ M5 structure ─ M6 senses ─┬─ M7 nominal
                                                                                  ├─ M8 verbal
                                                                                  ├─ M9 pron/etym
                                                                                  └─ M10 relations
                                     M11 P4 finalize ─ M12 full run ─ M13 quality ─ M14 release
```

---

## M0 — Repo skeleton and tooling ✅
*Done.*

- uv + make toolchain; Python 3.13 pinned in `.python-version` and installed by uv;
  `uv.lock` committed; dev tools and the `wiktextract` oracle in a PEP 735 `dev` group.
- Upstream git-pinned by SHA (R10.2): `wikitextprocessor@04e98337`,
  `wiktextract@32bce658` (both main as of 2026-10-06), with `tests/test_upstream.py`
  smoke-testing the API we build on — SQLite `Wtp(db_path=…)`, template expansion, and
  a Lua `#invoke` on Polish text.
- Package layout per R10.4, each subpackage a documented stub.
- `polwikt.toml` (dump pin placeholder, `languages`, `drop_labels`) and a loader that
  validates every key loudly (R10.5). Per-section data tables (POS headings, labels,
  template policy) arrive with the milestone that uses them.
- CLI with the full R10.3 surface; `config` works, every pass fails with a non-zero exit
  naming the milestone that delivers it.
- `make check` = ruff lint + format check + `mypy --strict` + pytest; CI runs the same
  (`.github/workflows/ci.yml` — unverified until the repo has a remote).

---

## M1 — Protobuf schema and corpus I/O ✅
*Done. 78 tests.* Beyond the bullets below: every readable string is one `RichText`
message (plain text + codepoint `LinkSpan`s + source wikitext), so R7.6a is satisfied
the same way everywhere; shards are sequences of independent zstd frames so the index
stores a real seekable `Location` (R7.3); a frame cut short raises instead of reading
as a shorter shard, and `read_corpus` checks `Corpus.word_count` to catch a cut exactly
on a frame boundary; codegen freshness is a pytest test, so it fails locally, not just
in CI. Participle entries link from the verb's `Form.record` (decision 10).

- `proto/polwikt.proto`: `Word`, `EtymologyGroup`, `PosEntry`, `Sense`, `Form`,
  `LinkSpan`, `Pronunciation`, `Relation`, `Descendant`, `Example`, `TemplateCall`,
  `FormOf`, `Corpus`, and the grammatical enums (case, number, gender, animacy, person,
  tense, mood, aspect, degree, voice, non-finite forms) — §7, R7.1/R7.6–R7.8.
- Include what the spec review found real entries carry: POS `PREPOSITIONAL_PHRASE`,
  `AFFIX`, `CIRCUMFIX`, `COMBINING_FORM` (R5.3); a `Government` message on `Sense` for
  `{{+obj}}` (R6.11); a collocation example kind for `{{coi}}` (R6.12); `Word`-level
  alternative forms, trivia and references (R5.5); prose (usage notes, trivia) stored
  plain + marked up like glosses (R7.6a); a link from a verb `Form` to its participle
  record (decision 10); dialect pronunciations as `raw_tags`.
- Design rules learned the first time round: **no `map<>` fields** (unspecified wire
  order breaks G5; enforce with a test over the descriptors); `Corpus` metadata written
  **out of band** to `corpus.meta.pb` (its timestamp would break byte-identical shards);
  a cell covering several cases becomes **one `Form` per case** so tags stay scalar;
  `case` is a C++ keyword, so the field is `grammatical_case`.
- `make proto` → committed `_pb2.py`/`_pb2.pyi`; CI fails if regeneration dirties the tree.
- `polwikt/proto/io.py`: varint-delimited zstd shard writer/reader with `-of-N` names
  resolved at close (R7.2), `index.sqlite` helpers (R7.3), JSON view (R7.5),
  deterministic serialization.

**Exit:** round-trip tests incl. a 50k-message sharding test and a two-run byte-identity
test; a `LinkSpan` test on non-ASCII text proving codepoint offsets (R7.6a); enums cover
every §6 category with `_UNSPECIFIED = 0`; a test that no message has a map field.

**Risk:** getting this wrong is expensive later (R7.6 forbids renumbering). Review the
schema against §6 *before* writing extractors, not after.

---

## M2 — Dump acquisition and P1 scan
*2–3 days of work, plus ~1 h wall clock per scan.*

- `polwikt fetch`: download the pinned recombined file
  (`enwiktionary-20261001-pages-articles.xml.bz2`, 1.65 GB, sha1 `f9ed426c…`) with a
  descriptive User-Agent, sha1-verify (R2.1, R2.1a); write the pin to `polwikt.toml` in
  its own commit.
- Streaming reader over `lbzcat` — never decompress to disk (R2.4). Upstream's
  `parse_dump_xml()`/`process_dump()` can't be used as-is: they call `add_page` with no
  page id or revision id, have no per-page content filter, and silently skip
  `/documentation`, `/testcases` and non-wikitext pages. Write our own `lxml.iterparse`
  loop over upstream's `decompress_dump_file()` (declare `lxml` as a direct dependency),
  counting every skip.
- P1 store in **upstream's own `pages` schema** so `Wtp(db_path=…)` reads it directly,
  plus our side tables `page_meta`, `all_titles`, `scan_meta` (R3.1, R3.2a). ns-0 kept
  **only** on a `==Polish==` heading line (R3.2); R2.2 namespaces unfiltered (R3.3);
  everything else title-only; redirects recorded (R2.3).
- Resumability + predicate fingerprint (R3.4); read/kept counters (R3.5).
- `TMPDIR`/`SQLITE_TMPDIR` inside the project share — `/` has 6.8 GB (§9).

**Exit:** `pages.sqlite` built from the pinned dump; kept ns-0 count lands in
**1–3×10^5** (expect ~1.8×10^5 from the category counts; near 0 or near 10^7 means the
predicate is broken); re-running skips; scan wall clock vs R9.1 (≤60 min), store size,
and Template/Module page counts recorded. **Decision point:** if `pages.sqlite` is too
large to stay in page cache on this box, revive P2 (decision 6).

---

## M3 — Golden fixtures and test harness
*Needs M2. 1–2 days.*

- `tools/golden.py` pulls ~50 chosen pages' raw wikitext from `pages.sqlite` into
  `tests/golden/` (R8.1). A dev tool, not pipeline code.
- Coverage per R8.1, including the negative and edge cases: `dobry` (Middle Polish in
  every R6.6a position), an all-Middle-Polish page (find one here), lemma-and-form pages
  `bez` and `mieć`, the two-lemma form page `mamy`, `kotów`, multi-etymology `zamek`,
  pluralia tantum, a participle, irregular verbs (`być`, `iść`, `jeść`, `chcieć`).
- Harness: run extraction over a fixture, diff against expected JSON, `--update-golden` to
  re-bless. `polwikt inspect <title>` printing raw wikitext → node tree → proto.

**Exit:** harness runs green with all expectations still empty/`TODO`; tests that need
expansion are marked to skip until M4 commits the store snapshot. Tests never touch the
dump.

---

## M4 — Expansion layer
*Needs M2, M3. 1–2 weeks. The hardest and least predictable milestone.*

- `wikitextprocessor` wiring: `Wtp(db_path=pages.sqlite)`, `start_page`, `expand`,
  `parse`, Lua via lupa, per-page time limit.
- Hermeticity (R4.5): stub upstream's **live Wikidata HTTP** entry points
  (`mw.wikibase.*` and label/description lookups) and count every hit; no other network.
- Existence via `all_titles`; `getContent()` on a pruned ns-0 page raises a counted
  error rather than upstream's silent nil (R3.2a).
- Touched-page recorder (R3.8a) → `tools/golden.py --snapshot` builds the committed
  `tests/golden/store.sqlite.zst` (R8.1a); un-skip the expansion tests.
- Expansion **policy** in config (R4.2): expand inflection tables; capture `{{lb}}`,
  `{{uxi}}`, `{{coi}}`, `{{+obj}}`, inline nyms, `{{inflection of}}`, etymology templates
  incl. `{{etymon}}`, `{{pl-pr}}` as structured calls; both for headwords; aliases
  resolved first; raw `{name, args}` retained everywhere (R4.2.1).
- Parser functions, magic words, `<nowiki>`/`<ref>`/comments (R4.4); Lua failure degrades
  gracefully and is counted (R4.3); `unhandled.jsonl` (R4.6).

**Exit:** `{{pl-decl-noun-*}}`/`{{pl-decl-noun}}` (`Module:pl-noun`), `{{pl-adecl}}`
(`Module:pl-adjective`), the `{{pl-conj-ai}}`/`{{pl-conj-ap}}` families,
`{{pl-noun}}`/`{{pl-verb}}`/`{{pl-adj}}` (`Module:zlw-lch-headword`) and `{{pl-pr}}`
(`Module:zlw-lch-IPA`) expand correctly for every golden fixture, from the committed
snapshot, with zero Wikidata network attempts. Throughput measured (pages/sec/worker,
lemma vs form page) and **R9.2's provisional 2 h target replaced with the measured
number**; snapshot size recorded (expect a few MB compressed).

**Risks:** en.wiktionary's Lua stack reaches further than expected (the recorder shows
exactly how far); a Polish-reachable module that needs `getContent()` on a pruned ns-0
page (R3.2a — if it fires for real, P1 needs a carve-out); a module that needs Wikidata.

---

## M5 — Section structure extraction
*Needs M1, M3, M4. ~1 week.*

- L2 `==Polish==` isolation; `Etymology N` grouping preserved, **not** flattened (R5.1);
  POS at L3/L4 and subsections at L4/L5, attached by heading type, not depth (R5.2);
  repeated POS headings within one etymology (`iść`); the POS heading map as config
  (R5.3), unknown headings counted; nested sense lists as child senses (R5.4);
  language-level sections above and below the etymologies (R5.5).
- Emits `Word` with structure + plain glosses only.

**Exit:** every fixture produces the right tree — correct etymology-group count, POS set,
sense/subsense nesting. `zamek` keeps its senses attached to the right etymology; `mieć`
keeps its shared page-level pronunciation on `Word`.

---

## M6 — Senses in detail
*Needs M5. ~1 week.*

- Labels → typed tags with string passthrough (R6.7), label aliases resolved; dialect
  labels as `TAG_DIALECTAL` + region in `raw_tags`; topics; `{{ux}}`/`{{uxi}}` examples
  and `{{quote-*}}`/`{{RQ:pl:…}}` with fields kept separate (R6.9); `{{coi}}`
  collocations (R6.12); `{{+obj}}` government (R6.11); sense-scoped nyms; `{{senseid}}`
  (R5.6); `form_of` from `{{inflection of}}` & friends, incl. `;` / `//` multi-set tags
  (R6.6).
- Plain gloss + `LinkSpan` list, codepoint offsets (R7.6a).
- **Middle Polish drop** framework: `drop_labels` config, sense → entry → page cascade,
  per-label and per-kind counts (R6.6a–c). This milestone owns senses and `{{tlb}}`
  entries; M7, M9 and M10 plug their kinds (tables, `mp=`, alt forms, reference groups)
  into the same counter.

**Exit:** golden expectations filled for senses; `dobry`'s Middle Polish senses gone and
counted; the all-Middle-Polish fixture yields no record; `stats.json` reports drop counts
by label and kind.

---

## M7 — Nominal inflection (nouns, adjectives, pronouns, numerals)
*Needs M4, M5. ~1–2 weeks.*

- Parse expanded declension tables → flat tagged `Form` list (R7.8): 7 cases × 2 numbers,
  alternative cells, absent cells genuinely absent (R6.1). Both the pattern templates
  (`{{pl-decl-noun-m-anml}}`, …) and explicit-cell `{{pl-decl-noun|noms=…}}`.
- Gender **and animacy** incl. virile/nonvirile from headword templates (R6.1).
- Adjectives via `{{pl-adecl}}`; degree + non-comparable marking (R6.3);
  pronoun/numeral paradigms incl. collective numerals (R6.4).
- `{{pl-mid-decl-noun}}` tables dropped and counted (R6.6a).

**Exit:** all nominal fixtures match expectations, pluralia tantum and defective
paradigms included; noun-declension coverage measured over a `--limit` sample.

---

## M8 — Verbal inflection
*Needs M4, M5. ~2 weeks — the largest paradigm.*

- Parse the conjugation template families — `{{pl-conj-ai}}`/`{{pl-conj-ap}}` and their
  class subtemplates (`-uję`, `-ić`, `-nąć`, `-VII`, …), `{{pl-conj-być}}`,
  `{{pl-conj-defective}}`, `{{pl-conj-powinienem}}`; identify what the `pl-skur-*`
  families are before deciding whether they're in scope.
- Full paradigm per R6.2: infinitive; present/perfective-future; past and conditional by
  person × number × gender (sg m/f/n, pl virile/nonvirile); both periphrastic futures;
  imperative; impersonal `-no`/`-to`; verbal noun; both adjectival and both adverbial
  participles.
- Aspect and aspect partner; reflexive `się`; frequentatives (`freq=`).

**Exit:** `być`, `iść`, `jeść`, `chcieć`, a regular imperfective/perfective pair and a
reflexive verb all match expectations, every paradigm slot tagged.

---

## M9 — Pronunciation and etymology
*Needs M4, M5. ~1 week.*

- `{{pl-pr}}` parameters: IPA, `a=` audio with `<text:…>` modifiers, `hh=` homophones,
  rhymes, **syllabification**, and per-dialect variants as separate `Pronunciation`s via
  a config dialect map (R6.5); `mp=` dropped and counted (R6.6a). Literal `{{IPA|pl|…}}`
  as the fallback.
- Etymology: rendered text **and** typed links (`{{inh}}`/`{{inh+}}`, `{{bor}}`,
  `{{der}}`, `{{etymon}}`, compounds/affixes) with source language codes, cognates,
  Proto-Slavic reconstructions (R6.8).

**Exit:** pronunciation and etymology expectations filled across the fixture set.

---

## M10 — Relations, descendants, and the remaining sections
*Needs M5. ~3–4 days.*

- Synonyms/antonyms/hypernyms/hyponyms/meronyms/holonyms, coordinate terms, derived and
  related terms (`{{col}}`, `{{pl-derived verbs}}`), descendants (`{{desc}}`,
  `{{desctree}}`), alternative forms (Middle Polish ones dropped), usage notes, trivia,
  references/further reading (the `Middle Polish:` group dropped), anagrams.
- Categories: explicit **and** template-emitted during expansion (R6.10).

**Exit:** no golden fixture has unclaimed section content; anything unrecognised lands in
the unhandled-section counter rather than being dropped.

---

## M11 — P4: folding, linking, finalize
*Needs M6–M10. ~1 week.*

- Resolve `form_of`/`alt_of` to lemma and specific entry (R3.13).
- **Fold and drop** inflectional form-of entries, per POS entry not per page; transfer
  attestation, missing cells and the form page's pronunciation onto the lemma's `Form`
  (R3.13a); participles, `{{syn of}}` and `{{alt form}}` entries are *not* folded;
  `index.sqlite` surface-form → lemma map (R3.13b); unresolved forms counted and logged
  (R3.13c). All of it through SQLite, within R9.3's memory budget.
- Aspect pairs, frequentatives, diminutive/augmentative chains, comparative ↔ positive
  (R3.14).
- Canonical sharded corpus + index (R3.15); `Corpus` metadata incl. dump pin and active
  `drop_labels` (R7.4); `stats.json` (R3.16) and `polwikt stats-diff` (R8.3).

**Exit:** `bez`/`mieć` keep only their lemma halves; `mamy` yields no record and resolves
to both `mieć` and `mama`; `kotów` yields no record but resolves through the index;
unresolved-form count is small and explained.

---

## M12 — Scale, parallelism, and the full run
*Needs M11. ~1 week.*

- `--jobs` multiprocessing with stateless workers (R3.10); deterministic output order
  regardless of job count (R3.11); per-page error isolation and `--max-error-rate` (R3.12).
- Full-corpus run end to end on this box; measure against R9.1–R9.5.

**Exit:** full runs at `--jobs 1` and `--jobs 2` produce **byte-identical** output; P3
within the R9.2 target as reset at M4; peak RSS ≤ 1.5 GB per worker; interrupted run
resumes correctly; disk total within R9.5.

---

## M13 — Quality pass
*Needs M12. Ongoing, ~2 weeks of focused work.*

- `wiktextract` oracle: generate its JSON for the golden set (from the same committed
  store), diff field by field, and triage each divergence into *our bug* / *their
  flattening* / *deliberate difference* (§12.1).
- Burn down `unhandled.jsonl` by frequency — the top entries are the backlog (R4.6).
- Hit R8.4 targets: senses ≥99%, noun declension ≥95%, verb conjugation ≥90%.
- CI gates the golden-run `stats.json` (R8.3); full-run `stats-diff` documented as the
  required local check for extraction changes and pin moves.

**Exit:** coverage targets met and quoted **from a real `stats.json`**, not estimated;
oracle diff has no unexplained entries.

---

## M14 — Release
*Needs M13. ~3 days.*

- README with the pipeline model and a consumer example (read shards, resolve a form
  through the index).
- `LICENSE-DATA` (CC BY-SA 4.0 + attribution) emitted next to every output; MIT for the
  code (R11).
- Versioned corpus artifact named by dump date + schema version; documented dump re-pin
  procedure (R2.1a), incl. regenerating the golden store.

**Exit:** a fresh clone can go from pinned dump to corpus with the documented commands.

---

## Cross-cutting risks

| Risk | Milestone | Mitigation |
|---|---|---|
| Lua/Scribunto expansion doesn't cover what Polish modules need | M4 | the touched-page recorder shows the real reach; degrade gracefully and count (R4.3); timebox and re-scope early |
| Upstream reaches the network (Wikidata) from Lua | M4 | stub and count every entry point (R4.5); a test asserts zero network attempts on the golden set |
| Inflection table layout varies by template family | M7, M8 | parse from the expanded table *and* keep raw template args (R4.2.1); cross-check against folded form pages in M11 |
| Template/module names drift (several in the original spec were already wrong) | all | names live in config, verified against the pinned dump, not the live wiki |
| Pinned dump expires from Wikimedia's retention (~10 months observed) | M2+ | keep the pinned dump archived locally; re-pin deliberately with a stats diff |
| `pages.sqlite` too large for page cache on a 5 GB box | M2, M12 | measure at M2; revive P2 (decision 6) only if needed |
| `wikitextprocessor`/`wiktextract` version drift | M4, M13 | exact pins, documented upgrade procedure (R10.2) |
| Schema churn after extractors are written | M1 | additive-only discipline (R7.6); M1 includes the review's gaps before any extractor exists |
