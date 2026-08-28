#!/usr/bin/env python3
"""
Compare the control-condition SPREAD of two persona styles.

The Tier-1 distribution metrics — variance ratio, OVL, KS and Wasserstein-1 —
compare the shape of our control answers with the humans'. This module reports
the part of that we can see while the human data are sealed: how wide our own
answers are, and whether the two persona styles differ.

**It cannot say which is right.** Only the humans can, and they are sealed. It
says whether the choice moves the spread at all. If it does not, take the
template: no writer model, no gates, and one less model to declare.

Run it from the repository root, after `sim/run_spread_test.sh`:

    uv run sim/compare_spread.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def load(tag: str) -> pd.DataFrame:
    path = OUT / f"{tag}.jsonl"
    if not path.exists():
        raise SystemExit(f"missing {path}. Run sim/run_spread_test.sh first.")
    return pd.DataFrame([json.loads(l) for l in path.open()])


def main() -> None:
    arms = {"template": load("spread_template"), "prose": load("spread_prose")}
    rows = []
    for name, frame in arms.items():
        frame = frame.dropna(subset=["value"])
        for item, block in frame.groupby("item"):
            rows.append({"arm": name, "item": item, "n": len(block),
                         "mean": block.value.mean(), "sd": block.value.std()})
    wide = (pd.DataFrame(rows).pivot(index="item", columns="arm",
                                     values=["mean", "sd"]))
    sd = wide["sd"]
    sd["sd_ratio"] = (sd.prose / sd.template).round(3)
    mean = wide["mean"]

    print("=" * 74)
    print("CONTROL-CONDITION SPREAD — template against prose")
    print("=" * 74)
    print(f"\n{len(arms['template'])//44} respondents, 44 items, "
          f"one answer each.\n")
    print("PER ITEM — standard deviation of the 300 answers")
    print("-" * 74)
    print(sd.round(2).to_string())
    print("\nSUMMARY")
    print("-" * 74)
    print(f"  median SD, template   {sd.template.median():.2f}")
    print(f"  median SD, prose      {sd.prose.median():.2f}")
    print(f"  median SD ratio       {sd.sd_ratio.median():.3f}"
          f"   (prose / template; 1.0 = no difference)")
    print(f"  items where prose is wider  "
          f"{int((sd.sd_ratio > 1).sum())} of {len(sd)}")
    print(f"\n  mean absolute difference in the item MEANS: "
          f"{np.abs(mean.prose - mean.template).mean():.2f} points")
    print("\n  A ratio near 1.0 says the persona style does not move the")
    print("  spread. Then take the template: no writer model, no gates, and")
    print("  one less model to declare under B.1 and B.2.")
    print("=" * 74)


if __name__ == "__main__":
    main()
