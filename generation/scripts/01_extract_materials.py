#!/usr/bin/env python3
"""Step 1 — extract the experimental materials into one machine-readable file.

This builds the *fixed prefix* every prediction task carries: the 17 stimulus
texts and the 44 raw survey items that the 13 scored outcomes are made of.

Both come out of files already in this repository, so nothing is transcribed by
hand:
  survey/questionnaire.txt   the benchmark's plain-text rendering of the
                             instrument, in chronological order
  codebook.csv               qualtrics_label -> target_label, question text,
                             response options
  scripts/lib/submission_spec.R  the canonical condition / outcome labels

Output
  generation/build/materials.json

Why items and not outcomes
--------------------------
6 of the 13 scored outcomes are composites of several survey items (see
design.md section 4). The model predicts the *items*; the composites are
arithmetic, computed in 05_aggregate.py. Asking a model for both invites a
composite that contradicts its own items, which `make check` warns about and
the scorer keeps as submitted.

Licence note: the stimulus texts adapt copyrighted material and are not covered
by this repository's own licence grant. They are already in the deposit, in
survey/. This script copies them into build/ and into the task prompts (which
registration item C.1 requires verbatim); it does not add material to the
deposit that was not already there.

Usage:
  python3 generation/scripts/01_extract_materials.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.spec import REPO, load_spec  # noqa: E402

QUESTIONNAIRE = REPO / "survey" / "questionnaire.txt"
CODEBOOK = REPO / "codebook.csv"
OUT = REPO / "generation" / "build" / "materials.json"

# --------------------------------------------------------------- items -------
# The 44 raw items behind the 13 scored outcomes, keyed by the qualtrics_label
# in codebook.csv. `question` and `scale` are filled from codebook.csv below —
# this table only says which items exist and how they roll up.
#
# rule: "copy"       the outcome is this single item, unchanged
#       "mean"       the outcome is the arithmetic mean of the listed items
#       "mean_of_means"  mean of sub-composites (trust_multidimensional)
#       "reverse100"     100 - item (funding_perceptions, per codebook.csv)
#       "pct_to_prop"    item is a percentage 0-100, outcome a proportion 0-1
OUTCOME_ITEMS: dict[str, tuple[str, list]] = {
    "trust_multidimensional": ("mean_of_means", [
        ["trust_competent_1", "trust_intelligent_1", "trust_qualified_1"],
        ["trust_honest_1", "trust_ethical_1", "trust_sincere_1"],
        ["trust_concerned_1", "trust_improve_1", "trust_considerate_1"],
        ["trust_feedback_1", "trust_transparent_1", "trust_attention_1"],
    ]),
    "trust_post":           ("copy", ["trust_post_1"]),
    "distrust_post":        ("copy", ["distrust_1"]),
    "funding_perceptions":  ("reverse100", ["funding_5"]),
    "policy_role_mean":     ("mean", ["policy_1_1", "policy_2_1", "policy_3_1", "policy_4_1"]),
    "inst_trust_mean":      ("mean", ["inst_trust_epa_1", "inst_trust_nasa_1",
                                      "inst_trust_noaa_1", "inst_trust_uni_1",
                                      "inst_trust_gov_1"]),
    "belief_post":          ("copy", ["belief_post_1"]),
    "concern_mean":         ("mean", ["concern_1_1", "concern_2_1", "concern_3_1"]),
    "policy_general":       ("copy", ["policy_general_1"]),
    "policy_specific_mean": ("mean", [f"policy_specific_{i}_1" for i in range(1, 8)]),
    "behavior_mean":        ("mean", ["individual_meat_1", "individual_transport_1",
                                      "individual_solar_1", "individual_fly_1",
                                      "individual_talk_1", "individual_donate_1"]),
    "donation_ams":         ("copy", ["donation"]),
    "newsletter_signup":    ("pct_to_prop", ["newsletter"]),
}

# What the model is asked to produce for each item, and the range the collector
# enforces. Everything is a *cell mean*, so decimals are expected even where an
# individual answer is an integer.
ITEM_KIND = {
    "donation": ("dollars", 0.0, 10.0,
                 "mean donation in dollars out of the $10 bonus (0-10, 2 decimals)"),
    "newsletter": ("percent", 0.0, 100.0,
                   "percentage of the group who subscribed (0-100, 1 decimal)"),
}
DEFAULT_KIND = ("slider", 0.0, 100.0, "mean of the 0-100 slider (1 decimal)")

# Survey-flow facts the model needs to predict a post-treatment mean well.
# Taken from survey/questionnaire.txt; the section list below is read from it.
FLOW_NOTES = [
    "Respondents are US adults recruited to preregistered gender x age and "
    "gender x race quotas (N = 18,000 across the 17 conditions).",
    "Order: consent -> demographics -> pre-treatment measures (including a "
    "trust-in-climate-scientists item and a climate-belief item) -> ONE "
    "condition text -> the post-treatment outcomes below.",
    "Because a pre-treatment trust item is asked first, the post-treatment "
    "answers are anchored on it: a single text moves a group mean by a few "
    "points at most, not by tens of points.",
    "Sliders start empty and are integers 0-100. Only the endpoints are "
    "labelled. The donation item is a whole-dollar choice, $0-$10.",
    "The newsletter offer is a real, optional sign-up on an earlier page; "
    "real sign-up rates for such an offer are low.",
]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# ------------------------------------------------------------- stimuli -------
def read_stimuli(sst: dict) -> tuple[dict, list[str]]:
    """Split the CONDITION section of questionnaire.txt into 17 stimulus texts.

    The section holds 19 `### ` blocks: three control filler texts plus the 16
    intervention titles. The three fillers are joined into the single `control`
    condition, exactly as the survey assigns them (one at random per
    respondent).
    """
    q = QUESTIONNAIRE.read_text()
    try:
        sec = q.split("CONDITION  (each respondent sees exactly ONE")[1] \
               .split("POST-TREATMENT OUTCOMES")[0]
    except IndexError:
        sys.exit("01: could not find the CONDITION section in "
                 f"{QUESTIONNAIRE.relative_to(REPO)} — has the file changed?")

    blocks = re.split(r"^### ", sec, flags=re.M)[1:]
    stim: dict[str, str] = {}
    controls: list[tuple[str, str]] = []
    for b in blocks:
        title = b.split("\n")[0].strip()
        body = re.sub(r"\n=+\s*$", "", "\n".join(b.split("\n")[1:]).strip()).strip()
        if title.startswith("control"):
            controls.append((title, body))
        else:
            stim[title] = body

    if len(controls) != 3:
        sys.exit(f"01: expected 3 control filler texts, found {len(controls)}")
    stim["control"] = "\n\n".join(
        f"--- filler {i + 1} of 3: {t.split(':', 1)[-1].strip()} ---\n{b}"
        for i, (t, b) in enumerate(controls))

    # Every condition in the spec must have a text, and no text may be unknown.
    missing = [c for c in sst["conditions"] if c not in stim]
    extra = [c for c in stim if c not in sst["conditions"]]
    if missing or extra:
        sys.exit(f"01: stimulus titles do not match submission_spec.R.\n"
                 f"  missing: {missing}\n  unexpected: {extra}")

    notes = [
        "The control arm shows ONE of three neutral, off-topic filler texts, "
        "assigned at random; all three are reproduced under `control`.",
        "Each respondent read exactly one text, once, immediately before "
        "answering the outcomes.",
    ]
    return stim, notes


# --------------------------------------------------------------- items -------
def read_items(sst: dict) -> dict:
    """Pull question text and response options for the 44 items from codebook.csv."""
    book = {}
    with CODEBOOK.open(newline="") as fh:
        for row in csv.DictReader(fh):
            if row["qualtrics_label"] and row["qualtrics_label"] != "NA":
                book[row["qualtrics_label"]] = row

    wanted: list[str] = []
    for _rule, spec in OUTCOME_ITEMS.values():
        for entry in spec:
            wanted.extend(entry if isinstance(entry, list) else [entry])

    unknown = [i for i in wanted if i not in book]
    if unknown:
        sys.exit(f"01: items not found in codebook.csv: {unknown}")

    items = {}
    for name in wanted:
        row = book[name]
        kind, lo, hi, howto = ITEM_KIND.get(name, DEFAULT_KIND)
        items[name] = {
            "target_label": row["target_label"],
            "question": re.sub(r"\s+", " ", row["question_text"]).strip(),
            "scale": re.sub(r"\s+", " ", row["response_options"]).strip(),
            "kind": kind, "lo": lo, "hi": hi, "ask": howto,
        }

    # Every one of the 13 outcomes must be covered, and only those.
    if list(OUTCOME_ITEMS) != list(sst["outcomes"]):
        sys.exit("01: OUTCOME_ITEMS does not match sst$outcomes, in order:\n"
                 f"  here: {list(OUTCOME_ITEMS)}\n  spec: {sst['outcomes']}")
    return items


def main() -> int:
    sst = load_spec()
    stim, stim_notes = read_stimuli(sst)
    items = read_items(sst)

    outcomes = {}
    for name, (rule, spec) in OUTCOME_ITEMS.items():
        flat = [i for e in spec for i in (e if isinstance(e, list) else [e])]
        outcomes[name] = {"rule": rule, "items": flat,
                          "groups": spec if rule == "mean_of_means" else None,
                          "n_items": len(flat)}

    doc = {
        "built_by": "generation/scripts/01_extract_materials.py",
        "sources": {
            "stimuli": "survey/questionnaire.txt (CONDITION section)",
            "items": "codebook.csv (qualtrics_label, question_text, response_options)",
            "labels": "scripts/lib/submission_spec.R",
        },
        "licence_note": (
            "The stimulus texts adapt copyrighted material and are not covered "
            "by this repository's licence grant. They are reproduced here and in "
            "the task prompts from survey/questionnaire.txt, already in the deposit."),
        "flow_notes": FLOW_NOTES,
        "stimulus_notes": stim_notes,
        "n_items": len(items),
        "items": items,
        "outcomes": outcomes,
        "stimuli": {c: stim[c] for c in sst["conditions"]},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

    print(f"{len(stim)} stimulus texts, {len(items)} items -> "
          f"{len(outcomes)} scored outcomes")
    for name, o in outcomes.items():
        print(f"  {name:<24} {o['rule']:<14} {o['n_items']:>2} item(s)")
    words = sum(len(t.split()) for t in stim.values())
    print(f"\nstimuli: {words:,} words total "
          f"(the fixed prefix every task carries)")
    print(f"-> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
