#!/usr/bin/env python3
"""List the tasks that still need an answer, as ready-to-use subagent prompts.

A task is pending when generation/runs/raw/<task_id>.json does not exist. Give
one line to one subagent. Nothing here writes anything, so it is safe to run at
any point in a wave to see what is left.

Usage:
  python3 generation/scripts/07_next_tasks.py --limit 12
  python3 generation/scripts/07_next_tasks.py --count
  python3 generation/scripts/07_next_tasks.py --limit 12 --only-draw F1r1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.spec import REPO  # noqa: E402

RUNS = REPO / "generation" / "runs"
TASKS = RUNS / "tasks"
RAW = RUNS / "raw"

LINE = ("Read {prefix} in full, then read {prompt} and do exactly what it says. "
        "Write the JSON file it asks for. Reply with only the number of values "
        "you wrote.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--count", action="store_true", help="print counts only")
    ap.add_argument("--only-draw", action="append")
    a = ap.parse_args()

    specs = sorted(TASKS.glob("*.spec.json"))
    if not specs:
        sys.exit("07: no tasks — run 03_prepare_wave.py first")

    pending, done = [], 0
    for sp in specs:
        spec = json.loads(sp.read_text())
        if a.only_draw and spec["draw"] not in a.only_draw:
            continue
        if (RAW / f"{spec['task_id']}.json").exists():
            done += 1
        else:
            pending.append(spec)

    print(f"# {done} answered, {len(pending)} pending, "
          f"{done + len(pending)} total", file=sys.stderr)
    if a.count:
        by_draw: dict[str, int] = {}
        for s in pending:
            by_draw[s["draw"]] = by_draw.get(s["draw"], 0) + 1
        for d in sorted(by_draw):
            print(f"  {d}: {by_draw[d]} pending", file=sys.stderr)
        return 0

    for spec in pending[:a.limit]:
        print(LINE.format(prefix=spec["prefix"],
                          prompt=f"generation/runs/tasks/{spec['task_id']}.md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
