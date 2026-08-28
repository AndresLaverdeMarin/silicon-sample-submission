# How the synthetic population is made

This folder documents how we build the 9,000 synthetic respondents. The
benchmark asks for this in `registration.md`, section D (Persona construction)
and section K.1 (Code & materials).

The size is the benchmark's own rule, not ours: 500 for each intervention and
1,000 in control. See `../README.md` and `../FAQ.md`, and `sim/lib/spec.py`
for the numbers the pipeline enforces.

## The method

| File | What it is |
|---|---|
| `gss_profiles.csv` | The base pool. 9,000 GSS respondents. See below. |
| `quotas_18000.csv` | The quota target, as published in the preregistration. |
| `census_quota_targets.json` | The target the raking uses. Gender, age band, race and the two cross-quotas come from `quotas_18000.csv`; education and income come from Census CPS 2024. |
| `01c_quotas_18000.py` | Recovers the target from the preregistration page. See "The quota source" below. |
| `02_build_personas.py` | Rakes the GSS pool to the target, then quota-samples 9,000 personas. |
| `quota_report.txt` | Realised against target, for every level. |

**The base pool is real people.** We use 9,000 General Social Survey (GSS)
respondents with their post-stratification weights (`wtssps`). The pool is
`gss_profiles.csv` in this folder.

| Property | Value |
|---|---|
| Rows | 9,000 |
| GSS waves | **2018 (1,867), 2021 (2,687), 2022 (2,214), 2024 (2,232)** |
| Weight column | `wtssps` |
| Columns | GSS variable names: `age`, `sex`, `racecen1`, `hispanic`, `degree`, `income16`, `hompop`, `class`, `region`, `srcbelt`, `partyid`, `polviews`, `relig`, `reborn`, `reliten`, `consci` |

**Where this pool comes from. Read this before you cite it.**

**The benchmark ships no participant pool.** Its FAQ says: *"The benchmark ships
the survey, the codebook, the intervention texts, and a validator, but no
profiles and never any human outcome data."* Registration item D.1 says the same:
*"The benchmark ships no participant pool; report how you built yours."*

This file is `clone_profiles/profiles.csv` from the organizers' **own research
repository**. It is the pool they built for their **own v1 simulation**, not a
resource given to teams. Their v1 preregistration describes it:

> *"Clone profiles were constructed by drawing 9,000 individuals from four recent
> waves of the General Social Survey (GSS; 2018, 2021, 2022, 2024). Within-year
> normalized sampling weights were applied so that each wave contributes equal
> sampling probability to the pool, while preserving within-year relative
> weights."*

Using GSS is allowed. The FAQ names it: *"You construct your own synthetic
respondents from any source (a public survey such as GSS, ANES, or the
Census...)"*. But **we did not draw this pool ourselves** — we reuse the
organizers' draw. Say that in registration item D.1. Do not write that the
benchmark shipped it.

The weights are close to 1 in each wave (means 1.02 to 1.15), which matches the
within-year normalisation the quotation describes. They are not raw GSS weights.

**Why not draw each variable on its own?** Independent draws make people who do
not exist, such as a 19-year-old with a doctorate. They also make the moderator
variables independent, which they are not in real life. That would give the
simulation an easy and false signal.

So the GSS gives the **joint** structure (education x income x party x religion
x region x class). Iterative proportional fitting (raking) then moves it onto
the quota **margins**.

**Conditions are quota-sampled one arm at a time.** Every arm is balanced to the
same quotas on its own. This is what randomisation does in the real study. It
stops demographic composition from confounding the treatment effects.

## The quota source — read this before you change anything

**Do not compute the quotas from raw Census data.**

The benchmark preregistration says its quota table holds *"proportions matching
the parent megastudy, with counts rescaled to N = 18,000"*. The parent megastudy
is a real recruitment. Its realised sample is not the Census.

Our first version used raw Census PEP 2024. That was wrong. The largest error
was the 18-29 age band: raw Census gives 19.18 %, the organizers give 20.16 %.
The error was small, but it was systematic. More personas did not remove it.

`01c_quotas_18000.py` now reads the target from **Table 3 of the
preregistration**, which is the rendered output of the organizers'
`R/quotas_18000.R`. The recovered table is `quotas_18000.csv` in this folder.

## Realised quotas

Seed `20260807`. The run is deterministic. `quota_report.txt` holds the full
report.

| Dimension | Largest deviation from Table 3 |
|---|---|
| gender | 0.53 pts |
| age band | 0.27 pts |
| race / ethnicity | 0.29 pts |
| gender x age and gender x race (cross-quota) | 1.20 pts |

The worst cross-quota cell is `Other` race. It holds about 250 of the 9,000
people, so its sampling noise is large. Every other cell is inside 0.61 pts.

## Known limits

1. **Party is raked to the GSS, not to the Census.** The Census collects no
   party ID. The survey's 4-option wording pushes leaners into Independent.
2. **Two GSS variables are too coarse** for the study's categories, and are
   split with Census conditional shares:
   - `degree` puts "some college, no degree" into "high school".
   - `income16` top-codes at "$170,000 or over".
   Both are scored moderators, so an error here would bias the subgroup
   analyses.
3. **Only gender, age and race are quota-enforced.** Education, income, party
   and religion follow from the GSS joint structure. They vary by up to about
   8 points between arms. Real randomisation has the same property.

4. **We did not draw the GSS pool ourselves.** We reuse the organizers' own v1
   clone pool. See "Where this pool comes from" above, and declare it in
   registration item D.1.

## Where the code runs

Both inputs of `02_build_personas.py` are in this folder — `gss_profiles.csv`
and `census_quota_targets.json` — and it resolves them from its own directory.
So it runs here, with no sibling project:

```bash
python3 population/02_build_personas.py              # writes here
python3 population/02_build_personas.py --out DIR    # writes to DIR
```

The Tier-2 pipeline calls it with `--out generation/build/population/`, because
`personas.csv` and `personas.jsonl` are 12 MB together and are deterministic.
`quota_report.txt` in this folder is the deposited quota evidence; the run that
produced it is reproducible byte for byte from the two inputs above and seed
`20260807`.

One input is **not** here: `01c_quotas_18000.py` reads Table 3 out of a local
mirror of the benchmark preregistration, which is the organizers' own web page.
Pass it with `--page`. You do not need the mirror unless you rebuild the target,
because that script's outputs — `quotas_18000.csv` and
`census_quota_targets.json` — are both in this folder.

Record the code location in `metadata.json` → `code_repository`.

## File sizes

`gss_profiles.csv` is 2.1 MB. GitHub does not show files above 1 MB in the web
view. Read `quota_report.txt` (3 KB) instead to check the quotas.
