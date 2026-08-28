# `sim/` — the Tier-1 pipeline

How to run it. Read `../CLAUDE.md` and `../README.md` for what the submission
is; this file is only the runbook.

## Set up, one time

    uv sync

Python 3.11. This makes `.venv/` in the repository root. Stages 2 and 3 need
the GPU extra as well:

    uv sync --extra generate

## Run, in order

    .venv/bin/python sim/01_persona_characteristics.py
    .venv/bin/python sim/02_write_personas.py          # not written yet
    .venv/bin/python sim/03_generate_replies.py        # not written yet
    .venv/bin/python sim/04_parse.py                   # not written yet
    .venv/bin/python sim/05_raw_export.py              # not written yet

Then the benchmark's own tooling:

    make clean      # raw export -> predictions/<team_id>_T1_primary_v1.csv
    make check      # validate. Wants PASS or PASS WITH WARNINGS, never FAIL.
    make manifest   # SHA-256 into metadata.json

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

**One stage, one script, one output file.** Stage 3 costs about three hours,
so no stage may make you run the stage before it again. Keep
`out/03_replies.jsonl` and re-run stage 4 as often as you need.

## Stage 1 — persona characteristics

    .venv/bin/python sim/01_persona_characteristics.py

Writes `out/01_personas.csv` (9,000 rows x 20 columns) and
`out/01_report.txt`. It rebuilds the pool into `out/00_pool/` on the way.

A pass prints six `OK` lines:

    spec mirror        OK   ... agree with submission_spec.R
    pool rebuilt       OK   ... reproduced population/quota_report.txt byte for byte
    size               OK   9,000 rows, 9,000 unique profile_id
    moderator levels   OK   ... every value is an exact schema string
    conditions         OK   17 present, control 1,000, every intervention 500
    age bands          OK   ... every band matches its age

Options:

    --pool PATH    read a pool that is on disk instead of rebuilding it

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

**The pool is rebuilt, not copied.** Stage 1 runs
`population/02_build_personas.py` (seed 20260807) and stops unless it
reproduces `population/quota_report.txt` byte for byte. No persona file is
committed, and the population step is reproducible from `population/` alone.

**Written in ASD-STE100 Simplified Technical English.**
