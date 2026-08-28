"""
The stage-2 writer prompt, and the gates that check what comes back.

The design is ported from the `modelbench` v10 arm, which measured it. Two
findings from there set the shape:

  * **Short wins.** A short description of a GIVEN person reached 99.8 per
    cent fact coverage. A long one that invented extra detail reached 86.0.
    So the writer is asked to describe, never to invent.
  * **No opinions.** *Demographic predictability* is a Tier-1 scored analysis
    that compares the R2 of an outcome on one moderator between the humans
    and us. A persona that states an attitude inflates it, and a higher R2 is
    read as stereotyping. So the writer may not give the person a view.

The fact ORDER is shuffled for each persona, and the voice is drawn. Both
stop one sentence pattern from repeating over 9,000 texts.
"""
from __future__ import annotations

import random
import re

SYSTEM = ("You write short, plain descriptions of one person. You use ONLY "
          "the facts you are given. You never invent a fact, a name, a job, "
          "an opinion or an event. You never say what the person thinks "
          "about any topic.")

VOICE_RULE = {
    "second_person": 'Write in the second person. Refer to the person as "You".',
    "third_person": 'Write in the third person. Use one pronoun throughout.',
}
VOICES = tuple(VOICE_RULE)

USER = """Write a short description of one person.

{facts}

Rules:
- Write 4 to 6 sentences of plain prose.
- {voice_rule}
- Use every fact. Add nothing.
- Never write "survey", "study" or "research".
- Do not give the person a name, a job, a hobby, or an opinion.
- Do not say what the person believes about climate, science or politics
  beyond the facts above.
- Do not add a closing sentence about the person's background or diversity.

Write only the description."""

# Words the text must not contain. The first three name the instrument; the
# rest are the openers a writer reaches for when it starts inventing.
LEAK_WORDS = ("survey", "study", "research", "questionnaire", "respondent",
              "participant", "profile", "persona")

# A fact is CHECKABLE when it puts a distinctive token in the text. A negative
# fact ("religion: none") has no such token, so it is counted as unverifiable
# and never as missing.
EDUCATION_TOKEN = {
    "Less than high school": ("did not finish high school",
                              "less than high", "less than a high"),
    "High school diploma / GED": ("high school",),
    "Some college or Associate's degree": ("college", "associate"),
    "Bachelor's degree": ("bachelor",),
    "Master's degree / Professional degree": ("master", "professional"),
    "Doctorate degree / Ph.D.": ("doctorate", "ph.d", "phd", "doctoral"),
}
INCOME_TOKEN = {
    "Less than $30,000": ("30,000", "30000"),
    "$30,000 to $55,999": ("55,999", "56,000", "30,000"),
    "$56,000 to $99,999": ("99,999", "56,000", "100,000"),
    "$100,000 to $167,999": ("167,999", "100,000", "168,000"),
    "$168,000 or more": ("168,000", "168000"),
}
RACE_TOKEN = {
    "White / Caucasian": ("white", "caucasian"),
    "Black / African American": ("black", "african"),
    "Hispanic / Latino": ("hispanic", "latino", "latina", "latinx"),
    "Asian / Asian American": ("asian",),
    "Other": (),                      # no distinctive token
}
PARTY_TOKEN = {"Republican": ("republican",), "Democrat": ("democrat",),
               "Independent": ("independent",), "Other": ()}
# The GSS `srcbelt` labels are its own jargon — "12 largest smsas" is a
# Standard Metropolitan Statistical Area. The writer must not copy that into a
# description of a person, so each level becomes plain English.
# A writer that spells "two-person household" is writing better English than
# one that writes "2". The gate accepts either, so good prose is not punished.
NUMBER_WORD = {1: "alone", 2: "two", 3: "three", 4: "four", 5: "five",
               6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
               11: "eleven", 14: "fourteen"}

URBANICITY = {
    "central city of 12 largest smsas": "in one of the largest US cities",
    "central city of the remainder of the 100 largest smsas":
        "in a mid-sized US city",
    "suburbs of 12 largest smsas": "in the suburbs of a very large US city",
    "suburbs of the remaining 100 largest smsas":
        "in the suburbs of a mid-sized US city",
    "other urban (counties having towns of 10,000 or more)":
        "in a small town",
    "other rural (counties having no towns of 10,000 or more)":
        "in a rural area",
}

TRUST_PHRASE = {"a great deal": "a great deal of confidence in the scientific "
                                "community",
                "only some": "only some confidence in the scientific community",
                "hardly any": "hardly any confidence in the scientific "
                              "community"}


def fact_lines(row) -> dict[str, str]:
    """The fact bullets for one persona, keyed by the gate that checks them."""
    out = {
        "age": f"{int(row.age)} years old",
        "gender": f"gender: {row.gender.lower()}",
        "race": f"ethnicity: {row.race}",
        "education": f"highest education: {row.education}",
        "income": f"household income: {row.income}",
        "household_size": ("lives alone" if int(row.household_size) == 1
                           else f"lives in a household of "
                                f"{int(row.household_size)} people"),
        "social_class": f"describes their social class as {row.social_class}",
        "region": f"lives in the {row.region} of the United States",
        "party": f"politically: {row.party_detail or row.party}",
        "ideology": f"political views: {row.ideology}",
    }
    place = URBANICITY.get(str(row.urbanicity or "").strip())
    if place:
        out["urbanicity"] = f"lives {place}"
    religion = str(row.religion or "").strip().lower()
    out["religion"] = ("has no religion" if religion in ("none", "na", "")
                       else f"religion: {row.religion}")
    if str(row.religiosity or "").strip() not in ("NA", "", "nan"):
        out["religiosity"] = f"strength of religion: {row.religiosity}"
    if str(row.born_again or "").strip().lower() == "yes":
        out["born_again"] = "describes themself as born-again or evangelical"
    phrase = TRUST_PHRASE.get(str(row.trust_science_prior or "").strip().lower())
    if phrase:
        out["trust_science_prior"] = f"has {phrase}"
    return out


def build_prompt(row, rng: random.Random) -> tuple[str, str, list[str]]:
    """Give the user prompt, the voice, and the fact order for one persona."""
    lines = fact_lines(row)
    order = list(lines)
    rng.shuffle(order)
    voice = rng.choice(VOICES)
    facts = "\n".join(f"- {lines[k]}" for k in order)
    return (USER.format(facts=facts, voice_rule=VOICE_RULE[voice]),
            voice, order)


def tokens_for(key: str, row) -> tuple[str, ...]:
    """The lower-case tokens that prove one fact reached the text."""
    if key == "age":
        return (str(int(row.age)),)
    if key == "gender":
        return () if row.gender == "Other" else (row.gender.lower(),)
    if key == "race":
        return RACE_TOKEN.get(row.race, ())
    if key == "education":
        return EDUCATION_TOKEN.get(row.education, ())
    if key == "income":
        return INCOME_TOKEN.get(row.income, ())
    if key == "party":
        return PARTY_TOKEN.get(row.party, ())
    if key == "household_size":
        size = int(row.household_size)
        word = NUMBER_WORD.get(size)
        return (str(size), word) if word else (str(size),)
    if key == "social_class":
        return (str(row.social_class).split()[0].lower(),)
    if key == "religion":
        religion = str(row.religion or "").strip().lower()
        return () if religion in ("none", "na", "") else (religion.split(",")[0],)
    if key == "born_again":
        return ("born-again", "born again", "evangelical")
    if key == "trust_science_prior":
        return ("confidence",)
    if key == "ideology":
        word = str(row.ideology).split(",")[0].split()[-1].lower()
        return (word,) if word in ("liberal", "conservative", "moderate") else ()
    return ()                                   # region, urbanicity, religiosity


def check(text: str, row, low: int = 45, high: int = 160) -> dict:
    """Run every gate on one written persona."""
    body = text.lower()
    keys = list(fact_lines(row))
    checkable = {k: tokens_for(k, row) for k in keys}
    checkable = {k: v for k, v in checkable.items() if v}
    missing = [k for k, toks in checkable.items()
               if not any(t in body for t in toks)]
    leaks = [w for w in LEAK_WORDS if re.search(rf"\b{w}", body)]
    words = len(text.split())
    return {
        "n_facts": len(keys), "n_checkable": len(checkable),
        "n_missing": len(missing), "missing": "|".join(missing),
        "leaks": "|".join(leaks), "n_words": words,
        "ascii_ok": text.isascii(),
        "length_ok": low <= words <= high,
        "ok": (not missing) and (not leaks) and text.isascii()
              and low <= words <= high,
    }
