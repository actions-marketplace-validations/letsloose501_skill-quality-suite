# Evaluating a skill

Three different questions, often confused, measured separately:

1. **Does it fire?** The description is the whole triggering mechanism. A skill that
   never activates is worth nothing, however good its instructions.
2. **Does it help?** The same task, run with the skill and with no skill at all. A skill
   that changes nothing is load the agent pays for and gets nothing back.
3. **Did the last edit make it worse?** Two stored runs, diffed. Without this, every
   description change is a guess with a good feeling attached.

The first two follow the official skill-creation guidance:
[optimizing-descriptions](https://agentskills.io/skill-creation/optimizing-descriptions),
[evaluating-skills](https://agentskills.io/skill-creation/evaluating-skills).

Everything on this page **runs an agent**, so it costs money and minutes and needs one
installed. The rest of the suite is offline, deterministic and dependency-free; nothing
here runs unless you name it.

```
my-skill/
├── SKILL.md
└── evals/
    ├── trigger/
    │   ├── should-trigger.yaml       wordings that must reach this skill
    │   └── should-not-trigger.yaml   near-misses that must not
    ├── eval_queries.json             the older single-file form, still read
    ├── evals.json                    the task set: does it help
    └── files/                        inputs a task needs
```

`sqs.py evals <skill> --init` writes the skeletons. `sqs.py evals <skill>` checks that
they parse and that the trigger set is not lopsided; neither costs anything.

## The commands

```
sqs.py eval ./my-skill                     what it would run, and what it would cost
sqs.py eval ./my-skill --trigger           does it fire, and only when it should
sqs.py eval ./my-skill --runtime           the task set, with the skill and without
sqs.py eval ./my-skill --all --save v1     both, stored under a label
sqs.py eval ./my-skill --compare v1 v2     what the last edit moved
```

`eval` with no layer named runs nothing: it prints how many agent runs each layer would
take and stops. A command that spends money on the strength of a typo is a command
people stop trusting.

## 1. Does it fire

```
sqs.py eval ./my-skill --trigger --runs 5
```

It sends each query to a headless session and watches whether the skill was loaded.
That is a harder question than any description-reading check answers: a judge asked
"where would this wording route" is reasoning about the description, while this
observes the activation.

### Writing the queries

```yaml
# evals/trigger/should-trigger.yaml
- prompt: "Log this receipt: 12.40 EUR at Bakery Nord"
  expected: trigger
```

One item per `prompt`, with an optional `expected` that restates the file's own label.
The parser reads that shape and refuses everything else - nesting, block scalars, flow
collections - by name and line number. A tolerant parser would be a liability here:
silently misreading a label turns a should-not-trigger case into a should-trigger one,
and the report would then call a precision failure a success.

About twenty queries, eight to ten on each side. Vary phrasing, explicitness, detail
and number of steps; include casual wording, file paths, a bit of backstory, the odd
typo. Real prompts carry context that invented test strings do not.

- **The useful positives** are the ones where the skill would help and the query does
  not say so. If the query already asks for exactly what the skill does, any description
  triggers and the case measures nothing.
- **The useful negatives are near-misses** - queries sharing vocabulary with the skill
  that need something else. "Write a fibonacci function" against a CSV skill tests
  nothing. "Write a script that reads a CSV and uploads each row to postgres" does: it
  is full of CSV and is not analysis.

`EV005` reports a set that is thin on either side, because a set with few negatives
measures breadth and cannot tell you the description got greedy.

### Reading the result

The model is not deterministic, so each query runs several times and what is measured
is a **trigger rate**. Above 0.5 counts as "it fires". From that come the four counts
and the three ratios:

```
    fired when it should        9   (recall    90%)
    stayed quiet when it should 8
    missed                      1   (precision 82%)
    barged in                   2   (F1        86%)
```

**F1 is printed, not scored.** It weighs a miss and a false fire equally, and they are
not equal: a skill that stays quiet costs a turn, a skill that barges in costs the user
their work. Which one your tree can afford is a judgement about your tree, not a
property of the number. The cases are printed under the counts for the same reason -
two false positives that are both the same near-miss are one problem, and only the list
shows that.

The runner splits the set **60/40 into train and validation**, stratified so both halves
carry positives and negatives, with a fixed seed so iterations compare like with like.

- Failures in the **train** set guide the next description.
- The **validation** numbers are the only thing that says the change generalised. Keep
  them out of the revision itself, or the split has bought nothing.

### Revising the description

- Positives failing means the description is too narrow: widen the scope, or say more
  about when the skill is useful.
- Negatives firing means it is too broad: add specificity, or draw the boundary against
  the adjacent capability.
- **Do not paste keywords from a failed query into the description.** That is the
  overfitting the split exists to expose. Find the category the failures represent and
  address that.
- Stuck after several passes? Try a structurally different description rather than more
  tweaks. And check the length: descriptions grow during optimisation and the limit is
  1024 characters.
- Five iterations is usually the point of diminishing returns. If nothing improves, the
  queries may be the problem - too easy, too hard, or mislabelled.
- **Pick the iteration with the best validation numbers, not the last one.** Later ones
  often overfit.

Then re-read [writing-rubric.md](writing-rubric.md) §1: a description that triggers well
can still be carrying restated identity and synonym triggers that cost context on every
turn.

## 2. Does it help

```
sqs.py eval ./my-skill --runtime
```

The same task twice, and the difference is the whole point:

```
task
 ├── baseline   the agent with no skills at all      (claude --bare)
 └── treatment  the agent with this one skill loaded (--plugin-dir)
```

Isolation rests on two documented flags of the Claude Code CLI. `--bare` skips
auto-discovery of hooks, skills, commands, subagents, plugins and memory, which is what
makes a baseline a baseline: without it, the skill under test is installed on the
machine doing the measuring and **both** arms can reach it. `--plugin-dir` then loads
exactly one plugin, built from the skill under test and nothing else. A provider that
cannot do this says so in its report rather than calling the comparison a baseline.

### The task set

```json
{"skill_name": "ledger-lite",
 "evals": [{"id": "ledger-01",
            "prompt": "Log this receipt: 12.40 EUR at Bakery Nord on 2026-09-18",
            "expected_output": "a row appended to ledger.csv and the balance printed",
            "assertions": ["12.40", "re:balance", "not:could not"],
            "fixtures": ["evals/files/ledger.csv"],
            "files": ["ledger.csv"],
            "forbidden_tools": ["WebSearch"],
            "max_tool_calls": 6}]}
```

- an assertion is a **substring** by default, a **regex** behind `re:`, a **prohibition**
  behind `not:`;
- `files` names what the run must have created - the only assertion form that survives a
  model rewording its answer;
- `fixtures` are copied into the run's working directory, which is fresh for every run;
- `forbidden_tools` and `max_tool_calls` are how "it worked" is told apart from "it
  worked eventually, after eleven tool calls and a web search".

A case with **no assertions and no files is ungraded**, and stays that way in the report.
Counting it as a pass would turn "nobody said what success is" into evidence of success.

Write assertions **after** you have seen the first outputs: you rarely know what good
looks like before the skill has run. Good assertions are checkable; weak ones are vague
("the output is good") or brittle ("uses exactly the phrase ...").

### Reading the table

```
                           treatment    baseline       delta
  task success                  100%          0%       +100%
  tool calls                     1.5         0.5        +1.0
  tokens                      1960.0       815.0     +1145.0
  cost USD                    0.0340      0.0100     +0.0240
  safety violations                0           0           0
```

- `n/a` is not zero. A provider that did not report a token count reports `n/a`, and a
  comparison that invented a zero there would be quietly lying about cost.
- Assertions that pass in **both** columns measure nothing and inflate the score - cut
  or replace them. Assertions that fail in both are broken, or the case is too hard. The
  ones that pass only under `treatment` are where the skill's value is.
- **Safety violations** are the security module's own command patterns, applied to what
  the agent actually ran. A rule reported at rest and a rule reported in flight are the
  same rule, so the two lists cannot drift apart.
- Results that differ run to run mean the instructions are ambiguous, not that the model
  is moody. Raise `--runs`.

**If the agent handles the task well without the skill, the skill may not be adding
anything.** That is a real outcome and worth acting on.

## 3. Did the last edit make it worse

```
sqs.py eval ./my-skill --all --save v1
# ... edit the skill ...
sqs.py eval ./my-skill --all --save v2
sqs.py eval ./my-skill --compare v1 v2
```

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

Two kinds of worse, deliberately kept apart. **Quality** - task success, trigger
precision and recall - fails the gate. **Cost** - tokens, money, wall time, tool calls -
is reported and does not fail by default, because a skill that got 18% more expensive
and 20% more reliable is a trade somebody has to look at, not a build to break.
`--fail-on-cost` moves the line when a budget depends on it.

The thresholds are 5 points for a quality ratio and 15% for a cost one. Below that, the
model's own variance is louder than the change, and a gate that fires on variance gets
switched off.

Runs are stored in `.sqs/evals/<skill>/<label>.json` beside the skills, out of the skill
itself: an evaluation result is a measurement of a version, not a file that should ship
inside it.

## What the machine cannot grade

Assertions check what you thought to ask for. Read the outputs and the execution traces
yourself; the guidance names three signals worth more than any score:

- the agent tried several approaches before one worked → the instruction was vague;
- the agent followed an instruction that did not apply → the instruction is unscoped;
- the agent wrote the same helper script in every run → that script belongs in
  `scripts/`.

The third is the most valuable, and the cheapest to act on. Feed failures, complaints
and traces back into the skill, and **generalise the fixes**: a patch per failing case
is how a skill turns into sediment.

## Testing the machinery without paying for it

```
SQS_FAKE_RUNS=script.json sqs.py eval ./my-skill --all --provider fake
```

The `fake` provider replays canned runs from a JSON script instead of calling a model.
It exists so the arithmetic on top of the runs - the confusion matrix, the two arms, the
regression diff - has tests that cost nothing; `tests/evaluation/` is that test. It
measures nothing about any skill, and every report it produces carries `fake` in the
provider line, so a scripted number can never be mistaken for a measured one.
