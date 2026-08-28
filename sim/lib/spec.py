"""
The submission schema, in Python.

`scripts/lib/submission_spec.R` is the AUTHORITY. This module mirrors it so
the Python pipeline can check itself without calling R. `sim/01_persona_
characteristics.py` compares the two at run time and stops if they disagree,
so this file cannot drift in silence.

Read `codebook.csv` for the wording of each item and its response options.

**Written in ASD-STE100 Simplified Technical English.**
"""
from __future__ import annotations

# The 16 text interventions, exactly as `submission_spec.R` names them. The 4
# interactive arms of the parent megastudy are NOT in this benchmark.
INTERVENTIONS = [
    "Corporate reliance",
    "Social justice",
    "Interview Prof. Maraun",
    "Funding",
    "Oil industry misinformation",
    "Measurement & modeling (1)",
    "Former skeptics",
    "High public trust",
    "Measurement & modeling (2)",
    "Peer-review",
    "Scientist community helpers",
    "Consensus",
    "Portrait Prof. Cherry",
    "Model accuracy",
    "Interview Prof. Sebille",
    "Extreme weather predictions",
]
CONDITIONS = ["control"] + INTERVENTIONS

# The control condition holds THREE filler texts. One respondent reads ONE of
# them, and all three carry the single label `control`.
CONTROL_FILLERS = ["neckties", "baseball", "dances"]

# The six scored moderators, and their EXACT level strings. A string that is
# not on this list is a hard error in `scripts/clean.R`, on purpose: a near
# miss would drop the respondent from every subgroup analysis in silence.
MODERATORS: dict[str, list[str]] = {
    "gender": ["Male", "Female", "Other"],
    "age_band": ["18-29", "30-44", "45-59", "60+"],
    "race": ["White / Caucasian", "Black / African American",
             "Hispanic / Latino", "Asian / Asian American", "Other"],
    "education": ["Less than high school",
                  "High school diploma / GED",
                  "Some college or Associate's degree",
                  "Bachelor's degree",
                  "Master's degree / Professional degree",
                  "Doctorate degree / Ph.D."],
    "income": ["Less than $30,000", "$30,000 to $55,999",
               "$56,000 to $99,999", "$100,000 to $167,999",
               "$168,000 or more"],
    "party": ["Republican", "Democrat", "Independent", "Other"],
}

# The sample-size floor. It is the size of the human half we are scored
# against, from the benchmark's precision requirement.
N_PER_INTERVENTION = 500
N_CONTROL = 1000
N_TOTAL = N_PER_INTERVENTION * len(INTERVENTIONS) + N_CONTROL   # 9,000

# `clean.R` computes the age from the birth year. So the raw export carries
# `year_birth`, not `age`.
SURVEY_YEAR = 2026
AGE_BREAKS = [(18, 29, "18-29"), (30, 44, "30-44"),
              (45, 59, "45-59"), (60, 200, "60+")]

# ---------------------------------------------------------------------------
# The 44 answer items, under the RAW survey column names. The raw export uses
# these names; `scripts/clean.R` renames them and builds the composites.
# ---------------------------------------------------------------------------
TRUST_ITEMS = [                      # the primary outcome, 4 dimensions x 3
    "trust_competent_1", "trust_intelligent_1", "trust_qualified_1",
    "trust_honest_1", "trust_ethical_1", "trust_sincere_1",
    "trust_concerned_1", "trust_improve_1", "trust_considerate_1",
    "trust_feedback_1", "trust_transparent_1", "trust_attention_1",
]
INST_TRUST_ITEMS = ["inst_trust_epa_1", "inst_trust_nasa_1",
                    "inst_trust_noaa_1", "inst_trust_uni_1",
                    "inst_trust_gov_1"]
POLICY_ROLE_ITEMS = [f"policy_{i}_1" for i in range(1, 5)]
CONCERN_ITEMS = [f"concern_{i}_1" for i in range(1, 4)]
POLICY_SPECIFIC_ITEMS = [f"policy_specific_{i}_1" for i in range(1, 8)]
BEHAVIOR_ITEMS = ["individual_meat_1", "individual_transport_1",
                  "individual_solar_1", "individual_fly_1",
                  "individual_talk_1", "individual_donate_1"]

# Everything on a 0-100 slider.
SLIDER_ITEMS = (TRUST_ITEMS + ["trust_post_1", "distrust_1", "funding_5"]
                + POLICY_ROLE_ITEMS + INST_TRUST_ITEMS + ["belief_post_1"]
                + CONCERN_ITEMS + ["policy_general_1"]
                + POLICY_SPECIFIC_ITEMS + BEHAVIOR_ITEMS)
# The two that are NOT sliders. Both are real behaviour in the human survey.
DONATION_ITEM = "donation"            # 0 to 10 whole dollars
NEWSLETTER_ITEM = "newsletter"        # 0 or 1
ALL_ITEMS = SLIDER_ITEMS + [DONATION_ITEM, NEWSLETTER_ITEM]      # 44

# The identifying columns of the raw export, before the 44 items.
RAW_ID_COLUMNS = ["profile_id", "condition", "gender", "year_birth", "race",
                  "education", "income", "party"]
RAW_COLUMNS = RAW_ID_COLUMNS + ALL_ITEMS

# ---------------------------------------------------------------------------
# TRAPS. `scripts/clean.R` does each of these. The pipeline must NOT.
# ---------------------------------------------------------------------------
TRAPS = {
    "funding_5": (
        "REVERSE CODED IN CLEANING. Answer on the survey's own scale: "
        "0 = far too little, 50 = about right, 100 = far too much. "
        "`clean.R` writes funding_perceptions = 100 - funding_5. "
        "Do not flip it here."),
    "year_birth": (
        "Emit the BIRTH YEAR, not the age. `clean.R` computes "
        f"age = {SURVEY_YEAR} - year_birth and then cuts the band."),
    "trust_multidimensional": (
        "It is the mean of the FOUR DIMENSION means, not the mean of the 12 "
        "items. `clean.R` builds it. Never write it here."),
    "newsletter": (
        "0 or 1 for one person at Tier 1. It becomes a 0-1 PROPORTION at "
        "Tier 2. `clean.R` handles the Tier-1 form."),
}


def age_band(age: int) -> str:
    """Give the band of one age, with the same cuts as `clean.R`."""
    for low, high, label in AGE_BREAKS:
        if low <= age <= high:
            return label
    raise ValueError(f"age {age} is outside 18 to 200")
