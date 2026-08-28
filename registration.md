# Silicon Sample Benchmark — method registration form

> ## ⚠ STATUS — this form is being rewritten for a TIER 1 entry
>
> **Do not deposit this file as it stands.** Everything below item D.1 still
> describes the entry's earlier form: a **Tier-2** cell-mean forecast made by
> `claude-fable-5`, with a pipeline in `generation/`. That entry was withdrawn
> on 2026-08-28 and `generation/` was deleted. The text is kept, and not
> blanked, so that a reader can see what changed. The Tier-2 form is in git
> history at commit `aa4e060`.
>
> **What is true now:**
>
> | item | state |
> |---|---|
> | tier | **1** — 9,000 individual synthetic respondents |
> | answering model | `Qwen/Qwen3.8-27B`, local weights, vLLM |
> | persona writer | **not chosen yet** |
> | D.1, D.3 (population) | **current and correct** — `population/` is unchanged |
> | D.2 (verbalization) | rewritten below; the Tier-2 answer was false for Tier 1 |
> | every other item | **superseded**, and rewritten as each stage runs |
>
> Items that name `generation/`, `claude-fable-5`, 612 tasks, 28 cell
> profiles, 3 framings, or 6 draws per cell describe the withdrawn entry.
>
> B.1 and B.2 need the exact model identifier and the call-date window of the
> run that produced the answers. That run has not happened, so they stay
> `PENDING` — a wrong declaration is worse than an open one.

Fill in every item before the prediction lock; this file ships inside your repo's Zenodo release
(see the README's *Deposit* step). This form covers **one entry** (one repo / one Zenodo release,
`primary` or `secondary-k` — see the README's *What counts as a submission*); if you submit several
entries, fill one form per entry. Items marked **★**
must be disclosed **fully publicly** (never escrowed or withheld). Items marked **†** must be at
minimum escrowed — they may be sealed from the public, but never withheld from the core team. Items
not applicable to your approach: write `N/A`. When several models serve different pipeline stages, complete the model
sections (B) once per model. See the call's *Disclosure policy* for escrow rules.

Items below marked `PENDING (after the generation run)` are facts the run itself produces. They are
filled from `generation/build/registration_facts.md`, which `generation/scripts/06_diagnostics.py`
writes, before the deposit. Everything else is pre-specified.

---

## 0 · Approach identity and output
- **0.1 Team ★** — name, the one or two members (teams are at most two, unless a larger team was approved on request), affiliations, corresponding contact:
  `PENDING (team identity)` — team `team_27`. Member name, affiliation, ORCID and corresponding
  contact are to be entered here and in `metadata.json` (`team_name`, `contact`, `creators`).
  The ORCID must pass the ISO 7064 MOD-11-2 checksum, or Zenodo rejects the deposit with an opaque
  HTTP 500.
- **0.2 Plain-language summary ★** — one paragraph, what the approach does (not how):
  We ask one large language model to forecast, before any human data exist, what each of 17
  experimental groups will answer on 13 outcome measures, and what each of 27 demographic subgroups
  will answer inside each of those groups. The model sees the same 17 texts the human respondents
  read, and a statistical description of the people who will read them. It never simulates
  individual people. Every prediction is made six times, in three differently worded requests, and
  the six answers are averaged.
- **0.3 Submission tier & approach family ★** — tier (1/2/3); family (e.g. per-respondent simulation / agent / direct forecast; single model / ensemble / multi-agent / zero-shot / literature-conditioned):
  **Tier 2.** Cell-level direct forecast (not per-respondent simulation). Single model, one prompt
  ensemble: 3 framings x 2 repeats = 6 draws per cell, aggregated by their mean. Zero-shot: no
  fine-tuning, no retrieval, no in-context examples of any study's results. The 44 raw survey items
  are predicted and the 6 composite outcomes are computed arithmetically in code.
- **0.4 Pipeline diagram** — ordered steps from raw inputs to submitted file:
  1. `population/02_build_personas.py` — rake 9,000 GSS respondents to the preregistered quotas and
     quota-sample one balanced set per condition (seed `20260807`).
  2. `generation/scripts/00_model_probe.py` — record the session's own model identifier. This gates
     step 4.
  3. `generation/scripts/01_extract_materials.py` — extract the 17 condition texts from
     `survey/questionnaire.txt` and the 44 items from `codebook.csv`.
  4. `generation/scripts/02_cell_profiles.py` — compute the 28 group descriptions (whole sample +
     27 moderator levels) and their population shares.
  5. `generation/scripts/03_prepare_wave.py` — write 612 task prompts: 6 draws x 13 outcomes x
     (whole sample + 6 moderators), split by item so no task asks for more than 520 numbers.
  6. One subagent per task answers it as a JSON file in `generation/runs/raw/`.
  7. `generation/scripts/04_collect.py` — validate every answer (model identity, read-check, exact
     key sets, ranges, no nulls) and flatten it.
  8. `generation/scripts/05_aggregate.py` — composites per draw, ensemble across draws, reconcile
     the moderator file to the main file, clamp, round, write the two CSVs.
  9. `make manifest` then `make check` — SHA-256 into `metadata.json`, then the organizers' validator.
- **0.5 Coverage ★** — number of respondents/cells/estimates; mapping to conditions. Full coverage is required: every submission predicts **all 16 interventions and all 13 outcomes** (partial coverage is not accepted). Confirm here:
  **Full coverage, confirmed.** 221 main cells (17 conditions x 13 outcomes) and 5,967 moderator
  cells (17 conditions x 27 moderator levels x 13 outcomes) = 6,188 predicted means. All 16
  interventions and the control are predicted for all 13 outcomes. No cell is left empty, and no
  cell is `NA`. Condition and outcome labels come from `scripts/lib/submission_spec.R`; the model
  answers in codes and the code maps them back, so no label is typed by hand or by the model.

## A · Scope of LLM use
- **A.1 Purpose** — every workflow stage where LLMs are used:
  One stage only: producing the cell means (step 6 above). Every other step is deterministic Python
  or R. No LLM builds the population, writes the prompts, chooses the aggregation rule, or edits the
  output files.
- **A.2 Degree of automation ★** — confirm fully automated, no human in the loop at prediction time; note any exception:
  Fully automated at prediction time. The prompts are written by `03_prepare_wave.py` before any
  answer is seen, and no answer is edited, re-asked with different wording, or selected by hand. Two
  automated exceptions to "accept whatever comes back", both pre-specified and both blind to the
  values: an answer is rejected and its task re-run when it fails structural validation (wrong keys,
  a null, a value out of range, a missing read-check, or a model that is not the declared one). The
  human decisions were all made before generation: the framings, the batching, the ensemble size,
  and the aggregation rule.

## B · Model / system details (once per model)
- **B.1 Model name(s)** — exact identifiers incl. provider, size, version/timestamp, source link:
  `PENDING (after the generation run)` — declared as `claude-fable-5` (Anthropic; hosted, so no
  parameter count or local weights). Every answer file records the model identifier its own session
  reported, and `generation/runs/model_probe/` holds each step-0 probe, including failed ones. The
  identifier written here is the one those records show, not the one intended.
- **B.2 Access & context mode** — API/web/local; API name + version; chat vs stateless; exact call dates:
  `PENDING (after the generation run)` — a Claude Code session (not the HTTP API), so no API version
  applies. Each task is answered by a fresh subagent with no history of any other task, which makes
  every one of the 612 calls stateless with respect to the others. The call-date window is taken
  from the answer-file timestamps.
- **B.3 Configuration** — temperature, top-p/top-k, max tokens, penalties, stop sequences, seeds, reasoning effort, completions per item:
  No sampling parameters are set: Fable 5 exposes no `temperature`, `top_p` or `top_k`, and its
  reasoning is always on. No stop sequences, no penalties, no seed (the model is not seedable). One
  completion per task; six draws per cell come from six separate tasks (3 framings x 2 repeats), not
  from six completions of one call. Reasoning effort: the session default, recorded with the probe.
- **B.4 Customization** — fine-tuning, RAG, prompt optimization, tool use, web search, agentic scaffolds (cross-ref H):
  No fine-tuning, no retrieval, no web search, no prompt optimization against any outcome data. The
  prompts were written once, from the study materials, and were not revised in response to any
  answer. Tool use: each subagent uses a file-read tool to read its prompt and the shared
  condition-text file, and a file-write tool to write its JSON answer. Agentic scaffold: a
  deterministic wave harness dispatches one subagent per task and re-queues failures; it makes no
  decisions about values.
- **B.5 Persistent memory** — across interactions? what persisted:
  None. Each of the 612 tasks is answered by a subagent that sees only its own prompt and the shared
  condition-text file. No memory, cache or state carries an answer from one task to another.
- **B.6 Inference stack** — for local models: serving framework + version, quantization, hardware:
  N/A — hosted model, no local inference.
- **B.7 Ensembles** — members + exact aggregation rule:
  Six members per cell, one model: framings `F1` (plain — the group label only), `F2` (the same
  request plus the computed demographic profile of the group), `F3` (the same context as `F2`, asked
  in two stages: the control mean, then each intervention's signed shift from it, with the level
  computed as control + shift). Each framing is run twice with a byte-identical prompt. The framings
  also present the 17 texts in three different fixed orders. Aggregation rule: the arithmetic mean of
  the six draws, per cell, after each draw's composites are computed from its own items. The
  fallback rule, pre-specified: if the draws do not agree on the sign of the effect in at least 60 %
  of intervention cells, or if averaging keeps less than 50 % of the per-framing effect size, submit
  one framing instead of the mean. `06_diagnostics.py` measures both and states the verdict.

## C · Prompts
- **C.1 Exact prompts** — verbatim text or link to deposited file; were they iteratively refined? pre-specified vs in response to outputs:
  Deposited verbatim: all 612 prompts in `generation/runs/tasks/*.md`, and the shared condition-text
  files in `generation/runs/prefix_F1.md`, `prefix_F2.md`, `prefix_F3.md`. Each prompt's SHA-256 is
  in its `generation/runs/tasks/*.spec.json`, and `03_prepare_wave.py` rebuilds all 612 byte for
  byte, so any prompt can be verified against the deposit. **Pre-specified.** They were written from
  the study materials before any answer existed, and were not refined in response to any output. The
  wording was reviewed against the design notes only.
- **C.2 System-wide instructions**:
  No custom system prompt. The stock system prompt of the Claude Code session applies. Everything
  specific to this task is in the task prompt, which contains: the framing; a statement that this is
  a blind forecast and that no result from this study or its pilots may be searched for or used; the
  survey flow; the arm sizes; the population description (`F2`, `F3`); the 17 condition codes; the
  items with their exact scales; and the output contract. One general calibration statement is
  included, and is not derived from this study: that a single message shifts a group mean on a 0-100
  scale by a few points at most, that some texts shift it not at all, and that a text may move the
  mean the wrong way. It is paired with the opposite warning, that a table of 17 near-identical
  numbers is as wrong as a table of 20-point swings.
- **C.3 Prompt-design rationale** — brief rationale for the prompt design: why prompts were structured as they were, and the reasoning behind major design choices (recommended, not required):
  *Batch by outcome, not by condition.* The benchmark scores how the 17 texts compare with one
  another. One task therefore shows all 17 texts and asks for one outcome, so the model places them
  on a single scale inside one answer. Seventeen separate calls would make the ranking between them
  noise. Where an outcome has too many items to fit one task, the item list is split and the
  conditions and moderator levels are kept together, because those are the two comparisons the
  study measures.
  *Predict items, compute composites.* Asking for both a composite and its items invites a composite
  that contradicts them, and the benchmark scores the composite as submitted.
  *No numeric prior in the prompt.* We deliberately did not tell the model where the outcome levels
  sit (for example "trust is near 65 on 0-100"). That would make the base rate our prediction rather
  than the model's, and the level is most of what Tier 2 scores. The model is asked to reason about
  the population itself. The one calibration statement we do make is about the *size* of a
  single-message effect, is qualitative, and comes from the published megastudy literature, not from
  this study.
  *Codes, not labels.* The model answers in `C07` and `L3`, never in `"Measurement & modeling (1)"`.
  A near-miss label is a hard failure or a silently dropped subgroup, and this removes the risk from
  the model's output entirely.
  *A read-check.* The 17 texts sit in one shared file rather than inside all 612 prompts, so each
  answer must quote four words out of one named text. That is what proves the texts were read.

## D · Persona / profile construction (Tiers 1–2)
- **D.1 Profile source** — source of demographic profiles you constructed: a public survey (e.g. GSS / ANES / Census), other survey, fully synthetic, or none. The benchmark ships no participant pool; report how you built yours, incl. condition assignments:
  A public survey: 9,000 General Social Survey respondents from the 2018, 2021, 2022 and 2024 waves,
  with their post-stratification weights. **We did not draw this pool ourselves.** The file is
  `clone_profiles/profiles.csv` from the organizers' own research repository — the pool they built
  for their own v1 simulation, not a resource given to teams, and not something the benchmark ships.
  It is deposited here as `population/gss_profiles.csv`. Full provenance, including the quotation
  from their v1 preregistration that describes the draw, is in `population/README.md`.
  Construction: iterative proportional fitting of the GSS weights onto the preregistered quota
  margins (gender, age band, race from Table 3 of the benchmark preregistration, N = 18,000;
  education and income from Census CPS 2024), then quota sampling of the gender x age and
  gender x race cross-quotas **independently within each of the 17 conditions**, which is what
  randomisation achieves in the real study and removes demographic composition as a confound of the
  treatment effects. Real microdata is used for the joint structure because independent draws per
  variable produce people who do not exist and make the moderators independent, which they are not.
  Deterministic: seed `20260807`, and `population/quota_report.txt` is the realised-against-target
  check. Known limits, including the two GSS variables that are coarser than the study's categories,
  are listed in `population/README.md`.
- **D.2 Profile verbalization** — which variables, rendered how (template vs generated narrative; if generated: model + prompt):
  `PENDING (stage 2 of the Tier-1 pipeline)`. **This entry is Tier 1, so every profile IS
  verbalized and addressed as a person** — the Tier-2 answer that stood here, which said no persona
  is ever addressed, does not apply and has been removed.
  Decided so far: each of the 9,000 profiles becomes one short prose persona written by a language
  model from its own attributes. The variables offered to the writer are the six scored moderators
  (gender, age band, race, education, income, party) and nine unscored attributes carried by the
  pool (ideology, household size, social class, region, urbanicity, religion, religiosity,
  born-again, prior confidence in the scientific community). The writer model, its prompt, its
  sampling settings and the fidelity gates are recorded here when stage 2 runs, together with the
  measured share of attributes that reach the written text.
  `sim/01_persona_characteristics.py` writes the table the writer reads, and its checks are in
  `sim/out/01_report.txt`.
- **D.3 Assignment & weighting** — number of personas, assignment to conditions (your responsibility, all 17 conditions), reuse, weighting/matching:
  9,000 profiles: 500 in each of the 16 interventions and 1,000 in control, matching the per-cell
  sizes of the human half that submissions are scored against. Each profile is assigned to exactly
  one condition, by quota sampling within that condition, so no profile is reused across arms. No
  profile is queried, so there is no per-respondent weighting. The population shares of the 27
  moderator levels, computed from this pool, are used for one purpose: reconciling the moderator file
  to the main file, so that for every condition and outcome the level means weighted by their shares
  average back to the main mean.

## E · Stimulus and survey administration
- **E.1 Stimulus presentation** — verbatim vs paraphrase; how state-contingent content is handled:
  Verbatim. All 17 condition texts are extracted from `survey/questionnaire.txt`, unmodified, and
  every task carries all 17. State-contingent content: the control arm shows one of three neutral
  off-topic filler texts at random. Because the prediction target is one control cell mean over
  2,000 respondents, all three fillers are shown together under the single `control` label, with a
  note that each respondent read only one. The newsletter item depends on an offer made on an
  earlier page; that dependency is stated in the item description.
- **E.2 Survey walk-through** — one item/call vs blocks vs whole survey; context carry-over; item/option ordering & randomization; scale display; attention/comprehension handling:
  No walk-through: the model is not administered the survey. It is asked directly for cell means, in
  blocks of one outcome x one group set x all 17 conditions. There is no context carry-over between
  tasks. The 17 conditions are presented in three fixed orders, one per framing, so a text's
  position cannot fix its rank; items keep codebook order. Each item is shown with its verbatim
  question and its endpoint labels, and the answer format states the scale again (0-100 to one
  decimal, dollars to two, or a percentage). Attention and comprehension items are not predicted —
  the benchmark does not score them — but the prompt states that a pre-treatment trust measure is
  asked before the condition, because that anchoring is what keeps a post-treatment mean from
  swinging freely.
- **E.3 Response elicitation** — free text / constrained choice / structured output / token log-probabilities (if logprobs: normalization & mapping):
  Structured output: each task specifies a JSON object with an exact key set and the model writes it
  to a named file. No log-probabilities are used. Answers are validated mechanically rather than
  interpreted: `04_collect.py` requires the exact set of group codes, item names and condition codes,
  rejects nulls, non-numbers and out-of-range values, and for the two-stage framing also rejects a
  shift larger than 40 % of the scale as a mistake rather than a prediction.

## F · Stochasticity and aggregation
- **F.1 Runs & seeds** — runs per respondent/item/estimate; seeds; reproducibility under identical settings:
  Six runs per cell: 3 framings x 2 repeats, where a repeat is the same prompt run again. The model
  is not seedable and Fable 5 exposes no sampling parameters, so identical settings do not give
  identical answers; `generation/build/draw_spread.csv` reports the resulting per-cell spread.
  Everything around the model is seeded and deterministic: the population (seed `20260807`) and all
  612 prompts, which rebuild byte for byte and are hash-pinned.
- **F.2 Aggregation rule** — how multiple generations become submitted values (mean/median/mode/first/sampled/…):
  `PENDING (after the generation run)` — pre-specified as the arithmetic mean of the six draws, with
  composites computed inside each draw first. The pre-specified fallback, and the two thresholds that
  trigger it, are in B.7; `generation/build/diagnostics_report.txt` records which rule the
  measurement selected and the numbers behind it. Afterwards, the moderator file is reconciled to the
  main file by an additive shift per condition x outcome x moderator block, using the population
  shares from `generation/build/cells.json`; values are then clamped to the outcome's range and
  rounded to three decimals.

## G · Validation & post-processing
- **G.1 Human validation** — any human review of outputs (often N/A):
  No human reviewed, edited or selected any predicted value. Human review was limited to the
  pipeline: reading the prompts before generation, and reading the aggregate and diagnostic reports
  after it to apply the pre-specified aggregation rule.
- **G.2 Post-processing** — parsing rules; handling of refusals/malformed/missing/out-of-range; exclusions; for approaches that generate individual responses, the resulting effective N per condition (descriptive disclosure, not a scoring input):
  `PENDING (after the generation run)` — parsing: strict JSON, exact key sets, numbers only. A
  malformed, incomplete, out-of-range, wrong-model or refused answer is not repaired and not
  partially used: the whole answer file is moved to `generation/runs/rejected/` with its reason and
  the task is re-run unchanged. Rejected files stay in the deposit. Nothing is excluded from the
  submission — full coverage is mandatory, and a task is re-run until it produces a valid answer.
  Effective N per condition: N/A, no individual responses are generated. The count of rejected
  answers and their reasons goes here.
- **G.3 Calibration corrections** — any post-hoc scaling/shifting/debiasing and exactly what data it was fit on (cross-ref H/I):
  One correction, pre-specified, fit on no data at all: the moderator file is shifted so that each
  condition x outcome x moderator block's share-weighted level means equal the main-file mean. The
  shift is computed from our own two predictions and our own population shares. No human outcome
  data, from this study or any other, is used to scale, shift or debias anything. No other
  calibration is applied.

## H · Learning and conditioning components
- **H.1 Fine-tuning data** — exact corpus (hashes/DOIs), hyperparameters, checkpoints:
  N/A — no fine-tuning. The hosted model is used as published.
- **H.2 Context & retrieval corpora** — exact document set in context / indexed, archived in the deposit:
  No retrieval and no index. The entire context of every call is deposited: the task prompt
  (`generation/runs/tasks/*.md`) and the shared condition-text file
  (`generation/runs/prefix_F*.md`). Their sources are `survey/questionnaire.txt`, `codebook.csv`,
  `scripts/lib/submission_spec.R` and `generation/build/cells.json`, all in this repository. Nothing
  else is placed in context.

## I · Data inputs, blinding, and competing interests
- **I.1 Competing interests ★** — funding, in-kind compute/model access, relationships with LLM-interested entities:
  `PENDING (team identity)` — to be declared by the team. The model was accessed through an existing
  commercial subscription, not through a grant of compute or credits from the model provider for this
  benchmark. Any funding and any relationship with an entity with an interest in LLM performance is
  to be listed here.
- **I.2 External human data †** — all external human datasets that informed the approach anywhere (training/fine-tuning/retrieval/ICL/calibration):
  One: the General Social Survey (2018, 2021, 2022, 2024 waves), used only to build the demographic
  profiles, as described in D.1, and reused from the organizers' own v1 clone pool. It contains no
  outcome measure of this study. Census CPS 2024 marginals are used for the education and income
  raking targets. No other external human dataset informed the pipeline: no outcome data, from this
  study or from any comparable experiment, was placed in context, used to fit anything, or used to
  select among configurations. One qualitative prior from the published megastudy literature — that
  single-message effects on group means are small — is stated in the prompt (see C.2); it is not a
  dataset and no numeric value from any study is quoted to the model. The model's own pre-training
  corpus is unknown to us; see I.4.
- **I.3 Blinding attestation ★** — **mandatory.** Signed attestation that no team member accessed, solicited, or was shown any human outcome data from this study, including pilots, before the prediction lock:
  `PENDING (team signature)` — the attestation must be signed by the team member named in 0.1, with a
  date, and must state that no team member accessed, solicited or was shown any human outcome data
  from this study, including pilots, before the prediction lock. It is not signed here on the team's
  behalf. Supporting facts for the signatory: the pipeline reads only the files listed in H.2, all of
  which are benchmark materials that contain no outcome data; each task prompt instructs the model
  not to search for or use any result from this study or its pilots; and `blinding_attestation` in
  `metadata.json` is `true`.
- **I.4 Contamination note †** — training cutoff of every model vs public release dates of this project's materials; note any known exposure:
  `PENDING (after the generation run)` — the model's exact training cutoff is not published at the
  precision this item wants, and is to be recorded from the provider's documentation as of the call
  dates in B.2. Relevant exposure risk: the benchmark's own materials — the call for participation,
  the preregistration and the survey instrument — are public web pages, so a model with a later
  cutoff may have seen the *design*, including the intervention texts and the quota table. That is
  not an advantage on the outcomes, which do not exist publicly. The parent megastudy's results are
  not published. The stimulus texts adapt previously published material, so a model may have seen the
  source articles. No team member has any knowledge of the study's human results to contaminate the
  prompts with.

## J · Internal selection procedure
- **J.1 Design-space search †** — how the final pipeline was chosen: how many configurations tried, internal validation criterion, what data it ran against:
  `PENDING (after the generation run)` — what is fixed in advance:
  *Configurations considered.* Two routes: the HTTP API, and a session with subagents. The session
  was chosen because it needs no metered spend and reuses an existing wave harness. Two batching
  schemes: by condition (17 calls of 13 outcomes) and by outcome (13 calls of 17 conditions). By
  outcome was chosen because the benchmark scores the comparison between conditions. Two ways to
  spend six draws: one framing repeated six times, or three framings twice each. Three framings was
  chosen because Fable 5 exposes no sampling parameters, so repeats of an identical prompt vary
  little and prompt sensitivity is the larger risk. Three framings were designed and all three are
  kept in the ensemble; none was dropped.
  *Validation criterion, and what it ran against.* The aggregation rule is chosen on the
  **voelkel2025** megastudy, not on the target study, because the target's human data cannot be seen
  without breaking blinding. Two internal measurements on our own draws, which use no human data at
  all, are also reported: the share of intervention cells where the six draws agree on the sign of
  the effect, and the ratio of the ensemble's mean absolute effect to the average framing's. Their
  thresholds (60 % and 50 %) were set before generation and decide whether the ensemble mean or a
  single framing is submitted. The results, and the rule actually used, go here, from
  `generation/build/diagnostics_report.txt`.
  *Spread.* The per-cell standard deviation across the six draws is the entry's own uncertainty, and
  is deposited per cell in `generation/build/draw_spread.csv`. Its summary goes here.

## K · Reproducibility & frozen artifacts
- **K.1 Code & materials** — link/DOI, secrets removed, determinism/seeds documented (also record the link in `metadata.json` → `code_repository`):
  The whole pipeline is in this repository, and this repository is the deposit:
  `population/` (the profiles) and `generation/` (the prediction pipeline), with
  `generation/README.md` as the runbook. Link recorded in `metadata.json` → `code_repository`:
  <https://github.com/AndresLaverdeMarin/silicon-sample-submission>. No secrets, no credentials and
  no API keys are used or stored — the model is reached through a session, not a key. Determinism:
  the population uses seed `20260807` and rebuilds byte for byte; all 612 prompts rebuild byte for
  byte and each carries its SHA-256; only the model's own answers are non-reproducible, and all of
  them are deposited raw. Two large derived files are rebuilt rather than deposited
  (`generation/build/population/`, `generation/build/draws.csv`); both are reproducible from
  deposited inputs.
- **K.2 Raw output logs †** — complete unprocessed model responses archived, hashed, time-stamped (required for Tiers 1–2, public or escrowed; Tier 3 where intermediate generations exist; oversized logs may be a separate linked Zenodo upload):
  `PENDING (after the generation run)` — public, not escrowed. Every model answer is deposited
  unprocessed and unedited in `generation/runs/raw/*.json`, one file per call, each stating the model
  identifier its session reported. Answers that failed validation are kept too, in
  `generation/runs/rejected/`, with the reason. Each answer's prompt is deposited beside it and
  hash-pinned in `generation/runs/tasks/*.spec.json`. Timestamps: the Zenodo release fixes the
  archive, and `metadata.json` carries the SHA-256 of the prediction files. The file count and total
  size go here.
- **K.3 Computational resources** — API-call counts, total tokens, cost, compute time:
  `PENDING (after the generation run)` — 612 model calls (one subagent run each), asking for 125,664
  numbers in total, over 6 draws x 13 outcomes x 28 groups. No metered API tokens or cost: the calls
  run inside a Claude Code session on an existing subscription, so the honest resource figure is the
  call count, not a token bill. The counts and the wall-clock time go here, from
  `generation/build/registration_facts.md`.

## L · Disclosure class
Each item above is deposited as **public**, **escrowed** (sealed from the public but available to the
core team and auditors under confidentiality, with a public SHA-256 hash + timestamp so the lock is
still verifiable — an embargo with a sunset date is encouraged), or **withheld** (permitted only for
items marked neither ★ nor †). Your entry's class is set by its **most restricted item** and recorded
in `metadata.json` → `disclosure_class` (and `escrow_doi` if anything is escrowed):
- **A · Open** — all items public. Full results-table standing; all features enter the design-choice analysis.
- **B · Escrowed** — some items sealed but every item is available to the core team/auditors under confidentiality. Full standing with an *escrowed* badge; only publicly disclosed features enter the design-choice analysis.
- **C · Sealed** — one or more permitted items withheld even from escrow. Scored and reported with a *not independently verifiable* flag; excluded from the approach catalogue and design-choice analysis.

**This entry is class A · Open.** Every item above is public, including the † items: the prompts, the
raw model answers, the rejected answers, the design-space search, the population code and the
profile pool itself. Nothing is escrowed and nothing is withheld, so `escrow_doi` in
`metadata.json` is `null`. No part of the pipeline is proprietary and nothing is gitignored for
confidentiality; the two files that are not deposited are large derived artifacts, and both rebuild
from deposited inputs.

★ items must always be public (never escrowed or withheld); † items must be at minimum escrowed. Full
policy: <https://janpfander.github.io/llm_predictions_megastudy/#disclosure>
