# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Not a library or app — this repo **is** a submission to the [Silicon Sample Benchmark](https://janpfander.github.io/llm_predictions_megastudy/): teams predict, blind, the results of a behavioral megastudy on trust in climate scientists before the human data are revealed. It is a participant copy of the organizers' template (all git history is authored upstream by the benchmark organizer; `origin` is the participant's own fork).

**One repo = one entry = one tier = one Zenodo deposit.** The deliverables are `predictions/*.csv`, `metadata.json` (which carries each file's SHA-256), and a completed `registration.md`, released together to Zenodo before the **August 31, 2026** prediction lock. Everything else in the repo exists for transparency.

The repo is currently in its shipped example state: `metadata.json` has `team_id: "example"` and `predictions/` holds one `example_*` file per tier, so a fresh clone already passes `make check` (PASS WITH WARNINGS). The generation pipeline is meant to be built *inside* this repo, in **any language** — the R helpers are conveniences, not a required pipeline. The only non-negotiable outputs are well-formed prediction file(s) and their SHA-256 fingerprints.

## Commands

| Command | Notes |
|---|---|
| `make check` | The test suite. Validates repo files, `metadata.json`, filenames, SHA-256, per-tier structure/coverage, and `.zenodo.json`. Exits 1 **only** on FAIL; writes the gitignored `metadata_check_report.txt`. |
| `make clean` | Tier-1 only: cleans the single CSV in `raw_data_deposit/` into `predictions/`, then runs the manifest step. `make clean INPUT=path/to/raw.csv` for a file kept elsewhere. (Only passing an explicit *output* path — `Rscript scripts/clean.R in.csv out.csv` — skips the automatic manifest refresh.) |
| `make manifest` | Fingerprints this entry's prediction files and rewrites `metadata.json` → `prediction_files`. |
| `make zenodo_citation` | (Re)generates `.zenodo.json` from `metadata.json`. |

Without GNU Make: `Rscript scripts/check.R`, `Rscript scripts/clean.R [in.csv] [out.csv]`, `Rscript scripts/manifest.R`, `Rscript scripts/zenodo_citation.R`. There are no unit tests and nothing to build.

Requires R ≥ 4.2 with **tidyverse**, **jsonlite**, **digest** (this environment: R 4.3.1, all present and working). `.github/workflows/check.yml` runs `Rscript scripts/check.R` on every push/PR.

## Architecture

### `scripts/lib/submission_spec.R` is the single source of truth

Sourcing it defines the `sst` list, which both `clean_lib.R` and `check_lib.R` (and the organizers' local-only example generator) read. It defines the 16 intervention titles + `control` (17 conditions), the raw-survey code name → title map, the 13 scored outcomes, the 12 trust items, the 6 moderators **with their exact level strings**, and the per-tier column sets.

**Read this file first when generating predictions in another language.** Labels are compared by exact string — `"Measurement & modeling (1)"`, `"Doctorate degree / Ph.D."`, `"Hispanic / Latino"`. A near-miss is a hard FAIL (conditions, outcomes, moderator names) or silently drops respondents from subgroup analyses.

### `metadata.json` is the control file

`team_id`, `tier`, and `entry` (`primary` | `secondary-k`) are not just documentation — they drive:

- the output filename `clean.R` writes (`predictions/<team_id>_T1_<entry>_v1.csv`),
- the glob `manifest.R` uses to decide which files belong to this entry,
- the filename regex and expected file count `check_lib.R` enforces (2 files for Tier 2 — main + moderator cells — 1 otherwise).

So **edit `metadata.json` before running `make clean` / `make manifest`**, not after.

### Data flow (Tier 1)

`raw_data_deposit/<one>.csv` (Qualtrics-shaped export) → `scripts/clean.R` → `predictions/<team_id>_T1_<entry>_v1.csv` → manifest (SHA-256 into `metadata.json`) → `make check`.

`clean_lib.R` reproduces the human study's own cleaning: the `.rename_map` (raw Qualtrics label → target label, mirrored by `codebook.csv`'s `qualtrics_label`/`target_label` columns), numeric-code → label recodes for the demographics, `age = 2026 − birth_year` with `age_band` cut at 17/29/44/59, the reverse-coded `funding_perceptions = 100 − funding_5`, and the `rowMeans` composites (`trust_multidimensional` is the mean of the four 3-item subscale means). It tolerates a genuine Qualtrics export (two extra header rows + system columns) or a plain one-header CSV, and errors loudly rather than producing NAs on unrecognized condition/demographic values. Tiers 2–3 skip all of this: write the cell/effect CSVs straight into `predictions/`, matching the `example_*` shapes, then `make manifest`.

### Derived artifacts — never hand-edit

`.zenodo.json` (from `metadata.json`, always overwritten) and `metadata.json` → `prediction_files[].sha256` (from `manifest.R`). Change the source and re-run. `.zenodo.json` controls a **permanent** DOI record; an ORCID that fails the ISO 7064 MOD-11-2 checksum makes Zenodo reject the deposit with an opaque HTTP 500, which is why both `zenodo_citation.R` and `check_lib.R` verify it.

## Validation semantics

FAIL (exit 1): missing or duplicated grid cells; **any `NA`** in a prediction value column; unknown condition, outcome, or moderator labels (but an invalid Tier-2 `moderator`/`moderator_level` *pair* is only a WARN); a moderator column that is entirely NA; SHA-256 or filename mismatch; declared coverage other than 16 interventions × 13 outcomes; `blinding_attestation` not `true`.

WARN (still exit 0): below the precision floor (500/intervention, 1,000 control); `team_id` still `example`; leftover `example_*` files; blank `registration.md` items; a `trust_multidimensional` that disagrees with its own items; missing `.zenodo.json`.

Full coverage is mandatory — every cell of the grid exactly once (Tier 2 main: 17 × 13; Tier 2 moderator: 17 × 27 moderator levels × 13; Tier 3: 16 × 13, with **no control row**). To predict "no moderation" for a group, repeat that condition's main-file mean in the group's cells; leaving cells out or NA is not accepted.

## Things that bite

- **The "staged" short-circuit.** If `team_id` is set but `prediction_files` still point at `example_*`, `check_lib.R` emits one WARN and **returns early**, skipping every per-file structural check. A near-clean report there means "not checked yet", not "valid".
- **Composites are scored as submitted**, not recomputed from the item columns. A hand-built file is scored on its own (possibly deviant) composite values; `make check` only warns.
- **Tier-2 `newsletter_signup` is a 0–1 proportion**, unlike the Tier-1 individual 0/1. `donation_ams` is 0–10; other outcomes 0–100. Tier-3 `ate` is unbounded and deliberately not range-checked.
- **Semicolon-joined condition code names are single names** (e.g. `"crushing chicken; gross grasshopper; homely halibut"` = one condition). Join on the full string; never split on `;`.
- **Nobody reweights your sample, and mostly it does not matter.** There is no post-stratification of a submission; the only weighting is on the human side, where attrition checks *"may lead the human models to apply inverse-probability weights, in which case submissions are scored against the weighted estimates"* (`preregistration_benchmark.qmd:281`). The Census quota table there is explicitly informational: *"Participating teams are not required to use this information for their own synthetic sample"* (`:250`). This is safer than it sounds, because Sections 1 and 2 score **differences**: `run_main_treatment_model()` gives ATEs as treatment minus the shared control cell mean (`:342`), so a compositional skew shifts both terms and cancels. It survives only to the extent the effect really varies by that moderator, and the benchmark warns there may be little heterogeneity to find at all. Subgroup analyses are computed *within* each moderator level, so the marginal never enters them either. **The exception, and it is Tier 1 only:** the control-condition response distributions — variance ratio, OVL, KS, Wasserstein-1 — compare the *pooled* shape of your control respondents against the humans' (`:426`, eligibility table `:307`). That is a level, not a difference, so composition goes straight in. Practical read: do not spend effort chasing the human demographic mix; do care about the shape of the control-condition answers.
- **A vivid persona is scored against you.** The six moderators are not only file columns; three preregistered analyses use them (`preregistration_benchmark.qmd`): condition x moderator interactions (Tiers 1–2), the demographic parity gap, and — **Tier 1 only** — *demographic predictability*, which fits an OLS of the outcome on one moderator plus condition fixed effects and compares R² between the humans and the submission. *"An R² substantially higher for the submission than for humans flags exaggeration of demographic variables (stereotyping)."* So a persona that makes party or race louder than it is in real people loses points, and the naive instinct — write a memorable character — is the wrong one. Their worked example is party: a control baseline off by 6 pp for Republicans and 1 pp for Democrats is a 5 pp parity gap.
- **Subgroup analyses use four outcomes, not thirteen.** `preregistration.qmd:190` names them: multidimensional trust, donation to AMS, funding perceptions, and general climate policy support. The submission file must still carry all 13 outcomes x 27 moderator levels — completeness is enforced — but the scored subgroup work is those four. There may also be little real heterogeneity to recover: the benchmark notes that in Ashokkumar's archive only 7.7 %, 8.8 % and 18.3 % of effects were significantly moderated by gender, ethnicity and party, so *"a submission that predicts no heterogeneity at all then scores well."*
- **`README.md` is generated from `README.qmd`** via Quarto (`format: gfm`) — edit the `.qmd` and re-render, or the two drift. Quarto is **not** installed in this environment, so a docs edit here means editing both files consistently.

## Editing boundaries

- `scripts/` is the organizers' engine — treat as read-only. Local changes make the self-check disagree with the scoring the organizers run.
- `survey/` and `codebook.csv` are reference material and stay in the deposit unchanged; the stimulus texts adapt copyrighted material and are not covered by the repo's own license grant.
- Before depositing: delete every `example_*` file in `predictions/` and `raw_data_deposit/example_raw_export.csv`, then re-run `make manifest` and `make check`.
- Proprietary parts of a pipeline may be gitignored and kept private (this affects the entry's disclosure class, recorded in `metadata.json` and `registration.md` §L).

## Files that stay untracked

`CLAUDE.md` and a future `docs/` folder must **not** be tracked, and must **not** be added to `.gitignore` either — leave them untracked and unlisted (`.gitignore` is itself a tracked file, so an entry there would appear in the repo's history). Never stage with `git add -A` / `git add .` here; stage files by name.

## Commit messages

Format each commit subject as `action (file): description`:
- **action** — the verb describing what was done: `add`, `modify`, `update`, `delete`, `correct`, ...
- **(file)** — the file that changed, in parentheses
- **`:`** — a colon separating the file from the description
- **description** — what the change does

Example: `modify (slides.md): add Typst rendering slide`

Do not add a `Co-Authored-By: Claude` trailer (or any Claude attribution) to commits.
