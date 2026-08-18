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

# 4. Answer them (see "Running it in Claude Code with Fable 5"), then
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

## Running it in Claude Code with Fable 5

This is the only manual step of the pipeline. One person opens a Claude Code
session, sets it to Fable 5, and hands the pending tasks to subagents. Every
step before and after it is a script.

### 1. Set up the session

| What | How |
|---|---|
| Model | `/model`, then select **Fable 5**. Subagents inherit the session model, so this one setting decides the whole run. |
| Reasoning effort | Use the highest effort the session offers. One task asks for up to 520 numbers in one table. |
| Directory | The repository root. Every command below assumes it. |
| Before you start | `git pull`, so your pending count includes the other person's answers. |

Python 3 with the standard library is all you need to answer tasks. R is needed
only for the final `make check`.

### 2. Prove the session runs Fable

Do this one time in each new session, before anything else.

```bash
make -C generation probe
```

It prints three questions. Put them to a **fresh subagent**, not to the session
itself: the orchestrating context can hold an environment block that predates a
`/model` switch. Then record what the subagent answered:

```bash
python3 generation/scripts/00_model_probe.py \
    --record "claude-fable-5" \
    --how "fresh subagent quoted its own system prompt"
```

`03_prepare_wave.py` refuses to write a wave until a recorded probe names
Fable. Every probe is kept, including a failed one, because registration item
B.1 asks for them.

### 3. The loop

```bash
python3 generation/scripts/07_next_tasks.py --count      # what is left
python3 generation/scripts/07_next_tasks.py --limit 12   # the next 12 prompts
make -C generation collect                               # validate what landed
```

`--limit 12` prints one line per pending task, like this:

> Read generation/runs/prefix_F1.md in full, then read
> generation/runs/tasks/F1r1__inst_trust_mean__age_band__c01.md and do exactly
> what it says. Write the JSON file it asks for. Reply with only the number of
> values you wrote.

Give **one line to one subagent**, and run 8 to 12 subagents at a time. Each
subagent reads the shared prefix file with the 17 condition texts, reads its own
task file, writes one JSON file into `generation/runs/raw/`, and replies with
the count of values it wrote. When the batch finishes, run `collect`, then ask
for the next 12. Repeat until the count is zero.

`collect` is a pure function of the files on disk. Run it as often as you like.

### 4. Rules while the run is open

* **One task, one subagent.** Do not answer a task in the main context. Every
  answer must come from the same kind of fresh context; the main session has
  already read other tasks and other answers.
* **Never re-run `make -C generation wave WAVE=1`.** All 612 prompts exist
  already, and that command would overwrite `runs/waves/wave01.json`, which is
  part of the deposit record. You do not need it.
* **Never edit a file in `generation/runs/raw/` by hand.** Those are the raw
  model answers and they are deposited unprocessed. If a number looks wrong,
  delete the file and let the task run again.
* **Never edit `scripts/` at the repository root.** That directory is the
  organizers' engine. A local change makes our self-check disagree with their
  scoring.
* **Never use `git add -A` or `git add .`.** Stage files by name. Some files are
  deliberately untracked and must stay out of the public history.
* **Do not look for the human results of this study.** The entry is a blind
  forecast, and any contact with the outcome data invalidates it.

### 5. When an answer is rejected

`04_collect.py` checks every answer against its own task spec. Four things cause
a rejection:

| Reason | What happened |
|---|---|
| `model_id` does not name Fable | the session was not Fable when that subagent ran |
| `read_check` does not match | the subagent did not open the prefix file with the 17 texts |
| the keys do not match the spec | a missing condition, a stray group, a wrong item code |
| a value is not a number | a `null`, a string, or a placeholder |

The file moves to `generation/runs/rejected/` with the reason in a
`.reason.txt` beside it, and its task becomes pending again on its own. Read the
reason, then let `07_next_tasks.py` hand the task out again.

### 6. Two people at the same time

`07_next_tasks.py` prints the pending tasks from the front of one sorted list,
so two people who run it at the same moment get the same tasks. Split the work
by draw and pass `--only-draw` on every command:

```bash
python3 generation/scripts/07_next_tasks.py --limit 12 \
    --only-draw F2r2 --only-draw F3r1 --only-draw F3r2
```

There are six draws of 102 tasks each: `F1r1`, `F1r2`, `F2r1`, `F2r2`, `F3r1`,
`F3r2`. Each answer is its own file, named after its task, so two people in two
lanes never write the same file and git merges the work without a conflict.
`HANDOVER.md` holds the full lane and commit rules.

### 7. When every task is answered

One person runs the last four steps. They take minutes.

```bash
make -C generation collect      # every answer -> build/draws.csv
make -C generation aggregate    # writes the two files in predictions/
make -C generation diagnose     # direction agreement and spread
make manifest                   # SHA-256 into metadata.json
make check                      # the organizers' validator - must be 0 fail
```

`aggregate` refuses to write `predictions/` while any cell is missing, and
refuses again if any draw was not produced by Fable. If it stops, it tells you
how many cells are short.

Read the verdict line that `diagnose` prints. If direction agreement is below
60 %, or the attenuation ratio is below 0.50, do **not** submit the ensemble
mean. Re-run the aggregation with one framing:

```bash
make -C generation aggregate RULE=framing:F3
```

Both thresholds were fixed before any answer arrived. Follow what they say.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `03: no model probe names Fable` | step 0 was not recorded in this session | run `make -C generation probe` and record the answer |
| `collect` rejects with `model_id ... is not Fable` | the session was not Fable when that subagent ran | set `/model`, probe again, let the task run again |
| `collect` rejects with a `read_check` reason | the subagent answered without opening the prefix file | nothing to repair; the task is pending again |
| `05: N cells have no prediction yet` | the run is not finished | answer more tasks, then `collect` again |
| a subagent replies with prose instead of a count | it may not have written the file | look in `generation/runs/raw/`; if the file is missing, hand the task out again |
| `make check` looks clean but reports very little | the staged short-circuit: `metadata.json` still points at the `example_*` files | delete them, run `make manifest`, then `make check` again |

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
