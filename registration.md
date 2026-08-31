# Silicon Sample Benchmark — method registration form

Fill in every item before the prediction lock; this file ships inside your repo's Zenodo release
(see the README's *Deposit* step). This form covers **one entry** (one repo / one Zenodo release,
`primary` or `secondary-k` — see the README's *What counts as a submission*); if you submit several
entries, fill one form per entry. Items marked **★**
must be disclosed **fully publicly** (never escrowed or withheld). Items marked **†** must be at
minimum escrowed — they may be sealed from the public, but never withheld from the core team. Items
not applicable to your approach: write `N/A`. When several models serve different pipeline stages, complete the model
sections (B) once per model. See the call's *Disclosure policy* for escrow rules.

> **History.** An earlier version of this entry was a **Tier-2** cell-mean forecast made by
> `claude-fable-5`, with a pipeline in `generation/`. It was withdrawn on 2026-08-28 and its code
> was deleted. That form is in git history at commit `aa4e060`. Nothing from it is carried into the
> answers deposited here.

> **This form covers the `secondary-1` entry.** It is one of two entries from `team_27`. The
> `primary` entry uses the same population, the same stimuli, the same model and the same
> hardware, and asks each multi-item scale as one block instead of one item for each call. That is
> the only factor that differs, and the pair is designed to bracket the human coherence value from
> below and above. See E.2 and J.1. Its repository:
> <https://github.com/AndresLaverdeMarin/silicon-sample-submission-secondary-1>. The repository name holds the word `secondary-1` because it was made before the labels
> were set on 2026-08-31. The name is not the label; see J.1.

> **Every fact the run produces is filled in**, from `sim/out/03_report.txt` and the run log. Two
> items are complete. Andres Laverde Marin signs the competing-interests declaration (I.1) and
> the blinding attestation (I.3) for `team_27`, and sends the benchmark's own exposure declaration
> with the deposit email.

---

## 0 · Approach identity and output
- **0.1 Team ★** — name, the one or two members (teams are at most two, unless a larger team was approved on request), affiliations, corresponding contact:
  Team `team_27`, two members.
  Andres Laverde Marin, Joint Research Centre, European Commission, ORCID
  [0000-0002-9578-4412](https://orcid.org/0000-0002-9578-4412), andres.laverde-marin@ec.europa.eu.
  **Corresponding contact, and the member who deposits and signs for the team.**
  Giordano De Marzo, University of Konstanz, ORCID
  [0000-0002-3127-5336](https://orcid.org/0000-0002-3127-5336), giordano.de-marzo@uni-konstanz.de.
  The same values are in `metadata.json` (`team_name`, `contact`, `creators`). Both ORCIDs pass the
  ISO 7064 MOD-11-2 checksum.
- **0.2 Plain-language summary ★** — one paragraph, what the approach does (not how):
  We build 9,000 synthetic people whose demographics match the United States adult population, and
  who are related to each other the way real people are. We give each person one of the 17 texts to
  read, then ask that person all 44 survey questions, one question at a time. A local open-weights
  language model answers as that person. We never ask the model for an average, a trend or an
  effect. We collect 9,000 individual questionnaires, and the effects come out of the arithmetic
  afterwards, exactly as they do for the human study.
- **0.3 Submission tier & approach family ★** — tier (1/2/3); family (e.g. per-respondent simulation / agent / direct forecast; single model / ensemble / multi-agent / zero-shot / literature-conditioned):
  **Tier 1.** Per-respondent simulation. Single model, single draw for each respondent and item; no
  ensemble, no multi-agent scaffold, no averaging over repeats. Zero-shot: no fine-tuning, no
  retrieval, no in-context example of any study's results. The model is local open weights, run on
  our own hardware. The 44 raw survey items are generated and the 13 scored outcomes are computed by
  the benchmark's own `scripts/clean.R`.
- **0.4 Pipeline diagram** — ordered steps from raw inputs to submitted file:
  1. `population/01c_quotas_18000.py` — build the quota targets from the preregistration Table 3 and
     Census CPS 2024.
  2. `population/02_build_personas.py` — rake 9,000 GSS respondents onto those margins by iterative
     proportional fitting, then quota-sample independently inside each of the 17 conditions
     (seed `20260807`).
  3. `sim/00_extract_materials.py` — extract the 17 condition texts and the 44 items into
     `sim/out/00_materials.json`.
  4. `sim/01_persona_characteristics.py` — write the 9,000-row persona table
     (`sim/out/01_personas.csv`) and its self-check (`sim/out/01_report.txt`).
  5. `sim/03_generate_replies.py` — 9,000 respondents x 44 items = 396,000 generations. One prompt
     asks one item. Writes `sim/out/03_replies.jsonl`.
  6. `sim/04_build_raw_export.py` — one row for each respondent, 44 raw item columns, into
     `raw_data_deposit/`.
  7. `make clean` — the benchmark's own `scripts/clean.R` builds every composite and writes
     `predictions/team_27_T1_secondary-1_v1.csv`.
  8. `make manifest` then `make check` — SHA-256 into `metadata.json`, then the organizers' validator.
  **Stage 2 (`sim/02_write_personas.py`) is NOT in this pipeline.** It writes prose personas with a
  second model. It was measured and dropped; see D.2.
- **0.5 Coverage ★** — number of respondents/cells/estimates; mapping to conditions. Full coverage is required: every submission predicts **all 16 interventions and all 13 outcomes** (partial coverage is not accepted). Confirm here:
  **Full coverage, confirmed.** 9,000 synthetic respondents: 500 in each of the 16 interventions and
  1,000 in `control`. Every respondent answers all 44 raw items, so all 13 scored outcomes are
  present for all 17 conditions. No cell is empty and no cell is `NA`. This meets the preregistered
  precision floor exactly (500 per intervention, 1,000 in control). Condition and outcome labels come
  from `scripts/lib/submission_spec.R`; no label is typed by hand or written by the model.

## A · Scope of LLM use
- **A.1 Purpose** — every workflow stage where LLMs are used:
  One stage produces submitted values: step 5, the answers. Every other step is deterministic Python
  or R. No language model builds the population, renders a persona, computes a composite, or edits an
  output file.
  Two models were used **for validation only**, and neither contributed any submitted value:
  `google/gemma-4-26B-A4B-it` wrote prose personas in the measurement that led us to drop stage 2
  (D.2) and answered block prompts in the v18 format measurement on public Voelkel data (J.1); and
  `qwen/qwen3.8-flash` answered a 60-respondent probe used to check response realism (J.1). Gemma has
  a section B, because it ran locally on the same stack as the answering model. Flash does not,
  because it serves no pipeline stage; it is described in J.1 with its settings and cost in K.3.
  Six further open-weight models were run **only in the comparison that chose the answering model**,
  before this pipeline existed. None of them answered any item of this megastudy and none
  contributed a submitted value. They are named in section B (models 3 to 8).
- **A.2 Degree of automation ★** — confirm fully automated, no human in the loop at prediction time; note any exception:
  Fully automated at prediction time. The prompts are built by code from the materials before any
  answer exists. No answer is edited, selected, or re-asked with different wording. One automated
  exception, pre-specified and blind to the value: a generation whose text holds no number inside the
  item's scale is re-asked with the identical prompt, up to five rounds, until every cell has a
  value. Nothing else is repaired.

## B · Model / system details (once per model)

### B — Model 1: the answering model (produces every submitted value)
- **B.1 Model name(s)** — exact identifiers incl. provider, size, version/timestamp, source link:
  `Qwen/Qwen3.8-27B` — 27 billion parameters, dense (no mixture of experts), instruction-tuned.
  Local weights from the Hugging Face Hub, <https://huggingface.co/Qwen/Qwen3.8-27B>. The weights are
  read from the local cache; no hosted endpoint answers any item.
- **B.2 Access & context mode** — API/web/local; API name + version; chat vs stateless; exact call dates:
  Local inference on our own hardware. No API, no provider, no account, no key. The interface is a
  **text completion, not a chat turn**: the chat template is not applied, and the model continues a
  prompt that ends with `You choose: '`. Every one of the 396,000 generations is stateless with
  respect to every other; the model is given one prompt and keeps no history.
  Call-date window: **2026-08-29T12:07:30Z to 2026-08-29T17:40:33Z**, one continuous run of
  5 h 33 m. No submitted value was generated outside this window.
- **B.3 Configuration** — temperature, top-p/top-k, max tokens, penalties, stop sequences, seeds, reasoning effort, completions per item:
  `temperature 1.0`, `top_p 0.95`, no top-k, no penalties, `max_tokens 64`, stop sequence `'`
  (the closing quote), `seed 20260828`, `max_model_len 4096`. **One completion per respondent and
  item.** Reasoning: not applicable — this is a completion, and no thinking mode is enabled.
  The 64-token budget is deliberate: the answer is normally about 3 tokens, but a tight budget
  truncates the rare answer that opens with a sentence before the number and turns a good answer into
  a parse failure.
- **B.4 Customization** — fine-tuning, RAG, prompt optimization, tool use, web search, agentic scaffolds (cross-ref H):
  None. No fine-tuning, no retrieval, no web search, no tool use, no agentic scaffold, and no prompt
  optimization against any outcome data. The published weights are used as they are.
- **B.5 Persistent memory** — across interactions? what persisted:
  None. Each generation sees one prompt and nothing else. The engine's prefix cache is a speed
  optimization over identical token prefixes; it changes no output.
- **B.6 Inference stack** — for local models: serving framework + version, quantization, hardware:
  vLLM 0.19.1, torch 2.10.0+cu128, transformers 5.14.1, Python 3.11. **No quantization** — the
  published BF16 weights. Hardware: one NVIDIA H100 80GB HBM3, driver 550.127.08, CUDA 12.4.
  `gdn_prefill_backend: triton` is set, because the default kernel needs `nvcc`, which this machine
  does not have.
- **B.7 Ensembles** — members + exact aggregation rule:
  N/A. One model, one draw for each respondent and item. Nothing is averaged, and no ensemble exists.
  This is deliberate: v16 measured that averaging several draws for one person improves treatment-
  effect recovery a little and reduces the response variance ratio a great deal (from 0.36 to 0.14 on
  `Concern`), and the variance ratio is the benchmark's headline distributional diagnostic.

### B — Model 2: `google/gemma-4-26B-A4B-it` (validation only, no submitted value)
- **B.1–B.6** — `google/gemma-4-26B-A4B-it`, local weights, same vLLM stack and same H100. It was
  used twice, both times on public data: it wrote prose personas in the v15 measurement described in
  D.2, and it answered Voelkel block prompts in the v18 format measurement described in J.1. **No
  text or value it produced reaches the deposited answers**, because stage 2 is not in the pipeline
  and no Voelkel answer is a submitted value. Call windows: 2026-08-29 (v15) and 2026-08-29T21:23Z
  to 2026-08-29T21:53Z (v18).

### B — Models 3 to 8: the open-weight comparison set (validation only, no submitted value)
- **B.1–B.6** — The answering model was chosen before this pipeline existed, by running Ashokkumar
  et al.'s own method over that paper's **secondary archive (archive 2)**. Two criteria selected the
  studies, applied together: **nearest in subject** to this megastudy, and **deliverable as survey
  text**, because our model reads text only. That leaves three — `Voelkel2025`, `Doell` and
  `Zickfeld`. `Zickfeld` is pure text. `Voelkel2025` and `Doell` are text survey pages that also
  hold images (22 and 62 image positions); the image files are not deposited on OSF, so each
  position is marked in place and carries the authors' own caption where one exists. **`Goldwert`
  was left out**: six of its arms are video and **the control is one of them**, so no text control
  exists and no treatment effect can be formed. Eight open-weight models were scored on effect
  recovery, all locally on the same H100 and the same vLLM stack, no quantization, in the window
  **2026-08-17 to 2026-08-20**. Two are declared above: `Qwen/Qwen3.8-27B` (model 1, chosen) and
  `google/gemma-4-26B-A4B-it` (model 2). The other six are `google/gemma-4-E4B-it`,
  `openai/gpt-oss-20b`, `google/gemma-3-27b-it`, `microsoft/Phi-4`,
  `mistralai/Mistral-7B-Instruct-v0.3` and `deepseek-ai/DeepSeek-R1-Distill-Llama-8B`.
  `Qwen/Qwen3.8-27B` recovered the measured effects best and was chosen for Tier 1. **None of the
  six answered any item of this megastudy, and none contributed a submitted value.** This comparison
  ran in a separate working project, `modelbench`, which is **not part of this deposit** — see K.1.
  What is deposited is its conclusion: the choice of model 1. The ranking and the rest of the search
  are described in J.1. **Where these names appear in the deposited code.**
  `sim/03_generate_replies.py` holds a vLLM engine-settings table that names
  `google/gemma-4-26B-A4B-it`, `google/gemma-4-E4B-it` and `google/gemma-3-27b-it`, and
  `sim/02_write_personas.py` names `google/gemma-4-26B-A4B-it` as the stage-2 persona writer. Both
  are configuration only. Stage 2 is not in the submitted pipeline (D.2), and **only
  `Qwen/Qwen3.8-27B` answered a submitted item**. The files are kept as they ran, because K.1
  claims the deposited code rebuilds every prompt byte for byte.

## C · Prompts
- **C.1 Exact prompts** — verbatim text or link to deposited file; were they iteratively refined? pre-specified vs in response to outputs:
  The prompt is built by `sim/lib/answer_prompt.py::build_prompt` from four parts: the persona
  sentence, the condition text the respondent read, the item question, and the item's scale. The
  builder and its inputs (`sim/out/00_materials.json`, `sim/out/01_personas.csv`) are deposited, so
  every one of the 396,000 prompts rebuilds exactly. The prompts are also stored verbatim beside
  every answer in the raw log (K.2).
  **Pre-specified**, in the sense that matters: the structure follows Ashokkumar et al. (2026), whose
  method this replicates, and it was fixed before any megastudy item was answered. It was not refined
  in response to any answer to this study's items.
- **C.2 System-wide instructions**:
  **None.** There is no system prompt, and no chat template is applied. The whole context is the
  completion text shown in C.1. The model is not told it is a language model, not told to be helpful,
  and not given any instruction about how to answer.
- **C.3 Prompt-design rationale** — brief rationale for the prompt design: why prompts were structured as they were, and the reasoning behind major design choices (recommended, not required):
  *One item for each prompt.* This is Ashokkumar et al.'s own format, and it is what our replication
  of that paper reproduces. The alternative — all 44 items in one JSON answer — was used earlier in
  the sibling project and was reversed on 2026-08-19, because the paper, its Supplementary
  Information and its Code Ocean capsule all show one question per prompt.
  *A completion, not a chat turn.* The model continues a survey transcript instead of replying to a
  request. The published evidence says the two regimes differ: base and completion-style interfaces
  are better **emulators** — they give response distributions nearer to human data and preserve
  demographic structure better — while post-trained chat interfaces are better **estimators**
  (<https://arxiv.org/abs/2608.03044>). Tier 1 is an emulation task.
  *The prompt ends at an open quote.* This makes the candidate answers prefix-free, so the model
  writes a number and stops at the closing quote, and no instruction about formatting is needed.
  *No numeric prior.* The prompt never states where an outcome level sits. The level is part of what
  Tier 1 is scored on, so a stated prior would make our own base rate the prediction.

## D · Persona / profile construction (Tiers 1–2)
- **D.1 Profile source** — source of demographic profiles you constructed: a public survey (e.g. GSS / ANES / Census), other survey, fully synthetic, or none. The benchmark ships no participant pool; report how you built yours, incl. condition assignments:
  A public survey: 9,000 General Social Survey respondents from the 2018, 2021, 2022 and 2024 waves,
  with their post-stratification weights. **We did not draw this pool ourselves.** The file is
  `clone_profiles/profiles.csv` from the organizers' own research repository — the pool they built
  for their own v1 simulation, not a resource given to teams, and not something the benchmark ships.
  It is deposited here as `population/gss_profiles.csv`. Full provenance is in
  `population/README.md`.
  Construction: iterative proportional fitting of the GSS weights onto the preregistered quota
  margins (gender, age band, race from Table 3 of the benchmark preregistration, N = 18,000;
  education and income from Census CPS 2024), then quota sampling of the gender x age and
  gender x race cross-quotas **independently inside each of the 17 conditions**, which is what
  randomisation achieves in the real study and removes demographic composition as a confound of the
  treatment effects. Real microdata gives the joint structure, because independent draws for each
  variable produce people who do not exist and make the moderators artificially independent.
  Deterministic: seed `20260807`. `population/quota_report.txt` is the realised-against-target check.
- **D.2 Profile verbalization** — which variables, rendered how (template vs generated narrative; if generated: model + prompt):
  **A fixed template, built in code. No model writes any persona.** The renderer is
  `sim/lib/answer_prompt.py::template_persona`. It writes one paragraph in the second person, from
  these attributes: age, race, gender, region, education, household income, household size, social
  class, party (the detailed label where the pool has one), political ideology, religion,
  religiosity, born-again status, and prior confidence in the scientific community. A respondent with
  race `Other` has no race clause, and a respondent with no religion gets one sentence saying so.
  Nothing else is stated, and no attribute is invented.
  **Why a template and not a generated narrative.** We measured both. Run v15 answered 6,000
  respondents on Voelkel et al. (2025) twice, changing only the rendering: the code template, and
  prose written by `google/gemma-4-26B-A4B-it`. The template scored a mean treatment-effect
  correlation of 0.334 against the prose arm's 0.304, and the two were equal on every distributional
  metric (Concern variance ratio 0.41 against 0.40; Policies overlap 0.60 against 0.58). The prose
  writer therefore bought nothing measurable, while adding a second model to declare and silently
  dropping attributes it chose not to mention. It was removed.
- **D.3 Assignment & weighting** — number of personas, assignment to conditions (your responsibility, all 17 conditions), reuse, weighting/matching:
  9,000 profiles: 500 in each of the 16 interventions and 1,000 in `control`, matching the per-cell
  sizes of the human half that submissions are scored against. Each profile is assigned to exactly
  one condition, by quota sampling inside that condition, so no profile is reused across arms and
  the design is between-subjects, as the study is. Every profile is queried. **No weighting of any
  kind is applied to the submitted respondents**: the file is the raw synthetic sample.

## E · Stimulus and survey administration
- **E.1 Stimulus presentation** — verbatim vs paraphrase; how state-contingent content is handled:
  Verbatim. Each respondent reads exactly one condition text, extracted unmodified from the study
  materials. Control: each control respondent reads **one** of the three neutral filler texts, drawn
  in the persona table, not all three. State-contingent content: the `Extreme weather predictions`
  arm is state-adaptive in the real study. We reproduce it — a state is drawn for each respondent,
  weighted by adult population inside that respondent's region, and the respondent then reads the
  intro that names that state and its risk category, followed by the one case text that state maps
  to. A respondent with no region gets the study's own fallback, the generic intro and case 4, which
  is what a real participant who answers "prefer not to say" is shown.
- **E.2 Survey walk-through** — one item/call vs blocks vs whole survey; context carry-over; item/option ordering & randomization; scale display; attention/comprehension handling:
  **One item for each call.** 44 calls for each respondent. **No context carry-over**: a respondent's
  answer to item 12 is not visible when item 13 is asked. Every prompt restates the persona and the
  condition text, so each item is answered by the same described person reading the same page, and
  nothing else. Items are asked in codebook order; options are not randomised. The scale is shown
  with the item, with its endpoint labels, and `funding_5` also keeps its labelled midpoint, because
  the midpoint is part of the instrument. Attention and comprehension items are not generated — the
  benchmark does not score them.
  **A consequence we state plainly.** Because the items are independent calls, a respondent's answers
  are not conditioned on one another. We measured the result on a 60-respondent probe of the
  megastudy items: mean inter-item correlation 0.127 and Cronbach alpha 0.635 on the 12-item trust
  scale, against a human anchor near 0.49 and 0.92. Our respondents are therefore internally noisier
  than real respondents. This is a property of the paper-faithful item-mode format, it is disclosed
  here, and it was not corrected after the fact.
- **E.3 Response elicitation** — free text / constrained choice / structured output / token log-probabilities (if logprobs: normalization & mapping):
  Free text, then a strict parse. The model completes the open quote and stops at the closing quote.
  `sim/lib/answer_prompt.py::parse` takes the first number in the completion and accepts it only if
  it is inside that item's scale: 0 to 100 for the 42 sliders, 0 to 10 whole dollars for
  `donation_ams`, 0 or 1 for `newsletter_signup`. **No log-probabilities are used**, and no answer is
  interpreted or rewritten.

## F · Stochasticity and aggregation
- **F.1 Runs & seeds** — runs per respondent/item/estimate; seeds; reproducibility under identical settings:
  **One run for each respondent and item.** No repeats and no draws to average. Seed `20260828` for
  the sampler, `20260807` for the population. Reproducibility: the population rebuilds byte for byte,
  and every prompt rebuilds byte for byte. The generations themselves are sampled at temperature 1.0,
  so an identical rerun on identical hardware reproduces them only up to the engine's own batching
  non-determinism. All raw generations are deposited (K.2), so no result depends on a rerun.
- **F.2 Aggregation rule** — how multiple generations become submitted values (mean/median/mode/first/sampled/…):
  **None, at the respondent level.** There is exactly one generation for each respondent and item, and
  it is submitted as it is. The only aggregation is the benchmark's own: `scripts/clean.R` builds the
  six composite outcomes as row means of their items, and reverse-codes
  `funding_perceptions = 100 - funding_5`. **We compute no composite in our own code.**

## G · Validation & post-processing
- **G.1 Human validation** — any human review of outputs (often N/A):
  No human read, reviewed, edited or selected any generated value. Human review was limited to the
  code and to the aggregate reports.
- **G.2 Post-processing** — parsing rules; handling of refusals/malformed/missing/out-of-range; exclusions; for approaches that generate individual responses, the resulting effective N per condition (descriptive disclosure, not a scoring input):
  Parsing: the first number in the completion, accepted only inside the item's scale (E.3). A
  completion with no number, or with a number outside the scale, is **re-asked with the identical
  prompt**, up to five rounds, until every cell has a value. Nothing is repaired, interpolated or
  imputed, and no respondent is excluded — full coverage is mandatory.
  Effective N per condition: 500 for each intervention and 1,000 for control, with no exclusions.
  Measured over the 396,000 generations of the deposited run: **95.9 per cent parsed on the first
  pass**, then four retry rounds recovered the rest — round 1 re-asked 16,263 cells and recovered
  15,268; round 2 re-asked 995 and recovered 887; round 3 re-asked 108 and recovered 95; round 4
  re-asked 13 and recovered 13. **Final parse rate 100.0 per cent, and no cell was filled.** Every
  submitted value is a parsed model generation. A 60-respondent probe of the same materials on
  2026-08-28 gave 95.6 per cent on the first pass, which the full run reproduced.
- **G.3 Calibration corrections** — any post-hoc scaling/shifting/debiasing and exactly what data it was fit on (cross-ref H/I):
  **None.** No scaling, no shifting, no debiasing, no clamping, no rounding, no reweighting. The
  submitted values are the parsed generations, and the composites are the benchmark's own arithmetic
  over them. No human outcome data, from this study or any other, was used to adjust any value.
  This item is about the adjustment of values. Human data from the public Voelkel study did
  select design settings, among them the persona rendering and the number of draws for each
  answer. See D.2, B.7 and J.1.

## H · Learning and conditioning components
- **H.1 Fine-tuning data** — exact corpus (hashes/DOIs), hyperparameters, checkpoints:
  N/A — no fine-tuning. The published weights are used as they are.
- **H.2 Context & retrieval corpora** — exact document set in context / indexed, archived in the deposit:
  No retrieval and no index. The entire context of every generation is the prompt described in C.1,
  built from `sim/out/00_materials.json` (from the benchmark's own `survey/` and `codebook.csv`) and
  `sim/out/01_personas.csv`. Both are in this repository. Nothing else is ever placed in context.

## I · Data inputs, blinding, and competing interests
- **I.1 Competing interests ★** — funding, in-kind compute/model access, relationships with LLM-interested entities:
  **Declared by the team. There are no competing interests.** No funding was received for this
  entry. No compute, credits, model access or other in-kind support was given by any language-model
  provider, or by any other entity with an interest in language-model performance. The answering
  model, `Qwen/Qwen3.8-27B`, is open weights. The team downloaded it publicly and ran it on its own
  hardware. The one hosted model used for validation, `qwen/qwen3.8-flash` through OpenRouter
  (J.1, K.3), was paid for out of pocket at a cost below one United States dollar, and it
  contributed no submitted value. The two members are employed by the Joint Research Centre of the
  European Commission and by the University of Konstanz. Neither institution funded this entry, and
  neither has a stake in the result. Neither member has a financial or advisory relationship with a
  language-model provider. The benchmark's own exposure declaration carries the same statement. The
  organizers ask for one such declaration for each team, signed by one member for everyone. Andres
  Laverde Marin signs it for `team_27` and sends it with the deposit email to
  janlukas.pfaender@gmail.com.
- **I.2 External human data †** — all external human datasets that informed the approach anywhere (training/fine-tuning/retrieval/ICL/calibration):
  Four, and none of them contains any outcome of this study.
  1. **General Social Survey** (2018, 2021, 2022, 2024), used only to build the demographic profiles
     (D.1), reused from the organizers' own v1 clone pool.
  2. **Census CPS 2024** marginals, used only as raking targets for education and income.
  3. **Voelkel et al. (2025)**, 13,821 public individual responses from OSF. Used **only for
     validation and for selecting the design** (J.1), never placed in context and never used to fit,
     scale or shift any submitted value. It is a different study, on climate attitudes, with no
     measure of trust in climate scientists.
  4. **Ashokkumar et al. (2026)**, *LLMs can predict the results of social science experiments*,
     Code Ocean capsule 9843791. It is our method reference and our scoring reference, in three
     distinct ways, none of which puts a number into a prediction:
     a. **Method.** The prompt structure and the one-item-per-call format come from that paper. This
        entry keeps that format; our `primary` entry departs from it for the 6 multi-item
        outcomes.
     b. **Measured effects of other studies.** The capsule's archive holds the published arm effects
        and their standard errors for 4 megastudies (`voelkel2025`, `doell2024`, `zickfeld2025`,
        `broockman2023`). These are the human targets our model choice and format search were scored
        against (J.1, B models 3 to 8).
     c. **Scoring code.** `r_raw` and `r_adj` in J.1 are computed by the capsule's own R functions
        (`metafor::rma.mv`), not by a re-implementation, so our numbers and the paper's are the same
        quantity. The published GPT-4 value we compare against, 0.745 / 0.803 on Voelkel, is that
        paper's own result and is reproduced from the archive to four decimal places.
     **No value from the capsule enters any prediction**, and it holds no outcome of this study.
  No outcome data from this study, or from any pilot of it, informed any part of the pipeline.
- **I.3 Blinding attestation ★** — **mandatory.** Signed attestation that no team member accessed, solicited, or was shown any human outcome data from this study, including pilots, before the prediction lock:
  **Attested.** *"We attest that no member of team_27 accessed, solicited, or was shown any human
  outcome data from the target megastudy, including any pilot of it, at any time before the
  prediction lock."*
  Signed for `team_27` by **Andres Laverde Marin** (andres.laverde-marin@ec.europa.eu),
  **2026-08-31**. Giordano De Marzo (giordano.de-marzo@uni-konstanz.de) is the second member and is
  covered by this attestation. The benchmark's own exposure declaration carries the same statement.
  The organizers ask for one such declaration for each team, signed by one member for everyone.
  Andres Laverde Marin signs it and sends it with the deposit email to janlukas.pfaender@gmail.com.
  Supporting facts: the pipeline reads only the files listed in H.2, all of which
  are benchmark materials that contain no outcome data; no network request of any kind is made during
  generation, because the model is local; and `blinding_attestation` in `metadata.json` is `true`.
- **I.4 Contamination note †** — training cutoff of every model vs public release dates of this project's materials; note any known exposure:
  `Qwen/Qwen3.8-27B` publishes no exact training cutoff at the precision this item asks for. Relevant
  exposure risk: the benchmark's own materials — the call for participation, the preregistration and
  the survey instrument — are public web pages, so a model with a later cutoff may have seen the
  **design**, including the intervention texts and the quota table. That is not an advantage on the
  outcomes, which do not exist publicly: the parent megastudy's results are unpublished and the human
  data is sealed. The stimulus texts adapt previously published material, so the model may have seen
  the source articles. No team member has any knowledge of the study's human results.

## J · Internal selection procedure
- **J.1 Design-space search †** — how the final pipeline was chosen: how many configurations tried, internal validation criterion, what data it ran against:
  **This entry's design was selected on distributional realism, not on effect recovery.** We state the
  reason, because it is unusual and it is measured.
  *What was tried.* The sibling project `modelbench`, **which is not part of this deposit (K.1)**,
  scored 8 open-weight models and 14 prompt versions on 4 megastudies from the Ashokkumar archive
  (`voelkel2025`, `doell2024`, `zickfeld2025`, `broockman2023`), covering 255 arms over 49 cells,
  against a permutation null. Model choice used the 3 climate studies (B, models 3 to 8);
  `broockman2023` was added later, for the prompt-version work only.
  Renderings tried and rejected: enriched personas, per-replicate donors, two-voice narratives, ten
  bios for each person, ten different people for each demographic slot, and exact-distribution
  reading by log-probabilities.
  *Why we did not select on effect recovery.* Over the 11 prompt versions that ran on two of those
  megastudies, the ranking they induce agrees at **r = +0.16 (p = 0.63)**, Spearman +0.20 (p = 0.56).
  The spread across versions (sd 0.042 on `voelkel2025`) is **smaller** than the spread across single
  persona draws of one version (sd 0.023 to 0.132). Choosing the best of 12 such versions would buy
  about +0.07 in correlation from luck alone. A configuration selected that way would not generalise,
  and we did not select one.
  *What we did select on.* Properties of the generator that do not depend on which study is used to
  test them: inter-item coherence, response-shape realism, and the absence of any outcome with zero
  variance. These were measured against Voelkel et al. (2025), whose respondents are public.
  *The decisions this produced.* Drop the prose persona writer (D.2, measured in v15). Do not average
  several draws for each person (B.7, measured in v16). Keep one item for each call, the paper's own
  format (C.3).
  *A validation probe, disclosed for completeness.* `qwen/qwen3.8-flash` answered the same 60
  respondents and 44 items through a hosted endpoint, to test whether a much larger model uses the
  persona more. It produced higher inter-item coherence (0.581 against 0.120) and an equal
  party gap (18.4 against 17.1 points), but piled 44 per cent of its answers on the scale endpoints
  and returned a constant zero for `newsletter_signup`, which is a degenerate outcome. It was not
  adopted, and it contributed no submitted value.
  *Effect recovery was measured after the design was fixed, not used to choose it.* We ran this
  entry's format and the `primary` entry's format on Voelkel's 11 arms and scored them with the
  Ashokkumar capsule's own R code (`metafor::rma.mv`). Mean over the 4 outcomes: this entry r_raw
  0.449 / r_adj 0.476; `primary` r_raw 0.504 / r_adj 0.537; GPT-4, as published by Ashokkumar et
  al., 0.745 / 0.803. The two entries are the same within noise — with 10 arms a Pearson r has a 95
  per cent interval of about [-0.46, +0.75]. **The measurement selected no value in this file. It did select which entry the team
  calls `primary`; see the next paragraph.**
  *The `primary` label was set on 2026-08-31, after these measurements. We declare it as a
  post-hoc order.* The two entries were both complete before any of these numbers were read. The
  numbers changed no value in either prediction file. They changed only which entry the team calls
  its best. `modelbench/random_baseline_entryAB.py` adds a permutation test on the same Voelkel
  arms: shuffle our 10 arm labels 20,000 times, the same shuffle in all four outcomes, and score
  again. Against the archive's published effects, the `primary` entry gives mean r +0.505, against a null 95th
  percentile of +0.411 (p = 0.018); this entry gives +0.450 against +0.418 (p = 0.038). Against effects
  recomputed from Voelkel's raw OSF file, neither entry clears its null (p = 0.068 and p = 0.140),
  and the two human estimates agree with each other at only r = 0.80 to 0.90. The `primary` entry is also
  nearer to the human respondents on level error (mean absolute error 5.11 against 11.45 scale
  points) and on distribution shape (density overlap 0.72 against 0.63, mean absolute correlation
  between outcomes 0.605 against 0.238, where real people give 0.651). With 10 arms the gap between
  the two entries is not significant, so the order is a judgement on consistent direction and not a
  test result. No outcome data of the target study was used, because none exists.
  *What we did not fix.* The item-mode format leaves our respondents internally noisier than real
  ones (E.2). We disclose the measurement rather than tune it away after seeing it. Our `primary`
  entry is the same pipeline with that one factor changed, so the pair brackets the human value
  rather than guessing at it. **The bracket applies to the 6 multi-item outcomes only.** The 7
  single-item outcomes are byte-identical in the two entries, because the `primary` entry reuses
  them unchanged. On those 7 of the 13 scored outcomes the two entries submit the same values.
- **J.2 Selection blinding †** — confirm no selection used outcome data from this study:
  Confirmed. No configuration, model, prompt, rendering or sampling setting was chosen using any
  outcome data from the target study, or from any pilot of it. Every selection above used either the
  public Voelkel et al. (2025) respondents, the public Ashokkumar archive, or measurements that use
  no human data at all.

## K · Reproducibility & frozen artifacts
- **K.1 Code & materials** — link/DOI, secrets removed, determinism/seeds documented (also record the link in `metadata.json` → `code_repository`):
  **Everything that produced a submitted value is in this repository, and this repository is the
  deposit**: `population/` (the profiles) and `sim/` (the Tier-1 pipeline), with `sim/README.md` as
  the runbook. Running `population/` then `sim/` steps 00 to 04 rebuilds
  `predictions/team_27_T1_secondary-1_v1.csv` from the deposited inputs, with no other repository
  needed.
  **What is deliberately NOT in this deposit.** The measurements that CHOSE the design — the model
  comparison in B (models 3 to 8) and the v15 to v21 format search in J.1 — ran in a separate
  working project, `modelbench`, against public archives. No code or output of theirs is used by any
  step above, and no value they produced enters a prediction. They are reported here as results, and
  the deposit stands on its own without them.
  Link recorded in `metadata.json` → `code_repository`:
  <https://github.com/AndresLaverdeMarin/silicon-sample-submission>. **No secrets, no credentials and
  no API keys** are stored in the repository; the answering model is local and needs none.
  Determinism: the population uses seed `20260807` and rebuilds byte for byte; every prompt rebuilds
  byte for byte from deposited inputs; the sampler uses seed `20260828`.
- **K.2 Raw output logs †** — complete unprocessed model responses archived, hashed, time-stamped (required for Tiers 1–2, public or escrowed; Tier 3 where intermediate generations exist; oversized logs may be a separate linked Zenodo upload):
  **Public, not escrowed.** All 396,000 generations are deposited unprocessed in
  `sim/out/03_replies.jsonl`, one record for each respondent and item, each holding the raw
  completion text beside the parsed value. The file is too large for the git repository, so it is a
  separate Zenodo upload linked from this deposit.
  SHA-256 `b18b26a766933b8c1a1f46726b27e486eebe7252fbbafd2800df3e370904f75e`, 70,825,249 bytes
  (67.5 MiB), 396,000 records.
- **K.3 Computational resources** — API-call counts, total tokens, cost, compute time:
  **No API calls and no monetary cost for any submitted value**: the answering model runs on the
  team's own H100 80GB, on local weights, with `HF_HUB_OFFLINE=1`. Measured on the deposited run:

  | quantity | measured |
  |---|---|
  | API calls | **0** |
  | monetary cost | **0.00 USD** |
  | generations, first pass | 396,000 |
  | generations, retries | 17,379 (16,263 + 995 + 108 + 13) |
  | input tokens, first pass | **259,068,496** (mean 654.2 for each prompt) |
  | output tokens, first pass | **1,206,790** (mean 3.0 for each completion) |
  | input tokens, retries | about 11,370,000, at the same mean |
  | wall clock, generation | **333.0 min** (5 h 33 m), 2026-08-29T12:07:30Z to 17:40:33Z |
  | throughput | **19.8 generations for each second** |
  | engine start-up and prompt building | **61 s**, before the call window opens (process start 12:06:29Z) |

  Token counts are exact, not estimated: the 396,000 prompts were rebuilt from the deposited inputs
  and tokenized with the model's own tokenizer, and the completions were counted from the raw log
  named in K.2. The retry figure is the one estimate here, because the retry prompts are identical
  to the prompts they re-ask.
  *Validation cost outside the submission.* One hosted model was used, `qwen/qwen3.8-flash` through
  OpenRouter (provider: Alibaba Cloud Int.), `/api/v1/chat/completions`, thinking disabled,
  `temperature` 1.0 / 0.7 / 0.3, `top_p` 0.95, `max_tokens` 16, call window 2026-08-29. It answered a
  60-respondent, 44-item probe in the control condition. **Total spend under one United States
  dollar, and no value it produced reaches the deposited answers.** Local compute: about 5 hours of
  the same H100 for the v15 to v21 measurements, of which 38 minutes was the v21 effect-recovery run
  on Voelkel reported in J.1.

## L · Disclosure class
Each item above is deposited as **public**, **escrowed** (sealed from the public but available to the
core team and auditors under confidentiality, with a public SHA-256 hash + timestamp so the lock is
still verifiable — an embargo with a sunset date is encouraged), or **withheld** (permitted only for
items marked neither ★ nor †). Your entry's class is set by its **most restricted item** and recorded
in `metadata.json` → `disclosure_class` (and `escrow_doi` if anything is escrowed):
- **A · Open** — all items public. Full results-table standing; all features enter the design-choice analysis.
- **B · Escrowed** — some items sealed but every item is available to the core team/auditors under confidentiality. Full standing with an *escrowed* badge; only publicly disclosed features enter the design-choice analysis.
- **C · Sealed** — one or more permitted items withheld even from escrow. Scored and reported with a *not independently verifiable* flag; excluded from the approach catalogue and design-choice analysis.

**This entry is class A · Open.** Every item above is public, including the † items: the prompt
builder, all 396,000 raw generations, the design-space search, the population code and the profile
pool itself. Nothing is escrowed and nothing is withheld, so `escrow_doi` in `metadata.json` is
`null`. No part of the pipeline is proprietary. The one artifact not inside the git repository is
the raw generation log, which is too large for git and is deposited to Zenodo separately (K.2).

★ items must always be public (never escrowed or withheld); † items must be at minimum escrowed. Full
policy: <https://janpfander.github.io/llm_predictions_megastudy/#disclosure>
