#!/usr/bin/env python3
"""
Stage 2 — write one short prose persona for each of the 9,000 respondents.

Stage 1 gives 9,000 people as rows of attributes. Stage 3 needs each of them
as a paragraph a language model can be asked to answer as. This stage makes
that paragraph.

**The writer is not the answerer.** `google/gemma-4-26B-A4B-it` writes and
`Qwen/Qwen3.8-27B` answers in stage 3. Two reasons. On the harder of the two
persona tasks the sibling `modelbench` project measured, gemma kept the most
facts. And a model that reads its own prose is not the same test as a model
that reads someone else's, so splitting the roles removes a confound that
would otherwise need declaring under registration item J.1.

Every text passes four gates. A text that fails any of them is written again,
with a new seed, up to `--repair-rounds` times, and the retry is kept only
when it fails fewer gates:

    every checkable fact present   a fact with no distinctive token, such as
                                   "has no religion", counts as unverifiable
                                   and never as missing
    no leak word                   "survey", "study", "research" and the
                                   words a writer reaches for when inventing
    ASCII only                     stage 3 renders these into prompts
    45 to 160 words                short descriptions keep more facts

What it writes:

    sim/out/02_persona_text.csv        profile_id, text, and the gate result
    sim/out/02_report.txt              coverage, leaks, length, repairs
    sim/out/02_provenance.json         writer, sampling, call window, seed

Run it from the repository root. It needs a vLLM environment:

    uv run --extra generate sim/02_write_personas.py
    uv run --extra generate sim/02_write_personas.py --limit 20   # smoke test

`--limit` writes to `02_persona_text_smoke.csv`, so a smoke test never
overwrites a full run.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import persona_prompt as pp                            # noqa: E402

ROOT = HERE.parent
OUT = HERE / "out"
PERSONAS = OUT / "01_personas.csv"

WRITER = "google/gemma-4-26B-A4B-it"
SEED = 20260828
TEMPERATURE = 0.9          # prose needs variety; the gates catch the drift
TOP_P = 0.95
MAX_TOKENS = 320
# A retry samples more safely: a text that failed once usually failed because
# the writer wandered, so the retry is pulled back toward the facts.
REPAIR_TEMPERATURE = 0.7
REPAIR_TOP_P = 0.9


def build(frame: pd.DataFrame, seed: int,
          replicates: int = 1) -> pd.DataFrame:
    """`replicates` prompts for each persona, each with its own voice.

    One bio per person is the Tier-1 regime: a respondent is one row, and the
    variation between people is the deliverable. More than one exists only to
    test what averaging them does — see v16 in the sibling modelbench project.
    Each replicate draws its own seed, so the voice and the fact order move.
    """
    rows = []
    for row in frame.itertuples():
        for rep in range(replicates):
            rng = random.Random(f"{seed}:{row.profile_id}:{rep}")
            prompt, voice, order = pp.build_prompt(row, rng)
            rows.append({"profile_id": row.profile_id, "replicate": rep,
                         "prompt": prompt, "voice": voice,
                         "fact_order": "|".join(order)})
    return pd.DataFrame(rows)


def generate(engine, tokenizer, prompts: list[str], temperature: float,
             top_p: float, seed: int) -> list[str]:
    """Ask the writer for one text for each prompt."""
    from vllm import SamplingParams
    chats = [tokenizer.apply_chat_template(
        [{"role": "system", "content": pp.SYSTEM},
         {"role": "user", "content": prompt}],
        tokenize=False, add_generation_prompt=True) for prompt in prompts]
    params = SamplingParams(temperature=temperature, top_p=top_p,
                            max_tokens=MAX_TOKENS, seed=seed, n=1)
    return [o.outputs[0].text.strip()
            for o in engine.generate(chats, params)]


def tidy(text: str) -> str:
    """Strip the wrappers a chat model adds around a plain answer."""
    text = text.strip()
    for fence in ('"""', "```"):
        if text.startswith(fence):
            text = text.strip(fence).strip()
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()
    # A leading "Here is ..." line, and any markdown heading.
    lines = [l for l in text.splitlines()
             if not l.lstrip().startswith("#")]
    if lines and lines[0].rstrip().endswith(":") and len(lines) > 1:
        lines = lines[1:]
    return " ".join(" ".join(lines).split())


def score(frame: pd.DataFrame, personas: pd.DataFrame) -> pd.DataFrame:
    """Run the gates over every written text."""
    by_id = personas.drop_duplicates("profile_id").set_index("profile_id")
    checks = [pp.check(t, by_id.loc[i]) for i, t in
              zip(frame.profile_id, frame.text)]
    return pd.concat([frame.reset_index(drop=True),
                      pd.DataFrame(checks)], axis=1)


def report(scored: pd.DataFrame, repairs: list[dict], args,
           window: tuple[str, str]) -> str:
    """The text report, and the numbers registration item D.2 needs."""
    n = len(scored)
    ok = int(scored.ok.sum())
    coverage = 100 * (1 - scored.n_missing.sum() / scored.n_checkable.sum())
    lines = [
        "=" * 74, "STAGE 2 — WRITTEN PERSONAS", "=" * 74, "",
        f"writer        {args.writer}",
        f"sampling      temperature {TEMPERATURE}, top_p {TOP_P}, "
        f"seed {args.seed}",
        f"call window   {window[0]}  to  {window[1]}", "",
        "GATES", "-" * 74,
        f"  personas            {n:,}",
        f"  passed every gate   {ok:,}  ({100 * ok / n:.1f}%)",
        f"  fact coverage       {coverage:.1f}%  "
        f"({int(scored.n_missing.sum()):,} of "
        f"{int(scored.n_checkable.sum()):,} checkable facts missing)",
        f"  leak words          {int((scored.leaks != '').sum()):,}",
        f"  non-ASCII           {int((~scored.ascii_ok).sum()):,}",
        f"  outside 45-160 wds  {int((~scored.length_ok).sum()):,}",
        f"  words, median       {scored.n_words.median():.0f}"
        f"  (min {scored.n_words.min()}, max {scored.n_words.max()})", "",
        "REPAIRS", "-" * 74]
    if repairs:
        for r in repairs:
            lines.append(f"  round {r['round']}   attempted {r['attempted']:,}"
                         f"   kept {r['kept']:,}")
    else:
        lines.append("  none needed")
    worst = (scored[scored.missing != ""].missing.str.split("|").explode()
             .value_counts().head(6))
    if len(worst):
        lines += ["", "FACTS MOST OFTEN MISSING", "-" * 74]
        lines += [f"  {k:<22} {v:,}" for k, v in worst.items()]
    lines += ["", "=" * 74, ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--writer", default=WRITER)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--limit", type=int, help="smoke test on the first N")
    ap.add_argument("--replicates", type=int, default=1,
                    help="bios per person. 1 is the Tier-1 regime.")
    ap.add_argument("--personas", help="read a different persona table")
    ap.add_argument("--out", help="write to this CSV instead")
    ap.add_argument("--repair-rounds", type=int, default=2)
    ap.add_argument("--max-model-len", type=int, default=2048)
    args = ap.parse_args()

    if not PERSONAS.exists():
        raise SystemExit(f"missing {PERSONAS}. Run stage 1 first.")
    personas = pd.read_csv(args.personas or PERSONAS)
    if args.limit:
        personas = personas.head(args.limit).copy()
    prompts = build(personas, args.seed, args.replicates)

    from transformers import AutoTokenizer
    from vllm import LLM
    tokenizer = AutoTokenizer.from_pretrained(args.writer)
    engine = LLM(model=args.writer, max_model_len=args.max_model_len,
                 gpu_memory_utilization=0.85, seed=args.seed)

    started = datetime.now(timezone.utc).isoformat()
    texts = generate(engine, tokenizer, list(prompts.prompt),
                     TEMPERATURE, TOP_P, args.seed)
    prompts["text"] = [tidy(t) for t in texts]
    scored = score(prompts, personas)

    repairs = []
    for round_no in range(1, args.repair_rounds + 1):
        bad = scored[~scored.ok]
        if bad.empty:
            break
        again = generate(engine, tokenizer, list(bad.prompt),
                         REPAIR_TEMPERATURE, REPAIR_TOP_P,
                         args.seed + round_no)
        retry = score(bad[["profile_id", "replicate", "prompt", "voice",
                           "fact_order"]]
                      .assign(text=[tidy(t) for t in again]), personas)
        # Keep a retry only when it fails FEWER gates than what it replaces.
        def failures(frame):
            return (frame.n_missing + (frame.leaks != "").astype(int)
                    + (~frame.ascii_ok).astype(int)
                    + (~frame.length_ok).astype(int)).to_numpy()
        better = failures(retry) < failures(bad)
        # **Index on (profile_id, replicate), never profile_id alone.** With
        # more than one bio per person the id repeats, and assigning through a
        # duplicated index makes pandas align every matching row against every
        # other. On 9,000 rows that hangs, and where it does not hang it
        # writes one replicate's text over all five.
        key = ["profile_id", "replicate"]
        kept = retry[better].set_index(key)
        scored = scored.set_index(key)
        scored.loc[kept.index, kept.columns] = kept
        scored = scored.reset_index()
        repairs.append({"round": round_no, "attempted": int(len(bad)),
                        "kept": int(better.sum())})
    ended = datetime.now(timezone.utc).isoformat()

    stem = (args.out[:-4] if args.out and args.out.endswith(".csv")
            else "02_persona_text_smoke" if args.limit else "02_persona_text")
    keep = ["profile_id", "replicate", "text", "voice", "fact_order",
            "n_facts",
            "n_checkable", "n_missing", "missing", "leaks", "n_words", "ok"]
    scored[keep].to_csv(OUT / f"{stem}.csv", index=False)
    text = report(scored, repairs, args, (started, ended))
    (OUT / f"{stem.replace('02_persona_text', '02_report')}.txt").write_text(text)
    (OUT / f"{stem.replace('02_persona_text', '02_provenance')}.json"
     ).write_text(json.dumps({
         "stage": "2 — written personas", "writer_model": args.writer,
         "answering_model": "Qwen/Qwen3.8-27B (stage 3)",
         "temperature": TEMPERATURE, "top_p": TOP_P,
         "repair_temperature": REPAIR_TEMPERATURE, "repair_top_p": REPAIR_TOP_P,
         "max_tokens": MAX_TOKENS, "seed": args.seed,
         "repair_rounds": args.repair_rounds,
         "call_window": {"start": started, "end": ended},
         "n_personas": int(len(scored)),
         "voices": list(pp.VOICES), "gates": [
             "every checkable fact present", "no leak word", "ASCII only",
             "45 to 160 words"],
         "note": ("The writer and the answering model are different, so no "
                  "model reads its own prose. Declare under registration "
                  "items B.1, B.2 and D.2."),
     }, indent=2) + "\n")
    print(text)


if __name__ == "__main__":
    main()
