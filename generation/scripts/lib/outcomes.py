"""The 13 scored outcomes, computed from predicted items.

One implementation, used by both 05_aggregate.py and 06_diagnostics.py. Two
copies of this arithmetic would be two chances for the aggregated file and the
diagnostics to disagree about what a composite is.

The rules mirror codebook.csv exactly:
  copy           the outcome is the item
  mean           arithmetic mean of the items
  mean_of_means  mean of the four 3-item trust subscale means
  reverse100     100 - item          (funding_perceptions)
  pct_to_prop    item / 100          (newsletter_signup, a Tier-2 proportion)
"""
from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def outcome_value(spec: dict, vals: dict[str, float]) -> float:
    """One outcome from one draw's item values. `spec` is materials.outcomes[o]."""
    items, rule = spec["items"], spec["rule"]
    if rule == "copy":
        return vals[items[0]]
    if rule == "reverse100":
        return 100.0 - vals[items[0]]
    if rule == "pct_to_prop":
        return vals[items[0]] / 100.0
    if rule == "mean":
        return statistics.fmean(vals[i] for i in items)
    if rule == "mean_of_means":
        return statistics.fmean(statistics.fmean(vals[i] for i in sub)
                                for sub in spec["groups"])
    sys.exit(f"outcomes.py: unknown composite rule {rule!r}")


def read_items(draws_csv: Path, keep_draws: set[str] | None = None
               ) -> dict[tuple[str, str, str], dict[str, float]]:
    """draws.csv -> {(group, condition, draw): {item: value}}."""
    per: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
    with draws_csv.open(newline="") as fh:
        for r in csv.DictReader(fh):
            if keep_draws and r["draw"] not in keep_draws:
                continue
            k = (r["group_key"], r["condition"], r["draw"])
            if r["item"] in per[k]:
                sys.exit(f"outcomes.py: duplicate value for {k} item "
                         f"{r['item']} — two answers cover the same cell")
            per[k][r["item"]] = float(r["value"])
    return per


def cell_values(per_items, materials: dict, outcomes: list[str]
                ) -> dict[tuple[str, str, str], dict[str, float]]:
    """{(group, condition, outcome): {draw: value}}, composites applied per draw.

    A draw that has not answered every item of an outcome yet simply does not
    appear for that outcome, rather than contributing a partial composite.
    """
    out: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
    for (group, cond, draw), vals in per_items.items():
        for outcome in outcomes:
            spec = materials["outcomes"][outcome]
            if all(i in vals for i in spec["items"]):
                out[(group, cond, outcome)][draw] = outcome_value(spec, vals)
    return out
