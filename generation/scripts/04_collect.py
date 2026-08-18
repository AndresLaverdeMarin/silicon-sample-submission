#!/usr/bin/env python3
"""Step 4 — validate the model's answers and flatten them into one table.

Every file in generation/runs/raw/ is checked against its task spec before any
of it is used: the model that produced it, the exact set of group codes, item
names and condition codes, no nulls, and every value inside the item's range.
A file that fails is moved to generation/runs/rejected/ with the reason, which
leaves its task "not done", so the next wave asks for it again.

Two checks earn their place here:

* `model_id` must name Fable. design.md section 3 records the trap: a session
  was assumed to be Fable and was in fact Opus 5. Provenance is checked per
  answer, not once per session, and a Class-A entry that names the wrong model
  is a misregistration. Pass --allow-model to relax it (the dry run needs this).
* `read_check` must quote the condition text back. The 17 texts sit in one
  shared prefix file rather than inside all 612 prompts, so this is what proves
  a subagent actually opened it instead of predicting from the item names.
* Codes, not labels. The model answers in `C07` / `L3`, never in
  `"Measurement & modeling (1)"`, so a near-miss label cannot reach the
  submission. This step maps codes back to the exact spec strings.

Output
  generation/build/draws.csv   draw, framing, repeat, group_key, condition,
                               item, value, task_id

Usage:
  python3 generation/scripts/04_collect.py
  python3 generation/scripts/04_collect.py --allow-model MOCK   # dry run only
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.spec import REPO, load_spec  # noqa: E402

RUNS = REPO / "generation" / "runs"
TASKS = RUNS / "tasks"
RAW = RUNS / "raw"
REJECTED = RUNS / "rejected"
OUT = REPO / "generation" / "build" / "draws.csv"
PROV = REPO / "generation" / "build" / "draws_provenance.json"

# A shift larger than this is treated as a mistake rather than a prediction:
# single-message effects in this literature are a few points, and a 40-point
# shift on a 0-100 group mean would be an order of magnitude out.
MAX_SHIFT_FRACTION = 0.4


class Reject(Exception):
    """One answer file is unusable; the reason is reported and the task requeued."""


def _num(v, where: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise Reject(f"{where}: {v!r} is not a number")
    f = float(v)
    if f != f or f in (float("inf"), float("-inf")):
        raise Reject(f"{where}: {v!r} is not finite")
    return f


def _exact_keys(got, want, where: str) -> None:
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    if missing or extra:
        raise Reject(f"{where}: missing {missing or 'none'}, unexpected "
                     f"{extra or 'none'}")


def parse_answer(doc: dict, spec: dict, sst: dict,
                 allow_model: str | None) -> list[dict]:
    """Validate one answer file and return its rows in long format."""
    if doc.get("task_id") != spec["task_id"]:
        raise Reject(f"task_id is {doc.get('task_id')!r}, expected "
                     f"{spec['task_id']!r}")

    model = str(doc.get("model_id") or "").strip()
    if not model:
        raise Reject("model_id missing — every answer records its own model")
    ok_model = "fable" in model.lower() or (
        allow_model and allow_model.lower() in model.lower())
    if not ok_model:
        raise Reject(f"model_id {model!r} is not Fable. design.md section 3, "
                     "step 0: prove the session runs Fable before generating.")

    # The 17 condition texts live in one shared prefix file, so an agent could
    # in principle answer without opening it. The read_check is four words
    # quoted out of a named text: cheap to give if the file was read, and
    # impossible to guess if it was not.
    want = " ".join(str(spec["read_check"]).split()).lower()
    got = " ".join(str(doc.get("read_check") or "").split()).lower()
    if got != want:
        raise Reject(f"read_check is {doc.get('read_check')!r}, expected the "
                     f"first four words of {spec['check_code']} "
                     f"({spec['read_check']!r}) — the condition texts in "
                     f"{spec['prefix']} were not read")

    gcodes = spec["group_codes"]              # code -> group key
    items = spec["items"]
    ranges = spec["ranges"]
    ccodes = spec["condition_codes"]          # code -> condition label
    interventions = [c for c in ccodes if c != "C00"]

    rows: list[dict] = []

    def emit(gcode: str, item: str, ccode: str, value: float) -> None:
        lo, hi = ranges[item]
        if not (lo <= value <= hi):
            raise Reject(f"{gcode}/{item}/{ccode}: {value} outside [{lo}, {hi}]")
        rows.append({
            "draw": spec["draw"], "framing": spec["framing"],
            "repeat": spec["repeat"], "group_key": gcodes[gcode],
            "condition": ccodes[ccode], "item": item, "value": value,
            "task_id": spec["task_id"],
        })

    if spec["framing"] == "F3":
        _exact_keys(doc.get("control") or {}, gcodes, "control groups")
        _exact_keys(doc.get("shifts") or {}, gcodes, "shifts groups")
        for gcode in gcodes:
            ctrl = doc["control"][gcode]
            shifts = doc["shifts"][gcode]
            _exact_keys(ctrl, items, f"control[{gcode}] items")
            _exact_keys(shifts, items, f"shifts[{gcode}] items")
            for item in items:
                base = _num(ctrl[item], f"control[{gcode}][{item}]")
                emit(gcode, item, "C00", base)
                _exact_keys(shifts[item], interventions,
                            f"shifts[{gcode}][{item}] conditions")
                lo, hi = ranges[item]
                span = (hi - lo) * MAX_SHIFT_FRACTION
                for ccode in interventions:
                    d = _num(shifts[item][ccode],
                             f"shifts[{gcode}][{item}][{ccode}]")
                    if abs(d) > span:
                        raise Reject(f"shifts[{gcode}][{item}][{ccode}]: shift "
                                     f"{d:+} exceeds {span} on a [{lo}, {hi}] "
                                     "scale — a mistake, not a prediction")
                    emit(gcode, item, ccode, round(base + d, 6))
    else:
        _exact_keys(doc.get("values") or {}, gcodes, "values groups")
        for gcode in gcodes:
            per_group = doc["values"][gcode]
            _exact_keys(per_group, items, f"values[{gcode}] items")
            for item in items:
                _exact_keys(per_group[item], ccodes,
                            f"values[{gcode}][{item}] conditions")
                for ccode in ccodes:
                    emit(gcode, item, ccode,
                         _num(per_group[item][ccode],
                              f"values[{gcode}][{item}][{ccode}]"))

    if len(rows) != spec["n_values"]:
        raise Reject(f"produced {len(rows)} values, expected {spec['n_values']}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-model", help="also accept model ids containing this "
                                          "string (dry runs only)")
    ap.add_argument("--keep-rejected", action="store_true",
                    help="report rejects without moving them out of raw/")
    a = ap.parse_args()

    sst = load_spec()
    answers = sorted(RAW.glob("*.json"))
    if not answers:
        sys.exit(f"04: no answers in {RAW.relative_to(REPO)}. Run a wave first.")

    rows: list[dict] = []
    models: dict[str, int] = {}
    rejects: list[tuple[str, str]] = []
    for path in answers:
        tid = path.stem
        spec_path = TASKS / f"{tid}.spec.json"
        if not spec_path.exists():
            rejects.append((tid, "no task spec — not a task of this pipeline"))
            continue
        spec = json.loads(spec_path.read_text())
        try:
            doc = json.loads(path.read_text())
            if not isinstance(doc, dict):
                raise Reject("top level is not a JSON object")
            got = parse_answer(doc, spec, sst, a.allow_model)
        except json.JSONDecodeError as e:
            rejects.append((tid, f"not valid JSON: {e}"))
        except Reject as e:
            rejects.append((tid, str(e)))
        else:
            rows.extend(got)
            models[str(doc["model_id"]).strip()] = models.get(
                str(doc["model_id"]).strip(), 0) + 1

    if rejects and not a.keep_rejected:
        REJECTED.mkdir(parents=True, exist_ok=True)
        for tid, why in rejects:
            src = RAW / f"{tid}.json"
            if src.exists():
                n = len(list(REJECTED.glob(f"{tid}.*.json"))) + 1
                shutil.move(str(src), REJECTED / f"{tid}.{n}.json")
                (REJECTED / f"{tid}.{n}.reason.txt").write_text(why + "\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["draw", "framing", "repeat",
                                           "group_key", "condition", "item",
                                           "value", "task_id"])
        w.writeheader()
        w.writerows(rows)

    PROV.write_text(json.dumps({
        "n_answer_files": len(answers) - len(rejects),
        "n_rejected": len(rejects),
        "n_values": len(rows),
        "models": models,
        "note": ("model_id as each answer reported it. 05_aggregate.py refuses "
                 "to write predictions/ unless every one of these names Fable."),
        "rejected": [{"task_id": t, "reason": w} for t, w in rejects],
    }, indent=2) + "\n")

    print(f"accepted {len(answers) - len(rejects)} of {len(answers)} answer "
          f"file(s) -> {len(rows):,} values")
    for m, n in sorted(models.items(), key=lambda kv: -kv[1]):
        print(f"  model_id {m!r}: {n} file(s)")
    if rejects:
        print(f"\nrejected {len(rejects)} file(s) "
              f"(moved to {REJECTED.relative_to(REPO)}/, task requeued):")
        for tid, why in rejects[:20]:
            print(f"  {tid}\n      {why}")
        if len(rejects) > 20:
            print(f"  ... and {len(rejects) - 20} more")
    print(f"\n-> {OUT.relative_to(REPO)}"
          f"\n-> {PROV.relative_to(REPO)}")
    return 1 if rejects else 0


if __name__ == "__main__":
    raise SystemExit(main())
