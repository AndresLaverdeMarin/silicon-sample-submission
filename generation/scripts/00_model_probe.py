#!/usr/bin/env python3
"""Step 0 — prove the session runs Fable, before spending 612 subagent runs.

design.md section 3 records the trap this exists for: a session was assumed to
be Fable and was in fact Opus 5. Registration item B.1 wants the exact model
identifier and B.2 the call-date window, and a Class-A entry that names the
wrong model is a misregistration.

So the probe is a real gate, not a note. 03_prepare_wave.py refuses to write a
wave until a probe recorded here names Fable.

How to run it, inside the session that will do the generating:

  1. python3 generation/scripts/00_model_probe.py --prompt
     Prints a short question. Answer it yourself, as the session's own model —
     do not delegate it to a subagent and do not guess.
  2. python3 generation/scripts/00_model_probe.py --record "<the model id>" \
       --how "Claude Code session, /model shows ..."
  3. python3 generation/scripts/00_model_probe.py            # verify

If the answer is claude-opus-5, or anything that is not Fable, stop. Switch the
session model and probe again. Nothing else in the pipeline should run first.

Every probe is kept: generation/runs/model_probe/ is an append-only record, and
a failed probe stays in it. That is the honest version of the check.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.spec import REPO  # noqa: E402

PROBES = REPO / "generation" / "runs" / "model_probe"

QUESTION = """\
STEP 0 — MODEL IDENTITY PROBE

Answer from what this session is, not from what it was meant to be:

  1. What is your exact model identifier?
  2. Where does that come from — your own system prompt, or an assumption?
  3. Today's date, as this session sees it.

Then record it:

  python3 generation/scripts/00_model_probe.py \\
      --record "<exact model id>" \\
      --how "<where the identifier came from>"

The pipeline accepts an identifier containing "fable". Anything else — and
claude-opus-5 in particular — means this session cannot generate this entry.
"""


def load() -> list[dict]:
    if not PROBES.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(PROBES.glob("*.json"))]


def is_fable(model: str) -> bool:
    return "fable" in model.lower()


def verified() -> dict | None:
    """The most recent probe naming Fable, or None. Used as the generation gate."""
    for probe in reversed(load()):
        if is_fable(probe.get("model_id", "")):
            return probe
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", action="store_true", help="print the question")
    ap.add_argument("--record", metavar="MODEL_ID",
                    help="record the answer this session gave")
    ap.add_argument("--how", default="",
                    help="where the identifier came from (system prompt, /model, ...)")
    ap.add_argument("--note", default="", help="anything else worth keeping")
    a = ap.parse_args()

    if a.prompt:
        print(QUESTION)
        return 0

    if a.record:
        PROBES.mkdir(parents=True, exist_ok=True)
        now = dt.datetime.now()
        doc = {"recorded_at": now.isoformat(timespec="seconds"),
               "model_id": a.record.strip(),
               "source_of_identifier": a.how.strip(),
               "note": a.note.strip(),
               "is_fable": is_fable(a.record)}
        path = PROBES / f"probe_{now:%Y%m%dT%H%M%S}.json"
        path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"recorded -> {path.relative_to(REPO)}")
        if not doc["is_fable"]:
            print(f"\nSTOP. {a.record!r} is not Fable. design.md section 3, "
                  "step 0: this session must not generate the entry. Switch the "
                  "session model and probe again. The failed probe is kept.")
            return 1
        print(f"\nOK. {a.record!r} names Fable. Waves may be built now.")
        return 0

    probes = load()
    if not probes:
        print("no probe recorded yet — run with --prompt first")
        return 1
    for p in probes:
        mark = "[ok]  " if p["is_fable"] else "[FAIL]"
        print(f"{mark} {p['recorded_at']}  {p['model_id']!r}"
              f"{'  — ' + p['source_of_identifier'] if p['source_of_identifier'] else ''}")
    v = verified()
    print()
    if v:
        print(f"gate OPEN: {v['model_id']!r} recorded at {v['recorded_at']}")
        return 0
    print("gate CLOSED: no probe names Fable. 03_prepare_wave.py will refuse "
          "to write a wave.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
