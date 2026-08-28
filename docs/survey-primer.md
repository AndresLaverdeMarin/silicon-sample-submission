# Survey Primer

An introduction to the Silicon Sample Benchmark study for someone new to survey
experiments. Explains what the human study measures, the vocabulary you need to read
`codebook.csv` and `survey/`, why the control group is built the way it is, and how all
of that turns into the file you submit.

Local notes — this file is deliberately untracked (see `CLAUDE.md`).

---

## 1. What the study is

Researchers want to know: **can you increase public trust in climate scientists, and
what works best?** Rather than test one message, they test **16 different messages at
once** against a shared comparison group. That's what "megastudy" means — one big horse
race between many interventions.

It is delivered as an online questionnaire. Roughly 9,000+ real Americans each:

1. answer background questions,
2. are **randomly assigned** to read *one* of 17 things — 16 climate-related texts, or a
   filler text about neckties, baseball, or dance,
3. then answer ~90 questions about trust in climate scientists, willingness to donate,
   support for climate policy, and so on.

The filler-text group is the **control**. Because assignment is random, the control group
is on average identical to every treatment group in every way *except* what they read. So
if the "Peer-review" group ends up more trusting than the control group, the text caused
it. Random assignment is what turns a difference between two groups into a *causal* claim.

**The scale of it:** 17 conditions (control + 16 interventions) × 13 outcomes, with 6
moderator variables spanning 27 levels.

---

## 2. Vocabulary

**Condition** (also *arm*, *treatment group*) — which of the 17 things a person was
assigned. One column in the data, `condition`, with values like `control`, `Consensus`,
`Peer-review`.

**Stimulus** — the actual text they read. Reproduced in `survey/questionnaire.txt`;
200–700 words each.

**Pre-treatment / post-treatment** — measured *before* vs *after* the stimulus. Some
things are deliberately asked twice: `trust_pre` before, `trust_post` after. Only
post-treatment answers are scored.

**Item** — a single question. `trust_honest_1` ("How dishonest or honest are most climate
scientists?") is one item.

**Slider / scale** — the answer format. Nearly everything is a 0–100 integer slider:
0 = "very dishonest", 100 = "very honest". An answer is just a number.

**Composite** (or *scale score*) — several items **averaged into one number**, because no
single question captures a construct like "trust" well. This is the concept newcomers trip
on most. A real respondent from the shipped example file:

```
p00001's 12 trust items:  20 17 39 | 74 100 17 | 73 61 87 | 10 47 53
                          competence  integrity   benevolence  openness
average each group of 3:    25.33      63.67        73.67       36.67
average those four:                    49.83   ←  trust_multidimensional
```

That last number, **`trust_multidimensional`, is the primary outcome** — the headline
result of the whole study. Nobody was ever asked it directly; it is built from 12 answers.
Same idea for `concern_mean` (3 items), `behavior_mean` (6 items), `policy_specific_mean`
(7 items), and the rest.

**Outcome** — a thing being predicted. There are **13**: the primary trust composite plus
12 others (donation amount, newsletter signup, policy support, climate concern, …). The
canonical list is `scripts/lib/submission_spec.R` → `outcomes`.

**Moderator** — a background characteristic you split people by, to ask "did this work
*differently* for different people?" There are 6 — gender, age band, race, education,
income, party — with **levels** (party has 4: Republican, Democrat, Independent, Other),
27 levels in total.

**Cell** — one group's average on one outcome. "Control group's average
`trust_multidimensional`" is a cell.

**ATE** (average treatment effect) — what the study is really about: *treatment cell minus
control cell*. How much did this text move the needle, relative to reading about neckties?

---

## 3. The control group

### The medical analogy

In a drug trial you don't compare "took the pill" against "took nothing." You compare
against a **sugar pill** — same size, same color, same ritual of swallowing it with water
at 8am. Everything identical except the active ingredient.

The filler texts are the sugar pill. Neckties, baseball rules, dance styles: ~310 words
each, same reading effort, same "please read carefully" instruction, same screen layout —
everything a treated participant experiences, minus the climate content.

### What it's for

The question you want to answer is: *this person read the Peer-review text and rated trust
at 64. What would they have rated it if they hadn't?*

Unanswerable — you can't rewind a person. So the experiment builds a stand-in: a group
that is, thanks to random assignment, statistically identical to the Peer-review group in
every respect and did *not* read it. Their average becomes the "what would have happened"
number. The whole study is that one subtraction, repeated 16 times.

### Why not just "read nothing"?

Because then the groups would differ in **two** ways at once, with no way to tell which
moved the result:

1. they read climate-related content, and
2. they spent three minutes reading *something*, were told to pay close attention, and
   then got asked how much they trust scientists.

The second has real effects on its own. Being asked to concentrate changes how carefully
you answer; reading anything at all creates a break between the earlier questions and the
outcome questions. If control participants skipped straight to the outcomes, every
measured "effect" would be *the climate message plus the reading experience*, tangled
together inseparably.

The filler holds the experience constant so only content varies. In methods jargon this is
an **active control** (or attention-matched control), as opposed to a passive "do nothing"
control.

Note what the fillers are careful *not* to be: nothing about science, scientists,
expertise, the environment, politics, or trust; nothing persuasive or argumentative;
nothing emotionally charged. Any of those would contaminate the baseline — a control text
that made people think warmly about experts would shrink every measured effect toward zero.

### Why three fillers instead of one

One text would let a single quirk poison the baseline. If the one control text happened to
be boring, or delightful, or subtly evocative of authority figures, that idiosyncrasy would
shift the control mean — and since the control mean is subtracted from **all 16**
interventions, every effect estimate in the study would be biased by the same amount in the
same direction.

Three unrelated texts, randomly assigned, average that risk away.

They are **not three conditions**. They are three interchangeable instances of "read
something neutral." In the survey they are the code names `control neckties`,
`control baseball`, `control dances`; in your data they all collapse to the single label
`control`. You never predict them separately, and there is no "neckties" cell anywhere.

### Why control gets twice as many people

The survey's assignment randomizer has 18 equally-likely slots, of which **two** are
control. Control therefore ends up with roughly double any single intervention — the
1,000 vs 500 minimum in the rules.

The control mean isn't one number among 17. It appears in **all 16 comparisons**: every
effect is `intervention mean − control mean`. If your control mean is off by 2 points, all
16 of your effects are off by 2 points simultaneously, in the same direction. It is the
single most consequential number in the study, so it gets the most data.

### What the baseline actually represents

Easy to get wrong when simulating: control participants are **not** "random Americans who
haven't thought about climate today."

By the time they reach the filler text they have already been told *"Climate scientists
study changes in the Earth's climate over time…"*, and have already answered `belief_pre`
("Human activities are causing climate change — how accurate is this?") and `trust_pre`
("How much do you trust climate scientists?"). Then they read about neckties. Then they are
asked about trust again.

So the baseline is: *a person who has just been primed to think about climate scientists,
then read something irrelevant.* Simulating control respondents as blank slates who were
never asked those pre-questions measures something the human control group isn't.

Control participants also get everything after the stimulus — the $10 donation question,
the newsletter offer, all 13 outcomes. Those baselines matter too: "how much does someone
donate *without* a climate message" is a real quantity the study estimates.

### Why this matters most for your simulation

Your language model almost certainly has systematic biases — LLMs tend to be agreeable, to
avoid scale extremes, to over-report virtuous intentions. Those biases make your absolute
numbers wrong. But they appear in **both** groups, so they largely cancel under subtraction:

```
Truth:              control 60,  Peer-review 64        → effect +4
Your model:         control 72,  Peer-review 76        → effect +4   ✅
                    (absolute levels off by 12, effect exactly right)
```

Now suppose you skip simulating control and plug in an outside baseline — a poll you found,
or just asking the model "what's average trust in climate scientists?":

```
Your model:         Peer-review 76
Borrowed baseline:              65
                                                       → effect +11  ❌
```

Nearly three times too large, purely from a mismatched baseline. The model's optimism never
got cancelled because it was applied to only one side of the subtraction.

**The control group is your bias-canceller — and it only works if control respondents come
off the exact same production line as treated ones:** same profile construction, same
prompts, same call settings, same parsing, differing only in which text they were shown.

---

## 4. What one respondent goes through

Traced from `survey/survey.json` → `result.SurveyFlow`:

```
consent → filter (attention pledge) → filter_ai        ← "No" ends the survey
demographics (gender, year_birth, race, education, income, party …)
   ↳ age_band computed by branch from year_birth
   ↳ partisan_importance / religion / religiosity shown conditionally
epistemic autonomy → attention2                        ← failing ends the survey
── transition ──
[randomized order] belief_pre · trust_pre · alienation
── transition ──
CONDITION  (1 of 18 slots: 2 control + 16 interventions)
── transition ──
trust multidimensional                                 ← PRIMARY, always first
[randomized order] trust_post · donation · distrust · policy role · funding ·
                   institutional trust · newsletter
[randomized order] belief_post · concern · individual behavior ·
                   policy general · policy specific
```

Two design facts worth internalizing. The primary outcome block is **always first**; every
other outcome block appears in **randomized order**, so no two respondents answer the
secondary and tertiary items in the same context. And the screen-outs are real branches —
humans who fail a filter or the attention check never reach the outcomes at all.

---

## 5. The `survey/` folder

| File | What it is | Use it when |
|---|---|---|
| `survey.qsf` | Qualtrics' proprietary export | You want to *run* the survey in Qualtrics (needs a license) |
| `survey.json` | Qualtrics Survey-Definitions API output — `result.Questions` (203), `result.Blocks` (58), `result.SurveyFlow` | You want to *parse* the instrument programmatically |
| `questionnaire.txt` | Plain-text rendering in chronological order, each item annotated `[qualtrics_label · answer values]`, all stimulus texts verbatim | Building prompts by hand — the practical source |
| `condition_codenames.csv` | `code_name → title → tag`, 19 rows | Translating raw survey condition values into scored labels |

`survey.qsf` and `survey.json` encode the **same** survey and differ only in format.
Nothing in `survey/` is scored — `codebook.csv` defines that — but it is the definition of
what your synthetic respondents saw.

**Condition code names.** The raw `condition` value is an animal code name, not a title.
Three control fillers collapse to `control`; four names are semicolon-joined multi-pair
strings (`"crushing chicken; gross grasshopper; homely halibut"`) that are **one** condition
each — join on the full string, never split on `;`. `scripts/clean.R` applies this mapping
automatically via `sst$codenames`.

**Licensing.** Several stimulus texts adapt published journalism and other copyrighted
material. Keep `survey/` unchanged in your deposit; your `CC-BY-4.0` grant covers your own
contribution, not those texts.

---

## 6. Arms that aren't just a block of text

Most interventions are a single read-only text. Four are not, and a simulation that treats
them as one will misrepresent them:

- **Extreme weather predictions** (`practical planarian`) — **state-adaptive, 3 pages**: a
  state question, then an intro with `[STATE]`/`[CASE]` filled in, then exactly *one* of
  four case texts (flood / wildfire / winter storm / generic fallback for "prefer not to
  say"). The block in `questionnaire.txt` is ~1,650 words of scaffolding; a respondent sees
  ~300. Never feed it whole.
- **Consensus** (`jealous jaguar`) — intro → three consensus-estimate sliders in randomized
  order (item 3 always middle) → **immediate feedback after each** revealing the correct
  figure → summary.
- **High public trust** (`crushing chicken; …`) — estimate-then-reveal: guess what % of
  Americans trust climate scientists, then see the Pew figure. The text alone is only ~90
  words; the guess is the mechanism.
- **Funding** (`phony parrotfish`) — four agreement sliders, then a message that builds on
  them.

Also: the **newsletter** outcome has an offer page shown immediately before the scored item
(`survey/questionnaire.txt:833`). A one-shot pipeline must supply it or the item isn't
answerable.

The four genuinely interactive arms of the human study (3 LLM-chatbot conditions + the
"Value similarity" quiz) were **removed** from this reduced instrument.

---

## 7. What you're being asked to produce

You are **not analyzing data.** No human data exists to you — it is sealed until the
prediction lock.

Your job is to make an AI system *predict* what those humans will do. The usual way is to
**simulate synthetic respondents**: invent a person ("52-year-old Republican woman, some
college, Midwest"), show your model the same text a real participant would see, ask it the
same ~90 questions, record the answers as a survey row. Do that thousands of times and you
have a dataset shaped exactly like the real one. Later the organizers unseal the human data
and score how close you got.

That is why `survey/` matters so much: it is the script your synthetic respondents follow.

You build your own profiles — the benchmark ships **no** participant pool — and you assign
them to conditions yourself. `registration.md` §D is where you document how.

---

## 8. The three tiers are one thing at three zoom levels

You choose how granular your prediction is. Numbers below come from the shipped example
file — **random placeholders with no real effects**, shown only for the arithmetic.

**Tier 1 — one row per synthetic person.**

```
profile_id, condition,  party,     trust_multidimensional, donation_ams, ...
p00001,     control,    Democrat,  49.83,                  1
```

**Tier 2 — group averages.** Average all control rows → one cell:

```
control,   trust_multidimensional,  50.59
Consensus, trust_multidimensional,  51.89
```

17 conditions × 13 outcomes = **221 cells**, in `*_cells_main.csv`. Plus a moderator file:
every condition × each of the 27 moderator levels × 13 outcomes = **5,967 cells** (e.g.
`Consensus, party, Republican, trust_multidimensional, 51.85`).

**Tier 3 — effects only.** Subtract:

```
Consensus, trust_multidimensional, +1.30      ← 51.89 − 50.59
```

16 interventions × 13 outcomes = **208 numbers**. No control row — control *is* the
baseline being subtracted.

The arithmetic flows one direction: individuals → cells → effects. That is why **Tier 1 is
preferred**: hand in individuals and the organizers can compute the Tier-2 and Tier-3
numbers themselves. The reverse is impossible.

**A warning hiding in that example.** The `+1.30` came from **pure noise** — the example
values are random placeholders with no effects built in. With only 60 fake people per
group, noise alone manufactures effects that size. Real intervention effects are often just
a few points. That is the entire reason for the 500 / 1,000 minimum.

---

## 9. Traps

- **Composites are scored as submitted, not recomputed.** If your file says
  `trust_multidimensional = 80` but the 12 items average to 50, you are scored on the 80.
  The number must actually be the average of its items.
- **`funding_perceptions` is reverse-coded.** The raw item asks "is the government spending
  too *much*?" — high = wants less funding. Cleaning flips it to `100 − answer` so high =
  supports more funding. Get this backwards and one of your 13 outcomes is inverted.
- **Label strings must match exactly.** `"Measurement & modeling (1)"`,
  `"Doctorate degree / Ph.D."`, `"Hispanic / Latino"`. A near-miss is either a hard
  validation failure or a silent drop from every subgroup analysis.
- **Two labelling quirks.** The survey's on-screen race labels hyphenate differently from
  the submission strings (`Black / African-American` vs `Black / African American`) —
  `clean.R` accepts both, but your final file must carry the canonical form. And party is
  displayed as Rep / Ind / Dem / Other but *exported* as `1=Republican, 2=Democrat,
  3=Independent, 4=Other`.
- **Scale differences by tier.** Tier-1 `newsletter_signup` is individual 0/1; Tier-2 it is
  a 0–1 **proportion**. `donation_ams` is 0–10 dollars. Everything else is 0–100.
- **Every cell must be filled.** No gaps, no `NA`, no duplicates — otherwise teams could
  effectively pick their own exam questions. If you believe an intervention works the same
  for a subgroup, say so by repeating that condition's overall mean in the subgroup's cells.
- **Simulate the control the same way as everything else** (see §3).

---

## 10. Where to look things up

| Question | File |
|---|---|
| Exact condition / outcome / moderator strings | `scripts/lib/submission_spec.R` |
| What each variable means, raw name → clean name | `codebook.csv` |
| Item wording, response scales, stimulus texts | `survey/questionnaire.txt` |
| Survey structure, branching, randomization | `survey/survey.json` |
| Raw condition code name → title | `survey/condition_codenames.csv` |
| How raw exports become the submission schema | `scripts/lib/clean_lib.R` |
| What makes a submission valid | `scripts/lib/check_lib.R`, or just run `make check` |
| Rules, deadlines, deposit steps | `README.md`, `FAQ.md` |
| What you must document about your method | `registration.md` |
