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

# **One arm is not one text.** `Extreme weather predictions` asks the person
# for their home state, and then shows ONE of four texts, chosen by the risk
# category of that state. Its block in `questionnaire.txt` holds all four
# texts, the state lists, the authoring notes and the references. A
# participant NEVER sees that block, and the block says so itself:
#     "do NOT feed the whole block below verbatim"
# It also ends with the outcome definitions, so feeding it whole would tell
# the respondent what the study measures. Stage 3 builds the page the
# participant really reads. This function gives it the parts.
STATE_ADAPTIVE = "Extreme weather predictions"


def state_adaptive(body: str) -> dict:
    """Cut the state-adaptive arm into the parts a participant sees.

    Nothing here is written by us. Every string is cut out of
    `survey/questionnaire.txt`.
    """
    # Section I — the state lists, and the risk phrase that names each case.
    logic = body.split("I. STIMULUS CASE ASSIGNMENT LOGIC")[1] \
                .split("II. STIMULUS")[0]
    parts = re.split(r"Case (\d) [\u2013-]", logic)[1:]
    state_case: dict[str, int] = {}
    case_label: dict[str, str] = {}
    for number, rest in zip(parts[0::2], parts[1::2]):
        head, _, tail = rest.partition("\n")
        case_label[number] = head.strip().strip('\u201c\u201d"')
        state_case.update({s.strip(): int(number)
                           for s in tail.replace("\n", ",").split(",")
                           if s.strip()})

    # Intervention page 2 — the one intro paragraph, in its two branches.
    # The IF branch is for a person who does not give a state.
    page2 = body.split("Intervention Page 2")[1].split("Intervention page 3")[0]
    generic = page2.split('IF state=\u201dPrefer not to say\u201d:')[1] \
                   .split("ELSE:")[0].strip()
    with_state = page2.split("ELSE:")[1].strip()

    # Intervention page 3 — the four texts. **`rsplit`, not `split`.** The
    # authoring note at the top of the block also says "Intervention page 3",
    # and splitting on the first one returns the notes instead of the texts.
    page3 = body.rsplit("Intervention page 3", 1)[1] \
                .split("References [not displayed")[0]
    chunks = re.split(r"^Case (\d)\s*$", page3, flags=re.M)
    cases = {chunks[i]: chunks[i + 1].strip()
             for i in range(1, len(chunks), 2)}

    if sorted(cases) != ["1", "2", "3", "4"]:
        raise SystemExit(f"{STATE_ADAPTIVE}: found cases {sorted(cases)}, "
                         "expected 1 to 4")
    if len(state_case) != 51:
        raise SystemExit(f"{STATE_ADAPTIVE}: {len(state_case)} states "
                         "mapped, expected 50 and D.C.")
    for placeholder in ("[STATE]", "[CASE]"):
        if placeholder not in with_state:
            raise SystemExit(f"{STATE_ADAPTIVE}: the intro lost "
                             f"{placeholder}")
    return {"state_adaptive": True,
            "intro_with_state": with_state,
            "intro_generic": generic,
            # `case_label` is the risk phrase that fills [CASE]. Case 4 has
            # no phrase: it uses the generic intro, which has no [CASE].
            "case_label": {k: v for k, v in case_label.items() if k != "4"},
            "cases": cases,
            "state_case": state_case}


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
        elif heading == STATE_ADAPTIVE:
            out[heading] = state_adaptive(body)
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

    # The state-adaptive arm has no single text. Report the longest page a
    # participant can be shown, so the number is comparable with the others.
    def served(v: dict) -> int:
        if not v.get("state_adaptive"):
            return len(v["text"].split())
        return max(len((v["intro_with_state"] + " " + t).split())
                   for t in v["cases"].values())

    words = {k: served(v)
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
