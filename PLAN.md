# PLAN.md — implementation milestones

Spec: `REQUIREMENTS.md`. Working rules: `CLAUDE.md`. Requirement IDs (`R3.2`, `R6.6a`)
are cited per milestone so exit criteria trace back to the spec.

**Shape of the plan.** Two things gate everything and start on day one: the **proto
schema** (every later module is written against it) and the **dump download + P1 scan**
(hours of wall clock, and nothing downstream is real without it). Golden fixtures are
fetched from the live wiki so extraction work can start before the dump lands. After that
the extractors go in dependency order — structure, then senses, then paradigms — each one
graded by the same golden harness.

```
M0 skeleton ─┬─ M1 proto ─────────────────────────┬─ M5 structure ─ M6 senses ─┬─ M7 nom.
             ├─ M2 dump + P1 scan ── M4 expansion ─┘                            ├─ M8 verb
             └─ M3 golden harness ───────────────────────────────────────────────┴─ M9 pron/etym
                                                                                     │
                                        M12 scale ── M11 finalize (P4) ── M10 relations
                                             └── M13 quality ── M14 release
```

---

## M0 — Repo skeleton and tooling
*No dump needed. Half a day.*

- `git init`; `pyproject.toml` with pinned deps and `[dev]` extra (R10.2); `.gitignore`
  excluding `data/`, `.venv/`, `*.sqlite`, `*.pb.zst`.
- Package layout per R10.4, each subpackage an importable stub.
- `Makefile`: `proto`, `lint`, `typecheck`, `test`, `run`.
- CI: `ruff check` + `ruff format --check` + `mypy --strict` + `pytest`, and a
  `make proto && git diff --exit-code` step (CLAUDE.md codegen rule).
- `polwikt.toml` with the dump pin placeholder and empty config tables (R10.5).

**Exit:** `make lint typecheck test` green on an empty package. CI runs on push.

---

## M1 — Protobuf schema and corpus I/O
*No dump needed. 1–2 days. Gates everything downstream.*

- `proto/polwikt.proto`: `Word`, `EtymologyGroup`, `PosEntry`, `Sense`, `Form`,
  `LinkSpan`, `Pronunciation`, `Relation`, `Descendant`, `Example`, `TemplateCall`,
  `FormOf`, `Corpus`, and the grammatical enums (case, number, gender, animacy, person,
  tense, mood, aspect, degree, participle type) — §7, R7.1/R7.6–R7.8.
- `make proto` → committed `_pb2.py`/`_pb2.pyi`.
- `polwikt/proto/io.py`: varint-delimited zstd shard writer/reader (R7.2), `index.sqlite`
  helpers (R7.3), `MessageToJson` view (R7.5).

**Exit:** round-trip test (write N messages → read back identical) incl. a 50k-message
sharding test; JSON view of a hand-built `Word` looks right; enums cover every category in
§6 with `_UNSPECIFIED = 0`.

**Risk:** getting this wrong is expensive later (R7.6 forbids renumbering). Review the
schema against §6 *before* writing extractors, not after.

---

## M2 — Dump acquisition and P1 scan
*Start the download at M0. 2–3 days of work, plus wall clock.*

- `polwikt fetch`: download pinned dump, sha1-verify (R2.1, R2.1a).
- Streaming bz2 XML reader — never fully decompress to disk (R2.4); prefer multistream.
- P1 store: SQLite, zstd per-row text (R3.1); ns-0 kept **only** on a `==Polish==` heading
  line match (R3.2); other namespaces unfiltered (R3.3); `all_titles` for every page,
  no text (R3.2a); redirects recorded (R2.3).
- Resumability + filter-predicate fingerprint (R3.4); read/kept counters (R3.5).

**Exit:** `pages.sqlite` built from the pinned dump; kept ns-0 count lands in 10^5–10^6
(a count near 0 or near 10^7 means the predicate is broken); re-running skips; store size
and scan wall clock recorded against the R9.1 target (≤60 min).

---

## M3 — Golden corpus and test harness
*No dump needed — fixtures come from the live wiki. 1–2 days. Unblocks all extractors.*

- Fetch raw wikitext for ~50 chosen pages via Special:Export **at authoring time** (this
  is a one-off tool, not pipeline code — R4.5 forbids network at runtime); check the
  wikitext into `tests/golden/`.
- Coverage per R8.1 plus the negative cases: Middle Polish senses, all-Middle-Polish page,
  lemma-and-form page (`mamy`, `piec`), multi-etymology (`zamek`), pluralia tantum,
  irregular verbs (`być`, `iść`, `jeść`, `chcieć`).
- Harness: run extraction over a fixture, diff against expected JSON, `--update-golden` to
  re-bless. `polwikt inspect <title>` printing expanded wikitext → node tree → proto.

**Exit:** harness runs green with all expectations still empty/`TODO`; each later milestone
fills them in. Tests never touch a dump.

---

## M4 — Expansion layer (P2 + template/Lua expansion)
*Needs M2. 1–2 weeks. The hardest and least predictable milestone.*

- Closure walker: `{{tpl}}`, `{{#invoke:}}`, `require`, `mw.loadData`, redirects (R3.6),
  over-approximated by module family with logged misses (R3.7) → `subset.sqlite` (R3.8).
- `wikitextprocessor` wiring: page db handoff, `start_page`, `expand`, `parse`, Lua
  sandbox via lupa, per-page time limit, hermetic execution (R4.5).
- Expansion **policy** in config (R4.2): expand inflection tables; capture `{{lb}}`,
  `{{ux}}`, `{{infl of}}`, `{{inh}}`/`{{bor}}`/`{{der}}`, IPA templates as structured
  calls; both for headwords; retain raw `{name, args}` everywhere (R4.2.1).
- Parser functions, magic words, `<nowiki>`/`<ref>`/comments (R4.4); Lua failure degrades
  gracefully and is counted (R4.3); `unhandled.jsonl` (R4.6).

**Exit:** `{{pl-decl-noun-*}}`, `{{pl-conj-*}}`, `{{pl-noun}}`, `{{pl-verb}}`, `{{pl-p}}`
expand to correct wikitext for every golden fixture; `subset.sqlite` < 2 GB; expansion
throughput measured (pages/sec/core) to sanity-check the R9.2 budget.

**Risks:** en.wiktionary's Lua stack reaches further than expected (missing modules → over-
approximate harder); `mw.title:getContent()` on a pruned ns-0 page (R3.2a corollary — if
this fires for real Polish modules, the P1 filter needs a carve-out).

---

## M5 — Section structure extraction
*Needs M1, M3, M4. ~1 week.*

- L2 `==Polish==` isolation; `Etymology N` grouping preserved, **not** flattened (R5.1);
  POS headings at L3 and L4 (R5.2); the POS heading map as config (R5.3); nested sense
  lists as child senses (R5.4); language-level trailing sections (R5.5).
- Emits `Word` with structure + plain glosses only.

**Exit:** every fixture produces the right tree — correct etymology-group count, POS set,
sense/subsense nesting. `zamek` keeps its senses attached to the right etymology.

---

## M6 — Senses in detail
*Needs M5. ~1 week.*

- Labels → typed tags with string passthrough (R6.7); topics; `{{ux}}` examples and
  `{{quote-*}}` with fields kept separate (R6.9); sense-scoped relations; `{{senseid}}`
  (R5.6); `form_of` from `{{infl of}}` & friends decoded to tags (R6.6).
- Plain gloss + `LinkSpan` list, codepoint offsets (R7.6a).
- **Middle Polish drop** with sense → entry → page cascade and per-label counts
  (R6.6a–c), driven by `drop_labels` config.

**Exit:** golden expectations filled for senses; the three negative fixtures behave
exactly as specified; `stats.json` reports drop counts by label.

---

## M7 — Nominal inflection (nouns, adjectives, pronouns, numerals)
*Needs M4, M5. ~1–2 weeks.*

- Parse expanded declension tables → flat tagged `Form` list (R7.8): 7 cases × 2 numbers,
  alternative cells, absent cells genuinely absent (R6.1).
- Gender **and animacy** incl. virile/nonvirile from headword templates (R6.1).
- Adjective degree + non-comparable marking (R6.3); pronoun/numeral irregulars (R6.4).

**Exit:** all nominal fixtures byte-match expectations, pluralia tantum and defective
paradigms included; noun-declension coverage measured over a `--limit` sample.

---

## M8 — Verbal inflection
*Needs M4, M5. ~2 weeks — the largest paradigm.*

- Full paradigm per R6.2: infinitive; present/perfective-future; past by person × number ×
  gender; periphrastic future; imperative; conditional; impersonal `-no`/`-to`; verbal
  noun; both adjectival and both adverbial participles.
- Aspect and aspect partner; reflexive `się`; frequentatives.

**Exit:** `być`, `iść`, `jeść`, `chcieć`, a regular imperfective/perfective pair and a
reflexive verb all match expectations, every paradigm slot tagged.

---

## M9 — Pronunciation and etymology
*Needs M4, M5. ~1 week.*

- IPA from `{{pl-IPA}}`/`{{pl-p}}`/`{{IPA}}`, audio, rhymes, **syllabification**,
  homophones, regional/diachronic qualifiers as tags (R6.5) — Middle Polish variants
  dropped per R6.6a.
- Etymology: rendered text **and** typed links (inherited/borrowed/derived/compound) with
  source language codes, cognates, Proto-Slavic reconstructions, affix decomposition
  (R6.8).

**Exit:** pronunciation and etymology expectations filled across the fixture set.

---

## M10 — Relations, descendants, and the remaining sections
*Needs M5. ~3–4 days.*

- Synonyms/antonyms/hypernyms/hyponyms/meronyms/holonyms, derived and related terms,
  descendants, alternative forms, usage notes, references/further reading, anagrams.
- Categories: explicit **and** template-emitted during expansion (R6.10).

**Exit:** no golden fixture has unclaimed section content; anything unrecognised lands in
the unhandled-section counter rather than being dropped.

---

## M11 — P4: folding, linking, finalize
*Needs M6–M10. ~1 week.*

- Resolve `form_of`/`alt_of` to lemma and specific entry (R3.13).
- **Fold and drop** inflected-form entries, per POS entry not per page; transfer
  attestation, missing cells and the form page's pronunciation onto the lemma's `Form`
  (R3.13a); `index.sqlite` surface-form → lemma map (R3.13b); unresolved forms counted and
  logged, never silently dropped (R3.13c).
- Aspect pairs, diminutive/augmentative chains, comparative ↔ positive (R3.14).
- Canonical sharded corpus + index (R3.15); `Corpus` metadata incl. dump pin and active
  `drop_labels` (R7.4); `stats.json` (R3.16).

**Exit:** `mamy`/`piec` keep only their lemma halves; `kotów` yields no record but resolves
through the index; unresolved-form count is small and explained.

---

## M12 — Scale, parallelism, and the full run
*Needs M11. ~1 week.*

- `--jobs` multiprocessing with stateless workers (R3.10); deterministic output order
  regardless of job count (R3.11); per-page error isolation and `--max-error-rate` (R3.12).
- Full-corpus run end to end; measure against R9.1–R9.5.

**Exit:** two full runs with different `--jobs` produce **byte-identical** output; P3 ≤ 20
min on 8 cores; peak RSS ≤ 4 GB/worker; interrupted run resumes correctly.

---

## M13 — Quality pass
*Needs M12. Ongoing, ~2 weeks of focused work.*

- `wiktextract` oracle: generate its JSON for the golden set, diff field by field, and
  triage each divergence into *our bug* / *their flattening* / *deliberate difference*
  (§12.1).
- Burn down `unhandled.jsonl` by frequency — the top entries are the backlog (R4.6).
- Hit R8.4 targets: senses ≥99%, noun declension ≥95%, verb conjugation ≥90%.
- Wire the `stats.json` regression gate into CI (R8.3, >1% drop fails).

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
  procedure (R2.1a).

**Exit:** a fresh clone can go from pinned dump to corpus with the documented commands.

---

## Cross-cutting risks

| Risk | Milestone | Mitigation |
|---|---|---|
| Lua/Scribunto expansion doesn't cover what Polish modules need | M4 | over-approximate the module closure; degrade gracefully and count (R4.3); this is the milestone to timebox and re-scope early |
| Inflection table HTML layout varies by template family | M7, M8 | parse from the expanded table *and* keep raw template args (R4.2.1); cross-check against folded form pages in M11 |
| Pinned dump expires from Wikimedia's retention window | M2+ | keep the pinned dump archived locally; re-pin deliberately with a stats diff |
| `wikitextprocessor`/`wiktextract` version drift | M4, M13 | exact pins, documented upgrade procedure (R10.2) |
| Schema churn after extractors are written | M1 | additive-only discipline (R7.6); review schema against §6 before M5 |
