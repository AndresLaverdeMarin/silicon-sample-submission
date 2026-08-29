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


# The Census calls it "District of Columbia". `questionnaire.txt` calls it
# "Washington D.C." in its own state list. Use the study's name in the prompt.
STATE_ALIAS = {"District of Columbia": "Washington D.C."}
STATE_POP = Path(__file__).resolve().parent.parent / \
    "population/state_adult_pop_2024.csv"


def draw_state(profile_id: str, region: str, states: pd.DataFrame,
               seed: int) -> str:
    """Give this respondent a home state, inside their own Census region.

    The draw is weighted by the adult population of each state, so the states
    come up as often as real adults of that region live in them. It is
    derived from the `profile_id`, so the same person always gets the same
    state and the run repeats exactly.
    """
    pool = states[states.region == region].sort_values("state")
    if pool.empty:
        return ""
    weight = pool.adults_18plus.to_numpy(dtype="float64")
    cut = weight.cumsum() / weight.sum()
    draw = int(hashlib.blake2b(f"{seed}:state:{profile_id}".encode(),
                               digest_size=8).hexdigest(), 16) % 10**12 / 1e12
    name = str(pool.state.to_numpy()[int((cut <= draw).sum())])
    return STATE_ALIAS.get(name, name)


def stimulus_for(row, materials: dict, states: pd.DataFrame,
                 seed: int) -> tuple[str, str]:
    """The text this respondent reads, and their state if the arm needs one.

    Control reads one of three fillers. Fifteen arms read one fixed text.

    The `Extreme weather predictions` arm is state-adaptive: the participant
    reports a state, reads one intro that names that state and its risk
    category, and then reads ONE of four texts. This builds that page. A
    respondent with no region gets the study's own fallback: the generic
    intro and case 4, which is what a real participant who answers "Prefer
    not to say" is shown.
    """
    cond = materials["conditions"][row.condition]
    if row.condition == "control":
        return cond["fillers"][row.control_filler], ""
    if not cond.get("state_adaptive"):
        return cond["text"], ""

    state = draw_state(row.profile_id, getattr(row, "region", ""), states,
                       seed)
    if not state:
        return f"{cond['intro_generic']}\n\n{cond['cases']['4']}", ""
    case = str(cond["state_case"][state])
    intro = (cond["intro_with_state"].replace("[STATE]", state)
             .replace("[CASE]", cond["case_label"][case]))
    return f"{intro}\n\n{cond['cases'][case]}", state


def build(personas: pd.DataFrame, prose: dict[tuple[str, int], str],
          materials: dict, style: str, items: list[str],
          states: pd.DataFrame, seed: int) -> pd.DataFrame:
    """One row for each (respondent, replicate, item).

    A respondent normally has ONE bio, which is the Tier-1 regime. When the
    stage-2 file holds more, each is asked the whole questionnaire, and the
    analysis decides whether to average them. A template persona has no
    replicate: the text is deterministic, so a second copy would be identical.
    """
    scales = {i: ap.scale_of(i, materials["items"][i]["options"])
              for i in items}
    reps = sorted({r for _, r in prose}) if prose else [0]
    rows = []
    for row in personas.itertuples():
        text, state = stimulus_for(row, materials, states, seed)
        for rep in ([0] if style == "template" else reps):
            if style == "template":
                persona = ap.template_persona(row)
            else:
                persona = prose.get((row.profile_id, rep))
                if persona is None:
                    raise SystemExit(
                        f"no stage-2 text for {row.profile_id} replicate "
                        f"{rep}. Run stage 2, or use --persona-style "
                        f"template.")
            for item in items:
                rows.append({
                    "profile_id": row.profile_id, "replicate": rep,
                    "condition": row.condition, "state": state, "item": item,
                    "target": materials["items"][item]["target"],
                    "prompt": ap.build_prompt(
                        persona, text, materials["items"][item]["question"],
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
    ap_.add_argument("--materials",
                     help="read a different materials file, e.g. a validation "
                          "study built by sim/validation/")
    ap_.add_argument("--personas",
                     help="read a different persona table")
    ap_.add_argument("--tag", help="name the output files")
    ap_.add_argument("--seed", type=int, default=SEED)
    ap_.add_argument("--retry-rounds", type=int, default=5,
                     help="re-ask cells that did not parse (default 3)")
    ap_.add_argument("--max-model-len", type=int, default=4096)
    args = ap_.parse_args()

    materials = json.loads(Path(
        args.materials or OUT / "00_materials.json").read_text())
    personas = pd.read_csv(args.personas or OUT / "01_personas.csv")
    if args.conditions:
        personas = personas[personas.condition.isin(args.conditions)]
    if args.limit:
        personas = (personas.groupby("condition", group_keys=False)
                    .head(args.limit))
    if personas.empty:
        raise SystemExit("no respondents selected")

    prose: dict = {}
    if args.persona_style == "prose":
        path = Path(args.persona_file) if args.persona_file \
            else OUT / "02_persona_text.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}. Run stage 2, or use "
                             f"--persona-style template.")
        text = pd.read_csv(path)
        if "replicate" not in text.columns:
            text["replicate"] = 0
        prose = {(pid, int(rep)): t for pid, rep, t
                 in zip(text.profile_id, text.replicate, text.text)}

    # The item list comes from the MATERIALS, not from the megastudy schema.
    # A validation study such as v15 carries its own items, and defaulting to
    # spec.ALL_ITEMS sent stage 3 looking for the megastudy's 44 inside
    # Voelkel's 13.
    items = args.items or list(materials["items"])
    unknown = [i for i in items if i not in materials["items"]]
    if unknown:
        raise SystemExit(f"the materials hold no item(s): {unknown}")
    # The state-adaptive arm needs the population weights. Read them only
    # when that arm is in the run, so a validation study needs no such file.
    states = pd.DataFrame(columns=["state", "region", "adults_18plus"])
    if any(c.get("state_adaptive")
           for k, c in materials["conditions"].items()
           if k in set(personas.condition)):
        if not STATE_POP.exists():
            raise SystemExit(f"missing {STATE_POP}. Run "
                             "sim/00b_state_populations.py.")
        states = pd.read_csv(STATE_POP)

    grid = build(personas, prose, materials, args.persona_style, items,
                 states, args.seed)
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
                                 f"{args.seed}:{r.profile_id}:{r.replicate}:"
                                 f"{r.item}".encode(),
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
                               f"{r.replicate}:{r.item}".encode(),
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

    # **Fill whatever the retries could not recover.** `make check` FAILS on
    # one NA in one prediction column, so a submission cannot ship a hole.
    # v16 left 8 of 117,000 cells empty after three rounds, and the recovery
    # rate is flat across rounds (91%, 89%, 88%), so more rounds alone do not
    # reach zero. Each fill is DETERMINISTIC and is counted, because
    # registration item G asks what post-processing the answers get.
    #
    # The order keeps as much of the person as possible:
    #   1. the person's median on the other items of the same composite
    #   2. the item's median over every other person
    #   3. the middle of the scale
    fills = {"person": 0, "item": 0, "midpoint": 0}
    holes = grid.index[grid.value.isna()]
    if len(holes):
        of_composite = {i: c for c, block in
                        materials.get("composites", {}).items()
                        for i in block}
        item_median = grid.groupby("item").value.median()
        for ix in holes:
            row = grid.loc[ix]
            comp = of_composite.get(row.item)
            val = float("nan")
            if comp:
                mates = grid[(grid.profile_id == row.profile_id)
                             & (grid.replicate == row.replicate)
                             & (grid.item.map(of_composite) == comp)]
                val = mates.value.median()
            if pd.notna(val):
                fills["person"] += 1
            elif pd.notna(item_median.get(row.item, float("nan"))):
                val = item_median[row.item]
                fills["item"] += 1
            else:
                sc = scales[row.item]
                val = (sc["low"] + sc["high"]) / 2
                fills["midpoint"] += 1
            grid.loc[ix, "value"] = float(val)
            grid.loc[ix, "raw"] = "[filled]"
        print(f"filled {len(holes):,} cell(s): "
              + ", ".join(f"{k} {v:,}" for k, v in fills.items() if v))

    elapsed = time.time() - clock
    ended = datetime.now(timezone.utc).isoformat()

    tag = args.tag or "03_replies"
    with (OUT / f"{tag}.jsonl").open("w") as f:
        for r in grid.itertuples():
            f.write(json.dumps({
                "profile_id": r.profile_id, "replicate": r.replicate,
                "condition": r.condition, "state": r.state,
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
        (f"  filled        {sum(fills.values()):,} cell(s) not recovered by "
         f"retries: " + ", ".join(f"{k} {v:,}" for k, v in fills.items() if v)
         if sum(fills.values()) else "  filled         none needed"),
        f"wall clock     {elapsed / 60:.1f} min  "
        f"({len(grid) / elapsed:.1f} generations/s)", "",
        f"wrote sim/out/{tag}.jsonl", "", "=" * 74, ""])
    (OUT / f"{tag.replace('03_replies', '03_report')}.txt").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
