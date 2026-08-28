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
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import answer_prompt as ap                             # noqa: E402
from lib import spec                                            # noqa: E402

OUT = HERE / "out"
MODEL = "Qwen/Qwen3.8-27B"

# Per-model engine settings, ported from the sibling modelbench project.
# **`gdn_prefill_backend: triton` is not optional for Qwen3.8-27B.** Without
# it vLLM picks a prefill kernel it must compile with `nvcc`, which is not on
# this machine, and the engine dies with
#   RuntimeError: Could not find nvcc and default cuda_home='/usr/local/cuda'
# `limit_mm_per_prompt` turns off the vision and audio towers we never use.
ENGINE_OVERRIDES: dict[str, dict] = {
    "Qwen/Qwen3.8-27B": {"limit_mm_per_prompt": {"image": 0, "audio": 0},
                         "additional_config":
                             {"gdn_prefill_backend": "triton"}},
    "google/gemma-4-26B-A4B-it": {"limit_mm_per_prompt": {"image": 0,
                                                          "audio": 0}},
    "google/gemma-4-E4B-it": {"limit_mm_per_prompt": {"image": 0,
                                                      "audio": 0}},
    "google/gemma-3-27b-it": {"limit_mm_per_prompt": {"image": 0}},
}
SEED = 20260828
TEMPERATURE = 1.0          # the spread between respondents is the deliverable
TOP_P = 0.95
# **Not 8.** The answer is normally about 3 tokens, but the model sometimes
# opens with "Based on the information provided, I ..." and reaches the number
# after it. A tight budget truncates before the number arrives and scores a
# good answer as a parse failure. `stop=["\'"]` ends a clean answer at once,
# so a generous budget costs nothing: modelbench measures ~4 output tokens per
# generation with a 256 budget.
MAX_TOKENS = 64


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
    ap_.add_argument("--retry-rounds", type=int, default=3,
                     help="re-ask cells that did not parse (default 3)")
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
    settings = dict(model=args.model, dtype="bfloat16",
                    max_model_len=args.max_model_len,
                    gpu_memory_utilization=0.85, seed=args.seed,
                    # The 44 items of one respondent share a long prefix: the
                    # condition text and the persona. Prefix caching computes
                    # it one time for each respondent instead of 44 times.
                    enable_prefix_caching=True, trust_remote_code=True)
    settings.update(ENGINE_OVERRIDES.get(args.model, {}))
    engine = LLM(**settings)
    # **One seed for each request, never one for the batch.** A single seed
    # shared by every request makes every respondent draw from the same RNG
    # stream, and at temperature 1.0 with a peaked distribution they all
    # return the SAME number. That is a degenerate panel: the Tier-1
    # distribution metrics measure exactly the spread it destroys. The seed is
    # derived from the respondent and the item, so the run stays reproducible.
    params = [SamplingParams(temperature=TEMPERATURE, top_p=TOP_P,
                             max_tokens=MAX_TOKENS, stop=["'"], n=1,
                             seed=int(hashlib.blake2b(
                                 f"{args.seed}:{r.profile_id}:{r.item}".encode(),
                                 digest_size=4).hexdigest(), 16))
              for r in grid.itertuples()]

    started, clock = datetime.now(timezone.utc).isoformat(), time.time()
    outputs = engine.generate(list(grid.prompt), params)
    grid["raw"] = [o.outputs[0].text for o in outputs]
    grid["value"] = pd.Series([ap.parse(r, scales[i]) for r, i in
                               zip(grid.raw, grid.item)],
                              index=grid.index, dtype="float64")
    first_pass = float(grid.value.notna().mean())

    # **Retry every cell that did not parse.** Tier 1 asks one answer per
    # person per item, so there is no second sample to fall back on and an
    # unparsed answer is a missing value in the submission. `make check`
    # FAILS on any NA in a prediction column. Each round re-asks only the
    # failures, with a new seed, and keeps whatever now parses.
    rounds = []
    for round_no in range(1, args.retry_rounds + 1):
        todo = grid[grid.value.isna()]
        if todo.empty:
            break
        retry_params = [
            SamplingParams(temperature=TEMPERATURE, top_p=TOP_P,
                           max_tokens=MAX_TOKENS, stop=["'"], n=1,
                           seed=int(hashlib.blake2b(
                               f"{args.seed}:{round_no}:{r.profile_id}:"
                               f"{r.item}".encode(),
                               digest_size=4).hexdigest(), 16))
            for r in todo.itertuples()]
        again = engine.generate(list(todo.prompt), retry_params)
        raw = [o.outputs[0].text for o in again]
        got = [ap.parse(t, scales[i]) for t, i in zip(raw, todo.item)]
        # `got` mixes floats and None. Assigning the bare list into a float
        # column raises LossySetitemError, so build a typed Series first.
        grid.loc[todo.index, "raw"] = pd.Series(raw, index=todo.index,
                                                dtype="object")
        grid.loc[todo.index, "value"] = pd.Series(got, index=todo.index,
                                                  dtype="float64")
        kept = sum(v is not None for v in got)
        rounds.append({"round": round_no, "attempted": len(todo),
                       "recovered": kept})
        print(f"retry {round_no}: {len(todo):,} attempted, {kept:,} recovered")
    elapsed = time.time() - clock
    ended = datetime.now(timezone.utc).isoformat()

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
        f"parsed, first  {100 * first_pass:.1f}%",
        f"parsed, final  {ok:,}  ({100 * ok / len(grid):.1f}%)",
        ("  retries       " + ",  ".join(
            f"round {r['round']}: {r['recovered']:,}/{r['attempted']:,}"
            for r in rounds)) if rounds else "  retries        none needed",
        (f"  !! {len(grid) - ok:,} CELLS STILL EMPTY — make check FAILS on an "
         f"NA in a prediction column" if ok < len(grid) else
         "  every cell has a value"),
        f"wall clock     {elapsed / 60:.1f} min  "
        f"({len(grid) / elapsed:.1f} generations/s)", "",
        f"wrote sim/out/{tag}.jsonl", "", "=" * 74, ""])
    (OUT / f"{tag.replace('03_replies', '03_report')}.txt").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
