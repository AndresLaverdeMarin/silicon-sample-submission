#!/usr/bin/env python3
"""
Stage 0b — the adult population of each state, for the state-adaptive arm.

The `Extreme weather predictions` arm is not one text. A participant reports
their home state, and then reads ONE of four texts. The text is chosen by the
risk category of that state. `survey/questionnaire.txt` holds the state lists.

Our personas carry a Census REGION, not a state. So stage 3 must give each
respondent of that arm a state. It draws the state inside the person's own
region. The draw is weighted by the number of adults in each state, so a
respondent is as likely to live in California as a real adult of the West is.
An unweighted draw would make Wyoming as common as California.

This stage writes the weights. It reads the Census Bureau Population
Estimates Program (PEP), vintage 2024, state by age and sex. It keeps ages
18 and over, both sexes, all 50 states and the District of Columbia. It is
the same programme and the same vintage that `population/` uses for the
quotas, so the two agree.

Source file (public bulk server, no API key):
  https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/
  asrh/sc-est2024-agesex-civ.csv

It writes:

    population/state_adult_pop_2024.csv    51 rows: state, region, adults

Run it from the repository root. It needs the network one time:

    uv run sim/00b_state_populations.py

**Written in ASD-STE100 Simplified Technical English.**
"""
from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "population/state_adult_pop_2024.csv"
URL = ("https://www2.census.gov/programs-surveys/popest/datasets/"
       "2020-2024/state/asrh/sc-est2024-agesex-civ.csv")

# The PEP REGION code, and the region name our personas use.
REGIONS = {1: "northeast", 2: "midwest", 3: "south", 4: "west"}
ADULT = 18          # the study is adults only
TOP_AGE = 85        # PEP codes 85 as "85 and over"; 999 is the total row


def main() -> None:
    print(f"reading {URL}")
    with urllib.request.urlopen(URL, timeout=180) as fh:
        raw = pd.read_csv(io.BytesIO(fh.read()))

    # SUMLEV 040 is a state row. SEX 0 is both sexes. AGE 999 is the total,
    # and it must not be added to the single ages.
    rows = raw[(raw.SUMLEV == 40) & (raw.SEX == 0)
               & (raw.AGE >= ADULT) & (raw.AGE <= TOP_AGE)]
    out = (rows.groupby(["NAME", "REGION"], as_index=False)["POPEST2024_CIV"]
              .sum()
              .rename(columns={"NAME": "state",
                               "POPEST2024_CIV": "adults_18plus"}))
    out["region"] = out.REGION.map(REGIONS)
    out = out[["state", "region", "adults_18plus"]].sort_values("state")

    if len(out) != 51:
        sys.exit(f"expected 51 states and D.C., got {len(out)}")
    if out.region.isna().any():
        sys.exit(f"unknown region code for: "
                 f"{out[out.region.isna()].state.tolist()}")

    OUT.write_text(out.to_csv(index=False))
    total = out.adults_18plus.sum()
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  states       {len(out)} (50 + District of Columbia)")
    print(f"  adults 18+   {total:,}")
    for reg, n in out.groupby("region").adults_18plus.sum().items():
        print(f"  {reg:10s}   {n:>12,}  ({n / total * 100:4.1f}%)")


if __name__ == "__main__":
    main()
