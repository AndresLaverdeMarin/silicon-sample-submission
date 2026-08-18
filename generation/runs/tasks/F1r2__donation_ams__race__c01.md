# BLIND PREDICTION TASK — F1r2__donation_ams__race__c01

## READ THIS FILE FIRST

  generation/runs/prefix_F1.md

It holds the 17 condition texts, which are the experimental manipulation. You
cannot predict this table without them. When you have read it, you will be
asked below to quote four words back as proof.

You are producing one table of numbers for a preregistered behavioural
megastudy on trust in climate scientists. The human data do not exist yet, or
are sealed: nobody involved has seen any outcome from this study. Your table
is a forecast of what the human respondents will do.

Predict what the humans WILL DO, not what the experimenters hope for, and not
what would make a tidy result.

Do not search for, or use, any result from this study or its pilots. Reason
from the texts, the items and the population described below. Every cell needs
a number: where you are unsure, give your best estimate rather than a
placeholder.

## THE STUDY

* Respondents are US adults recruited to preregistered gender x age and gender
  x race quotas (N = 18,000 across the 17 conditions).
* Order: consent -> demographics -> pre-treatment measures (including a trust-
  in-climate-scientists item and a climate-belief item) -> ONE condition text
  -> the post-treatment outcomes below.
* Because a pre-treatment trust item is asked first, the post-treatment
  answers are anchored on it: a single text moves a group mean by a few points
  at most, not by tens of points.
* Sliders start empty and are integers 0-100. Only the endpoints are labelled.
  The donation item is a whole-dollar choice, $0-$10.
* The newsletter offer is a real, optional sign-up on an earlier page; real
  sign-up rates for such an offer are low.

Each of the 17 conditions is a separate randomised arm of 18,000 US adults
(1,000 per intervention, 2,000 in control). Every number you give is a GROUP
MEAN over hundreds of people, so:

* Use decimals. A mean of several hundred integer answers is not a round
  number.
* Group means move much less than individuals do. One text read once shifts a
  group mean on a 0-100 scale by a few points at most, and some texts shift it
  not at all.
* Do not flatten either. Rank the 17 texts by how much they should move THIS
  group on THIS item, and let a genuinely stronger text show a larger
  difference. A table of 17 near-identical numbers is as wrong as a table of
  20-point swings.
* A text may move the mean the wrong way. If a text should reduce trust in
  this group, say so with a lower number than control.
* `control` is the untreated baseline: those respondents read a neutral, off-
  topic filler text, so their answers reflect the population, not the topic.

## THE GROUPS YOU ARE PREDICTING

The study scores six moderators. This task covers `race`, all 5 levels.
Predict each level separately, and keep them comparable: the difference
between levels is the moderation the study is testing.

### L1 — race = White / Caucasian

### L2 — race = Black / African American

### L3 — race = Hispanic / Latino

### L4 — race = Asian / Asian American

### L5 — race = Other


## THE 17 CONDITIONS

Refer to a condition by its CODE. Never type the title — the codes are how
your answer is read back, and a mistyped title is a failed submission.

  C00  control   (untreated baseline)
  C01  Corporate reliance
  C02  Social justice
  C03  Interview Prof. Maraun
  C04  Funding
  C05  Oil industry misinformation
  C06  Measurement & modeling (1)
  C07  Former skeptics
  C08  High public trust
  C09  Measurement & modeling (2)
  C10  Peer-review
  C11  Scientist community helpers
  C12  Consensus
  C13  Portrait Prof. Cherry
  C14  Model accuracy
  C15  Interview Prof. Sebille
  C16  Extreme weather predictions

The full text of each one is in generation/runs/prefix_F1.md, under the same
codes and in the same order.

* The control arm shows ONE of three neutral, off-topic filler texts, assigned
  at random; all three are reproduced under `control`.
* Each respondent read exactly one text, once, immediately before answering
  the outcomes.

## THE ITEM IN THIS TASK

The single item behind the scored outcome `donation_ams`. Predict each one
separately: they are
asked as separate survey questions.

  donation
      Of the $10 bonus, how much would you like to donate to the American Meteorological Society (AMS)?
      scale: $0–$10 in whole-dollar choices ($1 increments; integers only). All 0–100 slider items are also integers.
      give:  mean donation in dollars out of the $10 bonus (0-10, 2 decimals)

## HOW TO ANSWER

For every group, every item and all 17 conditions, give the group's mean.

Work condition by condition inside one item, so the 17 numbers stay on one
scale. Then move to the next item.

## OUTPUT

Write one JSON object of exactly this shape, and nothing else, to:

  generation/runs/raw/F1r2__donation_ams__race__c01.json

Use the Write tool. No prose in the file, no markdown fence, no comments. The
file must parse as JSON. `...` below marks entries left out of this example —
your file lists every one of them.

```json
{
  "task_id": "F1r2__donation_ams__race__c01",
  "model_id": "<your exact model id>",
  "read_check": "<first four words of C02>",
  "values": {
    "L1": {"donation": {"C00": 2.50, "C01": 2.50, "C02": 2.50, ...}},
    "L2": {"donation": {"C00": 2.50, "C01": 2.50, "C02": 2.50, ...}},
    ...
  }
}
```

Rules for the file:

* `model_id` — the exact model identifier you are running as. This is recorded
  as the entry's provenance, so state your own model, not the one you assume.
* `read_check` — the first four words of the C02 text, copied exactly from the
  file you were told to read first. This is checked against the text; a wrong
  or missing value means the answer is discarded and the task re-run.
* Every group code, every item name and every condition code listed above must
  appear exactly once. No extra keys, no missing keys, no nulls, no strings
  for numbers.
* Values are dollars, 0 to 10, two decimals. This is a mean donation out of a
  real $10 bonus.

When the file is written, reply with only the number of values it holds (85).
