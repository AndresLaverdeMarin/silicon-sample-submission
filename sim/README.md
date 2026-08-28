# `sim/` — the Tier-1 pipeline

How to run it. `../README.md` says what the submission is; this file is the
runbook.

Everything runs through **`uv run`**. It builds the environment on first use
and keeps it in step with `pyproject.toml`, so there is no separate install
step and no `.venv/bin/python` to remember.

## Run, in order

```bash
uv run sim/01_persona_characteristics.py
uv run sim/02_write_personas.py          # not written yet
uv run sim/03_generate_replies.py        # not written yet
uv run sim/04_parse.py                   # not written yet
uv run sim/05_raw_export.py              # not written yet
```

Then the benchmark's own tooling. These are **R**, not Python, so they do not
go through `uv`:

```bash
make clean      # raw export -> predictions/<team_id>_T1_primary_v1.csv
make check      # validate. Wants PASS or PASS WITH WARNINGS, never FAIL.
make manifest   # SHA-256 into metadata.json
```

| stage | writes | model | wall clock |
|---|---|---|---|
| 1 | `out/01_personas.csv` | none | **< 1 s**, measured |
| 2 | `out/02_persona_text.csv` | writer | ~1.5 h, ESTIMATE |
| 3 | `out/03_replies.jsonl` | `Qwen3.8-27B` | ~3 h on one H100, ESTIMATE |
| 4 | `out/04_answers.csv` | none | seconds, ESTIMATE |
| 5 | `../raw_data_deposit/…csv` | none | seconds, ESTIMATE |

An ESTIMATE is scaled from a run of the sibling `modelbench` project, not
measured here. Stage 3 is 9,000 respondents x 44 items = **396,000
generations**, at the ~40 generations/second that project measures for this
model in item mode. Replace each estimate with the measured number when the
stage runs: registration item K.3 wants the real wall clock.

Stages 2 and 3 need the GPU extra:

```bash
uv run --extra generate sim/03_generate_replies.py
```

**One stage, one script, one output file.** Stage 3 costs about three hours,
so no stage may make you run the stage before it again. Keep
`out/03_replies.jsonl` and re-run stage 4 as often as you need.

## Stage 1 — build the personas, then check them by hand

### Run it

```bash
cd ~/silicon-sample-submission
uv run sim/01_persona_characteristics.py
```

It rebuilds the pool into `out/00_pool/`, then writes `out/01_personas.csv`
(9,000 rows x 21 columns) and `out/01_report.txt`. It takes under a second.

A pass prints six `OK` lines:

```
spec mirror        OK   ... agree with submission_spec.R
pool rebuilt       OK   ... reproduced population/quota_report.txt byte for byte
size               OK   9,000 rows, 9,000 unique profile_id
moderator levels   OK   ... every value is an exact schema string
conditions         OK   17 present, control 1,000, every intervention 500
age bands          OK   ... every band matches its age
```

Options:

```bash
uv run sim/01_persona_characteristics.py --pool PATH   # read a pool from disk
```

### Check it by hand

The script already checks these. Run them yourself when you want to see the
data rather than trust a report.

```bash
# The report the run wrote, including the realised margins.
cat sim/out/01_report.txt

# 9,001 lines = 9,000 people plus the header.
wc -l < sim/out/01_personas.csv

# One person, field by field.
uv run python -c "import pandas as pd; \
print(pd.read_csv('sim/out/01_personas.csv').iloc[0].to_string())"

# 17 conditions: control 1,000, every intervention 500.
uv run python -c "import pandas as pd; \
print(pd.read_csv('sim/out/01_personas.csv').condition.value_counts())"

# Every moderator level, and its share. Any level not in the schema is a bug.
uv run python -c "import pandas as pd; d=pd.read_csv('sim/out/01_personas.csv'); \
[print(c, dict((d[c].value_counts(normalize=True)*100).round(1))) for c in \
['gender','age_band','race','education','income','party']]"

# The pool rebuild is deterministic. This must print nothing.
diff sim/out/00_pool/quota_report.txt population/quota_report.txt

# The benchmark's own validator. It reads predictions/, not sim/out/.
make check
```

Do not use `cut -d,` on the CSV. `income` holds values such as
`"$100,000 to $167,999"`, so the commas inside quotes will split the wrong
fields.

### If it stops

It stops on the first disagreement and writes nothing. That is on purpose: a
moderator level one character wrong passes `make check`, then drops that
respondent from every subgroup analysis at scoring time, in silence.

| message | what to do |
|---|---|
| `moderator ... differs from submission_spec.R` | the benchmark changed its schema. Update `sim/lib/spec.py` to match the R file, never the other way round. |
| `did not reproduce population/quota_report.txt` | the pool stopped being deterministic. Do not go on — find what changed in `population/` first. |
| `holds level(s) the schema does not allow` | a level string in the pool does not match. Fix the pool, not the check. |
| `below the 500 floor` | a condition has too few respondents. Rebuild the pool. |

## Rules

**Never edit `scripts/`.** That is the benchmark's validator. Change it and
`make check` stops being an independent verdict.

**Never build a composite.** `scripts/clean.R` makes
`trust_multidimensional`, `funding_perceptions` and the four `*_mean`
outcomes from the raw items. Scoring reads the composite columns as
submitted and never recomputes them, so an error here is scored as if it
were the prediction. `sim/lib/spec.py` lists the four traps.

**Do not caricature the moderators.** Stage 2 hands the writer six scored
moderators and ten unscored attributes. A memorable character is the wrong
target. *Demographic predictability* is a Tier-1-only scored analysis: it
fits an OLS of the outcome on one moderator plus condition fixed effects and
compares the R² of the humans with ours. An R² above the humans' is read as
stereotyping and counts against the entry. `party_detail` exists to make a
person specific ("independent, close to republican"), not to make the party
louder.

**The pool is rebuilt, not copied.** Stage 1 runs
`population/02_build_personas.py` (seed 20260807) and stops unless it
reproduces `population/quota_report.txt` byte for byte. No persona file is
committed, and the population step is reproducible from `population/` alone.
