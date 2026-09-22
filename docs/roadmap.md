---
title: "Roadmap - what skill-quality-suite does not do yet"
description: >-
  The planned layers of skill-quality-suite: a measured description budget, an optional
  LLM review layer, and last of all cross-runtime work - evaluation across engines and
  porting a skill from one harness to another - plus what Claude Code's own eval runner
  now covers, and what was rejected and why.
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
| 15 | Description budget, measured | how long a description can get before routing degrades |

Shipped: **the suite writes the checks (17)** - the `cases` module (`scripts/cases.py`,
prefix `CS`) in every `check` run, plus `sqs.py cases <skill> --generate [--apply]`,
which drafts `evals/evals.json` out of the three sources. Expectations are read from
`evals/expectations.md`, one list item per claim - prose around the items is the
author's note to themselves, which the first version read as three expectations the
skill had failed to meet. The improvement source is a composition rather than new
machinery: `--since` from item 16 materialises the earlier skill (`git archive` read
through `tarfile`, so no `tar` binary is needed on Windows) and the `capabilities`
module from items 9/10 says which capability is new. The promise source is read out of
the description's outcome clause.

Three of the table's four rows are visible without running anything and those are the
rules - `CS001` broken skill, `CS002` wrong skill, `CS003` undeclared capability. The
fourth row is behaviour, which `eval --runtime` already grades over the set this
drafts. The three refusals the item named are all kept: not a score, nothing judged by
a model, and no case per edit - the trigger is a capability changing, not a file.

One deviation from this item as written, stated rather than quietly taken. It said
prose-to-claims needs a model and is therefore an opt-in layer. What shipped is the
deterministic subset: the claim *shapes* the item itself enumerates - produces a file,
calls a tool, the outcome clause of a description - matched by pattern, with their
reach stated in the docs. The model layer for what a pattern cannot read is still
unbuilt and still belongs beside `check` rather than inside it.

Five rounds of live calibration, each one a false positive or a dead branch watched
happening on the 29 installed skills or on a fixture written to fail:

- one finding per *import site* rather than per capability - one skill with eight
  scripts reading the environment filled the report eight times;
- `запуск\w*` matches `запуска` and misses `запусти`, the form an instruction is
  actually written in, so a skill whose every step says "run the script" read as silent
  about running scripts. Hand-rolled inflection was replaced by the shared stemmer,
  which is what it exists for;
- `ANNOUNCE_WORDS` was matched with `quality.WORD_RE`, whose four-letter floor drops
  every word in it - `api`, `env`, `cli`, `run` - so the branch was unreachable without
  ever failing;
- `script` and `run` in `CB002`'s vocabulary made that arm structurally dead: `CB002`
  only fires because a *bundled* script spawns something, and a skill that bundles a
  script almost always says so. What goes unmentioned is that the script reaches past
  itself to a command on the machine, so only wording about an external command counts;
- a promise read out of the *trigger* branch: "Use when a bank export lands in the
  downloads folder" parsed as a promise to produce a folder. Promises are now read
  before `TRIGGER_RE`'s lead-in, the same split `EV007` makes for the same reason, and
  `export`, `file`, `record`, `store`, `copy` and `move` left the verb list because a
  word that is a plausible artefact cannot be the evidence that one was produced.

`CB003` - reading the environment - is out of `CS003`'s scope, and that is the finding
rather than an omission. Three vocabularies were tried and each was wrong in both
directions: one stray `config` in a reference page about something else silenced a skill
whose every script reads the environment, and `окружение`/`переменная` - the only words a
Russian author would use - are ordinary prose in exactly the domain these skills are
written about ("замыкание помнит окружение", "`snake_case` — переменные"). A fourth
vocabulary would have been tuning against the examples, which this project's own rules
about editing a skill forbid. After all five rounds: three findings on the fixture, zero
on the 29 installed skills, and every one of the eight live capability cases silenced by
several genuinely relevant words rather than by one coincidence.
Fixture: `tests/fixtures/case-sources`. Page: `docs/case-sets.md`.

Shipped: **version bump on improvement (16)** - `PB010`/`PB011` in `scripts/publish.py`,
opt-in behind `--since`, which now takes a directory as well as a git ref. The directory
form is the half git cannot do and the one the item was actually about: an installed copy
and an edited copy drift apart on one machine, in no repository, and the version number is
the only thing that was supposed to tell them apart. `PB010` fires when files under the
skill moved and the declared version did not; `PB011` when `name`, the invocation mode or
`allowed-tools` moved and only the patch digit followed. Neither rewrites: the number is
the author's claim about their own work, so `fix --apply` stays out of it.

Three silences are deliberate and each one is a false positive that did not happen: a
skill absent at `--since` has no claim yet to go stale; a skill declaring no version has
no claim either, and inventing one is the author's decision rather than a lint finding;
and a file hidden by `.sqsignore` is not a change, because what the suite does not read it
makes no claims about. `declared_version` also had to learn the nested spelling - `version`
is not a specification field, it lives under `metadata:`, and the flat frontmatter parser
folds a nested block into its parent's string - which `PB005` was quietly missing too and
now shares.

Calibrated against the real tree rather than the fixture, the way `EV007` and `capabilities`
were: two archives of the installed skills directory twelve commits apart, 29 skills, the
version held constant on both sides so the only variable was the real content diff. Three
findings, and `git diff --name-only` agreed file-for-file on all three (30, 1, 1); the two
skills it stayed silent on were the two that did not exist at the earlier commit. The
Windows trap this design avoided by using git's own diff rather than hashing files:
`core.autocrlf=true` makes every checked-out file differ from its blob by `\r` alone, and a
rule that read that as an improvement would fire on every skill on half the machines that
run it - the directory path normalises line endings for the same reason.
Fixture: `tests/fixtures/version-claim`.

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

Shipped: **routing analysis (6)** - `sqs.py route --prompt "..."` (`cmd_route` in
`scripts/sqs.py`), the offline sibling of `eval --trigger`. The trigger pass runs the
agent and observes activation; `route` reasons about the descriptions instead - the same
stem-overlap test as `EV007`, run between the prompt and every sentence of each skill's
description, keeping the best-matching sentence so the ranking names what it matched
rather than asking to be trusted. The caveat that it is cheaper and weaker prints in
every render, not once in a docstring. Two differences from `EV007` that a straight
reuse got wrong before they were watched happening against the real skill tree:
`content_stems`'s six-letter floor exists to drop scaffolding two *descriptions* share by
house-style construction, and a real prompt does not normally contain that scaffolding,
so reusing it here instead dropped short topic nouns (`видео` is five letters) and
degenerated the ranking into an alphabetical tie-break; and a sentence that fences work
out ("do not use for X") had to be excluded from matching, or the exclusion clause itself
outscored the skill it was excluding the wording in favour of. No fixture in the golden
corpus - `route` has no rule code and prints a ranking, not `findings` - so it is a unit
check in `tests/run_tests.py` instead, against `tests/fixtures/branch-overlap`.

Shipped: **static analysis of bundled scripts (9) and the capability manifest (10)** -
the new `capabilities` module (`scripts/capabilities.py`, prefix `CB`), folded into
`check`/`all` the way `security` already is, and `sqs.py capabilities <skill>` runs it
alone through the same generic single-module dispatch every other module gets from
`MODULES` - no second report format was built for item 10's "manifest": the findings
list, read on its own, already answers "what can this skill do". `security`'s own
discipline carries over unchanged: a finding names a capability - network, subprocess,
reads the environment - and stops, leaving the decision where it belongs, so every
`CB` code is `info` severity and never fails a build.

Python scripts are read with `ast`, which is exact: `CB002` (`subprocess`/
`multiprocessing`, `os.system`/`os.popen`/`os.exec*`) and `CB003` (`os.environ`/
`os.getenv`) only ever fire that way, and their grading says so (`high`/`low`). Every
other extension has no stdlib parser, so `CB001`'s network signal falls back to a
command-name regex for those - the same reliability `security`'s own `DANGEROUS`
patterns are graded at - and `CB001`'s grading is the honest blend of the two paths
(`medium`/`medium`), not the AST half's confidence claimed for both.

One over-broad claim was caught by running this against the 29 skills actually
installed here rather than only the fixture: `urllib.parse` (pure string parsing) and
`urllib.error` (exception classes) were reading as "can reach the network" purely
because the top-level package `urllib` was on the network list and only `urllib.request`
actually opens a connection. `NETWORK_ROOTS` (a whole package is network-purposed,
`requests`/`socket`/`paramiko`/...) and `NETWORK_EXACT` (one network-capable submodule
inside an otherwise-inert package, `urllib.request`/`http.client`/`http.server`/
`xmlrpc.client`/`xmlrpc.server`) are now two different sets rather than one root check,
and both import forms - `import urllib.request` and `from urllib import request` - are
checked against `NETWORK_EXACT` so the split does not silently create a false negative
in place of the false positive. Fixture: `tests/fixtures/script-capabilities`.

The one note left.

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
  Still unbuilt after item 17: `CS001` is the other half of the same promise - *use me when
  X and I will do Y* - and reads `Y` against the body. This one reads `X`, and the two
  cannot be folded together, because a trigger nothing serves and an outcome nothing
  produces are different defects with different fixes.

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
