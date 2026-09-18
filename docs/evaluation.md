---
title: "Agent Skill evaluation - does the skill fire, and does it help"
description: >-
  Runtime evaluation for AI Agent Skills: trigger evals with precision and recall, a
  baseline/treatment comparison that measures whether the skill improves the agent's
  work, and a regression gate between two versions.
---

# Evaluation

*Every other page on this site is about reading a skill. This one is about running it.*

Static analysis answers "is this skill intact and safe". It cannot answer the two
questions that decide whether the skill is worth having:

1. **Does it fire?** The description is the entire triggering mechanism. A skill that
   never activates is worth nothing, however good its instructions - and a skill that
   fires on a neighbour's work is worse, because it produces confident wrong work.
2. **Does it help?** Compared against the same task run with no skill at all.

Everything here runs an agent, so it costs money and minutes and needs one installed.
Nothing runs unless you name it:

```bash
sqs.py eval ./my-skill              # prints what each layer would cost, and stops
sqs.py eval ./my-skill --trigger    # does it fire, and only when it should
sqs.py eval ./my-skill --runtime    # the task set, with the skill and without it
sqs.py eval ./my-skill --all --save v1
sqs.py eval ./my-skill --compare v1 v2
```

## Trigger evaluation

The query set lives inside the skill:

```yaml
# evals/trigger/should-trigger.yaml
- prompt: "Convert this PDF into an Excel spreadsheet"
  expected: trigger

# evals/trigger/should-not-trigger.yaml
- prompt: "Write a Python HTTP server"
  expected: no-trigger
```

Each query is sent to a headless session several times, because the model is not
deterministic, and what is counted is how often the skill was actually **loaded**. That
is a harder question than any description-reading check answers: a judge asked "where
would this wording route" is reasoning about the description, while this observes the
activation.

The output is the confusion matrix and the cases behind it:

```
    fired when it should        9   (recall    90%)
    stayed quiet when it should 8
    missed                      1   (precision 82%)
    barged in                   2   (F1        86%)
```

**F1 is printed, not scored.** It weighs a miss and a false fire equally, and they are
not equal: a skill that stays quiet costs a turn, a skill that barges in costs the user
their work. Which one your tree can afford is a judgement about your tree.

The set is split 60/40 into train and validation, stratified. Tune the description
against the train failures; the validation numbers are the only thing that says the
change generalised rather than memorised the failures.

## Runtime evaluation

```
task
 ├── baseline   the agent with no skills at all      (claude --bare)
 └── treatment  the agent with this one skill loaded (--plugin-dir)
```

Isolation rests on two documented CLI flags. `--bare` skips auto-discovery of hooks,
skills, commands and plugins, which is what makes a baseline a baseline: without it the
skill under test is installed on the machine doing the measuring and **both** arms can
reach it. A provider that cannot isolate says so in its report instead of calling the
comparison a baseline.

```
                           treatment    baseline       delta
  task success                  100%          0%       +100%
  tool calls                     1.5         0.5        +1.0
  tokens                      1960.0       815.0     +1145.0
  cost USD                    0.0340      0.0100     +0.0240
  safety violations                0           0           0
```

Two rules the numbers obey:

- a task with no assertions comes back **ungraded**, never as a pass. Counting it would
  turn "nobody said what success is" into evidence of success;
- a metric the provider never reported comes back **`n/a`**, never as zero. A zero is a
  measurement, and inventing one is how a comparison quietly starts lying about cost.

Assertions are substrings, regexes behind `re:`, prohibitions behind `not:`, and files
the run had to create. **Safety violations** are the security module's own command
patterns applied to what the agent actually ran, so a rule reported at rest and a rule
reported in flight cannot drift apart.

## Regression gate

```
REGRESSION DETECTED   v1 → v2

  ! task success          100% → 50%
  ! trigger precision     100% → 67%
  ! token usage           1960 → 2810   +43%

  tasks that got worse:
    ledger-02               100% → 0%

  trigger cases that flipped:
    [0.00 → 1.00] should no-trigger: Rename every receipt photo in this folder by date
```

Quality falling fails the gate. Cost rising is reported and does not, because a skill
that got 18% more expensive and 20% more reliable is a trade somebody has to look at,
not a build to break; `--fail-on-cost` moves the line when a budget depends on it.

## See also

- [`references/evaluating.md`](https://github.com/letsloose501/skill-quality-suite/blob/main/references/evaluating.md)
  - the working detail: writing queries, writing assertions, and the part that stays a
  human's job
- [Skill validation](skill-validation.md) - the free, offline half
