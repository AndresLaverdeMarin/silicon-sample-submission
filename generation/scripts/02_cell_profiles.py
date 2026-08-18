#!/usr/bin/env python3
"""Step 2 — describe every prediction cell's population.

design.md section 8: for Tier 2 the personas are *context*, not a simulation.
We do not ask the model to answer as 9,000 people (that is Tier 1 work). We
compute what each subgroup looks like and put that in the prompt.

There are 28 groups: the whole sample (the main file) and the 27 moderator
levels (the moderator file). Each gets a share of the sample and a short
demographic summary, both computed from the quota-matched persona pool that
population/02_build_personas.py builds out of population/gss_profiles.csv.

The shares are also what reconciles the two prediction files
(design.md section 6): for every condition and outcome, the level means of one
moderator, weighted by these shares, must average back to the main mean.

Outputs
  generation/build/population/personas.csv|.jsonl   (rebuilt if absent)
  generation/build/cells.json                       the 28 group descriptions

Usage:
  python3 generation/scripts/02_cell_profiles.py [--rebuild]
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.spec import REPO, load_spec  # noqa: E402

BUILDER = REPO / "population" / "02_build_personas.py"
POP_OUT = REPO / "generation" / "build" / "population"
PERSONAS = POP_OUT / "personas.csv"
OUT = REPO / "generation" / "build" / "cells.json"

# Context variables that come from the GSS joint structure rather than the
# quotas. They are the strongest correlates of climate attitudes in the pool,
# so they are what makes a subgroup description informative beyond its label.
CONSERVATIVE = {"conservative", "extremely conservative", "slightly conservative"}
LIBERAL = {"liberal", "extremely liberal", "slightly liberal"}
BACHELOR_PLUS = {"Bachelor's degree", "Master's degree / Professional degree",
                 "Doctorate degree / Ph.D."}


def build_personas(rebuild: bool) -> list[dict]:
    if rebuild or not PERSONAS.exists():
        POP_OUT.mkdir(parents=True, exist_ok=True)
        print(f"building personas -> {POP_OUT.relative_to(REPO)}/ "
              "(deterministic, seed 20260807)")
        subprocess.run([sys.executable, str(BUILDER), "--out", str(POP_OUT)],
                       check=True, capture_output=True, text=True)
    with PERSONAS.open(newline="") as fh:
        return list(csv.DictReader(fh))


def pct(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else round(100 * part / whole, 1)


def summarise(rows: list[dict], share: float, sst: dict, n_pool: int,
              defines: str | None = None) -> str:
    """One paragraph describing a group, in the study's own label strings.

    `defines` is the moderator this group is a level of. Its clause is dropped,
    because restating it ("Gender: 100 % Male") only spends prompt on what the
    group heading already says. Age is kept even for an age band: the mean age
    inside the band is new information.
    """
    n = len(rows)
    g = Counter(r["gender"] for r in rows)
    ages = sorted(int(r["age"]) for r in rows)
    bands = Counter(r["age_band"] for r in rows)
    race = Counter(r["race"] for r in rows)
    party = Counter(r["party"] for r in rows)
    inc = Counter(r["income"] for r in rows)
    ideo = Counter(r["ideology"].strip().lower() for r in rows)
    sci = Counter(r["trust_science_prior"].strip().lower() for r in rows)
    relig = Counter(r["born_again"].strip().lower() for r in rows)
    edu_bplus = sum(1 for r in rows if r["education"] in BACHELOR_PLUS)

    # median age band, by walking the spec order until half the group is passed
    cum, median_band = 0, sst["moderators"]["age_band"][-1]
    for band in sst["moderators"]["age_band"]:
        cum += bands[band]
        if cum >= n / 2:
            median_band = band
            break

    top_race = ", ".join(f"{pct(v, n)} % {k}" for k, v in race.most_common(3))
    parties = ", ".join(f"{pct(party[p], n)} % {p}"
                        for p in sst["moderators"]["party"])

    clauses = [
        f"This is the whole sample (n = {n:,} profiles)." if share == 1.0 else
        f"This group is {share * 100:.1f} % of the sample "
        f"(n = {n:,} of {n_pool:,} profiles).",
        None if defines == "gender" else
        (f"Gender: {pct(g['Male'], n)} % Male, {pct(g['Female'], n)} % Female, "
         f"{pct(g['Other'], n)} % Other."),
        f"Age: median band {median_band}, mean {sum(ages) / n:.0f} years.",
        None if defines == "race" else f"Race / ethnicity: {top_race}.",
        None if defines == "education" else
        f"Education: {pct(edu_bplus, n)} % hold a bachelor's degree or higher.",
        None if defines == "income" else
        (f"Income: {pct(inc['Less than $30,000'], n)} % under $30,000, "
         f"{pct(inc['$100,000 to $167,999'] + inc['$168,000 or more'], n)} % "
         f"$100,000 or more."),
        None if defines == "party" else f"Party: {parties}.",
        f"Ideology: {pct(sum(v for k, v in ideo.items() if k in CONSERVATIVE), n)} % "
        f"conservative, "
        f"{pct(sum(v for k, v in ideo.items() if k in LIBERAL), n)} % liberal.",
        f"Prior confidence in the scientific community: "
        f"{pct(sci['a great deal'], n)} % a great deal, "
        f"{pct(sci['hardly any'], n)} % hardly any.",
        f"{pct(relig['yes'], n)} % describe themselves as born-again or "
        f"evangelical Christian.",
    ]
    return " ".join(c for c in clauses if c)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true",
                    help="rebuild the persona pool even if it is present")
    a = ap.parse_args()

    sst = load_spec()
    rows = build_personas(a.rebuild)
    n_all = len(rows)
    if n_all != 9000:
        sys.exit(f"02: expected 9,000 personas, got {n_all:,}")

    groups = {"all": {"key": "all", "moderator": None, "level": None,
                      "n": n_all, "share": 1.0,
                      "summary": summarise(rows, 1.0, sst, n_all)}}
    shares: dict[str, dict[str, float]] = {}

    for mod, levels in sst["moderators"].items():
        shares[mod] = {}
        seen = Counter(r[mod] for r in rows)
        unknown = set(seen) - set(levels)
        if unknown:
            sys.exit(f"02: personas carry {mod} values outside the spec: "
                     f"{sorted(unknown)} — these would drop out of scoring")
        for lv in levels:
            sub = [r for r in rows if r[mod] == lv]
            share = len(sub) / n_all
            shares[mod][lv] = share
            if not sub:
                sys.exit(f"02: no personas in {mod} = {lv!r}. Every one of the "
                         "27 moderator cells needs a population description.")
            groups[f"{mod}::{lv}"] = {
                "key": f"{mod}::{lv}", "moderator": mod, "level": lv,
                "n": len(sub), "share": share,
                "summary": summarise(sub, share, sst, n_all, defines=mod)}

        total = sum(shares[mod].values())
        if abs(total - 1.0) > 1e-9:
            sys.exit(f"02: {mod} shares sum to {total}, not 1")

    doc = {
        "built_by": "generation/scripts/02_cell_profiles.py",
        "source": ("population/gss_profiles.csv, quota-matched by "
                   "population/02_build_personas.py (seed 20260807). "
                   "The pool is the organizers' own v1 clone pool, not a "
                   "benchmark resource — see population/README.md and "
                   "registration item D.1."),
        "n_personas": n_all,
        "n_groups": len(groups),
        "shares": shares,
        "groups": groups,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    print(f"{len(groups)} group descriptions "
          f"(1 whole sample + {len(groups) - 1} moderator levels)")
    for mod, sh in shares.items():
        parts = ", ".join(f"{k} {v * 100:.1f} %" for k, v in sh.items())
        print(f"  {mod:<10} {parts}")
    print(f"\nexample — gender::Male:\n  {groups['gender::Male']['summary']}")
    print(f"\n-> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
