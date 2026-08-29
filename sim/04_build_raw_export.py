#!/usr/bin/env python3
"""
Stage 4 — turn the stage-3 answers into the raw survey export.

The benchmark cleans a Tier-1 submission with its OWN script. We give it a
raw export; `make clean` (scripts/clean.R) builds every composite, reverse-
codes `funding_5` into `funding_perceptions`, and writes the prediction file.
**We never compute a composite ourselves.** See `sim/lib/spec.py`.

WHAT THIS WRITES

One row for each respondent. The columns are `spec.RAW_COLUMNS`: eight
identity and demographic columns, then the 44 raw items. `clean_lib.R` reads
a plain CSV as happily as a real Qualtrics export, so the 17 Qualtrics system
columns are not needed.

WHY IT CHECKS SO MUCH

`make check` is the only verdict that counts, and it runs after `make clean`.
Every failure it can report is cheaper to find here. This stage stops on:

  * an empty cell                  make check FAILS on one NA
  * a missing or extra respondent  coverage must be exact
  * a missing item                 all 44, every row
  * an unknown level string        condition and moderator names are exact
  * a value outside its scale      0-100 sliders, 0-10 dollars, 0/1 newsletter
  * more than one replicate        Tier 1 is one answer for each person

HOW TO RUN

    uv run sim/04_build_raw_export.py --answers sim/out/03_replies.jsonl

Then, from the repository root:

    make clean            # -> predictions/<team_id>_T1_<entry>_v1.csv
    make check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import spec                                       # noqa: E402

OUT = HERE / "out"
DEPOSIT = HERE.parent / "raw_data_deposit"


def fail(msg: str, detail: list | None = None) -> None:
    print(f"\nFAIL — {msg}", file=sys.stderr)
    for d in (detail or [])[:10]:
        print(f"       {d}", file=sys.stderr)
    if detail and len(detail) > 10:
        print(f"       ... and {len(detail) - 10} more", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", default=str(OUT / "03_replies.jsonl"))
    ap.add_argument("--personas", default=str(OUT / "01_personas.csv"))
    ap.add_argument("--out", default=None,
                    help="default raw_data_deposit/tier1_raw_export.csv")
    ap.add_argument("--expect", type=int, default=spec.N_TOTAL)
    ap.add_argument("--items", nargs="*", default=None,
                    help="override the item list (validation runs)")
    args = ap.parse_args()

    items = args.items or list(spec.ALL_ITEMS)
    long = pd.DataFrame([json.loads(l) for l in open(args.answers)])

    reps = sorted(long.replicate.unique())
    if reps != [0]:
        fail(f"stage 3 wrote replicates {reps}. Tier 1 takes ONE answer for "
             "each person. Re-run stage 3 without --replicates.")

    holes = long[long.value.isna()]
    if len(holes):
        fail(f"{len(holes):,} empty cell(s). make check FAILS on one NA.",
             [f"{r.profile_id} / {r.item}" for r in holes.itertuples()])

    wide = long.pivot(index="profile_id", columns="item", values="value")
    missing_items = [i for i in items if i not in wide.columns]
    if missing_items:
        fail(f"{len(missing_items)} item(s) never answered", missing_items)

    people = pd.read_csv(args.personas).set_index("profile_id")
    only_answers = wide.index.difference(people.index)
    only_people = people.index.difference(wide.index)
    if len(only_answers) or len(only_people):
        fail("the answers and the persona pool do not hold the same people",
             [f"answered but not in the pool: {list(only_answers[:5])}",
              f"in the pool but not answered: {list(only_people[:5])}"])

    frame = people.join(wide).reset_index()
    if len(frame) != args.expect:
        fail(f"{len(frame):,} respondents, expected {args.expect:,}")

    # ---------------------------------------------------------- coverage --
    counts = frame.condition.value_counts()
    if args.expect == spec.N_TOTAL:
        want = {c: spec.N_CONTROL if c == "control" else spec.N_PER_INTERVENTION
                for c in spec.CONDITIONS}
        bad = [f"{c!r}: {counts.get(c, 0)}, expected {n}"
               for c, n in want.items() if counts.get(c, 0) != n]
        unknown = sorted(set(counts.index) - set(spec.CONDITIONS))
        if unknown:
            bad += [f"unknown condition {c!r}" for c in unknown]
        if bad:
            fail("condition coverage is wrong", bad)

    # ------------------------------------------------------ level strings --
    for col, allowed in spec.MODERATORS.items():
        if col not in frame.columns:
            continue
        seen = set(frame[col].dropna().unique()) - set(allowed)
        if seen:
            fail(f"unknown level(s) in {col!r}", sorted(seen))

    # ------------------------------------------------------------ ranges --
    out_of_range = []
    for i in items:
        col = pd.to_numeric(frame[i], errors="coerce")
        if i == spec.DONATION_ITEM:
            lo, hi = 0, 10
        elif i == spec.NEWSLETTER_ITEM:
            lo, hi = 0, 1
        else:
            lo, hi = 0, 100
        bad = col[(col < lo) | (col > hi)]
        if len(bad):
            out_of_range.append(f"{i}: {len(bad)} value(s) outside {lo}-{hi}")
    if out_of_range:
        fail("value(s) outside the scale", out_of_range)

    # `donation` is whole dollars and `newsletter` is 0/1 at Tier 1.
    for i in (spec.DONATION_ITEM, spec.NEWSLETTER_ITEM):
        if i in frame.columns:
            frame[i] = pd.to_numeric(frame[i]).round().astype(int)

    cols = [c for c in spec.RAW_COLUMNS if c in frame.columns]
    missing_cols = [c for c in spec.RAW_COLUMNS if c not in frame.columns]
    if missing_cols and not args.items:
        fail("the export is missing required column(s)", missing_cols)

    dest = Path(args.out) if args.out else DEPOSIT / "tier1_raw_export.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame[cols].to_csv(dest, index=False)

    line = "=" * 74
    print("\n".join([
        line, "STAGE 4 — RAW EXPORT", line, "",
        f"respondents    {len(frame):,}",
        f"conditions     {frame.condition.nunique()}",
        f"items          {len([c for c in items if c in frame.columns])}",
        f"empty cells    0",
        f"columns        {len(cols)}", "",
        f"wrote {dest}", "",
        "Next, from the repository root:",
        "  make clean      # -> predictions/<team_id>_T1_<entry>_v1.csv",
        "  make check", "", line, ""]))


if __name__ == "__main__":
    main()
