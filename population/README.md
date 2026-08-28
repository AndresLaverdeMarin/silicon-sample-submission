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

Each item says what IS true first, then what stays open. None of them is a
defect of the build; they are the places where the pool can differ from the
humans, and we cannot see the humans.

1. **Party is representative by construction; the human target is unknown.**
   We never draw party. Each persona is one real GSS respondent, so party
   arrives attached to that person's age, education, race, religion and class,
   and the joint is the GSS joint. Stage 1 measures it: the party share inside
   each level of age band, ideology, religion and social class sits within a
   median of 1 to 2 percentage points of the weighted GSS.
   Raking moves the party MARGIN a little, because it targets education and
   income and both correlate with party: Democrat 29.8 to 32.7, Independent
   42.1 to 39.7, Republican 24.9 to 24.4. That is the cost of matching the
   study's education and income margins, not a distortion of party.
   **What stays open:** whether the HUMANS look like the US adult population
   on party. `quotas_18000.csv` holds `Age` and `Race / Ethnicity` only, so
   party was never quota-enforced in recruitment, and the human mix stays
   sealed until the lock. If it skews, our baselines shift — climate trust is
   partisan and the main cell means are sample averages. The within-group
   analyses are unaffected. *Planned check, once answers exist:* re-weight
   them to several party mixes and report how far the means move.

2. **Education and income match the Census margin; two GSS variables needed
   splitting to get there.** Both are raking targets, so the pool hits the
   Census CPS 2024 and P60-286 margins. Two GSS variables are coarser than the
   study's categories and are split with Census conditional shares:
   `degree` puts "some college, no degree" into "high school", and `income16`
   top-codes at "$170,000 or over".
   **What stays open:** the split is a share, not a person. Inside those two
   categories the assignment is probabilistic, so an individual can land in
   the wrong band even though the margin is right. Both are scored
   moderators, so this lands on the subgroup analyses.

3. **Every arm is balanced on the quota dimensions; the others float, as they
   do in a real trial.** Quota sampling runs inside each of the 17 conditions,
   so gender, age band and race are near-identical across arms — the largest
   spread between arms is 0.3, 0.9 and 0.6 percentage points. Education and
   income are raked to their margins for the pool as a whole, but are not
   quota-sampled per arm.
   **What stays open:** the attributes that are not quota-sampled vary between
   arms — education 7.4, income 6.0, party 8.2, religion 7.2 percentage
   points. Real randomisation has the same property, and with 500 per arm this
   is the size to expect, but it is unmodelled noise in every ATE.

4. **The GSS pool is real people; we did not draw it.** It is the organizers'
   own v1 clone pool, reused as it stands.
   **What stays open:** nothing technical, but it must be declared. See
   *Sources* above, and registration item D.1. Do not write that the benchmark
   shipped it.

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
