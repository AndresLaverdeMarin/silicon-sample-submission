# BLIND PREDICTION TASK — F3r2__policy_general__main__c01

## READ THIS FILE FIRST

  generation/runs/prefix_F3.md

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

## THE POPULATION

Whole sample:
This is the whole sample (n = 9,000 profiles). Gender: 49.0 % Male, 50.4 %
Female, 0.6 % Other. Age: median band 45-59, mean 48 years. Race / ethnicity:
59.9 % White / Caucasian, 18.4 % Hispanic / Latino, 12.3 % Black / African
American. Education: 35.7 % hold a bachelor's degree or higher. Income: 16.6 %
under $30,000, 42.2 % $100,000 or more. Party: 24.4 % Republican, 32.7 %
Democrat, 39.7 % Independent, 3.2 % Other. Ideology: 33.2 % conservative, 30.8
% liberal. Prior confidence in the scientific community: 30.5 % a great deal,
5.8 % hardly any. 33.3 % describe themselves as born-again or evangelical
Christian.

## THE GROUP YOU ARE PREDICTING

The whole sample, code `G0`. One mean per item and condition, over all 17
arms.

## THE 17 CONDITIONS

Refer to a condition by its CODE. Never type the title — the codes are how
your answer is read back, and a mistyped title is a failed submission.

  C00  control   (untreated baseline)
  C05  Oil industry misinformation
  C12  Consensus
  C16  Extreme weather predictions
  C02  Social justice
  C14  Model accuracy
  C01  Corporate reliance
  C04  Funding
  C03  Interview Prof. Maraun
  C10  Peer-review
  C07  Former skeptics
  C11  Scientist community helpers
  C06  Measurement & modeling (1)
  C15  Interview Prof. Sebille
  C09  Measurement & modeling (2)
  C08  High public trust
  C13  Portrait Prof. Cherry

The full text of each one is in generation/runs/prefix_F3.md, under the same
codes and in the same order.

* The control arm shows ONE of three neutral, off-topic filler texts, assigned
  at random; all three are reproduced under `control`.
* Each respondent read exactly one text, once, immediately before answering
  the outcomes.

## THE ITEM IN THIS TASK

The single item behind the scored outcome `policy_general`. Predict each one
separately: they are
asked as separate survey questions.

  policy_general_1
      How much do you oppose or support: "The U.S. government should do more to reduce global warming"
      scale: 0 = Strongly oppose … 100 = Strongly support
      give:  mean of the 0-100 slider (1 decimal)

## HOW TO ANSWER — TWO STAGES

Stage 1. For every group and item, give the CONTROL mean: what this group
answers with no climate-related text at all.

Stage 2. For every group and item, give each intervention's SHIFT from that
control mean, as a signed number. `+2.4` means the intervention raises the
mean by 2.4 points; `-1.1` means it lowers it; `0` means it does nothing.

Commit to the effects, not to the levels. The submitted level is control +
shift, computed in code, so a shift you would not defend is a level you did
not mean.

## OUTPUT

Write one JSON object of exactly this shape, and nothing else, to:

  generation/runs/raw/F3r2__policy_general__main__c01.json

Use the Write tool. No prose in the file, no markdown fence, no comments. The
file must parse as JSON. `...` below marks entries left out of this example —
your file lists every one of them.

```json
{
  "task_id": "F3r2__policy_general__main__c01",
  "model_id": "<your exact model id>",
  "read_check": "<first four words of C14>",
  "control": {
    "G0": {"policy_general_1": 62.5},
    ...
  },
  "shifts": {
    "G0": {"policy_general_1": {"C05": 1.4, "C12": 1.4, "C16": 1.4, ...}},
    ...
  }
}
```

Rules for the file:

* `model_id` — the exact model identifier you are running as. This is recorded
  as the entry's provenance, so state your own model, not the one you assume.
* `read_check` — the first four words of the C14 text, copied exactly from the
  file you were told to read first. This is checked against the text; a wrong
  or missing value means the answer is discarded and the task re-run.
* Every group code, every item name and every condition code listed above must
  appear exactly once. No extra keys, no missing keys, no nulls, no strings
  for numbers.
* Values are 0 to 100, one decimal. Shifts are signed and control + shift must
  stay in range.

When the file is written, reply with only the number of values it holds (17).
