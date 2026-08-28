#!/usr/bin/env python3
"""
Stage 1 — the persona CHARACTERISTICS.

This stage makes no text and calls no model. It builds the 9,000-person pool
with `population/02_build_personas.py`, checks every column against the
submission schema, and writes the canonical characteristics table that stages
2 and 3 read.

**It stops on the first disagreement.** A moderator level that is one
character wrong passes `make check` and then drops that respondent from every
subgroup analysis at scoring time, in silence. So this stage is strict.

What it checks:

    1.  `sim/lib/spec.py` agrees with `scripts/lib/submission_spec.R`.
        The R file is the authority; the Python copy must not drift.
    2.  The pool holds exactly 9,000 rows and 9,000 unique `profile_id`s.
    3.  Every one of the six moderators uses ONLY the exact level strings.
    4.  All 17 conditions are present, with 500 in each intervention and
        1,000 in control.
    5.  Each age sits in its own band, with the cuts `clean.R` uses.

What it writes:

    sim/out/00_pool/         the pool, from population/02_build_personas.py
    sim/out/01_personas.csv  the canonical characteristics table
    sim/out/01_report.txt    the checks, and the realised margins

The canonical table adds `year_birth` and `control_filler`, and keeps the nine
extra attributes. **The extra attributes are NOT scored.** They are there
because stage 2 writes a persona description from them, and a person with a
religion and a home region reads as a person.

The pool is REBUILT, not copied. `population/02_build_personas.py` is
deterministic — seed 20260807 — so this stage reproduces
`population/quota_report.txt` byte for byte every time. Pass `--pool` to read
a pool that is already on disk instead.

Run it from the repository root:

    .venv/bin/python sim/01_persona_characteristics.py

**Written in ASD-STE100 Simplified Technical English.**
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import spec                                            # noqa: E402

ROOT = HERE.parent
BUILDER = ROOT / "population/02_build_personas.py"
QUOTA_REFERENCE = ROOT / "population/quota_report.txt"
OUT = HERE / "out"
POOL_DIR = OUT / "00_pool"

# The attributes the benchmark does NOT score. Stage 2 uses them to write a
# person; nothing downstream may treat them as an outcome or a moderator.
EXTRA = ["party_detail", "ideology", "household_size", "social_class",
         "region", "urbanicity", "religion", "religiosity", "born_again",
         "trust_science_prior"]

# One control respondent reads ONE filler. The three share the label
# `control`, so the filler is recorded here and never leaves the pipeline.
FILLER_SEED = 20260828


class Stop(SystemExit):
    """A schema disagreement. Never continue past one."""


# ------------------------------------------------------------- the pool --
def build_pool(report: list[str]) -> Path:
    """Run the population builder, and check it reproduced its own report."""
    POOL_DIR.mkdir(parents=True, exist_ok=True)
    run = subprocess.run([sys.executable, str(BUILDER), "--out",
                          str(POOL_DIR)], capture_output=True, text=True)
    if run.returncode != 0:
        raise Stop(f"{BUILDER.name} failed:\n{run.stderr[-2000:]}")
    made = (POOL_DIR / "quota_report.txt").read_text()
    if made != QUOTA_REFERENCE.read_text():
        raise Stop(f"{BUILDER.name} did not reproduce "
                   f"{QUOTA_REFERENCE.relative_to(ROOT)}. The pool is not "
                   f"deterministic any more. Do not go on.")
    report.append(f"  pool rebuilt       OK   {BUILDER.name} reproduced "
                  f"population/quota_report.txt byte for byte")
    return POOL_DIR / "personas.csv"


# ------------------------------------------------------------- the checks --
def r_vector(text: str, name: str) -> list[str]:
    """Pull one `c("a", "b")` vector out of the R spec."""
    match = re.search(rf'{name}\s*=\s*c\((.*?)\)', text, re.S)
    if match is None:
        raise Stop(f"cannot find {name} in submission_spec.R")
    return re.findall(r'"([^"]*)"', match.group(1))


def check_spec_matches_r(report: list[str]) -> None:
    """Check 1 — the Python mirror still agrees with the R authority."""
    path = ROOT / "scripts/lib/submission_spec.R"
    text = path.read_text()
    for name, want in spec.MODERATORS.items():
        got = r_vector(text, name)
        if got != want:
            raise Stop(f"moderator {name!r} differs from {path.name}:\n"
                       f"  R      {got}\n  python {want}")
    block = re.search(r'interventions <- c\((.*?)\n\s*\)', text, re.S)
    got = re.findall(r'"([^"]*)"', block.group(1))
    if got != spec.INTERVENTIONS:
        raise Stop(f"interventions differ from {path.name}")
    report.append(f"  spec mirror        OK   6 moderators and {len(got)} "
                  f"interventions agree with submission_spec.R")


def check_pool(pool: pd.DataFrame, report: list[str]) -> None:
    """Checks 2 to 5 — the pool against the schema."""
    if len(pool) != spec.N_TOTAL:
        raise Stop(f"pool has {len(pool)} rows, the floor is {spec.N_TOTAL}")
    if not pool.profile_id.is_unique:
        raise Stop("profile_id is not unique")
    report.append(f"  size               OK   {len(pool):,} rows, "
                  f"{pool.profile_id.nunique():,} unique profile_id")

    for column, levels in spec.MODERATORS.items():
        if column not in pool.columns:
            raise Stop(f"pool has no column {column!r}")
        bad = sorted(set(pool[column].dropna()) - set(levels))
        if bad:
            raise Stop(f"{column!r} holds level(s) the schema does not "
                       f"allow: {bad}\n  allowed: {levels}")
        if pool[column].isna().any():
            raise Stop(f"{column!r} is missing for "
                       f"{int(pool[column].isna().sum())} rows")
    report.append("  moderator levels   OK   6 moderators, every value is an "
                  "exact schema string")

    counts = pool.condition.value_counts()
    missing = sorted(set(spec.CONDITIONS) - set(counts.index))
    extra = sorted(set(counts.index) - set(spec.CONDITIONS))
    if missing or extra:
        raise Stop(f"conditions wrong. missing={missing} unexpected={extra}")
    if counts["control"] != spec.N_CONTROL:
        raise Stop(f"control has {counts['control']}, "
                   f"the floor is {spec.N_CONTROL}")
    low = {c: int(counts[c]) for c in spec.INTERVENTIONS
           if counts[c] < spec.N_PER_INTERVENTION}
    if low:
        raise Stop(f"below the {spec.N_PER_INTERVENTION} floor: {low}")
    report.append(f"  conditions         OK   17 present, control "
                  f"{counts['control']:,}, every intervention "
                  f"{counts[spec.INTERVENTIONS[0]]}")

    wrong = pool[pool.age.map(spec.age_band) != pool.age_band]
    if len(wrong):
        raise Stop(f"{len(wrong)} rows: age_band does not match age")
    report.append(f"  age bands          OK   ages {pool.age.min()} to "
                  f"{pool.age.max()}, every band matches its age")


# ------------------------------------------------------------ the output --
def canonical(pool: pd.DataFrame) -> pd.DataFrame:
    """The characteristics table stages 2 and 3 read."""
    out = pool.copy()
    # `clean.R` computes age from the birth year, so the pipeline carries the
    # birth year from here on. `age` stays, because stage 2 writes it into
    # the persona text.
    out["year_birth"] = spec.SURVEY_YEAR - out.age
    # Which of the three filler texts a control respondent reads. Drawn once,
    # with a fixed seed, so the assignment is reproducible.
    filler = pd.Series(pd.NA, index=out.index, dtype="object")
    control = out.condition == "control"
    draw = (pd.Series(range(int(control.sum())))
            .sample(frac=1, random_state=FILLER_SEED).to_numpy())
    filler.loc[control] = [spec.CONTROL_FILLERS[i % len(spec.CONTROL_FILLERS)]
                           for i in draw]
    out["control_filler"] = filler
    columns = (["profile_id", "condition", "control_filler"]
               + list(spec.MODERATORS) + ["age", "year_birth"]
               + [c for c in EXTRA if c in out.columns])
    return out[columns]


def party_joint(table: pd.DataFrame) -> list[str]:
    """Check that party keeps its GSS joint with the other attributes.

    Party is never drawn. Each persona is one real GSS respondent, so party
    arrives attached to that person's age, race, ideology, religion and class.
    This reports how far the sampled pool moved from the weighted GSS, inside
    every level of each attribute. It is a REPORT, not a gate: the right
    threshold is a judgement, and small levels move on sampling noise alone.
    """
    gss = pd.read_csv(ROOT / "population/gss_profiles.csv")

    def collapse(value: str) -> str:
        v = str(value or "").strip().lower()
        if "republican" in v and "close to" not in v:
            return "Republican"
        if "democrat" in v and "close to" not in v:
            return "Democrat"
        if "other" in v:
            return "Other"
        return "Independent"

    gss["party"] = gss.partyid.map(collapse)
    gss["age_band"] = pd.cut(gss.age, [17, 29, 44, 59, 200],
                             labels=list(spec.MODERATORS["age_band"])
                             ).astype(str)
    gss["ideology"] = gss.polviews.fillna(
        "moderate, middle of the road").astype(str).str.strip()
    source = {"age_band": "age_band", "ideology": "ideology",
              "religion": "relig", "social_class": "class"}

    out = ["  attribute      levels   median gap   max gap   small levels"]
    for name, column in source.items():
        if name not in table.columns:
            continue
        gss["_k"] = gss[column].astype(str).str.strip()
        totals = gss.pivot_table(index="_k", columns="party", values="wtssps",
                                 aggfunc="sum", fill_value=0)
        want = totals.div(totals.sum(axis=1), axis=0) * 100
        got = pd.crosstab(table[name].astype(str), table.party,
                          normalize="index") * 100
        rows = [i for i in got.index if i in want.index]
        cols = [c for c in spec.MODERATORS["party"]
                if c in got.columns and c in want.columns]
        gap = (got.loc[rows, cols] - want.loc[rows, cols]).abs().to_numpy()
        counts = table[name].astype(str).value_counts()
        small = sum(1 for i in rows if counts.get(i, 0) < 200)
        out.append(f"  {name:<14} {len(rows):>6}   {np.median(gap):>10.1f}"
                   f"   {gap.max():>7.1f}   {small:>12}")
    out.append("  Gaps are percentage points, party share inside one level,")
    out.append("  our 9,000 against the GSS weighted by `wtssps`. A level with")
    out.append("  fewer than 200 people moves on sampling noise alone.")
    return out


def margins(table: pd.DataFrame) -> list[str]:
    """The realised share of each moderator level, for the report."""
    lines = []
    for column, levels in spec.MODERATORS.items():
        lines.append(f"  {column}")
        share = table[column].value_counts(normalize=True) * 100
        for level in levels:
            lines.append(f"      {level:<38} {share.get(level, 0.0):5.1f}%")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pool", help="read this pool instead of rebuilding it")
    args = ap.parse_args()

    report = ["=" * 74, "STAGE 1 — PERSONA CHARACTERISTICS", "=" * 74, "",
              f"schema   scripts/lib/submission_spec.R", "",
              "CHECKS", "-" * 74]
    check_spec_matches_r(report)
    if args.pool:
        path = Path(args.pool)
        report.append(f"  pool               --   read from {path}")
    else:
        path = build_pool(report)
    pool = pd.read_csv(path)
    check_pool(pool, report)

    table = canonical(pool)
    OUT.mkdir(exist_ok=True)
    table.to_csv(OUT / "01_personas.csv", index=False)

    report += ["", "WRITTEN", "-" * 74,
               f"  sim/out/01_personas.csv   {len(table):,} rows x "
               f"{len(table.columns)} columns",
               f"  scored moderators  {', '.join(spec.MODERATORS)}",
               f"  not scored         {', '.join(EXTRA)}",
               f"  control fillers    {table.control_filler.value_counts().to_dict()}",
               "", "REALISED MARGINS", "-" * 74] + margins(table)
    report += ["", "PARTY KEEPS ITS GSS JOINT", "-" * 74,
               "Party is never drawn. It arrives attached to a real person, so",
               "its joint with every other attribute is the GSS joint.",
               ""] + party_joint(table)
    report += ["", "NEXT", "-" * 74,
               "  Stage 2 writes a persona description for each row.",
               "  Stage 3 asks Qwen3.8-27B the 44 items for each row.", "",
               "=" * 74, ""]
    text = "\n".join(report)
    (OUT / "01_report.txt").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
