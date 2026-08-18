# How the Tier-2 predictions are made

This folder holds the pipeline that produces the two prediction files of this
entry. It implements the plan in the team's design notes. Every step is here;
nothing is done by hand.

The entry is **Tier 2**, team `team_27`, entry `secondary-1`, model
`claude-fable-5`, disclosure class **A** (everything public).

---

## What must be produced

| File | Rows | Grid |
|---|---|---|
| `predictions/team_27_T2_secondary-1_v1_cells_main.csv` | **221** | 17 conditions x 13 outcomes |
| `predictions/team_27_T2_secondary-1_v1_cells_moderator.csv` | **5,967** | 17 conditions x 27 moderator levels x 13 outcomes |

6,188 cell means in total. Every cell must appear exactly one time. An empty
cell fails. An `NA` fails.

---

## The five design decisions

**1. One task shows all 17 conditions.** The benchmark scores how the 17 texts
compare with each other. A task that asks for one condition at a time makes that
comparison noise. So each task gives the model all 17 texts and asks for one
table.

**2. The model predicts survey items. The code computes the composites.** 6 of
the 13 outcomes are means of several items. `trust_multidimensional` is the mean
of four 3-item subscale means. The model answers the 44 raw items;
`05_aggregate.py` does the arithmetic. This stops a composite from
contradicting its own items, which the benchmark keeps as submitted.

**3. Six draws per cell: 3 framings x 2 repeats.**

| Framing | What changes |
|---|---|
| `F1` | Plain. The group label only, no population description. |
| `F2` | The same request, plus the computed profile of the group. |
| `F3` | The same context as F2, but two stages: the control mean first, then each intervention's shift from control. |

The three framings also show the 17 texts in three different orders, so the
position of a text cannot fix its rank. The two repeats of a framing use the
same prompt, byte for byte. Fable 5 has no `temperature`, so repeats remove less
noise than an ensemble removes prompt sensitivity; the budget goes to the
framings.

**4. Every draw is kept.** `06_diagnostics.py` measures two things on them:
whether the draws agree on the sign of each effect, and how far they spread.
If they do not agree, the entry submits one framing instead of their mean. The
measurement decides, not a preference.

**5. The moderator file is reconciled to the main file.** For every condition
and outcome, the 27 level means weighted by their population shares must average
back to the main mean. Where they do not, the block gets an additive shift. A
shift corrects the level and keeps every difference between levels, which is the
moderation being predicted.

---

## The population

`population/` builds 9,000 quota-matched profiles from real GSS respondents.
For Tier 2 they are **context, not a simulation**: we do not ask the model to
answer as 9,000 people, which is Tier-1 work. `02_cell_profiles.py` turns them
into 28 group descriptions, one per prediction cell group, like this:

> This group is 24.4 % of the sample (n = 2,199 of 9,000 profiles). Gender:
> 52.2 % Male ... Ideology: 74.3 % conservative, 5.3 % liberal. Prior
> confidence in the scientific community: 19.9 % a great deal ...

The pool is the organizers' own v1 clone pool, not a benchmark resource. Say so
in registration item D.1. See `population/README.md`.

---

## Order of the work

Run every command from the repository root.

```bash
# 0. Prove the session runs Fable. Nothing else runs before this.
python3 generation/scripts/00_model_probe.py --prompt
python3 generation/scripts/00_model_probe.py --record "<exact model id>" --how "..."

# 1-2. Build the fixed inputs (fast, deterministic, safe to repeat)
make -C generation materials      # stimuli + 44 items, from survey/ and codebook.csv
make -C generation cells          # the 28 group descriptions

# 3. Write the tasks
make -C generation plan           # counts only
make -C generation wave WAVE=1    # 612 task files + runs/waves/wave01.json

# 4. Answer them (see "Running a wave" below), then
make -C generation collect        # validates every answer -> build/draws.csv

# 5-6. Build the files and measure the draws
make -C generation aggregate      # writes predictions/
make -C generation diagnose       # direction agreement, spread, J.1 facts

# 7. Fingerprint and validate with the organizers' own tools
make manifest
make check
```

`make -C generation wave WAVE=2` after some answers have landed selects only
what is still missing. Waves never repeat finished work.

---

## Running a wave

612 tasks, one subagent each. In the Fable session:

```bash
python3 generation/scripts/07_next_tasks.py --limit 12
```

That prints one line per pending task. Give one line to one subagent, about 8
to 12 at a time. Each line is:

> Read `generation/runs/prefix_F1.md` in full, then read
> `generation/runs/tasks/<task_id>.md` and do exactly what it says. Write the
> JSON file it asks for. Reply with only the number of values you wrote.

The subagents inherit the session's model, so a Fable session gives Fable
subagents. Two things check that, per answer and not per session:

* `model_id` — every answer states its own model. `04_collect.py` rejects any
  answer that does not name Fable.
* `read_check` — every answer quotes four words out of one condition text. The
  17 texts sit in one shared prefix file instead of inside all 612 prompts, so
  this is what proves a subagent opened it.

A rejected answer moves to `generation/runs/rejected/` with its reason, and its
task becomes pending again. Run `collect` as often as you like; it is a pure
function of the files on disk.

---

## The dry run

```bash
make -C generation dryrun
make -C generation dryclean
```

`dryrun` fills all 612 tasks with deterministic fake numbers and runs the whole
pipeline. It proved, before any model time was spent, that the tasks reassemble
into exactly 221 and 5,967 rows and that the organizers' `check.R` gives
`PASS WITH WARNINGS`, 0 fail, with every structural check green.

Its numbers are not a prediction and cannot become one. Each fake answer carries
`model_id: "MOCK-dry-run-not-a-model"`, which `04_collect.py` rejects without
`--allow-model MOCK`, and which makes `05_aggregate.py` refuse to write
`predictions/`. Its diagnostics are meaningless too: the fake effects are
identical across framings by construction, so the agreement number is high for a
reason that says nothing about Fable.

---

## Files

| Path | What it is | Deposited |
|---|---|---|
| `scripts/` | the pipeline | yes |
| `build/spec.json` | the canonical labels, dumped from `scripts/lib/submission_spec.R` | yes |
| `build/materials.json` | 17 stimulus texts + 44 items | yes |
| `build/cells.json` | the 28 group descriptions and their population shares | yes |
| `build/population/` | the 9,000 personas | no — 12 MB, deterministic from `population/` |
| `build/draws.csv` | every value of every draw, long format | no — 14 MB, rebuilt from `runs/raw/` |
| `build/draw_spread.csv` | per-cell SD and direction agreement | yes — registration J.1 |
| `runs/prefix_F*.md` | the 17 condition texts, one file per framing | yes — registration C.1 |
| `runs/tasks/*.md` | every prompt, word for word | yes — registration C.1 |
| `runs/tasks/*.spec.json` | machine-readable task spec + `prompt_sha256` | yes |
| `runs/raw/*.json` | every model answer, unprocessed | yes — registration K.2 |
| `runs/rejected/` | answers that failed validation, with the reason | yes — registration G.2 |
| `runs/model_probe/` | every step-0 model probe, including failed ones | yes — registration B.1 |

The pipeline is deterministic apart from the model itself. `03_prepare_wave.py`
rebuilds all 612 prompts byte for byte, and each `.spec.json` carries the
SHA-256 of its prompt, so any prompt can be checked against the deposit.

**Licence note.** The 17 stimulus texts adapt copyrighted material and are not
covered by this repository's licence grant. They are already in the deposit, in
`survey/`. `build/materials.json`, `runs/prefix_F*.md` and the prompts reproduce
them from there; they add no material that the deposit did not already hold.

---

## Labels

No label string is typed in this folder. `lib/spec.py` dumps
`scripts/lib/submission_spec.R` through R and reads the result, and it stops the
pipeline if that file ever describes a different grid. The model never types a
label either: it answers in codes (`C07`, `L3`), and `04_collect.py` maps them
back. A near-miss label therefore cannot reach the submission.
