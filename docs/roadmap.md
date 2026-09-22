---
title: "Roadmap - what skill-quality-suite does not do yet"
description: >-
  The planned layers of skill-quality-suite: routing analysis, capability manifests,
  static analysis of bundled scripts, a measured description budget, version bumps on
  improvement, generating a skill's case set from what you expect of it, from each
  improvement and from a stranger's promises, an optional LLM review layer, and last of
  all cross-runtime work - evaluation across engines and porting a skill from one harness
  to another - plus what Claude Code's own eval runner now covers, and what was rejected
  and why.
---

# Roadmap

What is not built yet, in the order it is worth building. Each item is here because it
answers a question about a skill that nothing in the suite answers today; an item that
only adds a command is not on this list.

## What counts as in scope

A working definition, not a settled one, and it is here because a roadmap without it grows by
whatever seemed interesting that week. The subject is a skill across its whole life: writing
one, adapting one (yours or somebody else's) to the runtime you actually use, linting and
validating it, improving it, measuring how it behaves as models change, reading it for danger
before trusting it, and getting the `SKILL.md` description right so that validators and agents
both do the right thing with it.

One goal in that list is worth stating on its own, because it is the only one that pays for
itself in money. Measuring a skill across models is not only about which scaffolding can be
dropped as models improve. It is about knowing, per task, which model does the job well enough
- so the work can be sent to the cheapest one that still clears the bar. A tool that answers
that has to be able to run the same task on more than one engine and grade the results the
same way, which is what P3 exists for.

The two rules the whole project runs on apply to everything below:

- **the static half stays offline, deterministic and standard library only.** Anything
  that needs a model, a network or an API key is an opt-in layer beside it, never a
  dependency of `check`;
- **every rule ships with a case that has been watched making it fire.** A new rule with
  no fixture in `tests/fixtures/` is not finished.

## What the runtime now ships itself

Claude Code added `claude plugin eval` in v2.1.269: cases with graders, a no-plugin arm on
by default, an HTML report. It answers "does it fire" and "does it help" for a plugin on
one engine, which is most of what the runtime half here does, and it does the authoring
step better - `claude plugin eval init` interviews the author and writes the cases.

Taken off this list as a result: any item that would have made the runtime half nicer to
use. A vendor with the agent in-process will do that better, and an item that only adds a
command was never admissible here anyway.

Not taken off, and now the whole reason the runtime half stays:

- **the regression gate.** It stores a run and diffs the next one against it. The official
  runner has no equivalent, so "did my last edit make this worse" still has no answer
  outside this repository;
- **more than one engine.** A single-engine runner cannot say which model clears the bar
  most cheaply, which is the goal named above and what P3 is for;
- **item 15, the measured description budget.** The official runner's documented first
  finding is a near-zero delta with the skill-activation grader failing - the same
  diagnosis this project makes. It reports the symptom per case; it does not turn a run
  into a threshold, which is the thing worth building.

The practical consequence for an author is a choice, not a merge: the two case formats do
not convert, and neither converts to the `evals/evals.json` the `skill-creator` plugin
uses. Three formats, one per skill.

## P1

| # | What | The question it answers |
|---|---|---|
| 6 | Routing analysis - `sqs.py route --prompt "..."` | which skill wins this prompt, and by how much |
| 9 | Static analysis of bundled scripts | what `scripts/*.py` inside a skill does: network, subprocess, credentials |
| 10 | Capability manifest - `sqs.py capabilities` | what this skill can actually do to the machine |
| 15 | Description budget, measured | how long a description can get before routing degrades |
| 16 | Version bump on improvement | this skill changed, does its version still say what it is |
| 17 | The suite writes the checks | this skill has no case set - what should be true of it, and is it |

Shipped: **the skill arrived inside a plugin (18)** - `PB007`/`PB008`/`PB009` in
`scripts/publish.py`, under `sqs.py publish`. What else the package wires beside this
skill (`hooks/hooks.json`), what this skill assumes the package provides (a pointer
through `${CLAUDE_PLUGIN_ROOT}` or a `../` into a sibling `commands/`, `agents/`,
`workflows/`, `hooks/`, `monitors/` or `bin/`), and where the package came from (a
marketplace entry's `source`, when it names a remote checkout rather than a local path).
Fixtures: `tests/fixtures/plugin-hooks`, `plugin-sibling`, `plugin-origin`.

Shipped: **semantic overlap / skill collision (5)** - `EV007` in `scripts/quality.py`
(`cross_overlap`), folded into every `check`/`all` run the way `ST014` already is.
Compares the trigger-branch sentences of every pair of skills with the same
stem-overlap-with-polarity test `QL003` runs inside one description, restricted to the
part of the description after `TRIGGER_RE`'s lead-in so two skills sharing a topic word
do not read as a collision. Needed three rounds of calibration against the 28 skills
actually installed here before it held: comma-level segments cut a disclaimer's quoted
phrase away from the neighbour's name it was deferring to, four-letter stems let generic
scaffolding ("when the user asks where ... went") stand in for a real topic match, and
the lead-in verb itself ("Срабатывай"/"trigger") is long enough to survive a six-letter
floor and is shared by every skill in the house style by construction - `content_stems`
drops it by name, read out of `TRIGGER_RE` rather than copied so the two cannot drift.
One residual case remains on that corpus: two skills that deliberately share a
disambiguation question read as a collision over that question, which is a fair reading
of "low confidence, high false-positive risk" and not a case worth another round of
patching one example at a time. Fixture: `tests/fixtures/branch-overlap`.

Notes on the harder ones.

**Routing analysis (6)** is the offline sibling of `eval --trigger`. The trigger pass
runs the agent and observes activation; `route` reasons about the descriptions and says
which one a wording most resembles. It is cheaper and weaker, and the report must say so
in the same breath, or the two get confused.

**Capabilities (10)** and **script analysis (9)** are one layer seen from two ends: the
first summarises, the second finds. Both describe capability rather than forbid it - the
security module's discipline is that a finding explains what a skill *can* do and leaves
the decision where it belongs. They are also the two items with a life outside this
project: the question "what can this thing do to my machine" is the same one for an MCP
server, a hook and a plugin script, and none of those is a `SKILL.md`.

**Description budget (15)** is the gap the registry admits to. `QL001` fires when a
description is too short to carry triggers and `SP008` fires at the specification's 1024
characters, and between those two there is no opinion at all. Neighbouring projects have
none either, and their thresholds are guesses. This project is the one that can stop
guessing: `eval --trigger` already measures precision and recall of activation, so the
same harness run against progressively trimmed descriptions turns a house style into a
measured threshold. That is also what justifies keeping the expensive half in the same
repository as the free one - it is where the free half's rules come from.

**Version bump on improvement (16)** is the smallest item here and the one that decays
fastest without a tool. A skill that has been improved and still carries its old version is a
skill nobody can tell apart from the version they installed. `PB005` only catches the manifest
and the skill disagreeing with each other; nothing notices that the content moved and the
number did not. The rule: a change to a skill's instructions bumps the patch, `0.0.1` at a
time, and a change that breaks how it is called bumps more than that. The machinery is already
here - `--changed --since` diffs skills against git and `fix --apply` already rewrites
frontmatter - so this is a rule plus a flag, not a layer. It reports rather than rewrites by
default: a version is a claim about the skill and the author makes it.

**The suite writes the checks (17)**. Two ways a skill wastes your time, and neither is
caught by anything in this repository as it stands.

**It passes every check and still does not deliver.** Intact, safe, well written, visibly
doing *something* - and not the thing it advertised. That skill is worse than no skill: it
occupies the routing slot, costs context on every turn, and the failure is silent, because
nothing about it looks broken. There is no verdict here today that separates a skill that
works from a skill that is merely well formed.

**You improve it and the improvement is a downgrade.** It answers worse, or takes twice as
long, or burns three times the tokens for the same answer. Without a set of checks underneath,
the only detector is you noticing months later, and by then the change that did it is twenty
commits back. Automated checks are what make an improvement safe to attempt, and their absence
is why a good skill quietly rots: every edit is a gamble nobody grades.

The machinery for the second one is already built, which is the frustrating part. `--save` and
`--compare` diff two runs and watch task success, trigger precision and recall, wall time,
tokens, cost and tool calls; quality falling fails the gate and cost rising is reported, with
`--fail-on-cost` to move that line. It is a working gate with nothing under it. Every layer
here assumes a case set that already exists: `--trigger` needs queries somebody wrote,
`--runtime` needs a task set somebody wrote, the gate needs two runs of that set. A stranger's
package has no `evals/` at all, and your own has whatever you had patience for on the first
day. The set is the foundation for everything expensive in this repository, and nothing here
helps you lay it.

So: given a skill, produce the checks. Three sources for what ought to be true, and they are
different sources, not three phrasings of one.

- **What you expect of it.** You say in plain words what you want this skill to do for you,
  and that becomes cases. It is the only source that survives the skill being wrong about
  itself, and the only one that exists before the skill does - write the expectation first and
  it is an acceptance test rather than a description of what already happened. For a skill you
  are adopting, this is the question nobody asks: not "is it good" but "is it the one I need".
- **Each improvement.** A capability the skill just gained is a thing no existing case
  exercises, and it is also the cheapest moment to write one, because you still remember what
  you changed and why. One check per improvement, kept for good. This is how the set accretes
  instead of standing still: the alternative is the set you wrote on day one, and a regression
  gate over a frozen set prints "no regression" about behaviour it has never sampled.
- **What a stranger's skill promises.** The description is a promise - *use me when X, and I
  will do Y* - and `X` is the only half anything tests today. Turn the description and body
  into claims: produces a file of this kind, refuses in this situation, calls that tool, its
  output carries these fields, finishes within this many steps. When you have neither the
  author nor a written expectation, this is all there is.

Those three disagreeing is the most useful thing the layer can print, and the reason it is one
item rather than three:

| expectation | promise | behaviour | what it means |
|---|---|---|---|
| ✓ | ✗ | - | wrong skill - it never claimed to do what you need |
| ✓ | ✓ | ✗ | broken skill - or a description that oversold |
| ✗ | ✓ | ✓ | fine skill, not for you |
| - | ✗ | ✓ | undeclared capability - it does `Z` and says nothing about it |

The last row is where this meets the capability manifest (10): that one says what a skill
*can* do to the machine, this says what it *does* and never mentioned.

Design constraints, all three learned from what is already here:

- **Generated is not trusted.** The output is a case file a human reads and edits before it
  counts. A set nobody can correct is a set nobody will believe, and it would be the same
  mistake as a linter whose rules cannot be suppressed.
- **Deterministic first, judged last, never circular.** Most claims reduce to an assertion -
  file exists, tool called, string present, step count under the cap - and `evals.json` already
  carries `files`, `assertions`, `forbidden_tools` and `max_tool_calls` for exactly that. A
  judge only for what no assertion reaches. A model that invents a claim and then grades its
  own claim has measured nothing, so judged claims are marked and kept apart in the report,
  the way `DETERMINISTIC` and `LLM REVIEW` are in P2.
- **Prose to claims needs a model, so it is an opt-in layer** beside `check`, never inside it.
  The expectation source does not: a sentence you wrote is already the claim.

What it must not become. Not a score - "78% honest" is unactionable and is the one-number
headline this project already rejected. Not a gate that fails on a judged claim, because an
opinion does not break a build. Not a case per edit either: a typo owes nobody a check; the
trigger is a *capability* changing, not a file.

Two fixtures prove it. A skill whose description promises a written file and whose body never
writes one: it passes `--trigger`, passes a hand-written `--runtime` set, and fails here. And a
skill that does exactly what it promised while the expectation written beside it asked for
something else - the case that must be reported as *wrong skill* and not as a defect.

## P2

- **LLM review as a separate optional layer** - clarity, gaps, contradictions, missing
  edge cases: the things a regex cannot reach. Hard requirement: `DETERMINISTIC` and
  `LLM REVIEW` stay separated in the output, and the model never promotes an opinion to
  an error.
- **Version and changelog analysis** - evidence-based warnings only: a version bumped
  with no changelog entry, a breaking change with no major bump. Where the evidence is
  not there, no finding.
- **Description written for the wrong reader** - a skill carrying
  `disable-model-invocation: true` whose description is a list of trigger wordings, or the
  reverse. Invocation mode decides the audience: a model matching wordings, or a person
  reading a menu entry. The mismatch is mechanical to spot and is currently invisible -
  `QL001` and `QL002` only look at the model-facing direction, so a manual-only skill
  passes them while spending its description on a reader who never sees it.
- **Ghost triggers, named as their own rule** - `QL004` reports that a description and a
  body barely overlap, which is a statistic and reads as vague. The specific defect worth
  its own code is narrower and checkable: a trigger phrase in the description that no
  instruction in the body serves. The skill fires on that wording and then has nothing to
  do about it, which is the half-working case users report as "it activates and ignores me".

## P3 - cross-runtime

Last, deliberately. Everything above makes one skill better on the runtime it already has;
this makes it work somewhere else. Both are worth building and neither is worth building
first, because a skill that is wrong travels its wrongness to every runtime it reaches.

### Evaluation across engines

The evaluation half runs one engine. The requirement is that a skill can be measured on
whatever runtime and model it will actually be used on, which is a different question from
"does it pass on mine". Three things stand between here and there, and the first two are
structural rather than new features.

**Separate what to run from how to run it.** `evals/evals.json` currently holds both: the
cases and, implicitly, the single environment they run in. There is nowhere to say *which
engine, which model, which workspace*, so a second engine has no place to be declared. The
split is a config file for the environment beside a case file for the cases, and it has to
land before any second provider, or the provider arrives with its settings threaded through
the command line forever.

**A judge that runs a program.** Grading is rule-based today, which in practice means matching
substrings in the output, and that has a ceiling: anything whose correctness is a property of
a produced *file* cannot be expressed. A judge that runs a program and takes its exit code
removes the ceiling and stays deterministic, which the model-based judge never will be. It is
also the cheapest of the three to build.

**The provider itself.** `providers.py` already carries the contract: `available()`, `run()`
with a `model`, and `isolates_skills`, which declares whether an engine can run a task with a
named skill present and absent. That flag is the honest part and it matters more as engines
multiply: an engine that cannot isolate a skill is still useful for output quality, and the
report has to say so rather than present the comparison as a baseline. Adding an engine is a
subclass and a registry entry; what it needs from elsewhere is where that runtime looks for a
skill, which the harness adapters already hold. Those two modules compose into this one.

### Porting a skill between harnesses

**`sqs.py port <skill> --to cursor`** - rewrite a skill written for one runtime so it works on
another. The question it answers: *this skill assumes Claude Code, what has to change before
Cursor runs it the same way.*

This is the first item that would make `compat` load-bearing rather than informational, and it
is the strongest argument for keeping that module alive at all. The knowledge is already in the
ten adapters: each carries its runtime's field table, discovery rule and locations, and
`fix --apply` is already a working transformation mechanism. A tool tied to one runtime cannot
follow: the knowledge of where every other runtime looks for a skill is what makes the rewrite
possible, and that knowledge is this project's own.

**It does not start until the adapters can age visibly.** A wrong compatibility *report* is read
by a person who can disagree with it. A wrong *port* silently rewrites their file. The adapters
name their source (`docs = "https://..."`) but record no date of last verification, and
`cursor.py` already carries in its own docstring the story of being built from the wrong page
and inventing an incompatibility. Porting on top of that produces broken skills and blames the
tool that produced them. The precondition is the `checked:` field below: a claim that cannot
say when it was last true must not be allowed to rewrite anything.

**It is also a third position.** The project's front page is being narrowed to reading somebody
else's skill before trusting it; a porting tool is a different promise to a different person.
Promoting this above P1 is a decision about what the project is, not a decision about features.
Recorded here so that decision is made on purpose.

## Deferred, not rejected

**Specification versions (13)** - `--spec latest` / `1.x`. Right shape, wrong moment: it
pays off once two versions of the specification are in the wild and old skills start
going red for a reason that is not their fault. Today there is effectively one. The form to
build it in is a versioned schema per specification version, kept as data, rather than a
version switch threaded through the code.

## Rejected, and why

Kept here so they stop coming back.

- **Packaging `pack` / `unpack` (14)** - that is an installer's job, and the ecosystem
  already has one in `npx skills add`. What was worth having in the item is the
  *verification*: path traversal, symlinks and secrets inside an archive. That is the
  `security` module reading an archive instead of a directory, which is a flag, not three
  commands.
- **Reproducible packages** - "this skill was modified after publication" needs an
  external anchor of trust. A manifest of hashes committed beside the files it describes
  proves nothing: whoever edits the files edits the manifest. Either a catalogue serves
  the hashes, and then it is a network feature that breaks the offline rule above, or the
  item does not exist.
- **`sqs.py rubric`** - fails this page's own admission rule. It adds a command and no
  question; the rubric is a file in `references/` that a person reads.
- **Visualisation and catalogue integrations** - no question named, so nothing to build
  against.
- **Dynamic harness registry (11, 12)** - rejected as written; `--format json` already
  covers the export half. What survives is one field: **`checked:` on every adapter**,
  printed with the row. A matrix that asserts today's facts without saying when it last
  looked is a matrix that rots silently, and it is the precondition for porting above.
