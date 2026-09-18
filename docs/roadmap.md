---
title: "Roadmap - what skill-quality-suite does not do yet"
description: >-
  The planned layers of skill-quality-suite: semantic overlap between skills, routing
  analysis, capability manifests, static analysis of bundled scripts, a measured
  description budget, and an optional LLM review layer - plus what was rejected and why.
---

# Roadmap

What is not built yet, in the order it is worth building. Each item is here because it
answers a question about a skill that nothing in the suite answers today; an item that
only adds a command is not on this list.

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

## P2

- **LLM review as a separate optional layer** - clarity, gaps, contradictions, missing
  edge cases: the things a regex cannot reach. Hard requirement: `DETERMINISTIC` and
  `LLM REVIEW` stay separated in the output, and the model never promotes an opinion to
  an error.
- **Version and changelog analysis** - evidence-based warnings only: a version bumped
  with no changelog entry, a breaking change with no major bump. Where the evidence is
  not there, no finding.

## Deferred, not rejected

**Specification versions (13)** - `--spec latest` / `1.x`. Right shape, wrong moment: it
pays off once two versions of the specification are in the wild and old skills start
going red for a reason that is not their fault. Today there is effectively one. The
schema-driven approach cclint uses (a versioned schema per spec version rather than a
version switch in the code) is the form to build it in when the time comes.

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
- **Dynamic harness registry, compatibility matrix as JSON (11, 12)** - half of it exists
  as `--format json`, and the other half is maintenance infrastructure for a scale this
  project does not have at ten harnesses.

## Worth taking from the neighbours

Two projects solve adjacent problems well. Read before building the items above.

### [alibaba/skill-up](https://github.com/alibaba/skill-up) - evaluation and evolution

Go, Apache 2.0, the largest of the neighbours. Its subject is the half this suite added
last, and it went further in four places:

- **Declarative eval config**: `eval.yaml` for environment, engine and model, and
  `cases/*.yaml` for the cases. This suite keeps everything in `evals/evals.json`, which
  mixes what to run with how to run it.
- **Multiple agent engines as first-class citizens**: `claude_code`, `codex`,
  `qodercli`, `qwen_code`, plus user-defined engines. This suite has one real provider
  and a scripted one; `evaluation/providers.py` was built for exactly this and has no
  second engine in it yet.
- **Three judging strategies**: `rule_based`, `script`, `agent_judge`. This suite has
  only the first. A `script` judge - run a program, take its exit code - is cheap to add
  and removes the substring-matching ceiling.
- **Anthropic-compatible reports**: `grading.json`, `benchmark.json`, `benchmark.md`,
  plus `skill-up import` for an existing `evals.json`. Interop worth having: a report
  nobody else can read is a report that stays local.

### [dotcommander/cclint](https://github.com/dotcommander/cclint) - linting the whole component family

Go, smaller, and aimed one level wider: agents, commands, skills, plugins and settings.

- **Schema-driven frontmatter validation** (embedded CUE schemas) rather than
  hand-written checks. That is the shape the specification-versioning item (13) wants: a
  versioned schema per spec version, not a version switch inside the code.
- **"Ghost triggers"** as a named cross-file defect. `QL004` here reports a description
  that drifted from its body statistically; naming the specific case - a trigger in the
  description that no instruction serves - would be sharper and checkable.
- **`fmt --write`** for component files. `sqs.py fix --apply` repairs what is broken; it
  does not normalise what merely differs.
- **Baseline mode** arrived at independently, in the same shape: snapshot, then fail on
  new findings only. Good evidence the design is right.

Where this project deliberately diverges: cclint gives every component a 0-100 score
with tier grades as its headline. Here the headline is the board - one line per layer,
with `NOT RUN` where nothing was measured - and the aggregate is optional and prints its
own arithmetic. A single number hides which question failed, and the questions are not
interchangeable.

The wider component family (agents, commands, plugins, settings) is a real gap and a
deliberate one: pointed at a plugin, this suite checks the skills inside it and says
plainly that the other components were not analysed. Half-checking them would imply the
rest had been looked at.
