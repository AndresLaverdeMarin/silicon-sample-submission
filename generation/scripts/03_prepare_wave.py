#!/usr/bin/env python3
"""Step 3 — build the prediction tasks, and select a wave of them to run.

What a task is
--------------
design.md section 4: batch by OUTCOME, not by condition. One task shows all 17
condition texts at once and asks for one table, so the model puts the 17 texts
on a single scale inside one answer. That comparison is what the benchmark
scores; 17 separate calls would make the ranking between them noise.

A task therefore covers:
  * all 17 conditions                      (never split — this is the point)
  * one outcome
  * one group set: the whole sample (main file) or all levels of one moderator
  * as many of that outcome's items as fit under --max-cells

6 of the 13 outcomes are composites, and we predict their items and compute the
composite in code (design.md section 4). Splitting a long item list across
several tasks is what keeps every task a table a model can hold in one answer,
while conditions and moderator levels — the two comparisons that matter — stay
inside one call.

Draws
-----
design.md section 5: 3 framings x 2 repeats = 6 draws per cell.
  F1  plain — no population description
  F2  with the persona summary of the cell
  F3  two stages — the control level first, then the shift from control
The framings also differ in the order the 17 texts are presented, so a position
effect cannot lock in the ranking. The two repeats of a framing are the *same
prompt run twice*; that is what makes them repeats.

Waves
-----
Task files are deterministic, so they live in one flat runs/tasks/ folder and
are written once. A wave is a *selection* of tasks that still need a model
answer: a task is done when runs/raw/<task_id>.json exists. Rerunning this
script after some answers have landed selects only what is left, so successive
waves walk the work to completion without duplication.

Usage:
  python3 generation/scripts/03_prepare_wave.py --plan          # counts only
  python3 generation/scripts/03_prepare_wave.py --wave 1 --limit 40
  python3 generation/scripts/03_prepare_wave.py --wave 2        # all remaining
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.spec import REPO, condition_codes, level_codes, load_spec  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
_probe = __import__("00_model_probe")

BUILD = REPO / "generation" / "build"
RUNS = REPO / "generation" / "runs"
TASKS = RUNS / "tasks"
RAW = RUNS / "raw"
WAVES = RUNS / "waves"

FRAMINGS = ["F1", "F2", "F3"]
REPEATS = 2
MAX_CELLS = 520          # numbers one task may ask for; see --max-cells
MAIN_GROUP = "all"

# ------------------------------------------------------------- framings ------
FRAMING_DOC = {
    "F1": ("plain",
           "Predict each condition's group mean directly. No description of the "
           "group beyond its label."),
    "F2": ("persona-summary",
           "Same request as F1, plus the computed demographic profile of the "
           "group being predicted."),
    "F3": ("two-stage",
           "Same context as F2, but answer in two stages: first the control "
           "mean, then each intervention's shift from control. The submitted "
           "level is control + shift, computed in code."),
}


def condition_order(framing: str, sst: dict) -> list[str]:
    """Presentation order of the 17 texts. Varies by framing, never by repeat."""
    codes = list(condition_codes(sst))
    if framing == "F1":
        return codes                                    # spec order
    if framing == "F2":
        return codes[:1] + codes[1:][::-1]              # control first, rest reversed
    shuffled = codes[1:]                                # F3: deterministic shuffle
    random.Random(f"order-{framing}").shuffle(shuffled)
    return codes[:1] + shuffled


# ------------------------------------------------------- task enumeration ----
def enumerate_tasks(sst: dict, materials: dict, cells: dict,
                    max_cells: int) -> list[dict]:
    conds = condition_codes(sst)
    tasks = []
    for framing in FRAMINGS:
        for rep in range(1, REPEATS + 1):
            draw = f"{framing}r{rep}"
            for outcome in sst["outcomes"]:
                items = materials["outcomes"][outcome]["items"]
                group_sets = [(None, [MAIN_GROUP])] + [
                    (mod, [f"{mod}::{lv}" for lv in levels])
                    for mod, levels in sst["moderators"].items()]
                for mod, groups in group_sets:
                    per_item = len(conds) * len(groups)
                    size = max(1, max_cells // per_item)
                    chunks = [items[i:i + size] for i in range(0, len(items), size)]
                    for ci, chunk in enumerate(chunks, 1):
                        tasks.append({
                            "task_id": f"{draw}__{outcome}__{mod or 'main'}__c{ci:02d}",
                            "draw": draw, "framing": framing, "repeat": rep,
                            "outcome": outcome, "moderator": mod,
                            "groups": groups, "items": chunk,
                            "n_chunks": len(chunks), "chunk": ci,
                            "n_values": per_item * len(chunk),
                            # Which text the answer must quote back, spread
                            # across the 16 interventions so no single text is
                            # the only one ever checked. C00 is excluded: its
                            # "text" is the three fillers joined, so its first
                            # words are a separator line, not prose.
                            "check_code": f"C{1 + len(tasks) % (len(conds) - 1):02d}",
                        })
    return tasks


# ----------------------------------------------------------- prompt text -----
HEADER = """\
# BLIND PREDICTION TASK — {task_id}

## READ THIS FILE FIRST

  {prefix}

It holds the 17 condition texts, which are the experimental manipulation. You cannot predict this table without them. When you have read it, you will be asked below to quote four words back as proof.

You are producing one table of numbers for a preregistered behavioural megastudy on trust in climate scientists. The human data do not exist yet, or are sealed: nobody involved has seen any outcome from this study. Your table is a forecast of what the human respondents will do.

Predict what the humans WILL DO, not what the experimenters hope for, and not what would make a tidy result.

Do not search for, or use, any result from this study or its pilots. Reason from the texts, the items and the population described below. Every cell needs a number: where you are unsure, give your best estimate rather than a placeholder.
"""

STUDY = """\
## THE STUDY

{flow}

Each of the 17 conditions is a separate randomised arm of {n_total:,} US adults ({n_per:,} per intervention, {n_control:,} in control). Every number you give is a GROUP MEAN over hundreds of people, so:

* Use decimals. A mean of several hundred integer answers is not a round number.
* Group means move much less than individuals do. One text read once shifts a group mean on a 0-100 scale by a few points at most, and some texts shift it not at all.
* Do not flatten either. Rank the 17 texts by how much they should move THIS group on THIS item, and let a genuinely stronger text show a larger difference. A table of 17 near-identical numbers is as wrong as a table of 20-point swings.
* A text may move the mean the wrong way. If a text should reduce trust in this group, say so with a lower number than control.
* `control` is the untreated baseline: those respondents read a neutral, off-topic filler text, so their answers reflect the population, not the topic.
"""

POPULATION = """\
## THE POPULATION

Whole sample:
{all_summary}
"""

GROUP_SECTION = """\
## THE GROUP{plural} YOU ARE PREDICTING

{groups}
"""

CONDITIONS_HEAD = """\
## THE 17 CONDITIONS

Refer to a condition by its CODE. Never type the title — the codes are how your answer is read back, and a mistyped title is a failed submission.

{table}

The full text of each one is in {prefix}, under the same codes and in the same order.
"""

PREFIX_HEAD = """\
# THE 17 CONDITION TEXTS — {framing}

Every respondent in this study read exactly ONE of the texts below, once, immediately before answering the outcome items. They are the experimental manipulation.

This file is the fixed part of every {framing} prediction task. The task file names the group, the items and the output path.

{table}
"""

ITEMS_HEAD = """\
## THE ITEM{plural} IN THIS TASK

{which} the scored outcome `{outcome}`. Predict each one separately: they are
asked as separate survey questions.

{table}
"""

HOWTO_LEVELS = """\
## HOW TO ANSWER

For every group, every item and all 17 conditions, give the group's mean.

Work condition by condition inside one item, so the 17 numbers stay on one scale. Then move to the next item.
"""

HOWTO_SHIFTS = """\
## HOW TO ANSWER — TWO STAGES

Stage 1. For every group and item, give the CONTROL mean: what this group answers with no climate-related text at all.

Stage 2. For every group and item, give each intervention's SHIFT from that control mean, as a signed number. `+2.4` means the intervention raises the mean by 2.4 points; `-1.1` means it lowers it; `0` means it does nothing.

Commit to the effects, not to the levels. The submitted level is control + shift, computed in code, so a shift you would not defend is a level you did not mean.
"""

OUTPUT = """\
## OUTPUT

Write one JSON object of exactly this shape, and nothing else, to:

  {out_path}

Use the Write tool. No prose in the file, no markdown fence, no comments. The file must parse as JSON. `...` below marks entries left out of this example — your file lists every one of them.

```json
{schema}
```

Rules for the file:

* `model_id` — the exact model identifier you are running as. This is recorded as the entry's provenance, so state your own model, not the one you assume.
* `read_check` — the first four words of the {check_code} text, copied exactly from the file you were told to read first. This is checked against the text; a wrong or missing value means the answer is discarded and the task re-run.
* Every group code, every item name and every condition code listed above must appear exactly once. No extra keys, no missing keys, no nulls, no strings for numbers.
* {range_note}

When the file is written, reply with only the number of values it holds ({n_values}).
"""


def wrap(s: str, width: int = 78) -> str:
    """Fill prose paragraphs; keep bullets hanging-indented and blocks verbatim."""
    out = []
    for line in s.split("\n"):
        if not line.strip() or line.startswith("  "):
            out.append(line)
        elif line.startswith(("* ", "- ")):
            out.append(textwrap.fill(line, width, subsequent_indent="  "))
        else:
            out.append(textwrap.fill(line, width))
    return "\n".join(out)


def json_schema(task: dict, sst: dict, materials: dict) -> str:
    """A short literal example of the wanted file — 2 groups, 2 items, 3 codes.

    The example numbers follow the item's own scale: a 62.5 next to a 0-10
    donation item would anchor the answer on the wrong range.
    """
    gs = list(group_codes(task, sst))[:2]
    its = task["items"][:2]
    order = condition_order(task["framing"], sst)
    kind = materials["items"][its[0]]["kind"]
    level = {"dollars": "2.50", "percent": "12.5"}.get(kind, "62.5")
    shift = {"dollars": "0.15", "percent": "1.8"}.get(kind, "1.4")

    def rowset(keys, val):
        return ", ".join(f'"{k}": {val}' for k in keys)

    lines = [f'  "task_id": "{task["task_id"]}",',
             '  "model_id": "<your exact model id>",',
             f'  "read_check": "<first four words of {task["check_code"]}>",']
    if task["framing"] == "F3":
        lines.append('  "control": {')
        lines += [f'    "{g}": {{' + rowset(its, level) + "}," for g in gs]
        lines += ["    ...", "  },", '  "shifts": {']
        for g in gs:
            inner = ", ".join(f'"{i}": {{' + rowset(order[1:4], shift) + ", ...}"
                              for i in its)
            lines.append(f'    "{g}": {{{inner}}},')
        lines += ["    ...", "  }"]
    else:
        lines.append('  "values": {')
        for g in gs:
            inner = ", ".join(f'"{i}": {{' + rowset(order[:3], level) + ", ...}"
                              for i in its)
            lines.append(f'    "{g}": {{{inner}}},')
        lines += ["    ...", "  }"]
    return "{\n" + "\n".join(lines) + "\n}"


def group_codes(task: dict, sst: dict) -> dict[str, str]:
    """Codes the model uses for the group(s) in this task."""
    if task["moderator"] is None:
        return {"G0": MAIN_GROUP}
    return {c: f"{task['moderator']}::{lv}"
            for c, lv in level_codes(sst, task["moderator"]).items()}


def render_task(task: dict, sst: dict, materials: dict, cells: dict) -> str:
    gcodes = group_codes(task, sst)
    conds = condition_codes(sst)
    order = condition_order(task["framing"], sst)
    n_items_out = materials["outcomes"][task["outcome"]]["n_items"]

    prefix = f"generation/runs/prefix_{task['framing']}.md"
    parts = [wrap(HEADER.format(task_id=task["task_id"], prefix=prefix))]

    parts.append(wrap(STUDY.format(
        flow="\n".join(f"* {n}" for n in materials["flow_notes"]),
        n_total=18000, n_per=1000, n_control=2000)))

    # F1 is the plain framing: it gets no population description at all.
    if task["framing"] != "F1":
        parts.append(POPULATION.format(all_summary=wrap(cells["groups"]["all"]["summary"])))

    if task["moderator"] is None:
        gtext = ("The whole sample, code `G0`. One mean per item and condition, "
                 "over all 17 arms.")
    else:
        gtext = wrap(
            f"The study scores six moderators. This task covers "
            f"`{task['moderator']}`, all {len(gcodes)} levels. Predict each level "
            f"separately, and keep them comparable: the difference between levels "
            f"is the moderation the study is testing.") + "\n"
        for code, key in gcodes.items():
            g = cells["groups"][key]
            gtext += f"\n### {code} — {task['moderator']} = {g['level']}\n"
            if task["framing"] != "F1":       # F1 is plain: the label, nothing else
                gtext += wrap(g["summary"]) + "\n"
    parts.append(wrap(GROUP_SECTION.format(
        plural="" if len(gcodes) == 1 else "S", groups=gtext)))

    table = "\n".join(
        f"  {c}  {conds[c]}" + ("   (untreated baseline)" if c == "C00" else "")
        for c in order)
    parts.append(wrap(CONDITIONS_HEAD.format(table=table, prefix=prefix)))
    for note in materials["stimulus_notes"]:
        parts.append(wrap(f"* {note}"))
    parts.append("")

    itable = "\n".join(
        f"  {name}\n      {materials['items'][name]['question']}\n"
        f"      scale: {materials['items'][name]['scale']}\n"
        f"      give:  {materials['items'][name]['ask']}"
        for name in task["items"])
    n_here = len(task["items"])
    which = (f"The single item behind" if n_items_out == 1 else
             f"All {n_items_out} items behind" if n_here == n_items_out else
             f"{n_here} of the {n_items_out} items behind")
    parts.append(wrap(ITEMS_HEAD.format(
        plural="" if n_here == 1 else "S", which=which,
        outcome=task["outcome"], table=itable)))
    if task["n_chunks"] > 1:
        parts.append(wrap(
            f"(This is part {task['chunk']} of {task['n_chunks']} for this "
            f"outcome and group set. The other items are asked in their own "
            f"task; answer only the item(s) above.)\n"))

    parts.append(wrap(HOWTO_SHIFTS if task["framing"] == "F3" else HOWTO_LEVELS))

    kinds = {materials["items"][i]["kind"] for i in task["items"]}
    if kinds == {"dollars"}:
        rng = ("Values are dollars, 0 to 10, two decimals. This is a mean "
               "donation out of a real $10 bonus.")
    elif kinds == {"percent"}:
        rng = ("Values are percentages, 0 to 100, one decimal: the share of the "
               "group that signed up.")
    else:
        rng = "Values are 0 to 100, one decimal."
    if task["framing"] == "F3":
        rng += " Shifts are signed and control + shift must stay in range."
    parts.append(wrap(OUTPUT.format(
        out_path=f"generation/runs/raw/{task['task_id']}.json",
        schema=json_schema(task, sst, materials),
        check_code=task["check_code"],
        range_note=rng, n_values=task["n_values"])))

    return "\n".join(parts).rstrip() + "\n"


def first_words(text: str, n: int = 4) -> str:
    """The first n words of a stimulus, as the read-check expects them back."""
    return " ".join(text.split()[:n])


def write_prefixes(sst: dict, materials: dict) -> dict[str, str]:
    """One shared condition-text file per framing; the tasks point at it.

    The 17 texts are ~7,700 words. Repeating them inside all 612 task files
    would make the deposit 40 MB of the same material. They differ between
    framings only in presentation order, so three files cover every task, and
    the read_check in each answer proves the agent opened one.
    """
    conds = condition_codes(sst)
    paths = {}
    for framing in FRAMINGS:
        order = condition_order(framing, sst)
        table = "\n".join(
            f"  {c}  {conds[c]}" + ("   (untreated baseline)" if c == "C00" else "")
            for c in order)
        parts = [wrap(PREFIX_HEAD.format(framing=framing, table=table))]
        for note in materials["stimulus_notes"]:
            parts.append(wrap(f"* {note}"))
        parts.append("")
        for c in order:
            parts.append(f"### {c} — {conds[c]}\n\n"
                         f"{materials['stimuli'][conds[c]]}\n")
        path = RUNS / f"prefix_{framing}.md"
        path.write_text("\n".join(parts).rstrip() + "\n")
        paths[framing] = str(path.relative_to(REPO))
    return paths


# ------------------------------------------------------------------ main -----
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, help="wave number to select")
    ap.add_argument("--limit", type=int, help="most tasks to put in this wave")
    ap.add_argument("--plan", action="store_true", help="print counts and stop")
    ap.add_argument("--max-cells", type=int, default=MAX_CELLS,
                    help=f"most values one task may ask for (default {MAX_CELLS})")
    ap.add_argument("--only-draw", action="append",
                    help="restrict to these draws, e.g. --only-draw F1r1")
    ap.add_argument("--skip-probe", action="store_true",
                    help="build a wave without a Fable probe (dry runs only)")
    a = ap.parse_args()

    sst = load_spec()
    materials = json.loads((BUILD / "materials.json").read_text())
    cells = json.loads((BUILD / "cells.json").read_text())

    tasks = enumerate_tasks(sst, materials, cells, a.max_cells)
    if a.only_draw:
        tasks = [t for t in tasks if t["draw"] in a.only_draw]

    n_values = sum(t["n_values"] for t in tasks)
    per_draw = {}
    for t in tasks:
        per_draw.setdefault(t["draw"], []).append(t)
    print(f"{len(tasks)} tasks, {n_values:,} predicted values "
          f"({len(per_draw)} draws x {len(tasks) // max(1, len(per_draw))} tasks)")
    print(f"  cap {a.max_cells} values/task; largest task "
          f"{max(t['n_values'] for t in tasks)}")
    grid = (len(sst["conditions"]) * materials["n_items"]
            * (1 + sum(len(v) for v in sst["moderators"].values())))
    print(f"  grid per draw: 17 conditions x {materials['n_items']} items x 28 "
          f"groups = {grid:,} values")
    if a.plan:
        return 0
    if a.wave is None:
        sys.exit("03: pass --wave N to write a wave, or --plan for counts only")

    # design.md section 3, step 0: prove the session runs Fable before any
    # generation. The gate is here because this is the step that commits the
    # subagent runs.
    probe = _probe.verified()
    if probe:
        print(f"model probe: {probe['model_id']!r} "
              f"(recorded {probe['recorded_at']})")
    elif a.skip_probe:
        print("model probe: SKIPPED. These tasks must not be answered by a "
              "session that has not been probed — 04_collect.py will reject "
              "any answer that is not Fable.")
    else:
        sys.exit("03: no model probe names Fable. Run\n"
                 "      python3 generation/scripts/00_model_probe.py --prompt\n"
                 "    and record this session's own model id, or pass "
                 "--skip-probe for a dry run.")

    for d in (TASKS, RAW, WAVES):
        d.mkdir(parents=True, exist_ok=True)

    todo = [t for t in tasks if not (RAW / f"{t['task_id']}.json").exists()]
    done = len(tasks) - len(todo)
    print(f"\nalready answered: {done} task(s); still to do: {len(todo)}")
    wave = todo[:a.limit] if a.limit else todo
    if not wave:
        print("nothing left — every task has an answer in generation/runs/raw/")
        return 0

    prefixes = write_prefixes(sst, materials)
    index = []
    for t in wave:
        md = render_task(t, sst, materials, cells)
        (TASKS / f"{t['task_id']}.md").write_text(md)
        spec = dict(t)
        spec["group_codes"] = group_codes(t, sst)
        spec["condition_codes"] = condition_codes(sst)
        spec["condition_order"] = condition_order(t["framing"], sst)
        spec["ranges"] = {i: [materials["items"][i]["lo"],
                              materials["items"][i]["hi"]] for i in t["items"]}
        spec["prefix"] = prefixes[t["framing"]]
        spec["read_check"] = first_words(
            materials["stimuli"][spec["condition_codes"][t["check_code"]]])
        spec["prompt_sha256"] = hashlib.sha256(md.encode()).hexdigest()
        (TASKS / f"{t['task_id']}.spec.json").write_text(
            json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
        index.append({"task_id": t["task_id"],
                      "prefix": prefixes[t["framing"]],
                      "prompt": f"generation/runs/tasks/{t['task_id']}.md",
                      "output": f"generation/runs/raw/{t['task_id']}.json",
                      "n_values": t["n_values"],
                      "prompt_sha256": spec["prompt_sha256"]})

    wpath = WAVES / f"wave{a.wave:02d}.json"
    wpath.write_text(json.dumps(
        {"wave": a.wave, "max_cells": a.max_cells,
         "n_tasks": len(index), "n_values": sum(i["n_values"] for i in index),
         "framings": {f: {"name": FRAMING_DOC[f][0], "instruction": FRAMING_DOC[f][1]}
                      for f in FRAMINGS},
         "prefixes": prefixes,
         "instruction": (
             "Give each task to one subagent. It reads the `prefix` file (the 17 "
             "condition texts) and then the `prompt` file, and writes the JSON "
             "named inside the prompt to `output`. Run the subagents in the Fable "
             "session only: every answer records its own model_id and its "
             "read_check, and 04_collect.py rejects an answer that is not Fable "
             "or that did not read the texts."),
         "tasks": index}, indent=2) + "\n")

    print(f"wave {a.wave}: {len(index)} task(s), "
          f"{sum(i['n_values'] for i in index):,} values")
    print(f"-> {wpath.relative_to(REPO)}")
    print(f"-> {TASKS.relative_to(REPO)}/<task_id>.md   (the prompts; "
          "registration item C.1)")
    for path in prefixes.values():
        print(f"-> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
