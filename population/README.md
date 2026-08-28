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
| `gss_profiles.csv` | The base pool. 9,000 GSS respondents. See *Sources*. |
| `quotas_18000.csv` | The quota target, as published in the preregistration. |
| `census_quota_targets.json` | The target the raking uses. Gender, age band, race and the two cross-quotas come from `quotas_18000.csv`; education and income come from Census CPS 2024. |
| `01c_quotas_18000.py` | Recovers the target from the preregistration page. See "The quota source" below. |
| `02_build_personas.py` | Rakes the GSS pool to the target, then quota-samples 9,000 personas. It writes `party` (the study's 4 options, the scored column) and `party_detail` (the raw GSS 7-point value, for the persona writer only). |
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

## Sources

Every input, with its official reference. `census_quota_targets.json` records
the same provenance in machine-readable form.

| Input | Used for | Official source |
|---|---|---|
| General Social Survey (GSS), waves 2018, 2021, 2022, 2024 | the base pool of 9,000 real respondents, their post-stratification weights (`wtssps`) and the joint structure of every attribute | NORC at the University of Chicago — <https://gss.norc.org/> |
| Benchmark preregistration, Table 3 (N = 18,000) | the quota target for gender, age band, race, and the gender x age and gender x race cross-quotas | <https://janpfander.github.io/llm_predictions_megastudy/preregistration.html> |
| US Census Bureau, CPS 2024, Educational Attainment, Table 1, 18+ | the education margin | Current Population Survey detailed tables — <https://www.census.gov/topics/education/educational-attainment.html> |
| US Census Bureau, P60-286, *Income in the United States: 2024*, Table A-2 | the income margin | <https://www.census.gov/library/publications/2025/demo/p60-286.html> |

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

## How the data is modified

The GSS pool is not used as it stands. Four changes, in order:

1. **Recode to the study's categories.** GSS variable names and codes become
   the exact level strings of `scripts/lib/submission_spec.R`. Two GSS
   variables are coarser than the study needs and are split with Census
   conditional shares — see *Comments* 2. Party goes the other way: the
   megastudy asks the GSS root question word for word but never asks the
   follow-up that splits Independents into leaners, so the GSS 7-point value
   collapses to the study's 4 options and reproduces its instrument. The raw
   value stays in `party_detail` for the persona writer, and never reaches the
   submission.
2. **Rake the weights.** Iterative proportional fitting moves the GSS
   post-stratification weights onto the quota margins above. The joint
   structure of the pool is kept; only the weights move. Real microdata
   supplies that joint structure because drawing each variable on its own
   makes people who do not exist, such as a 19-year-old with a doctorate, and
   makes the six moderators independent, which they are not.
3. **Quota-sample 9,000 personas** from the raked pool, taking the gender x
   age and gender x race cross-quotas **independently inside each of the 17
   conditions**. This is what randomisation does in the real study, and it
   stops demographic composition from confounding a treatment effect.
4. **Assign one condition to each persona.** 500 for each of the 16
   interventions and 1,000 in control. No persona is used in more than one
   condition.

Deterministic throughout: seed `20260807`. `quota_report.txt` is the realised
against target check.

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

## Comments

The benchmark ships no participant pool and does not say how to build one —
registration item D.1 asks only that we report what we did. So each of these
is our choice, with the reason.

1. **Party comes from the GSS.** The Census collects no party ID, and the
   benchmark quotas only age and race, so the GSS is the only national source.
   Party is never drawn: it arrives attached to a real person, so its joint
   with every other attribute is the GSS joint — stage 1 measures that gap at
   a median of 1 to 2 percentage points. The human party mix was never
   quota-enforced and stays sealed, but it matters less than it looks:
   submissions are never reweighted, and the ATEs are differences from the
   shared control, so a compositional skew cancels. It reaches only the
   control-condition distribution metrics, which are Tier 1 only.

2. **Two coarse GSS variables are split with Census shares.** `degree` and
   `income16` are coarser than the study's categories, so Census conditional
   shares split them. The margin is then right, and the assignment inside
   those two categories is probabilistic.

3. **Quota sampling runs inside each arm, not across the pool.** That is what
   randomisation does in the real study, and it stops demographic composition
   from confounding a treatment effect. Gender, age and race then differ
   between arms by under 1 point; the attributes that are not quota-sampled
   float by 6 to 8, as they would under real randomisation.

4. **We reuse the organizers' 9,000-person GSS draw instead of drawing our
   own.** Someone had to pick which 9,000 GSS respondents; the organizers did,
   for their own earlier v1 simulation, and published the file in their
   research repository. Using it is allowed and it saves rebuilding a draw,
   but it means our population IS the one behind their reference simulation,
   and we inherit choices we did not make — their weights are renormalized so
   each wave contributes equally, so `wtssps` is not the raw GSS weight.
   Registration items D.1 and I.2 must say we reused their draw: not that we
   drew it, and not that the benchmark shipped it, because the benchmark ships
   no pool at all.

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
