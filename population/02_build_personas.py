#!/usr/bin/env python3
"""
Step 2 — build the synthetic respondent pool.

Design
------
The study enforces *Census cross-quotas* on gender x age and gender x race, and
randomises respondents to 17 conditions. Two things therefore have to be true of
our pool, and neither is achieved by sampling each variable independently:

  1. The marginal and cross-quota distributions must match Census (step 1).
  2. The *joint* structure of the non-quota variables must be realistic —
     education correlates with income, party with ideology and religion, and so
     on. Independent draws would produce demographically impossible people and
     would hand the simulation an easy, artificial signal.

So we use real survey microdata as the source of joint structure and rake it to
the quota targets:

  base pool   population/gss_profiles.csv — 9,000 GSS respondents (2018-2024).
              This is the organizers' own v1 clone pool, NOT a benchmark
              resource: see "Where this pool comes from" in population/README.md
              and declare it in registration item D.1. It carries the GSS
              post-stratification weights (wtssps) and the full covariate joint
              distribution.
  targets     population/census_quota_targets.json — gender / age_band / race
              and the two cross-quotas come from preregistration Table 3
              (N = 18,000), recovered by 01c_quotas_18000.py; education and
              income come from Census CPS 2024 (step 01b in the sibling
              project).
  method      iterative proportional fitting (raking) of wtssps to the Census
              gender / age-band / race margins, then quota sampling *within each
              condition* so every arm is separately balanced to the quotas

Conditions are quota-sampled independently per arm, which mirrors what
randomisation achieves in the real study and removes demographic composition as
a confound in the treatment effects.

Outputs (this folder, or --out DIR):
  personas.csv        one row per synthetic respondent, all 9,000
  personas.jsonl      same, plus a rendered natural-language persona description
  quota_report.txt    realised vs target quota check

The two large outputs are build artifacts: `quota_report.txt` is kept in this
folder as the deposited quota evidence, and the Tier-2 pipeline writes the
personas themselves under generation/build/population/ (see generation/README.md).

Usage:
  python3 population/02_build_personas.py [--out DIR]
"""
from __future__ import annotations
import argparse, csv, json, math, random, re
from collections import Counter, defaultdict
from pathlib import Path

random.seed(20260807)                      # deterministic; recorded in the registration

HERE = Path(__file__).resolve().parent      # population/
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=str(HERE),
                help="output directory (default: population/)")
args = ap.parse_args()

GSS = HERE / "gss_profiles.csv"
TARGETS = json.loads((HERE / "census_quota_targets.json").read_text())
OUT = Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- design ----
INTERVENTIONS = [
    "Corporate reliance", "Social justice", "Interview Prof. Maraun", "Funding",
    "Oil industry misinformation", "Measurement & modeling (1)", "Former skeptics",
    "High public trust", "Measurement & modeling (2)", "Peer-review",
    "Scientist community helpers", "Consensus", "Portrait Prof. Cherry",
    "Model accuracy", "Interview Prof. Sebille", "Extreme weather predictions",
]
N_PER_INTERVENTION = 500
N_CONTROL = 1_000
CONDITIONS = {"control": N_CONTROL, **{i: N_PER_INTERVENTION for i in INTERVENTIONS}}

# Study moderator levels (scripts/lib/submission_spec.R) — these strings are
# what the scorer joins on, so they must match exactly.
GENDER = ["Male", "Female", "Other"]
AGE_BANDS = ["18-29", "30-44", "45-59", "60+"]
RACE = ["White / Caucasian", "Black / African American", "Hispanic / Latino",
        "Asian / Asian American", "Other"]
EDUCATION = ["Less than high school", "High school diploma / GED",
             "Some college or Associate's degree", "Bachelor's degree",
             "Master's degree / Professional degree", "Doctorate degree / Ph.D."]
INCOME = ["Less than $30,000", "$30,000 to $55,999", "$56,000 to $99,999",
          "$100,000 to $167,999", "$168,000 or more"]
PARTY = ["Republican", "Democrat", "Independent", "Other"]

# Share of adults who report a gender other than male/female. The Census
# quota dimensions are male/female only, so this group sits outside the
# cross-quota and is allocated proportionally. ~0.6% is consistent with recent
# large US probability samples; the study's own instrument offers the option.
P_GENDER_OTHER = 0.006


# ------------------------------------------------------ GSS -> study codes ---
def map_race(racecen1, hispanic):
    if hispanic and hispanic.strip().lower() not in ("not hispanic", "na", ""):
        return "Hispanic / Latino"
    r = (racecen1 or "").strip().lower()
    if r == "hispanic":
        return "Hispanic / Latino"
    if r == "white":
        return "White / Caucasian"
    if r.startswith("black"):
        return "Black / African American"
    if r == "asian":
        return "Asian / Asian American"
    return "Other"


SPLIT = TARGETS["gss_conditional_splits"]


def map_education(degree, rng):
    """GSS `degree` is coarser than the study's 6 levels in two places, so those
    two categories are split using Census CPS 2024 conditional shares
    (step 01b): GSS "high school" bundles HS-graduates with some-college-no-
    degree, and GSS "graduate" bundles master's/professional with doctorates."""
    d = (degree or "").strip().lower()
    if d == "less than high school":
        return "Less than high school"
    if d == "high school":
        return ("High school diploma / GED"
                if rng.random() < SPLIT["high_school_to_hs_grad"]
                else "Some college or Associate's degree")
    if d.startswith("associate"):
        return "Some college or Associate's degree"
    if d.startswith("bachelor"):
        return "Bachelor's degree"
    if d == "graduate":
        return ("Master's degree / Professional degree"
                if rng.random() < SPLIT["graduate_to_masters_prof"]
                else "Doctorate degree / Ph.D.")
    return "High school diploma / GED"


_MONEY = re.compile(r"\$?([\d,]+)")


def map_income(income16, rng):
    s = (income16 or "").strip().lower()
    if not s or s in ("na", "refused", "don't know"):
        return None
    if "under $1,000" in s or "less than $1,000" in s:
        return "Less than $30,000"
    if "or over" in s or "or more" in s:
        lo = int(_MONEY.search(s).group(1).replace(",", ""))
        return ("$168,000 or more" if lo >= 168_000 else
                "$100,000 to $167,999" if lo >= 100_000 else
                "$56,000 to $99,999" if lo >= 56_000 else
                "$30,000 to $55,999" if lo >= 30_000 else "Less than $30,000")
    nums = [int(x.replace(",", "")) for x in _MONEY.findall(s)]
    if not nums:
        return None
    mid = sum(nums[:2]) / 2 if len(nums) >= 2 else nums[0]
    return ("Less than $30,000" if mid < 30_000 else
            "$30,000 to $55,999" if mid < 56_000 else
            "$56,000 to $99,999" if mid < 100_000 else
            "$100,000 to $167,999" if mid < 168_000 else "$168,000 or more")


def map_party(partyid):
    p = (partyid or "").strip().lower()
    if "republican" in p and "close to" not in p:
        return "Republican"
    if "democrat" in p and "close to" not in p:
        return "Democrat"
    if "independent" in p:
        return "Independent"      # incl. leaners, matching the survey's 4 options
    if "other" in p:
        return "Other"
    return "Independent"


def age_band(age):
    a = int(age)
    return ("18-29" if a <= 29 else "30-44" if a <= 44 else
            "45-59" if a <= 59 else "60+")


# ------------------------------------------------------------ load pool ------
rng = random.Random(20260807)
raw = list(csv.DictReader(open(GSS)))
pool = []
for r in raw:
    try:
        age = int(r["age"])
    except (ValueError, TypeError):
        continue
    if age < 18:
        continue
    inc = map_income(r["income16"], rng)
    if inc is None:
        continue                                   # income is a scored moderator
    pool.append({
        "gender": "Male" if r["sex"] == "male" else "Female",
        "age": age,
        "age_band": age_band(age),
        "race": map_race(r["racecen1"], r["hispanic"]),
        "education": map_education(r["degree"], rng),
        "income": inc,
        "party": map_party(r["partyid"]),
        "ideology": (r["polviews"] or "moderate, middle of the road").strip(),
        "household_size": r["hompop"] if r["hompop"] not in ("NA", "") else "2",
        "social_class": (r["class"] or "middle class").strip(),
        "region": (r["region"] or "").strip(),
        "urbanicity": (r["srcbelt"] or "").strip(),
        "religion": (r["relig"] or "none").strip(),
        "religiosity": (r["reliten"] or "NA").strip(),
        "born_again": (r["reborn"] or "NA").strip(),
        "trust_science_prior": (r["consci"] or "NA").strip(),
        "w": float(r["wtssps"]) if r["wtssps"] not in ("NA", "") else 1.0,
    })
print(f"GSS base pool: {len(pool):,} usable records (of {len(raw):,})")

# ------------------------------------------------------------- raking -------
# IPF the GSS weights onto the Census margins for the three quota dimensions.
# Quota dimensions (Census PEP) plus the two scored moderators whose GSS
# marginals are known to be wrong (Census CPS / P60 — see step 01b).
DIMS = [("gender", {"Male": TARGETS["gender"]["Male"],
                    "Female": TARGETS["gender"]["Female"]}),
        ("age_band", TARGETS["age_band"]),
        ("race", TARGETS["race"]),
        ("education", TARGETS["education"]),
        ("income", TARGETS["income"])]

for it in range(60):
    maxdev = 0.0
    for dim, target in DIMS:
        tot = sum(p["w"] for p in pool)
        cur = defaultdict(float)
        for p in pool:
            cur[p[dim]] += p["w"] / tot
        for p in pool:
            t = target.get(p[dim])
            if t and cur[p[dim]] > 0:
                p["w"] *= t / cur[p[dim]]
        maxdev = max(maxdev, max(abs(cur.get(k, 0) - v) for k, v in target.items()))
    if maxdev < 1e-6:
        break
print(f"Raking converged after {it+1} iterations (max margin deviation {maxdev:.2e})")

# ------------------------------------------------- quota sampling per arm ----
# Target cell counts come from the *cross*-quotas: gender x age and gender x
# race. We sample each condition independently to the joint (age_band, race,
# gender) implied by those two cross-quotas.
def cell_targets(n):
    """Expected count per (gender, age_band, race) cell under the Census
    cross-quotas, treating age and race as conditionally independent given
    gender — which is exactly what enforcing two separate cross-quotas does."""
    t = {}
    n_mf = n * (1 - P_GENDER_OTHER)
    for g in ("Male", "Female"):
        for ab, ash in TARGETS["age_band"].items():
            g_ab = TARGETS["age_band_by_gender"][ab][g]
            for rc, rsh in TARGETS["race"].items():
                g_rc = TARGETS["race_by_gender"][rc][g]
                # P(g, ab) * P(rc | g)
                p_g = TARGETS["gender"][g]
                t[(g, ab, rc)] = n_mf * (ash * g_ab) * (rsh * g_rc / p_g)
    return t


by_cell = defaultdict(list)
for p in pool:
    by_cell[(p["gender"], p["age_band"], p["race"])].append(p)


def draw(cell, k):
    cands = by_cell.get(cell)
    if not cands:                                  # backfill: relax race, then age
        g, ab, rc = cell
        cands = [p for p in pool if p["gender"] == g and p["age_band"] == ab] \
             or [p for p in pool if p["gender"] == g] or pool
    ws = [p["w"] for p in cands]
    return rng.choices(cands, weights=ws, k=k)


personas, pid = [], 0
for cond, n in CONDITIONS.items():
    tgt = cell_targets(n)
    # Largest-remainder allocation so the cell counts sum exactly to n.
    base = {c: int(v) for c, v in tgt.items()}
    rem = sorted(tgt.items(), key=lambda kv: -(kv[1] - int(kv[1])))
    short = n - round(n * P_GENDER_OTHER) - sum(base.values())
    for i in range(max(0, short)):
        base[rem[i % len(rem)][0]] += 1
    picked = []
    for cell, k in base.items():
        if k:
            picked.extend(draw(cell, k))
    while len(picked) < n:                          # the "Other" gender allocation
        p = dict(rng.choices(pool, weights=[q["w"] for q in pool], k=1)[0])
        p["gender"] = "Other"
        picked.append(p)
    rng.shuffle(picked)
    for p in picked[:n]:
        pid += 1
        personas.append({"profile_id": f"P{pid:05d}", "condition": cond,
                         **{k: v for k, v in p.items() if k != "w"}})

print(f"Sampled {len(personas):,} personas across {len(CONDITIONS)} conditions "
      f"({N_CONTROL:,} control + {len(INTERVENTIONS)}x{N_PER_INTERVENTION})")

# --------------------------------------------------- persona narrative ------
IDEO = {"extremely liberal": "extremely liberal", "liberal": "liberal",
        "slightly liberal": "slightly liberal",
        "moderate, middle of the road": "politically moderate",
        "slightly conservative": "slightly conservative",
        "conservative": "conservative", "extremely conservative": "extremely conservative"}
TRUST = {"a great deal": "a great deal of confidence in the scientific community",
         "only some": "only some confidence in the scientific community",
         "hardly any": "hardly any confidence in the scientific community"}


def narrative(p):
    bits = [f"You are a {p['age']}-year-old"]
    if p["gender"] != "Other":
        bits.append(p["gender"].lower())
    else:
        bits.append("person who does not identify as male or female")
    bits.append(f"American who identifies as {p['race']}.")
    s = " ".join(bits)
    s += (f" Your highest level of education is: {p['education']}."
          f" Your total yearly household income is {p['income']}."
          f" You live in a household of {p['household_size']}"
          f"{' person' if str(p['household_size']) == '1' else ' people'}"
          f" in the {p['region']} of the United States.")
    if p["urbanicity"] and p["urbanicity"] != "NA":
        s += f" You live in {p['urbanicity']}."
    s += f" You describe your social class as {p['social_class']}."
    s += f" Politically you think of yourself as {p['party']}"
    ideo = IDEO.get(p["ideology"].lower())
    s += f" and {ideo}." if ideo else "."
    if p["religion"] and p["religion"].lower() not in ("none", "na"):
        s += f" Your religion is {p['religion']}"
        if p["religiosity"] not in ("NA", ""):
            s += f", and you consider yourself {p['religiosity']} in it"
        s += "."
        if p["born_again"] == "yes":
            s += " You describe yourself as a born-again or evangelical Christian."
    else:
        s += " You are not religious."
    t = TRUST.get(p["trust_science_prior"].lower())
    if t:
        s += f" Before this survey, you would have said you have {t}."
    return s


# ------------------------------------------------------------- outputs ------
cols = ["profile_id", "condition", "gender", "age", "age_band", "race", "education",
        "income", "party", "ideology", "household_size", "social_class", "region",
        "urbanicity", "religion", "religiosity", "born_again", "trust_science_prior"]
with open(OUT / "personas.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(personas)

with open(OUT / "personas.jsonl", "w") as f:
    for p in personas:
        f.write(json.dumps({**{k: p[k] for k in cols}, "persona": narrative(p)}) + "\n")

# ---------------------------------------------------------- quota report ----
lines = ["REALISED vs TARGET QUOTAS", "=" * 62,
         f"n = {len(personas):,}   (Census PEP 2024, 18+; seed 20260807)", ""]
for dim, target in [("gender", TARGETS["gender"]), ("age_band", TARGETS["age_band"]),
                    ("race", TARGETS["race"])]:
    c = Counter(p[dim] for p in personas)
    lines.append(f"{dim}")
    lines.append(f"  {'level':<28} {'target':>8} {'realised':>9} {'diff':>7}")
    for k in sorted(target, key=lambda x: -target[x]):
        got = c[k] / len(personas)
        lines.append(f"  {k:<28} {target[k]:>7.1%} {got:>8.1%} {got-target[k]:>+7.2%}")
    if dim == "gender":
        lines.append(f"  {'Other (outside quota)':<28} {P_GENDER_OTHER:>7.1%} "
                     f"{c['Other']/len(personas):>8.1%}")
    lines.append("")
lines.append("Non-quota moderators (from raked GSS joint distribution):")
for dim in ("education", "income", "party"):
    c = Counter(p[dim] for p in personas)
    lines.append(f"  {dim}")
    for k, v in c.most_common():
        lines.append(f"    {k:<40} {v/len(personas):>6.1%}")
lines.append("")
lines.append("Per-condition balance (max deviation of any quota level, pp):")
for cond in CONDITIONS:
    sub = [p for p in personas if p["condition"] == cond]
    dev = max(abs(Counter(p[d] for p in sub)[k] / len(sub) - t[k])
              for d, t in [("age_band", TARGETS["age_band"]), ("race", TARGETS["race"])]
              for k in t)
    lines.append(f"  {cond:<32} n={len(sub):>5}   max dev {dev*100:>5.2f} pp")
(OUT / "quota_report.txt").write_text("\n".join(lines))
print("\n".join(lines[:34]))
print(f"\n-> {OUT}/personas.csv, personas.jsonl, quota_report.txt")
print("\nExample persona:")
print(" ", narrative(personas[0])[:400])
