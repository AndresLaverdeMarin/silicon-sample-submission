#!/usr/bin/env python3
"""Step 5 — turn the draws into the two Tier-2 prediction files.

Order of operations, and why it is this order
--------------------------------------------
1. Composites first, per draw. Each draw is a complete prediction, so its
   `trust_multidimensional` is computed from its own 12 items (design.md
   section 4). Averaging items across draws before compositing would work for a
   plain mean and quietly change the answer for a median.
2. Then ensemble across draws (design.md section 5). Default rule: the mean of
   the draws. `--rule` also offers median, a trimmed mean, or a single framing —
   design.md section 5 says to fall back to one framing if the draws disagree on
   direction, and 06_diagnostics.py is what measures that.
3. Then reconcile the moderator file to the main file (design.md section 6).
   For each condition, outcome and moderator, the level means weighted by the
   population shares must average back to the main mean. Where they do not, an
   ADDITIVE shift is applied to that block. design.md says "rescale"; a shift is
   the better form of it — it corrects the level while preserving every
   difference between levels, which is the moderation being predicted, and it
   cannot blow up near zero the way a multiplicative factor can.
4. Then clamp to the outcome's range and round to 3 decimals.

Usage:
  python3 generation/scripts/05_aggregate.py
  python3 generation/scripts/05_aggregate.py --rule median
  python3 generation/scripts/05_aggregate.py --rule framing:F3
  python3 generation/scripts/05_aggregate.py --out-dir /tmp/dryrun --allow-model MOCK
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.outcomes import cell_values, read_items  # noqa: E402
from lib.spec import (REPO, TIER2_MAIN_ROWS, TIER2_MOD_ROWS,  # noqa: E402
                      load_spec, outcome_hi)

BUILD = REPO / "generation" / "build"
DRAWS = BUILD / "draws.csv"
PROV = BUILD / "draws_provenance.json"
REPORT = BUILD / "aggregate_report.txt"
CELLS = BUILD / "cells.json"
MAIN_GROUP = "all"
ALL_DRAWS = ["F1r1", "F1r2", "F2r1", "F2r2", "F3r1", "F3r2"]


def ensemble(values: list[float], rule: str) -> float:
    if rule == "median":
        return statistics.median(values)
    if rule == "trimmed":
        v = sorted(values)
        return statistics.fmean(v[1:-1] if len(v) > 3 else v)
    return statistics.fmean(values)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", default="mean",
                    help="mean (default) | median | trimmed | framing:F1|F2|F3")
    ap.add_argument("--reconcile", default="additive",
                    choices=["additive", "multiplicative", "none"])
    ap.add_argument("--require-draws", type=int,
                    help="fewest draws every cell must have "
                         "(default: all draws the rule selects)")
    ap.add_argument("--out-dir", help="write here instead of predictions/")
    ap.add_argument("--version", type=int, default=1, help="file version, v<N>")
    ap.add_argument("--allow-model", help="permit non-Fable draws (dry runs only)")
    a = ap.parse_args()

    sst = load_spec()
    materials = json.loads((BUILD / "materials.json").read_text())
    cells = json.loads(CELLS.read_text())
    meta = json.loads((REPO / "metadata.json").read_text())

    if not DRAWS.exists():
        sys.exit("05: generation/build/draws.csv not found — run 04_collect.py")

    # ---- provenance gate -----------------------------------------------------
    prov = json.loads(PROV.read_text()) if PROV.exists() else {}
    bad = [m for m in prov.get("models", {}) if "fable" not in m.lower()]
    out_dir = Path(a.out_dir) if a.out_dir else REPO / "predictions"
    if bad and out_dir == REPO / "predictions" and not a.allow_model:
        sys.exit("05: these draws were not produced by Fable: "
                 f"{bad}. Refusing to write predictions/. Regenerate in a Fable "
                 "session, or pass --out-dir for a dry run.")

    # ---- read draws ----------------------------------------------------------
    keep = None
    if a.rule.startswith("framing:"):
        f = a.rule.split(":", 1)[1]
        keep = {d for d in ALL_DRAWS if d.startswith(f)}
        if not keep:
            sys.exit(f"05: --rule framing:{f} matches no draw")
    need = a.require_draws if a.require_draws else len(keep or ALL_DRAWS)

    per = read_items(DRAWS, keep)
    if not per:
        sys.exit("05: no draws selected")

    # ---- per-draw outcomes: composites are applied inside each draw ----------
    cellvals = cell_values(per, materials, sst["outcomes"])

    # ---- coverage ------------------------------------------------------------
    groups_needed = [MAIN_GROUP] + [g for g in cells["groups"] if g != MAIN_GROUP]
    missing, thin = [], []
    for group in groups_needed:
        for cond in sst["conditions"]:
            for outcome in sst["outcomes"]:
                got = cellvals.get((group, cond, outcome), {})
                if not got:
                    missing.append((group, cond, outcome))
                elif len(got) < need:
                    thin.append((group, cond, outcome, len(got)))
    if missing:
        print(f"05: {len(missing):,} of "
              f"{len(groups_needed) * 17 * 13:,} cells have no prediction yet. "
              "First few:", file=sys.stderr)
        for m in missing[:5]:
            print(f"    {m}", file=sys.stderr)
        sys.exit("05: incomplete — run more waves, then 04_collect.py again.")
    if thin:
        counts = sorted({t[3] for t in thin})
        print(f"05: WARNING {len(thin):,} cell(s) have fewer than "
              f"{need} draws (counts seen: {counts}). The ensemble is "
              "uneven across cells; run the missing tasks for a clean entry.")

    # ---- ensemble ------------------------------------------------------------
    final: dict[tuple[str, str, str], float] = {}
    for key, byd in cellvals.items():
        final[key] = ensemble(list(byd.values()), a.rule.split(":", 1)[0])

    # ---- reconcile the moderator file to the main file -----------------------
    lines = [f"aggregation rule: {a.rule}",
             f"reconciliation:  {a.reconcile}",
             f"draws used:      {sorted({d for b in cellvals.values() for d in b})}",
             ""]
    drift_before: list[float] = []
    drift_after: list[float] = []
    clamped = 0
    for mod, shares in cells["shares"].items():
        for cond in sst["conditions"]:
            for outcome in sst["outcomes"]:
                target = final[(MAIN_GROUP, cond, outcome)]
                keys = [(f"{mod}::{lv}", cond, outcome) for lv in shares]
                w = [shares[lv] for lv in shares]
                got = sum(wi * final[k] for wi, k in zip(w, keys))
                drift_before.append(got - target)
                if a.reconcile == "none":
                    continue
                if a.reconcile == "additive":
                    delta = target - got
                    for k in keys:
                        final[k] = final[k] + delta
                else:
                    if got == 0:
                        continue
                    for k in keys:
                        final[k] = final[k] * (target / got)
                hi = outcome_hi(outcome)
                for k in keys:
                    v = min(max(final[k], 0.0), hi)
                    if v != final[k]:
                        clamped += 1
                        final[k] = v
                drift_after.append(
                    sum(wi * final[k] for wi, k in zip(w, keys)) - target)

    def dstat(d: list[float], label: str) -> str:
        if not d:
            return f"{label}: n/a"
        return (f"{label}: max |drift| {max(abs(x) for x in d):.4f}, "
                f"mean |drift| {statistics.fmean(abs(x) for x in d):.4f} "
                f"over {len(d):,} blocks")

    lines.append(dstat(drift_before, "moderator vs main, before"))
    lines.append(dstat(drift_after, "moderator vs main, after "))
    if clamped:
        lines.append(f"clamped to range after reconciliation: {clamped} cell(s) "
                     "(these blocks no longer average back exactly)")
    lines.append("")

    # ---- write ---------------------------------------------------------------
    team, entry = meta["team_id"], meta["entry"]
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{team}_T2_{entry}_v{a.version}"
    main_path = out_dir / f"{stem}_cells_main.csv"
    mod_path = out_dir / f"{stem}_cells_moderator.csv"

    def fmt(outcome: str, v: float) -> str:
        return f"{min(max(v, 0.0), outcome_hi(outcome)):.3f}"

    with main_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(sst["tier2_main_cols"])
        n = 0
        for cond in sst["conditions"]:
            for outcome in sst["outcomes"]:
                w.writerow([cond, outcome,
                            fmt(outcome, final[(MAIN_GROUP, cond, outcome)])])
                n += 1
    if n != TIER2_MAIN_ROWS:
        sys.exit(f"05: wrote {n} main rows, expected {TIER2_MAIN_ROWS}")

    with mod_path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(sst["tier2_mod_cols"])
        n = 0
        for cond in sst["conditions"]:
            for mod, levels in sst["moderators"].items():
                for lv in levels:
                    for outcome in sst["outcomes"]:
                        w.writerow([cond, mod, lv, outcome,
                                    fmt(outcome, final[(f"{mod}::{lv}", cond,
                                                        outcome)])])
                        n += 1
    if n != TIER2_MOD_ROWS:
        sys.exit(f"05: wrote {n} moderator rows, expected {TIER2_MOD_ROWS}")

    lines += [f"{main_path.name}: {TIER2_MAIN_ROWS} rows "
              f"(17 conditions x 13 outcomes)",
              f"{mod_path.name}: {TIER2_MOD_ROWS} rows "
              f"(17 x 27 moderator levels x 13)"]
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n-> {main_path}\n-> {mod_path}\n-> {REPORT.relative_to(REPO)}")
    if out_dir == REPO / "predictions":
        print("\nnext: make manifest && make check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
