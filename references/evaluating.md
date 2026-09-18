# Evaluating a skill

Two different questions, often confused, measured separately:

1. **Does it fire?** The description is the whole triggering mechanism. A skill that
   never activates is worth nothing, however good its instructions.
2. **Is the output any better?** Compared against the same task run with no skill at
   all. A skill that changes nothing is load the agent pays for and gets nothing back.

Everything below follows the official skill-creation guidance:
[optimizing-descriptions](https://agentskills.io/skill-creation/optimizing-descriptions),
[evaluating-skills](https://agentskills.io/skill-creation/evaluating-skills).

Both eval sets live inside the skill:

```
my-skill/
├── SKILL.md
└── evals/
    ├── eval_queries.json    [{query, should_trigger}]     does it fire
    ├── evals.json           {skill_name, evals: [...]}    is it any good
    └── files/               inputs a test case needs
```

`sqs.py evals <skill> --init` writes both skeletons. `sqs.py evals <skill>` checks that
they parse and that the trigger set is not lopsided; neither costs anything.

## 1. Does it fire

```
python scripts/sqs.py evals <skill> --trigger          train/validation, 3 runs each
python scripts/sqs.py evals <skill> --trigger --runs 5 --show
```

This one **runs the agent**. It sends each query to a headless session and watches
whether the skill was loaded. That is a harder question than any description-reading
check answers: a judge asked "where would this wording route" is reasoning about the
description, while this observes the activation.

### Writing the queries

About twenty, eight to ten on each side. Vary phrasing, explicitness, detail and number
of steps; include casual wording, file paths, a bit of backstory, the odd typo. Real
prompts carry context that invented test strings do not.

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

The model is not deterministic, so each query runs several times and what is measured is
a **trigger rate**. Above 0.5 counts as "it fires". A positive passes when its rate is
above the threshold, a negative when it is below.

The runner splits the set **60/40 into train and validation**, stratified so both halves
carry positives and negatives, with a fixed seed so iterations compare like with like.

- Failures in the **train** set guide the next description.
- The **validation** pass rate is the only thing that says the change generalised.
  Keep validation results out of the revision itself, or the split has bought nothing.

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
- **Pick the iteration with the best validation pass rate, not the last one.** Later
  ones often overfit.

Then re-read [writing-rubric.md](writing-rubric.md) §1: a description that triggers well
can still be carrying restated identity and synonym triggers that cost context on every
turn.

## 2. Is the output any better

This one is a human-in-the-loop process, not a command. The suite checks the shape of
`evals/evals.json` and stops there: grading output quality needs judgement it does not
have, and a linter that pretended otherwise would be the worst kind of wrong.

A test case is a **prompt**, an **expected_output** in plain words, optional **files**,
and, added after the first run, **assertions**:

```json
{
  "id": 1,
  "prompt": "I have a CSV of monthly sales in data/sales.csv. Find the top 3 months by revenue and make a bar chart.",
  "expected_output": "A bar chart of the top 3 months by revenue, axes labelled.",
  "files": ["evals/files/sales.csv"],
  "assertions": ["The output includes a chart image", "The chart shows exactly 3 months",
                 "Both axes are labelled"]
}
```

Start with two or three cases. Write assertions **after** you have seen the first
outputs: you rarely know what good looks like before the skill has run. Good assertions
are checkable ("the output file is valid JSON", "at least 3 recommendations"); weak ones
are vague ("the output is good") or brittle ("uses exactly the phrase ...").

### The loop

1. Run each case **twice**: with the skill, and with no skill at all. Each run starts
   from a clean context, or the skill's own development conversation leaks into it.
2. Grade each assertion PASS or FAIL **with evidence quoted from the output**. No
   benefit of the doubt: a section titled "Summary" holding one vague sentence is a FAIL.
3. Record tokens and duration per run. The skill's cost is part of the result.
4. Aggregate, and read the pattern rather than the average:
   - assertions that pass **both** with and without the skill measure nothing and
     inflate the score - cut or replace them;
   - assertions that fail **both** ways are broken, or the case is too hard;
   - assertions that pass only **with** the skill are where its value is, and worth
     understanding;
   - results that differ run to run mean the instructions are ambiguous, not that the
     model is moody.
5. Review the outputs yourself. Assertions only check what you thought to ask for.
   Specific complaints ("the months are in alphabetical order") are actionable; "looks
   bad" is not.
6. Feed failures, complaints and the execution traces back into the skill. Generalise
   the fixes; a patch per failing case is how a skill turns into sediment.

**If the agent handles the task well without the skill, the skill may not be adding
anything.** That is a real outcome and worth acting on.

## What the traces tell you

Read the execution transcript, not just the final output. The guidance names three
signals:

- the agent tried several approaches before one worked → the instruction was vague;
- the agent followed an instruction that did not apply → the instruction is unscoped;
- the agent wrote the same helper script in every run → that script belongs in
  `scripts/`.

The third is the most valuable, and the cheapest to act on.
