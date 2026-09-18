---
name: skill-quality-suite
description: Reviews, repairs and builds Agent Skills - structure, specification conformance, instruction quality, cross-runtime compatibility, security, routing, publication readiness and mechanical fixes, under one command. Use when asked to check, lint, validate, audit or score a SKILL.md; when a skill does not fire, fires on somebody else's work, or half-works and silently skips steps; when writing a new skill or reworking an existing one; after renaming a skill, a file inside one, or a heading a reference points at; before committing or publishing a skill; when a skill arrives from elsewhere and has to be read before it is trusted; and when the question is whether the skill fires on the right wordings, whether it makes the agent's work better at all, or whether the last edit to it made any of that worse.
license: MIT
---

# Skill quality suite

A quality gate for a skill, in two halves. The **static** half reads the skill: eight
checks, one command each, separate because they fail at different moments - structure
breaks today and in silence, the specification breaks on publication, compatibility
breaks on somebody else's machine, routing breaks when a neighbour's description moves.
Running them as one undifferentiated pass reports all four with the same urgency, which
is how a report stops being read.

The **evaluation** half runs an agent: does the skill fire, does it make the work come
out better, did the last edit make it worse. It costs money and minutes and needs an
agent installed, so nothing in it runs unless you ask for it by name.

Everything lives in `scripts/sqs.py`. The static half is standard library only and works
offline; it finds the skills folder on its own, or takes `--skills-dir`.

## Start here

| The situation | Run |
|---|---|
| Just edited a skill, want it intact | `sqs.py check <skill>` |
| A skill does not fire, or half-works | `sqs.py check <skill>`, then `sqs.py eval <skill> --trigger` |
| Does the skill actually help | `sqs.py eval <skill> --runtime` - the task with it and without it |
| Did my last edit break it | `sqs.py eval <skill> --all --save v2`, then `--compare v1 v2` |
| Switching the gate on over an old tree | `sqs.py baseline create`, then `check --baseline` |
| One line per layer, for a decision | `sqs.py check <skill> --format board` |
| Writing a new skill | `sqs.py new <name>`, then [creating-a-skill.md](references/creating-a-skill.md) |
| Reworking a skill that grew unwieldy | `sqs.py check <skill>`, then the reading pass in [writing-rubric.md](references/writing-rubric.md) |
| A skill arrived from elsewhere | `sqs.py security <skill>` **before** running it, then `check` |
| About to commit or publish | `sqs.py all <skill> --strict`, then [publishing.md](references/publishing.md) |
| Renamed something | `sqs.py structure` - it catches the pointers the rename orphaned |
| Sweeping the whole tree | `sqs.py check --quiet` |
| Will it work anywhere but this machine | `sqs.py compat <skill> --harness all` |

`check` is the everyday one: structure, spec, quality, compat and security together.
`all` adds the publish module. Neither runs an agent - that is `eval`, and it is always
opt-in.

## Reading the report

```
⛔ SP004  `name: video-tools` does not match the folder `video` (SKILL.md)
⚠️  ST006  SKILL.md is 21370 B > the 15000 B budget (SKILL.md)
·   QL006  при необходимости - lines 191, 295 (SKILL.md:191)
```

- **⛔ error** - fix it. Nothing here is cosmetic: a broken pointer into `references/`
  does not crash anything, the agent just skips the step in silence, and from outside it
  looks like the work came out weaker than usual. That is why this class of breakage
  survives for months.
- **⚠️ warning** - a decision, not a defect. An orphan file is either unwired or no
  longer needed, and only you know which.
- **· info** - a nudge. Real, small, and safe to leave.

`--format board` prints one line per layer instead of a finding list, which is the view
for deciding rather than fixing:

```
STRUCTURE       PASS      does every pointer still resolve
SPEC            WARN      2 warning
SECURITY        PASS      what can it do to the machine that loads it
TRIGGER         NOT RUN   `sqs.py eval <skill> --trigger` runs the agent
```

`NOT RUN` is the point of that view: a layer that was skipped and a layer that passed
look identical in a findings list, and that is how a report comes to say "clean" about a
question nobody asked. `--score` adds an aggregate number and prints the arithmetic that
produced it - additional, never the headline, because a number hides which question
failed. `--format sarif` is the same analysis for GitHub code scanning, `github` for
inline annotations, `json` for everything else.

Every finding carries a rule code. `sqs.py explain ST008` gives the code's reasoning and
its fix; `sqs.py rules` lists all of them. Reach for `explain` rather than guessing at
what a message means - the reasoning is the part that decides whether the finding
applies to your case.

## The modules

```
sqs.py structure   links, orphans, budgets, section pointers, outbound paths
sqs.py spec        layout, fences, description shape, asset weight, nesting
sqs.py quality     the description as a pointer, placeholders, vague bounds
sqs.py compat      will the skill work on somebody else's harness
sqs.py security    secrets, destructive commands, injection, hidden characters
sqs.py evals       the eval files and the routing invariants - free
sqs.py publish     what has to be true before the skill leaves the machine
sqs.py fix         the repairs with exactly one correct answer
sqs.py eval        runs the agent: triggering, task success, regressions - costs money
sqs.py baseline    the findings a tree has agreed to live with, for now
```

`evals` reads the eval files and costs nothing. `eval` runs the agent and costs money.
The two are one letter apart because they are about the same thing at two prices.

Four of them need a word of their own.

**`security`** is the one to run on a skill somebody else wrote, *before* the agent reads
it for work. A skill is executable text; an installed skill is a supply chain. It reports
credentials, destructive commands, text addressed at the agent rather than the task, and
hidden or bidirectional characters that make the rendered file differ from the file the
model reads.

**`compat`** is the check your own machine can never make for you. It reads the skill
as a list of features - a frontmatter field, a directory, a tool name, a hard-coded
path into someone's skill folder - and asks ten harness adapters what each one means
to them: Claude Code, Codex, Cursor, Gemini CLI, Antigravity, OpenCode, Cline, Roo
Code, Windsurf, GitHub Copilot. Every row rests on that project's own documentation,
and what the documentation does not state comes back `UNKNOWN` rather than as an
invented incompatibility. `sqs.py harnesses` lists them with the page each rests on.

**`evals`** is the free half of testing. Per skill: does this one carry a usable eval
set (`evals/trigger/*.yaml` or `evals/eval_queries.json`, and `evals/evals.json`;
`--init` scaffolds them). Tree-wide: do the routing invariants still hold, delegated to
`evals/run_evals.py` when one sits beside the skills.

**`eval`** is the half that runs an agent, and the only part of the suite that observes
behaviour instead of reasoning about text:

- `--trigger` sends each query to a headless session and counts what loaded. The output
  is the confusion matrix - true and false positives and negatives, precision, recall,
  F1 - printed beside the cases it came from. F1 is **printed, not scored**: it weighs a
  miss and a false fire equally, and in a tree of skills they are not equal.
- `--runtime` runs the task set twice, once with the skill loaded and once with no
  skills at all, and reports task success, tool calls, turns, time, tokens, cost and
  whether following the skill made the agent do something destructive. A task with no
  assertions comes back `ungraded`, never as a pass.
- `--save <label>` stores a run; `--compare v1 v2` diffs two. Quality falling fails the
  gate, cost rising is reported and does not, because cheaper-and-worse and
  dearer-and-better are both trades somebody has to look at.

`sqs.py eval <skill>` with no layer named runs nothing: it prints what each layer would
cost and stops. See [evaluating.md](references/evaluating.md).

**`fix`** is a dry run unless you pass `--apply`. It only repairs what the broken state
forces: the name the folder already dictates, characters that should never have been in
the file. It deliberately will not shorten an over-long description - there is no single
right shortening, and picking one for you deletes a trigger you needed.

## Fixing what it found

1. `sqs.py explain <CODE>` - the reasoning, then the fix.
2. `sqs.py fix --apply` for the mechanical ones.
3. The rest by hand. When the finding is about **what the skill says** rather than how it
   is wired, the report has taken you as far as counting can: open
   [writing-rubric.md](references/writing-rubric.md) and do the reading pass.
4. Re-run until clean. A run that ends `0 error` and a run you assumed would are
   different things.

Three scopes of escape hatch, for findings that are correct-and-intended:

- **A line** - write `sqs-allow: SE002` on it or just above it. This is how one
  quotation of a dangerous pattern avoids being reported as a use of one.
- **A file** - `sqs-allow-file: SE001, SE002` in its first 25 lines, for a file whose
  whole job is to hold the patterns. Annotating each occurrence there would be noise
  pretending to be care.
- **The tree** - `sqs.config.json` beside the skills: `rules` maps a code to
  `off`/`info`/`warning`/`error`, `ignore` skips skills, `allow_dirs` accepts a directory
  the spec does not name, `harnesses` sets the target environments and `lang` the
  publication language.
- **A subtree** - `.sqsignore` at the skill root, one path glob per line. What it lists
  is not read at all, so nothing about it is checked and nothing about it is claimed.
  That is the difference from `sqs-allow`, which says "found it, and it is meant to be
  there". For material inside the folder that is not skill payload: a test corpus,
  vendored files, generated output.

Two more ways to make a report survive contact with an old tree, neither of which hides
anything:

- `--baseline` reports only what the baseline file does not already carry, so switching
  the gate on over three hundred existing findings does not turn the build red on day
  one. The recorded findings stay in the file, dated, and `sqs.py baseline show` lists
  them: it is a queue, not a bin.
- `--min-confidence high` drops the findings the suite is less sure of - the prose
  heuristics - and keeps the filesystem and parse facts. Every rule carries a detection
  confidence and a false-positive risk, and `sqs.py explain <CODE>` prints both.

Record *why* in the config next to the entry. A silenced rule with no reason gets
un-silenced by the next person who reads the file, including you.

## Editing this suite

The rule codes are the join key of the whole thing: `rules.py` is the single place a code
is defined, and every engine emits codes from it. After adding or changing a rule:

```
python scripts/sqs.py rules --audit     registry against the engines, and against the corpus
python tests/run_tests.py               every case, then the unit checks
```

`rules --audit` fails when an engine emits a code the registry does not carry, when the
registry carries a row nothing emits, or when a rule has no confidence and
false-positive grading. It also reports how many rules the corpus has ever observed
firing.

`tests/fixtures/` is that corpus: small skills trees with an `expect.json` beside each,
listing the codes the suite must report and the codes it must not. A new rule needs a
**positive** case there - a rule nobody has watched fire is not a rule that works - and
the two cases that matter most are `clean/` and `escape-hatches/`, which must report
**nothing at all**. A linter is judged by what it stays quiet about.

The evaluation layer has its own fixture, `tests/evaluation/`, driven by the `fake`
provider: it replays canned runs so the confusion matrix, the two arms and the
regression diff are tested without a model in the loop.

The structure module is `scripts/check_skills.py`, imported rather than shelled out to.
It also runs standalone, and as a `PostToolUse` + `Stop` hook pair. Parsing its printed
output back into findings would be a second, drifting source of truth, so it carries the
rule codes itself.

A new harness is one file in `scripts/harnesses/` and nothing above it changes: the
registry finds it, the engine classifies through it, the report prints it. Its
declarations come from that project's own documentation, and what the documentation
does not state is left out - an empty `limits` means unchecked, which is not the same
as passed.

New heuristics earn their place by being **checkable**: a rule that cannot name a file
and a line does not belong in a linter - it belongs in the reading pass, where a human
applies judgement. A linter that cries wolf stops being read, and then the real findings
go unread with it.

## The references

- [creating-a-skill.md](references/creating-a-skill.md) - the order for building a new
  skill, and for reworking an old one. Open it before writing any skill from scratch.
- [writing-rubric.md](references/writing-rubric.md) - the reading pass: the pointer, the
  two loads, the information hierarchy, completion criteria, leading words, pruning. Open
  it when the problem is what the skill says rather than how it is wired.
- [agent-compatibility.md](references/agent-compatibility.md) - the ten harnesses, what
  each row rests on, the five portability verdicts, and how to add a harness without
  inventing one. Open it before answering "will this work on X".
- [evaluating.md](references/evaluating.md) - the three eval questions, the trigger loop
  with its train/validation split, the baseline/treatment comparison, the regression
  gate, and the part that stays a human's job. Open it before touching a description
  that already fires, and before the first `sqs.py eval`.
- [publishing.md](references/publishing.md) - the gate before a skill leaves the machine,
  and what the publish module cannot see.
