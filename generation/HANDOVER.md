# How to continue the run

This entry needs 612 answered tasks. Some are done, and the rest are waiting.
This file tells a second person how to take over part of the work.

Read `generation/README.md` first. It explains the pipeline. This file explains
only the operating rules.

---

## 1. What you need

* **A Claude Code session set to Fable 5.** Use `/model` to set it. This is not
  optional: `04_collect.py` reads the `model_id` inside every answer and rejects
  any answer that does not name Fable.
* **Python 3.** No packages beyond the standard library.
* **R with tidyverse, jsonlite and digest**, but only for the final check. You
  do not need R to answer tasks.

Clone the repository and work from its root. Every command below assumes that.

---

## 2. Prove your session runs Fable

Do this one time in each new session, before anything else.

```bash
python3 generation/scripts/00_model_probe.py --prompt
```

It prints a question. Give that question to a fresh subagent and record what it
answers:

```bash
python3 generation/scripts/00_model_probe.py --record "<exact model id>" --how "..."
```

Every probe is kept, including a failed one. Registration item B.1 wants them.

Ask a **fresh subagent**, not the session itself. The orchestrating context can
hold an environment block that predates a `/model` switch.

---

## 3. Take a lane, so two people never collide

`07_next_tasks.py` prints the pending tasks from the front of one sorted list.
Two people who run it at the same time get the **same** tasks and do the same
work twice.

So split the work by draw. There are six draws, 102 tasks each:

| Draw | Owner |
|---|---|
| `F1r1`, `F1r2`, `F2r1` | person A |
| `F2r2`, `F3r1`, `F3r2` | person B |

Add `--only-draw` to every command, and never leave it out:

```bash
python3 generation/scripts/07_next_tasks.py --count \
    --only-draw F2r2 --only-draw F3r1 --only-draw F3r2
```

Each answer is its own file, named after its task. Two people in two lanes
never write the same file, so git merges the work without a conflict.

---

## 4. Answer the tasks

```bash
python3 generation/scripts/07_next_tasks.py --limit 12 --only-draw F2r2
```

It prints one line per pending task, like this:

> Read `generation/runs/prefix_F2.md` in full, then read
> `generation/runs/tasks/F2r2__concern_mean__party__c01.md` and do exactly what
> it says. Write the JSON file it asks for. Reply with only the number of values
> you wrote.

Give **one line to one subagent**. Run 8 to 12 subagents at a time. The
subagents inherit the session's model, so a Fable session gives Fable
subagents.

Do not answer a task yourself in the main context. One task is one subagent.

When the batch finishes, run the command again. Repeat until the count is zero.

---

## 5. Check your work as you go

```bash
make -C generation collect
```

This validates every answer on disk and rebuilds `build/draws.csv`. It writes
nothing else, and it is safe to run as often as you like.

It reports how many files it accepted. A rejected file moves to
`generation/runs/rejected/` with the reason in a `.reason.txt` beside it, and
its task becomes pending again. Four things cause a rejection:

1. `model_id` does not name Fable.
2. `read_check` does not quote the stimulus text. The subagent did not open the
   prefix file.
3. The keys do not match the task spec exactly — a missing condition, a stray
   group, a wrong item code.
4. A value is not a number.

Read the reason, then let `07_next_tasks.py` hand the task out again.

---

## 6. Rules that keep the entry valid

**Never re-run `make -C generation wave WAVE=1`.** All 612 prompts already
exist. That command would overwrite `runs/waves/wave01.json`, which is part of
the deposit record. You do not need it.

**Never edit a file in `generation/runs/raw/` by hand.** Those are the raw model
answers and they are deposited unprocessed. If a number looks wrong, delete the
file and let the task run again.

**Never edit `scripts/` at the repository root.** That directory is the
organizers' engine. A local change makes our self-check disagree with their
scoring.

**Never use `git add -A` or `git add .` in this repository.** Stage files by
name. Some files are deliberately untracked and must stay out of the public
history.

**Do not look for the human results of this study.** The entry is a blind
forecast. Any contact with the outcome data invalidates it.

---

## 7. Commit and push your lane

Commit the answers you produced. Nothing else.

```bash
git add generation/runs/raw
git commit -m "add (runs/raw): answers for draws F2r2, F3r1, F3r2"
git push
```

Commit subjects in this repository follow `action (file): description`. Do not
add a `Co-Authored-By` trailer.

Pull before you start each session, so your pending count reflects the other
person's work:

```bash
git pull
```

---

## 8. When every task is answered

One person runs the last four steps. They take minutes.

```bash
make -C generation collect      # every answer -> build/draws.csv
make -C generation aggregate    # writes the two files in predictions/
make -C generation diagnose     # direction agreement and spread
make manifest                   # SHA-256 into metadata.json
make check                      # the organizers' validator — must be 0 fail
```

`aggregate` refuses to write `predictions/` while any cell is missing, and
refuses again if any draw was not produced by Fable. If it stops, it tells you
how many cells are short.

Read the line that `diagnose` prints. If direction agreement is below 60 %, or
the attenuation ratio is below 0.50, do **not** submit the ensemble mean. Re-run
the aggregation with one framing:

```bash
make -C generation aggregate RULE=framing:F3
```

Both thresholds were fixed before any answer arrived. Follow what they say.

---

## 9. State of the run

The pending count is the truth. Ask the scripts, not this file:

```bash
python3 generation/scripts/07_next_tasks.py --count
```

A task is pending when `generation/runs/raw/<task_id>.json` does not exist.
There is no other state anywhere. Work is never lost and never repeated: stop
at any moment, and the next session continues from the files on disk.
