---
title: "Roadmap - what skill-quality-suite does not do yet"
description: >-
  The planned layers of skill-quality-suite: semantic overlap between skills, routing
  analysis, capability manifests, static analysis of bundled scripts, package
  verification, specification versioning, and an optional LLM review layer.
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
| 10 | Capability manifest - `sqs.py capabilities` | what this skill can actually do to the machine |
| 9 | Static analysis of bundled scripts | what `scripts/*.py` inside a skill does: network, subprocess, credentials |
| 14 | Packaging - `pack` / `unpack` / `verify` | is the archive safe **before** installing: path traversal, symlinks, secrets |
| 13 | Specification versions - `--spec latest` / `1.x` | which version was validated against, and why an old skill went red |
| 11, 12 | Dynamic harness registry, compatibility matrix as JSON | where a table row came from, and when it was last checked |

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
the decision where it belongs.

## P2

- **LLM review as a separate optional layer** - clarity, gaps, contradictions, missing
  edge cases: the things a regex cannot reach. Hard requirement: `DETERMINISTIC` and
  `LLM REVIEW` stay separated in the output, and the model never promotes an opinion to
  an error.
- **Reproducible packages** - a manifest of file hashes, so "this skill was modified
  after publication" becomes checkable.
- **Version and changelog analysis** - evidence-based warnings only: a version bumped
  with no changelog entry, a breaking change with no major bump. Where the evidence is
  not there, no finding.
- **`sqs.py rubric`** - the human reading pass from
  [writing-rubric.md](https://github.com/letsloose501/skill-quality-suite/blob/main/references/writing-rubric.md)
  as a printable checklist. Deliberately not automated.
- **Visualisation and catalogue integrations.**

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
