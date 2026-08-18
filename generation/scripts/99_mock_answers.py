#!/usr/bin/env python3
"""Dry run — fill every task with deterministic fake numbers.

This is NOT a prediction and never becomes one. It exists to prove the pipeline
end to end before any model time is spent: that 612 task files reassemble into
exactly 221 and 5,967 rows, that the composites and the reconciliation work,
and that `make check` passes on the result.

Every file it writes carries `model_id: "MOCK-dry-run-not-a-model"`, which
04_collect.py rejects unless you pass `--allow-model MOCK`, and which
05_aggregate.py refuses to turn into predictions/ files. So a dry run cannot be
mistaken for the entry.

Usage:
  python3 generation/scripts/99_mock_answers.py            # fill missing answers
  python3 generation/scripts/99_mock_answers.py --clean    # delete mock answers
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.spec import REPO  # noqa: E402

RUNS = REPO / "generation" / "runs"
TASKS = RUNS / "tasks"
RAW = RUNS / "raw"
MODEL_ID = "MOCK-dry-run-not-a-model"


def unit(*parts: str) -> float:
    """A stable pseudo-random number in [0, 1) from the given key parts."""
    h = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def cell(item: str, group: str, condition: str, draw: str,
         lo: float, hi: float) -> float:
    """A plausible cell mean, stable across the tasks that ask for it."""
    span = hi - lo
    base = lo + span * (0.35 + 0.35 * unit("base", item))
    group_off = span * 0.10 * (unit("group", group, item) - 0.5)
    effect = 0.0 if condition == "control" else \
        span * 0.05 * (unit("eff", condition, item) - 0.45)
    jitter = span * 0.01 * (unit("jit", draw, item, group, condition) - 0.5)
    return min(max(base + group_off + effect + jitter, lo), hi)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true",
                    help="delete every mock answer file and stop")
    a = ap.parse_args()

    if a.clean:
        n = 0
        for p in sorted(RAW.glob("*.json")):
            doc = json.loads(p.read_text())
            if doc.get("model_id") == MODEL_ID:
                p.unlink()
                n += 1
        print(f"removed {n} mock answer file(s) from {RAW.relative_to(REPO)}")
        return 0

    specs = sorted(TASKS.glob("*.spec.json"))
    if not specs:
        sys.exit("99: no task specs — run 03_prepare_wave.py first")
    RAW.mkdir(parents=True, exist_ok=True)

    written = 0
    for sp in specs:
        spec = json.loads(sp.read_text())
        out = RAW / f"{spec['task_id']}.json"
        if out.exists():
            continue
        gcodes = spec["group_codes"]
        doc = {"task_id": spec["task_id"], "model_id": MODEL_ID,
               "read_check": spec["read_check"]}
        if spec["framing"] == "F3":
            doc["control"], doc["shifts"] = {}, {}
            for gc, gkey in gcodes.items():
                doc["control"][gc] = {}
                doc["shifts"][gc] = {}
                for item in spec["items"]:
                    lo, hi = spec["ranges"][item]
                    base = cell(item, gkey, "control", spec["draw"], lo, hi)
                    doc["control"][gc][item] = round(base, 2)
                    doc["shifts"][gc][item] = {
                        c: round(cell(item, gkey, spec["condition_codes"][c],
                                      spec["draw"], lo, hi) - base, 2)
                        for c in spec["condition_codes"] if c != "C00"}
        else:
            doc["values"] = {}
            for gc, gkey in gcodes.items():
                doc["values"][gc] = {}
                for item in spec["items"]:
                    lo, hi = spec["ranges"][item]
                    doc["values"][gc][item] = {
                        c: round(cell(item, gkey, lbl, spec["draw"], lo, hi), 2)
                        for c, lbl in spec["condition_codes"].items()}
        out.write_text(json.dumps(doc, indent=1) + "\n")
        written += 1

    print(f"wrote {written} mock answer file(s) "
          f"({len(specs) - written} already present)")
    print(f"-> {RAW.relative_to(REPO)}/")
    print("\nThese are NOT predictions. Collect them with "
          "`04_collect.py --allow-model MOCK` and aggregate with "
          "`--out-dir <somewhere outside predictions/>`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
