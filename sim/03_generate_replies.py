#!/usr/bin/env python3
"""
Stage 3 — each respondent reads their condition and answers all 44 items.

One prompt asks ONE item and the model completes one number. That is the
paper's own format, and it is the format that runs fast: the answer is about
three tokens, and the 44 prompts of one respondent share a long prefix, so
vLLM computes the condition text and the persona one time.

**One answer per person per item.** No replicate is drawn and nothing is
averaged. The variation between respondents IS the Tier-1 deliverable: the
control-condition distribution metrics (variance ratio, OVL, KS, Wasserstein-1)
are Tier 1 only, and they measure exactly that spread. Averaging would narrow
it.

`--persona-style` chooses how the person is written:

    prose      the stage-2 text, written by a model
    template   a fixed sentence built in code, no model involved

The two are worth measuring against each other before the full run. A template
is deterministic, so respondents with the same attributes read the same words;
71.6 per cent of our 9,000 share a full attribute vector.

What it writes:

    sim/out/03_replies.jsonl       one record for each (respondent, item)
    sim/out/03_report.txt          parse rate, rate, wall clock

Run it from the repository root, in a vLLM environment:

    uv run --extra generate sim/03_generate_replies.py
    uv run --extra generate sim/03_generate_replies.py \\
        --conditions control --limit 300 --persona-style template \\
        --tag spread_template
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import answer_prompt as ap                             # noqa: E402
from lib import spec                                            # noqa: E402

OUT = HERE / "out"
MODEL = "Qwen/Qwen3.8-27B"
SEED = 20260828
TEMPERATURE = 1.0          # the spread between respondents is the deliverable
MAX_TOKENS = 8


def stimulus_for(row, materials: dict) -> str:
    """The text this respondent reads. Control reads one of three fillers."""
    if row.condition == "control":
        return materials["conditions"]["control"]["fillers"][row.control_filler]
    return materials["conditions"][row.condition]["text"]


def build(personas: pd.DataFrame, prose: dict[str, str], materials: dict,
          style: str, items: list[str]) -> pd.DataFrame:
    """One row for each (respondent, item)."""
    scales = {i: ap.scale_of(i, materials["items"][i]["options"])
              for i in items}
    rows = []
    for row in personas.itertuples():
        if style == "template":
            persona = ap.template_persona(row)
        else:
            persona = prose.get(row.profile_id)
            if persona is None:
                raise SystemExit(
                    f"no stage-2 text for {row.profile_id}. Run stage 2, or "
                    f"use --persona-style template.")
        text = stimulus_for(row, materials)
        for item in items:
            rows.append({
                "profile_id": row.profile_id, "condition": row.condition,
                "item": item, "target": materials["items"][item]["target"],
                "prompt": ap.build_prompt(persona, text,
                                          materials["items"][item]["question"],
                                          scales[item]),
            })
    return pd.DataFrame(rows)


def main() -> None:
    ap_ = argparse.ArgumentParser(description=__doc__)
    ap_.add_argument("--model", default=MODEL)
    ap_.add_argument("--persona-style", choices=("prose", "template"),
                     default="prose")
    ap_.add_argument("--conditions", nargs="*",
                     help="only these conditions (default: all 17)")
    ap_.add_argument("--limit", type=int, help="first N respondents per condition")
    ap_.add_argument("--items", nargs="*", help="only these raw items")
    ap_.add_argument("--persona-file",
                     help="read prose personas from here instead of "
                          "sim/out/02_persona_text.csv")
    ap_.add_argument("--tag", help="name the output files")
    ap_.add_argument("--seed", type=int, default=SEED)
    ap_.add_argument("--max-model-len", type=int, default=4096)
    args = ap_.parse_args()

    materials = json.loads((OUT / "00_materials.json").read_text())
    personas = pd.read_csv(OUT / "01_personas.csv")
    if args.conditions:
        personas = personas[personas.condition.isin(args.conditions)]
    if args.limit:
        personas = (personas.groupby("condition", group_keys=False)
                    .head(args.limit))
    if personas.empty:
        raise SystemExit("no respondents selected")

    prose: dict[str, str] = {}
    if args.persona_style == "prose":
        path = Path(args.persona_file) if args.persona_file \
            else OUT / "02_persona_text.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}. Run stage 2, or use "
                             f"--persona-style template.")
        text = pd.read_csv(path)
        prose = dict(zip(text.profile_id, text.text))

    items = args.items or spec.ALL_ITEMS
    grid = build(personas, prose, materials, args.persona_style, items)
    scales = {i: ap.scale_of(i, materials["items"][i]["options"])
              for i in items}

    from vllm import LLM, SamplingParams
    engine = LLM(model=args.model, max_model_len=args.max_model_len,
                 gpu_memory_utilization=0.85, seed=args.seed)
    params = SamplingParams(temperature=TEMPERATURE, max_tokens=MAX_TOKENS,
                            stop=["'"], seed=args.seed, n=1)

    started, clock = datetime.now(timezone.utc).isoformat(), time.time()
    outputs = engine.generate(list(grid.prompt), params)
    elapsed = time.time() - clock
    ended = datetime.now(timezone.utc).isoformat()

    grid["raw"] = [o.outputs[0].text for o in outputs]
    grid["value"] = [ap.parse(r, scales[i]) for r, i in
                     zip(grid.raw, grid.item)]

    tag = args.tag or "03_replies"
    with (OUT / f"{tag}.jsonl").open("w") as f:
        for r in grid.itertuples():
            f.write(json.dumps({
                "profile_id": r.profile_id, "condition": r.condition,
                "item": r.item, "target": r.target,
                "raw": r.raw, "value": r.value}) + "\n")

    ok = int(grid.value.notna().sum())
    report = "\n".join([
        "=" * 74, "STAGE 3 — REPLIES", "=" * 74, "",
        f"model          {args.model}",
        f"persona style  {args.persona_style}",
        f"sampling       temperature {TEMPERATURE}, one answer per item, "
        f"seed {args.seed}",
        f"call window    {started}  to  {ended}", "",
        f"respondents    {personas.profile_id.nunique():,} "
        f"over {personas.condition.nunique()} condition(s)",
        f"items          {len(items)}",
        f"generations    {len(grid):,}",
        f"parsed         {ok:,}  ({100 * ok / len(grid):.1f}%)",
        f"wall clock     {elapsed / 60:.1f} min  "
        f"({len(grid) / elapsed:.1f} generations/s)", "",
        f"wrote sim/out/{tag}.jsonl", "", "=" * 74, ""])
    (OUT / f"{tag.replace('03_replies', '03_report')}.txt").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
