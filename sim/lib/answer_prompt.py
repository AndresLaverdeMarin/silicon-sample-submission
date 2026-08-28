"""
The stage-3 answering prompt, and the template persona it can use instead.

The prompt format is the paper's own item mode, as `modelbench` implements it:
one prompt asks ONE question, and the model completes one number after an open
quote. It needs no chat template, so a base model can run it, and the answer is
about three tokens.

Two persona styles, so the choice can be measured and not argued:

    prose      the LLM-written text from stage 2
    template   a fixed sentence built here, with no model involved

`template` is the cheaper option and it is what the paper itself used. It has
one property worth measuring first: it is deterministic, so two respondents
with the same attributes read the SAME text. In our 9,000 that is 71.6 per
cent of people, against 4,591 distinct attribute vectors.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- persona --
GENDER_NOUN = {"Male": "man", "Female": "woman", "Other": "person"}
ARTICLE = re.compile(r"^[aeiou]", re.I)


def template_persona(row) -> str:
    """A fixed-template persona. No model writes this."""
    noun = GENDER_NOUN.get(row.gender, "person")
    race = "" if row.race == "Other" else f" {row.race}"
    parts = [f"You are a {int(row.age)}-year-old{race} {noun} living in the "
             f"{row.region} of the United States."]
    parts.append(f"Your highest level of education is: {row.education}. "
                 f"Your total yearly household income is {row.income}.")
    home = ("You live alone" if int(row.household_size) == 1
            else f"You live in a household of {int(row.household_size)} people")
    parts.append(f"{home}, and you describe your social class as "
                 f"{row.social_class}.")
    party = str(row.party_detail or row.party)
    parts.append(f"Politically you think of yourself as {party}, and your "
                 f"political views are {row.ideology}.")
    religion = str(row.religion or "").strip().lower()
    if religion in ("none", "na", ""):
        parts.append("You are not religious.")
    else:
        line = f"Your religion is {row.religion}"
        if str(row.religiosity or "").strip() not in ("NA", "", "nan"):
            line += f", and you consider yourself {row.religiosity} in it"
        parts.append(line + ".")
        if str(row.born_again or "").strip().lower() == "yes":
            parts.append("You describe yourself as a born-again or "
                         "evangelical Christian.")
    trust = str(row.trust_science_prior or "").strip().lower()
    if trust in ("a great deal", "only some", "hardly any"):
        parts.append(f"Before this survey, you would have said you have "
                     f"{trust} confidence in the scientific community.")
    return " ".join(parts)


# ------------------------------------------------------------------ items --
ANCHOR = re.compile(r"0\s*=\s*(.+?)\s*(?:…|\.\.\.|…)\s*100\s*=\s*(.+?)$")


def scale_of(item: str, options: str) -> dict:
    """Read one item's answer scale out of its codebook response options."""
    if item == "donation":
        return {"kind": "dollars", "low": 0, "high": 10,
                "ask": "Please choose a whole number of dollars from 0 to 10"}
    if item == "newsletter":
        return {"kind": "binary", "low": 0, "high": 1,
                "ask": "Please answer 1 for yes or 0 for no"}
    match = ANCHOR.search(options.replace("…", "…"))
    if not match:
        raise SystemExit(f"cannot read a 0-100 scale for {item!r} from "
                         f"{options!r}")
    low, high = match.group(1).strip(), match.group(2).strip()
    return {"kind": "slider", "low": 0, "high": 100, "low_label": low,
            "high_label": high,
            "ask": f"Please choose a number from 0 ({low}) to 100 ({high})"}


def build_prompt(persona: str, stimulus: str, question: str,
                 scale: dict) -> str:
    """One prompt, one question, one number after the open quote."""
    return (f"{persona}\n\n"
            f"The first page of the survey says:\n"
            f"> {stimulus}\n\n"
            f"The next page of the survey says:\n"
            f"> {question}\n"
            f"> {scale['ask']}\n\n"
            f"You choose: '")


NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def parse(text: str, scale: dict) -> float | None:
    """The first number in the completion, if it is inside the scale."""
    match = NUMBER.search(text)
    if not match:
        return None
    value = float(match.group())
    if not (scale["low"] <= value <= scale["high"]):
        return None
    return value
