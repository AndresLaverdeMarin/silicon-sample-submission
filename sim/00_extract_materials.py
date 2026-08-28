#!/usr/bin/env python3
"""
Stage 0 — pull the study's own words out of the files the benchmark ships.

Nothing here is written by us. The 17 condition texts come from
`survey/questionnaire.txt`, and the 44 item wordings and their response
options come from `codebook.csv`. Both ship with the template, so this stage
needs no network and no model.

It writes:

    sim/out/00_materials.json    conditions and items, ready for stage 3

The control condition holds THREE filler texts. A control respondent reads
ONE of them; stage 1 already drew which, into `control_filler`.

Run it from the repository root:

    uv run sim/00_extract_materials.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib import spec                                            # noqa: E402

ROOT = HERE.parent
QUESTIONNAIRE = ROOT / "survey/questionnaire.txt"
CODEBOOK = ROOT / "codebook.csv"
OUT = HERE / "out"

# The three control headings carry the filler name after the last colon.
CONTROL = re.compile(r"^### control — filler text \d of 3: (.+)$")
FILLER_KEY = {"The History of Neckties": "neckties",
              "The Rules of Baseball": "baseball",
              "Different Types of Dances": "dances"}


def sections(text: str) -> list[tuple[str, str]]:
    """Split the questionnaire into its `### ` blocks, heading and body."""
    parts = re.split(r"^### (.+)$", text, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip())
            for i in range(1, len(parts), 2)]


def conditions() -> dict[str, dict]:
    """The 16 intervention texts, and the 3 control fillers."""
    blocks = sections(QUESTIONNAIRE.read_text())
    out: dict[str, dict] = {"control": {"fillers": {}}}
    for heading, body in blocks:
        match = CONTROL.match(f"### {heading}")
        if match:
            key = FILLER_KEY.get(match.group(1).strip())
            if key is None:
                raise SystemExit(f"unknown control filler: {match.group(1)!r}")
            out["control"]["fillers"][key] = body
        elif heading in spec.INTERVENTIONS:
            out[heading] = {"text": body}

    missing = [c for c in spec.INTERVENTIONS if c not in out]
    if missing:
        raise SystemExit(f"questionnaire.txt holds no text for: {missing}")
    if set(out["control"]["fillers"]) != set(spec.CONTROL_FILLERS):
        raise SystemExit(f"control fillers wrong: "
                         f"{sorted(out['control']['fillers'])}")
    return out


def items() -> dict[str, dict]:
    """The 44 items, with the question and its response options."""
    book = pd.read_csv(CODEBOOK).dropna(subset=["qualtrics_label"])
    book = book.drop_duplicates(subset=["qualtrics_label"], keep="first")
    book = book.set_index("qualtrics_label")
    out = {}
    for name in spec.ALL_ITEMS:
        if name not in book.index:
            raise SystemExit(f"codebook.csv holds no item {name!r}")
        row = book.loc[name]
        out[name] = {"question": str(row.question_text).strip(),
                     "options": str(row.response_options).strip(),
                     "target": str(row.target_label).strip()}
    return out


def main() -> None:
    data = {"conditions": conditions(), "items": items(),
            "source": {"conditions": "survey/questionnaire.txt",
                       "items": "codebook.csv"},
            "note": ("Every word here is the benchmark's own. Nothing in this "
                     "file was written by us.")}
    OUT.mkdir(exist_ok=True)
    (OUT / "00_materials.json").write_text(json.dumps(data, indent=1) + "\n")

    words = {k: len((v.get("text") or "").split())
             for k, v in data["conditions"].items() if k != "control"}
    fill = {k: len(v.split())
            for k, v in data["conditions"]["control"]["fillers"].items()}
    print(f"wrote sim/out/00_materials.json")
    print(f"  conditions   {len(words)} interventions + control")
    print(f"  words/text   median {sorted(words.values())[len(words)//2]}, "
          f"min {min(words.values())}, max {max(words.values())}")
    print(f"  control      {fill}")
    print(f"  items        {len(data['items'])}")


if __name__ == "__main__":
    main()
