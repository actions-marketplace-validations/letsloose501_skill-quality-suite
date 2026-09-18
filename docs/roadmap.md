---
title: "Roadmap - what skill-quality-suite does not do yet"
description: >-
  The planned layers of skill-quality-suite: semantic overlap between skills, routing
  analysis, capability manifests, static analysis of bundled scripts, a measured
  description budget, version bumps on improvement, an optional LLM review layer, and
  last of all cross-runtime work - evaluation across engines and porting a skill from one
  harness to another - plus what was rejected and why.
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

## P1

| # | What | The question it answers |
|---|---|---|
| 5 | Semantic overlap / skill collision | two skills claim the same wording, and only one can win |
| 6 | Routing analysis - `sqs.py route --prompt "..."` | which skill wins this prompt, and by how much |
| 9 | Static analysis of bundled scripts | what `scripts/*.py` inside a skill does: network, subprocess, credentials |
| 10 | Capability manifest - `sqs.py capabilities` | what this skill can actually do to the machine |
| 15 | Description budget, measured | how long a description can get before routing degrades |
| 16 | Version bump on improvement | this skill changed, does its version still say what it is |

Notes on the harder ones.

**Semantic overlap (5)** must not declare a collision on shared words. Two skills about
invoices are not a collision; two skills whose *trigger branches* cover one wording are.
The output has to name the pair of phrases, the way `QL003` already names the pair inside
one description, or it is unactionable.

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

## P2

- **LLM review as a separate optional layer** - clarity, gaps, contradictions, missing
  edge cases: the things a regex cannot reach. Hard requirement: `DETERMINISTIC` and
  `LLM REVIEW` stay separated in the output, and the model never promotes an opinion to
  an error.
- **Version and changelog analysis** - evidence-based warnings only: a version bumped
  with no changelog entry, a breaking change with no major bump. Where the evidence is
  not there, no finding.
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
