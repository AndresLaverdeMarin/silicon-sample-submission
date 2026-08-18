#!/usr/bin/env python3
"""
Step 1c — recover the organizers' N = 18,000 sampling quotas.

WHY THIS SCRIPT EXISTS
----------------------
Step 1 (`01_census_quotas.py`) computed the quota targets again, from the raw
2024 Census Population Estimates. That was wrong.

The benchmark does not use raw Census proportions. Its preregistration says the
quota table holds "proportions matching the parent megastudy, with counts
rescaled to N = 18,000". The parent megastudy is a real recruitment. Its
realised sample is not the same as the Census.

The difference is small but it is systematic. The largest error was the 18-29
age band: raw Census gives 19.18 %, the organizers give 20.2 %. That is 1.02
points, and it does not go away with more personas.

The organizers make the table with `R/quotas_18000.R` in their own repository.
That script reads `trust_climate_scientists/data/quotas.csv`, which we do not
have. But the rendered table is published as Table 3 of the preregistration,
and the mirror of that page is on disk. So we read the numbers from there.

INPUT
  A local mirror of the benchmark preregistration page (Table 3, N = 18,000):
      preregistration_benchmark.html
  That mirror is NOT part of this repository — it is the organizers' own web
  page. Pass it with --page. You only need it to rebuild the target; the
  rebuilt output is committed, so the rest of the pipeline runs without it.

OUTPUT
  population/quotas_18000.csv             the recovered table, as published
  population/census_quota_targets.json
      the `gender`, `age_band`, `race`, `age_band_by_gender` and
      `race_by_gender` blocks are replaced. `education`, `income` and
      `gss_conditional_splits` are NOT touched: Table 3 does not hold them,
      and they come from step 1b (Census CPS 2024, in the sibling project).

Usage:

    python3 population/01c_quotas_18000.py --page path/to/preregistration_benchmark.html

Then build the personas again:

    python3 population/02_build_personas.py
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent       # population/
_ap = argparse.ArgumentParser()
_ap.add_argument("--page", required=True,
                 help="local mirror of preregistration_benchmark.html (Table 3)")
_args = _ap.parse_args()

PAGE = Path(_args.page)
TARGETS = HERE / "census_quota_targets.json"
TABLE_OUT = HERE / "quotas_18000.csv"

# Table 3 names the largest race group "White (non-Hispanic)". The study's own
# response option is "White / Caucasian". Map it; change no other label.
RACE_LABEL = {"White (non-Hispanic)": "White / Caucasian"}


def read_table3(path: Path) -> list[dict]:
    """Read Table 3 out of the preregistration page.

    Each row gives a total count and the male/female split of that cell. Keep
    the counts, not the printed percentages: the page rounds them to one
    decimal, and the counts give more precision.
    """
    text = re.sub(r"(?s)<(script|style).*?</\1>", " ", path.read_text(
        encoding="utf-8", errors="ignore"))
    tables = re.findall(r"(?s)<table.*?</table>", text)
    wanted = [t for t in tables if "18-29" in t and "Female" in t]
    if len(wanted) != 1:
        raise SystemExit(f"expected 1 quota table, found {len(wanted)}")

    rows, variable = [], None
    for tr in re.findall(r"(?s)<tr.*?</tr>", wanted[0]):
        cells = [re.sub(r"\s+", " ", html.unescape(
            re.sub(r"<[^>]+>", " ", c))).strip()
            for c in re.findall(r"(?s)<t[dh].*?</t[dh]>", tr)]
        cells = [c for c in cells if c]
        if not cells:
            continue
        if len(cells) == 1:                      # a section header row
            variable = cells[0]
            continue
        if cells[0] in ("Total", "Male", "Female"):
            continue
        if len(cells) < 4:
            continue
        n = [int(re.match(r"(\d+)", c).group(1)) for c in cells[1:4]]
        rows.append({"variable": variable,
                     "category": RACE_LABEL.get(cells[0], cells[0]),
                     "total": n[0], "male": n[1], "female": n[2]})
    if len(rows) != 9:
        raise SystemExit(f"expected 9 quota rows, found {len(rows)}")
    return rows


def main() -> int:
    if not PAGE.exists():
        raise SystemExit(f"{PAGE} not found. Mirror the benchmark site first.")
    rows = read_table3(PAGE)

    TABLE_OUT.parent.mkdir(parents=True, exist_ok=True)
    with TABLE_OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["variable", "category", "total",
                                           "male", "female"])
        w.writeheader()
        w.writerows(rows)

    age = [r for r in rows if r["variable"].startswith("Age")]
    race = [r for r in rows if r["variable"].startswith("Race")]
    n_age = sum(r["total"] for r in age)
    n_race = sum(r["total"] for r in race)

    # Gender comes from the same table. Take it from the age panel, which
    # covers every respondent one time.
    n_male = sum(r["male"] for r in age)
    n_female = sum(r["female"] for r in age)

    targets = json.loads(TARGETS.read_text())
    before = dict(targets["age_band"])

    targets["gender"] = {"Male": n_male / (n_male + n_female),
                         "Female": n_female / (n_male + n_female)}
    targets["age_band"] = {r["category"]: r["total"] / n_age for r in age}
    targets["race"] = {r["category"]: r["total"] / n_race for r in race}
    targets["age_band_by_gender"] = {
        r["category"]: {"Male": r["male"] / r["total"],
                        "Female": r["female"] / r["total"]} for r in age}
    targets["race_by_gender"] = {
        r["category"]: {"Male": r["male"] / r["total"],
                        "Female": r["female"] / r["total"]} for r in race}
    targets["source"] = (
        "Benchmark preregistration Table 3 (N = 18,000), the rendered output "
        "of R/quotas_18000.R. Proportions match the parent megastudy, NOT raw "
        "Census. Recovered by simulation/scripts/01c_quotas_18000.py.")
    targets["matches"] = "R/quotas_18000.R in janpfander/llm_predictions_megastudy"
    targets["superseded"] = (
        "The gender, age_band, race and cross-quota blocks replace values that "
        "01_census_quotas.py computed from raw Census PEP 2024. Those were "
        "wrong: the 18-29 band was 19.18 % instead of 20.2 %.")

    TARGETS.write_text(json.dumps(targets, indent=2) + "\n")

    print(f"wrote {TABLE_OUT}  ({len(rows)} rows, N = {n_age:,})")
    print(f"wrote {TARGETS}")
    print()
    print(f"{'age band':<10}{'was':>9}{'now':>9}{'change':>9}")
    for band, now in targets["age_band"].items():
        was = before[band]
        print(f"{band:<10}{100 * was:>9.2f}{100 * now:>9.2f}"
              f"{100 * (now - was):>+9.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
