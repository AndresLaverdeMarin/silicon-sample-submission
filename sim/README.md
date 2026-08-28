# `sim/` — the Tier-1 pipeline

Python, managed by `uv`. Build the environment one time:

    uv sync

Then run each stage from the repository root, in order. **One stage, one
script, one output file.** Stage 3 costs about three hours on one H100, so no
stage may make you re-run the stage before it.

| stage | script | writes | model |
|---|---|---|---|
| 1 | `01_persona_characteristics.py` | `out/01_personas.csv` | none |
| 2 | `02_write_personas.py` | `out/02_persona_text.csv` | writer |
| 3 | `03_generate_replies.py` | `out/03_replies.jsonl` | `Qwen3.8-27B` |
| 4 | `04_parse.py` | `out/04_answers.csv` | none |
| 5 | `05_raw_export.py` | `../raw_data_deposit/…csv` | none |

Then the repository's own tooling takes over:

    make clean      # raw export -> predictions/<team>_T1_primary_v1.csv
    make check      # validate
    make manifest   # SHA-256 into metadata.json

**Never edit `scripts/`.** That is the benchmark's validator. If you change
it, `make check` stops being an independent verdict.

## The pool is rebuilt, not copied

Stage 1 runs `population/02_build_personas.py` itself and then checks that it
reproduced `population/quota_report.txt` byte for byte. The builder is
deterministic (seed 20260807). So the repository holds no copied persona file,
and the whole population step is reproducible from `population/`.

## Stage 1 — done

`01_persona_characteristics.py` checks the pool against
`scripts/lib/submission_spec.R` and writes the canonical table. It stops on
the first disagreement, because a moderator level that is one character wrong
passes `make check` and then drops that respondent from every subgroup
analysis in silence.

`sim/lib/spec.py` mirrors the R schema in Python. Stage 1 compares the two at
run time, so the mirror cannot drift.

It adds two columns the pool does not carry:

- **`year_birth`** = 2026 − age. `clean.R` derives the age and the band
  itself, so the raw export must carry the birth year.
- **`control_filler`** — one of neckties / baseball / dances for each control
  respondent, drawn with a fixed seed. All three keep the label `control`.

**Written in ASD-STE100 Simplified Technical English.**
