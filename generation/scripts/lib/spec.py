"""Canonical submission labels — read from R, never typed here.

`scripts/lib/submission_spec.R` is the benchmark's single source of truth for
every string the scorer joins on: the 17 condition titles, the 13 outcome
names, and the 27 moderator levels. A near miss is a hard FAIL, or it silently
drops a subgroup, so this module does not restate any of those strings. It
sources the R file with Rscript and caches the result as JSON.

    from lib.spec import load_spec
    sst = load_spec()
    sst["conditions"]          # 17 titles, control first
    sst["moderators"]["party"] # exact level strings

Run this file directly for a summary:
    python3 generation/scripts/lib/spec.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]          # repository root
SPEC_R = REPO / "scripts" / "lib" / "submission_spec.R"
CACHE = REPO / "generation" / "build" / "spec.json"

# Grid sizes the benchmark requires. Derived from the spec, asserted here so a
# silent change in either file is caught at load time rather than at `make check`.
N_CONDITIONS = 17
N_OUTCOMES = 13
N_MODERATOR_LEVELS = 27
TIER2_MAIN_ROWS = N_CONDITIONS * N_OUTCOMES                      # 221
TIER2_MOD_ROWS = N_CONDITIONS * N_MODERATOR_LEVELS * N_OUTCOMES   # 5,967


def _dump_from_r() -> dict:
    """Source submission_spec.R and return the `sst` list as a dict."""
    if not SPEC_R.exists():
        sys.exit(f"spec.py: {SPEC_R} not found — run from the repository root")
    r = (f'source("{SPEC_R}"); '
         'cat(jsonlite::toJSON(sst, auto_unbox = FALSE, digits = NA))')
    try:
        out = subprocess.run(["Rscript", "-e", r], capture_output=True,
                             text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("spec.py: Rscript not on PATH. submission_spec.R is the only "
                 "source of the label strings; install R (>= 4.2) with jsonlite.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"spec.py: Rscript failed sourcing the spec:\n{e.stderr}")
    return json.loads(out)


def _validate(sst: dict) -> dict:
    """Fail loudly if the spec no longer describes the grid we build for."""
    got = (len(sst["conditions"]), len(sst["outcomes"]),
           sum(len(v) for v in sst["moderators"].values()))
    want = (N_CONDITIONS, N_OUTCOMES, N_MODERATOR_LEVELS)
    if got != want:
        sys.exit("spec.py: submission_spec.R describes a different grid than "
                 f"this pipeline was built for: got {got} "
                 "(conditions, outcomes, moderator levels), expected "
                 f"{want}. Re-check the task builder before generating.")
    if sst["conditions"][0] != "control":
        sys.exit("spec.py: expected 'control' first in sst$conditions")
    return sst


def load_spec(refresh: bool = False) -> dict:
    """Return the spec, using generation/build/spec.json as a cache.

    The cache is refreshed whenever submission_spec.R is newer, so an upstream
    label change can never be served stale.
    """
    if not refresh and CACHE.exists() and CACHE.stat().st_mtime >= SPEC_R.stat().st_mtime:
        return _validate(json.loads(CACHE.read_text()))
    sst = _validate(_dump_from_r())
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(sst, indent=2, ensure_ascii=False) + "\n")
    return sst


# ---------------------------------------------------------------- codes ------
# The model never types a label. Every condition and every moderator level is
# addressed by a short ASCII code in the task file and in the JSON it writes;
# this module maps the code back to the exact string. That removes the
# byte-exactness hazard from the model's output entirely.

def condition_codes(sst: dict) -> dict[str, str]:
    """{'C00': 'control', 'C01': <intervention 1>, ...} in spec order."""
    return {f"C{i:02d}": c for i, c in enumerate(sst["conditions"])}


def level_codes(sst: dict, moderator: str) -> dict[str, str]:
    """{'L1': <level 1>, ...} for one moderator, in spec order."""
    return {f"L{i}": lv for i, lv in enumerate(sst["moderators"][moderator], 1)}


def outcome_hi(outcome: str) -> float:
    """Upper bound of a Tier-2 cell mean, per check_lib.R `.cell_value_warn`."""
    return 1.0 if outcome == "newsletter_signup" else 10.0 if outcome == "donation_ams" else 100.0


if __name__ == "__main__":
    s = load_spec(refresh="--refresh" in sys.argv)
    print(f"conditions ({len(s['conditions'])}): {s['conditions'][0]!r} + "
          f"{len(s['interventions'])} interventions")
    print(f"outcomes ({len(s['outcomes'])}): {', '.join(s['outcomes'])}")
    for m, lv in s["moderators"].items():
        print(f"  {m:<10} {len(lv)} levels: {' | '.join(lv)}")
    print(f"Tier-2 rows required: main {TIER2_MAIN_ROWS}, "
          f"moderator {TIER2_MOD_ROWS}")
    print(f"cached -> {CACHE.relative_to(REPO)}")
