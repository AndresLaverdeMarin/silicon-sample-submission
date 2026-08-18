#!/usr/bin/env python3
"""Step 6 — measure the draws, and decide whether to submit the ensemble.

design.md section 5 says to keep every draw and then check two things before
trusting their average:

1. Direction agreement. For each intervention cell, how many draws put it above
   control? 3 against 3 means the model has no signal in that cell.
2. Spread. The standard deviation across draws is the entry's own uncertainty,
   which registration item J.1 asks for.

It also warns that averaging helps the levels (Tier 2 scores levels) and can
hurt the effects: if framings disagree on direction, the mean shift moves toward
zero and a small real signal washes out. So this script also reports the
attenuation — the ensemble's mean |effect| against the mean of each framing's
own mean |effect|. That number, not a preference, decides between the ensemble
mean and a single framing.

Outputs
  generation/build/diagnostics_report.txt
  generation/build/registration_facts.md   numbers to paste into registration.md
  generation/build/draw_spread.csv         per-cell SD and direction agreement

Usage:
  python3 generation/scripts/06_diagnostics.py
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.outcomes import cell_values, read_items  # noqa: E402
from lib.spec import REPO, load_spec  # noqa: E402

BUILD = REPO / "generation" / "build"
RUNS = REPO / "generation" / "runs"
DRAWS = BUILD / "draws.csv"
REPORT = BUILD / "diagnostics_report.txt"
FACTS = BUILD / "registration_facts.md"
SPREAD = BUILD / "draw_spread.csv"
MAIN_GROUP = "all"

# Below this share of decided cells, design.md section 5 says the ensemble mean
# is not the thing to submit — a single framing is.
DECIDED_FLOOR = 0.60
# Below this ratio the averaging is cancelling effects rather than stabilising
# them (ensemble |effect| against the average framing's |effect|).
ATTENUATION_FLOOR = 0.50


def main() -> int:
    sst = load_spec()
    materials = json.loads((BUILD / "materials.json").read_text())
    if not DRAWS.exists():
        sys.exit("06: generation/build/draws.csv not found — run 04_collect.py")

    cellvals = cell_values(read_items(DRAWS), materials, sst["outcomes"])
    draws = sorted({d for b in cellvals.values() for d in b})
    framings = sorted({d[:2] for d in draws})

    lines = ["Silicon Sample Benchmark — Tier 2 draw diagnostics",
             "-" * 62,
             f"draws present: {', '.join(draws)}",
             f"cells with at least one draw: {len(cellvals):,}", ""]

    # ------------------------------------------------- direction agreement ----
    rows = []
    decided = split = 0
    per_outcome = defaultdict(lambda: [0, 0])
    for (group, cond, outcome), byd in cellvals.items():
        if cond == "control":
            continue
        ctrl = cellvals.get((group, "control", outcome), {})
        shared = [d for d in byd if d in ctrl]
        if not shared:
            continue
        up = sum(1 for d in shared if byd[d] > ctrl[d])
        down = sum(1 for d in shared if byd[d] < ctrl[d])
        n = len(shared)
        agree = max(up, down) / n
        is_decided = agree >= 0.75            # 6/6, 5/6 (or 4/4, 3/4)
        decided += is_decided
        split += (up == down)
        per_outcome[outcome][0] += is_decided
        per_outcome[outcome][1] += 1
        vals = [byd[d] for d in shared]
        rows.append({
            "group_key": group, "condition": cond, "outcome": outcome,
            "n_draws": n, "n_above_control": up, "n_below_control": down,
            "direction_agreement": round(agree, 3),
            "mean": round(statistics.fmean(vals), 4),
            "sd_across_draws": round(statistics.stdev(vals), 4) if n > 1 else 0.0,
            "effect_vs_control": round(statistics.fmean(vals)
                                       - statistics.fmean(ctrl[d] for d in shared), 4),
        })

    n_cells = len(rows)
    if not n_cells:
        sys.exit("06: no intervention cells to compare against control yet")
    share_decided = decided / n_cells
    lines += [
        "DIRECTION AGREEMENT  (do the draws agree on the sign of the effect?)",
        f"  intervention cells compared:     {n_cells:,}",
        f"  decided (>= 75 % of draws agree): {decided:,} ({share_decided:.1%})",
        f"  dead split (equal up and down):   {split:,} ({split / n_cells:.1%})",
        "",
        "  by outcome:",
    ]
    for outcome in sst["outcomes"]:
        d, t = per_outcome[outcome]
        if t:
            lines.append(f"    {outcome:<24} {d / t:>6.1%} decided  ({t:,} cells)")
    lines.append("")

    # ------------------------------------------------------------- spread ----
    sds = [r["sd_across_draws"] for r in rows if r["n_draws"] > 1]
    if sds:
        lines += ["SPREAD ACROSS DRAWS  (registration item J.1)",
                  f"  median SD: {statistics.median(sds):.3f}",
                  f"  mean SD:   {statistics.fmean(sds):.3f}",
                  f"  90th pct:  {sorted(sds)[int(0.9 * len(sds))]:.3f}",
                  f"  max SD:    {max(sds):.3f}", ""]

    # -------------------------------------------------------- attenuation ----
    # |effect| of the ensemble against the average framing's own |effect|.
    ens = statistics.fmean(abs(r["effect_vs_control"]) for r in rows)
    per_fr = {}
    for fr in framings:
        eff = []
        for (group, cond, outcome), byd in cellvals.items():
            if cond == "control":
                continue
            ctrl = cellvals.get((group, "control", outcome), {})
            ds = [d for d in byd if d.startswith(fr) and d in ctrl]
            if ds:
                eff.append(abs(statistics.fmean(byd[d] for d in ds)
                               - statistics.fmean(ctrl[d] for d in ds)))
        if eff:
            per_fr[fr] = statistics.fmean(eff)
    mean_fr = statistics.fmean(per_fr.values()) if per_fr else 0.0
    ratio = ens / mean_fr if mean_fr else 0.0
    lines += ["EFFECT SIZE AND ATTENUATION",
              f"  ensemble mean |effect|:        {ens:.3f}"]
    for fr, v in per_fr.items():
        lines.append(f"  framing {fr} mean |effect|:     {v:.3f}")
    lines += [f"  average framing |effect|:     {mean_fr:.3f}",
              f"  attenuation ratio:            {ratio:.3f}"
              "   (1.0 = averaging costs no signal)", ""]

    # ---------------------------------------------------------- the choice ----
    lines.append("DECISION (design.md section 5)")
    if share_decided < DECIDED_FLOOR:
        verdict = (f"Direction agreement is {share_decided:.1%}, below the "
                   f"{DECIDED_FLOOR:.0%} floor. The draws do not agree on the "
                   "sign in enough cells for their mean to be a prediction. "
                   "Submit the single best framing instead: "
                   "`05_aggregate.py --rule framing:F3`.")
    elif ratio < ATTENUATION_FLOOR:
        verdict = (f"Direction agreement is fine ({share_decided:.1%}) but "
                   f"averaging keeps only {ratio:.0%} of the per-framing effect "
                   "size. The levels are stabilised at the cost of the effects. "
                   "Prefer a single framing, or a median over the draws.")
    else:
        verdict = (f"Direction agreement {share_decided:.1%} and attenuation "
                   f"ratio {ratio:.2f} both clear the floors. Submit the "
                   "ensemble mean: `05_aggregate.py` with the default rule.")
    lines += ["  " + verdict,
              "  This is a measurement on our own draws only. The aggregation "
              "rule itself is chosen on voelkel2025 (design.md section 7), never "
              "on the target study.", ""]

    REPORT.write_text("\n".join(lines) + "\n")
    with SPREAD.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["group_key"], r["outcome"],
                                                r["condition"])))

    # --------------------------------------------- registration facts (K.3) ---
    answers = sorted((RUNS / "raw").glob("*.json"))
    tasks = sorted((RUNS / "tasks").glob("*.spec.json"))
    rejected = sorted((RUNS / "rejected").glob("*.json"))
    prov = json.loads((BUILD / "draws_provenance.json").read_text()) \
        if (BUILD / "draws_provenance.json").exists() else {"models": {}}
    if answers:
        stamps = [dt.datetime.fromtimestamp(p.stat().st_mtime) for p in answers]
        window = f"{min(stamps):%Y-%m-%d} to {max(stamps):%Y-%m-%d}"
    else:
        window = "no answers yet"

    facts = [
        "# Facts for registration.md",
        "",
        "Generated by `generation/scripts/06_diagnostics.py`. Paste these into "
        "the matching registration items; they are the run's own record.",
        "",
        f"* **B.1 model(s)** — as each answer reported itself: "
        f"{', '.join(f'`{m}` ({n} files)' for m, n in prov['models'].items()) or 'none yet'}",
        f"* **B.2 call-date window** — {window}",
        f"* **B.7 / F.1 draws** — {len(draws)} draws per cell: "
        f"{', '.join(draws)} ({len(framings)} framings x 2 repeats)",
        f"* **F.2 aggregation** — see the DECISION line in "
        f"`generation/build/diagnostics_report.txt`",
        f"* **G.2 post-processing** — {len(rejected)} answer file(s) rejected and "
        f"re-run; rejection reasons in `generation/runs/rejected/`",
        f"* **J.1 spread** — median SD across draws "
        f"{statistics.median(sds) if sds else 0:.3f}; direction agreement "
        f"{share_decided:.1%} of {n_cells:,} intervention cells",
        f"* **K.2 raw logs** — {len(answers)} answer file(s) in "
        f"`generation/runs/raw/`, {len(tasks)} prompt(s) in "
        f"`generation/runs/tasks/` with a SHA-256 per prompt in each "
        f"`.spec.json`",
        f"* **K.3 resources** — {len(tasks)} subagent run(s), "
        f"{sum(json.loads(t.read_text())['n_values'] for t in tasks):,} values "
        f"requested; Route B (a Claude Code session), so no metered API tokens",
    ]
    FACTS.write_text("\n".join(facts) + "\n")

    print("\n".join(lines))
    print(f"-> {REPORT.relative_to(REPO)}")
    print(f"-> {SPREAD.relative_to(REPO)}")
    print(f"-> {FACTS.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
