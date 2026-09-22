---
title: "Roadmap - what skill-quality-suite does not do yet"
description: >-
  The planned layers of skill-quality-suite: a measured description budget, an optional
  LLM review layer, and last of all cross-runtime work - plus what Claude Code's own eval
  runner now covers, and what was rejected and why.
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

### Where items 19-22 came from

Items 15-18 were reasoned out from this repository's own corpus. Items 19-22 are an
intake from published work on agent skills, recorded here with what each one rests on:
an item admitted on somebody else's evidence has to say whose evidence it is, because an
item this page cannot attribute is an item nobody can check. The sources, all 2026:

- **SkillSec-Eval** - *Agent Skill Security: Threat Models, Attacks, Defenses, and
  Evaluation*, Badhe & Tiwari, arXiv:2607.13987. The lifecycle taxonomy and the named
  threats behind items 20 and 21.
- **SkillAxe** - *Sharpening LLM-Authored Agent Skills Through Evaluation-Guided
  Self-Refinement*, Gautam, Radhakrishna & Gulwani, arXiv:2606.10546. The trigger
  geometry behind item 19, the fault-attribution split, and the measured finding that
  skills buy execution reliability rather than answer quality.
- **SkillTester** - *Benchmarking Utility and Security of Agent Skills*, Wang, Wang & Xu,
  arXiv:2603.28815. The invocation gate and the pre-flight evaluability check in item 22,
  and the practice of treating badges and self-claimed safety as claims to verify.
- **SkillEval** - *Decomposing Agent Skill Quality into Interpretable Signals*, Han et al.,
  arXiv:2608.06891. Document-level quality independent of any one downstream task, and the
  warning that length and formatting confound a score meant to measure something else -
  which is a caution aimed squarely at item 15.
- **SkillOpt** - *Executive Strategy for Self-Evolving Agent Skills*, Microsoft Research,
  June 2026. Bounded edits per revision, validation gating, and the measured median length
  of an optimized skill file.

The code stays free of all of this: a rule's docstring explains the rule, not who
suggested it. Attribution belongs on this page, where somebody deciding what to build
next can follow it.

The single most useful thing taken is not a rule but a frame: **a skill has a lifecycle,
and each stage is a separate trust boundary** - authoring, storage, retrieval, selection
by the planner, execution, and evolution. Laid over this suite, the modules cover
authoring (`spec`, `structure`, `quality`), storage and execution (`security`,
`capabilities`, `publish`) and, since item 16, evolution. Retrieval is covered thinly by
`EV007` and `route`. **Selection is not covered at all**, although the attacks on it are
exactly the kind this project can already see offline. That gap is why three of the four
items below exist.

Shipped: **trigger boundary geometry (19)** - `QL014` in `scripts/quality.py`
(`boundary_pairs`), beside `QL003` and on the same phrase comparison. SkillAxe scores a
trigger by three geometric quantities over its positive and negative phrases; only the
third is built here, and the other two were dropped on this project's own rules rather
than forgotten. *Coverage breadth* - how far the positives spread - reduces on a corpus
like this to `QL003` restated, and a third rule over the same measurement would be a
patch, not a rule. *Negative specificity* is that measurement averaged, and an average is
a statistic with nothing to point at, which is exactly the complaint `QL004` already
earns. What survived is the one that names a pair: the *minimum* distance between a
clause that claims work and a clause that fences it out, because a description can
separate its branches well on average and still be misrouted by one bad pair.

That pair is precisely the one `near_duplicates` throws away (`if na != nb: continue`).
It was right to: asked *is one branch written twice*, a pair that disagrees is two
branches and not its business. Asked *is the line sharp enough to hold*, the same pair is
the whole answer. No embeddings were needed for a comparison this suite already makes
with stems.

Two rounds of live calibration against the 29 installed skills, and the first one was the
whole rule being wrong:

- **`POLARITY_RE` cannot classify an exclusion.** It answers "do these two segments
  disagree", which is all `near_duplicates` needs; used as a classifier it was wrong on
  every case in the corpus. Of the seven segments it marked negative, none was an
  exclusion branch - and two of them, "что не так с этим текстом" and "не звучит как я",
  are wordings a user types to *invoke* the skill, so the label inverted their meaning.
  `EXCLUSION_RE` replaces it, and the difference is not a longer list of words: a clause
  fences work out because of what its negation *governs* - the act of using the skill, the
  purpose it would serve, or the neighbour it defers to - not because it contains one.
- **Third person is description, not instruction.** With that fixed, one case remained:
  this project's own description contains "when a skill does not fire", which is a
  situation it triggers on, and the pattern read it as an instruction not to fire. Two
  lookbehinds separate `do not fire` from `does not fire`.

After both: nine genuine exclusion clauses found across seven of the 29 skills, worst
overlap 0.00, and the rule silent - which is the corpus being clean rather than the branch
being dead, and the difference was checked by measuring the overlaps rather than by
reading a zero. The inversion cases cannot be reached by any fixture, because a phrase
wrongly labelled an exclusion usually produces no finding and looks exactly like a clean
description, so they are a unit check in `tests/run_tests.py` alongside `NEIGHBOUR_RE`'s.
Fixture: `tests/fixtures/trigger-boundary`, one fuzzy boundary and one sharp one, with
`QL003` rejected so the case stays about the boundary.

Deferred on evidence: **declared against actual (20)**, moved to *Deferred, not rejected*
below, with the measurement that sent it there.

What the attempt produced instead was a bug in shipped code, found because reading
`allowed-tools` on a real corpus was the first step of it. `model.py` matched tool names
with `[A-Za-z][\w:.()-]*`, which stops at the space inside `Bash(ls *)` and yields the
tool name `Bash(ls`. Every scoped declaration in the official plugin marketplace came out
truncated, and one published skill with a long scoped list produced **forty** "tool names"
that were fragments of shell commands - `p`, `null`, `git`, `maxdepth`, `dev` - each of
which was then handed to a harness adapter to be judged as tool vocabulary and printed in
a compatibility report as though it were one. Fixed to parse the three spellings published
skills actually use, with the scope kept in `detail` where an adapter can ignore it: 40
bogus names became 8 real ones on that skill. A unit check carries the three spellings,
because a fixture would only show the result through a compat verdict, where a truncated
name still reads like a name.

Shipped: **what changed between versions, read as a threat (21)** - `PB012`/`PB013` in
`scripts/publish.py`, behind the same `--since` as `PB010`/`PB011`. The lifecycle
taxonomy's last stage is the one nobody instruments: a skill keeps the trust it earned on
publication while its content moves underneath. SkillSec-Eval names the threats there as
*permission escalation*, *tool substitution*, *instruction injection* and *version
rollback*, and a second source names the live form: a poisoned run that rewrites the
skill's saved content so the payload fires on a later reuse.

`PB012` is escalation and substitution in one finding, because they are one claim - *this
update goes further than the copy you read* - made from two kinds of evidence: an
`allowed-tools` entry the earlier copy did not have, or a bundled script that gained
`CB001` (network) or `CB002` (process spawning). It fires whatever the version did; a
correct minor bump does not make the reader's consent retroactive. `PB013` is rollback:
both numbers parse and the new one is lower. Instruction injection is not built - a body
that changed under a still description is `PB010`'s diff already, and telling a malicious
rewrite from an honest one is not something a diff can do.

The three inversions the item named, as they landed:

- **`allowed-tools` growing, not only shrinking.** Compared entry by entry *with the
  scope*, because the tool name alone misses the case that matters: `Bash(git log *)`
  becoming `Bash(git *)` is the same tool and a wider permission. A scope covers a narrower
  one that matches it as a glob, so the reverse is silent. A rewrite that only looks
  narrower and does not match that way reads as new - a glance for the reader, where the
  opposite mistake waves a widening through.
- **A gained capability is a finding.** Compared at the level of the *code*, not the line:
  a skill that already reached the network and now imports a second HTTP library has not
  grown. This is why `cases.py` was left alone although the item named it -
  `gained_capabilities` compares capability *lines*, which is right for writing one test
  per new import and wrong for asking whether the reach grew. Sharing it would have made
  one of the two wrong. The capability half only materialises the earlier tree when a
  script actually changed.
- **A version going backwards is judged.** Only when both sides parse; `1.2` against
  `1.10` is a string comparison nobody asked for.

The first thing the work turned up was a bug in `PB011`, shipped with item 16. It read
`allowed-tools` with its own comma split, the same class of parser `model.py` had just
been fixed for. Against the eight real declarations in the official marketplace it was
wrong on seven: six YAML block lists came out as one "tool" called
`- Read - Write - Bash(ls *) - Bash(mkdir *)`, and the scoped `Agent(a, b, c)` list in
`claude-security` came out as seven fragments. `model.parse_tools` is now the one parser,
and both `PB011` and `PB012` read through it; a unit check carries both directions of the
comparison, and was watched failing when glob coverage was switched off.

Calibrated on the installed skills' own git history (89 commits) at four depths, with the
code sets before and after printed per skill rather than a zero read as clean. Three
depths were silent and the sets agreed on every skill whose scripts changed. At the root
of the history there is one finding, and it is real: `konspekt` gained a script that
spawns a process (`f70a47e`, 23.08.2026), so anybody who installed the skill before that
commit never agreed to it. What could not be calibrated, stated rather than papered over:
no installed skill declares `version` or `allowed-tools` at all, and the marketplace copy
that does has no history, so `PB013` and the `allowed-tools` half have been watched only
on the fixture and on the real declarations compared with themselves (silent, all eight).
A known residual: `Agent(a, b, c)` keeps its list as one scope, so dropping an agent from
it reads as a new entry. Fixtures: `tests/fixtures/version-reach` for both rules,
`tests/fixtures/version-claim` for the silent side - a narrowed scope in the bracket
spelling and a changed script that already spawned a process.

Shipped: **the paid layer's two missing gates (22)**, both from SkillTester.

*The invocation gate* (`scripts/evaluation/runtime.py`). A treatment run is credited only
when its transcript shows the skill loading, read by the same `Skill`-call parser the
trigger pass uses. The uncredited passes are not thrown away: they are reported as
`passed_without_skill`, because the model's own ability is the number the delta has to be
read against, and a report that hid it would trade one misreading for another.

It found something before it shipped. The scripted provider's own test run had been
passing its treatment arm with `skills: []` on every run - the script's default carried an
empty list and the treatment rules never overrode it. The test asserted 100% treatment
success, and under the gate that number is 0%: the fixture meant to show the comparison
working was itself the case the gate exists for. The scripts now record the load, one
task in each spelling (see below).

What is not verified, and is the first thing to look at when a live run is allowed: which
spelling a real treatment transcript carries. The arm hands the skill over inside a
one-skill plugin, plugin skills are called with the plugin's name in front, and the trigger
pass - which runs a plain skills tree - has only ever been watched printing the bare name.
Both spellings count, so neither guess can zero the column; if a live run shows the skill
loading in no run, the report says so in a line of its own rather than printing 0% as if
the skill had failed.

*The pre-flight gate* (`tasks.preflight`, shared). SkillTester's four criteria, and two of
them were already `EV004`: an objective (`prompt`) and an expected outcome. The other two
are new. A decidable pass criterion - no `assertions` and no `files` (now `outputs`) - is `EV008`. Runnable
as written is `EV009`, and reading for it turned up two failures that were silent today
rather than merely late: a fixture that does not exist is skipped by `prepare_workdir` with
no word, so the agent starts a task about a file it never received; and a `re:` that does
not compile raises inside the grader after both arms have already run - watched happening,
traceback and all, with the gate switched off. The third `EV009` reason is a draft left as
a draft: a field opening with `TODO`, anchored at the start because a real task may well
mention a todo list and a generated one never starts any other way. `eval --runtime`
refuses the whole set on any `EV009`, and on a set where no case is graded; `check` reports
both codes for free, so the refusal is never the first an author hears of it.

Calibration is thinner than it should be, and the reason is the corpus: there is no real
`evals/evals.json` anywhere on this machine outside the tests. The real inputs that do exist
are the drafts this suite writes, so the gate was run on those - `cases --generate --apply`
and `evals --init` over a copy of the 29 installed skills produced 26 sets, and all 26 came
back `EV009` with no `EV008` mislabel and no crash. The silent side is the filled
`ledger-lite` set, which stays quiet, and `totals-ok` in the fixture. One fixture mistake was
caught on the way and is worth keeping: `\d{2` without its brace *compiles* in Python - an
unmatched `{` is a literal - so the first "broken regex" in the fixture was not broken, and
only reading both sides showed it. Fixture: `tests/fixtures/evals-preflight`; the runtime
half is covered in `tests/run_tests.py` against the scripted provider, and both gates were
watched failing with their check switched off.

Shipped after it: **what an output holds, not only that it exists** - `outputs` in
`evals.json`, where `{"path", "contains"}` reads the created file as UTF-8 text and applies
the assertion grammar to it; a binary format under `contains` is `EV009`, since no run could
pass it. Building it turned up a misreading underneath: `tasks.py` says it reads
skill-creator's `evals.json`, and skill-creator's `files` are *inputs* ("Optional list of
input file paths (relative to skill root)", its `references/schemas.md`), while this suite
graded them as outputs. A case written for skill-creator came back 0% on **both** arms
(scripted run, answer correct) and the agent never received its input; `check` said
nothing. `files` now means input, an entry that is not a file in the skill is still graded
as an output - existence decides, the one reading both formats agree on - and `EV011` says
so instead of a published set changing meaning under its author. The failure report now
carries the reason with each check (`not in \`ledger.csv\``), without which a content
check fails indistinguishably from a missing file. Five mutations of the grader and the
pre-flight, each caught by the corpus. Fixture: `tests/fixtures/evals-files-meaning`.

### 23. Read from a real skill in the wild

The items above came from papers. This one came from reading a published, installable
skill the way a stranger would - which is the thing this project's front page says it is
for - and finding a defect in it that nothing here would have caught.

**The install command names a different repository than the one it ships in.** The
README's install instructions pointed at one GitHub owner while the repository itself
lived under another: the project had moved and the commands had not. Anyone following
those instructions installs from an account that is no longer the author's, which is a
supply-chain hole with a friendly face, and it is exactly the rename-leaves-a-pointer
failure this suite already claims to catch - just one level up, in the file that tells a
human what to type.

Shipped: `PB014` in `scripts/publish.py` (`install_findings`), the first PB rule that reads
the README as payload rather than as a box to tick. Two shapes: an install command -
`npx skills add`, `/plugin marketplace add`, `git clone`, a `raw.githubusercontent.com`
URL - whose `owner/repo` disagrees with the checkout's git remotes or the marketplace entry
beside it; and `/plugin install <this plugin>@<marketplace>` naming a marketplace other
than the one listing the plugin.

The item as written would have been wrong on its first real catalogue. "Disagrees with the
remote" read literally flags every README that installs somebody else's repository, which
is what a collection README exists to do. What moves when a project moves is the owner,
not the name, so the rule fires only when the *repository name* matches one this checkout
is known under and the owner is one it is not. Every remote counts, not only `origin`, so
a fork with `upstream` set is correct by construction rather than by suppression.

The second shape was not in the item. It came from calibration, on the official
marketplace: `plugin-dev`'s README says `/plugin install plugin-dev@claude-code-marketplace`,
and the `marketplace.json` that lists it is named `claude-plugins-official`. Whether a
marketplace by the other name exists somewhere cannot be checked offline, so the finding
states the disagreement and stops. Across the 23 plugins there that ship skills, that is the
only finding. The first run printed it once per skill - seven times for one README line,
the per-site noise item 17 already fixed once - so a README above the skill folder is
now reported on the first skill beside it only.

The owner half was watched on this repository's own README (remote in the
`ssh://…:443/owner/repo` spelling, both install lines extracted, silent because they
agree); on the installed skills it cannot fire at all, since no README there carries an
install command. A fixture cannot carry a git remote of its own - it would read this
repository's - so that half is a unit check building a throwaway checkout, including the
fork case, and was watched failing with the owner comparison switched off. Fixture:
`tests/fixtures/install-origin`, with three decoy install lines that must stay silent.

Two smaller things from the same reading, both parked:

- **A step with no way to tell done from not-done.** That skill's own fourth principle is
  that weak success criteria make an agent loop badly, and its format makes the criterion
  structural: `[step] -> verify: [check]`. `QL006` fires when a bound is *present and
  vague* (`be thorough`, `as needed`); the complementary rule fires when there is no bound
  at all. Parked because a good step often needs no explicit check, so the false-positive
  risk is high and the threshold is a guess.
- **The same guidance shipped in several files that can drift.** That repository carries
  its content as `SKILL.md`, as `CLAUDE.md` and as a Cursor rule, all by hand. Two copies
  of one instruction set with no mechanism keeping them equal is the drift this project
  already knows how to detect - the directory form of `--since` from item 16 is the same
  comparison. Parked because shipping several copies on purpose is legitimate, so the
  finding is a caution about a maintenance cost rather than a defect.

Shipped from the second intake: **`CB004`**, commands a skill runs the moment it loads.
One of the ten tools read has to translate the body syntax between runtimes, which is how
`` !`command` `` came up at all; the Claude Code skills page then settled what it does -
runs before the model is sent the skill, never prompts, lets through what a permission
rule or the skill's own `allowed-tools` allows. The static half had no view of it. On the
57 real skills here it fires on two, both from the official marketplace: one runs `date`
and `find` on every load, each pre-approved by its own `allowed-tools`; the other is a
guide to the syntax whose 14 injections all sit inside ordinary code blocks. Whether
those run was the one question the documentation left open, and one live load settled
it: a probe with `` !`echo RAN_FENCED` `` in a plain code block came back as
`RAN_FENCED`. So that guide runs `npm test $1`, `gh pr view $1` and a set of build
scripts on load, pre-approves none of them, and by the documented rule aborts outside
auto mode unless the user's own permissions allow each one. The porting half of the
same idea - `$ARGUMENTS` and `!` as Claude-only syntax in `compat` - was not built: the
other runtimes' pages on it were not checked, and an adapter row nobody checked is how
`cursor.py` once invented an incompatibility.

Shipped from a third reading (a security scanner whose change log is a list of evasions
it learned to see): **indirection in bundled scripts**. A probe of seven Python scripts,
each reaching a capability without naming it - `__import__('subprocess')`,
`importlib.import_module`, `getattr(os, 'sys' + 'tem')`, `vars(os)['system']`,
`exec(base64.b64decode(...))`, the network through `__import__('urllib.request')` - came
back with **no finding at all** from `CB` or `SE`; the plain import beside them fired, so
the rules were live and simply blind. `capabilities.py` now folds constant names (`+`,
f-strings of literals, `''.join([...])`) and follows `__import__`, `import_module`,
`getattr`, `vars()[...]`, `.__dict__[...]`, `from os import system` and `exec` of a literal,
reporting each as the capability it spells. What a name computed at run time reaches cannot
be read, and that is **`CB005`** (warning), limited to modules that carry a capability, so
`getattr(args, field)` stays ordinary code. **`SE008`** (error) is code decoded before it
runs: Python's `exec`/`eval` over a decoder, through one assignment, off the syntax tree;
a decoder piped into a shell, PowerShell's encoded command, `eval(atob(...))` and the
same Python shape inside an instruction, by pattern. On the 19 real skill trees here (173
script files) nothing that fired before was lost, and the one new finding was this
suite's own harness registry, which imports adapters by the names in its own directory -
true by the rule's definition and waived on the line. Found on the way: the first draft
crashed the whole `check` on a plain `os.path`, which only a probe that counted a crash as
a failure caught. Eighteen mutations of the new branches, all caught; the one that first
survived (the module list widened to everything) now has a silent case of its own.
Fixtures `script-indirection` (payloads assembled at run time) and
`script-indirection-benign` (exact).

The same reading also turned up a defect of this suite's own. Asked why signing, SBOM and
a sandbox were out of scope, the honest answer for the sandbox was that the suite needed
one: `eval --runtime` runs the treatment arm with permission checks bypassed, which the
Claude Code CLI's help recommends only in a sandbox with no internet access, and this
suite advertises itself for reading skills that came from elsewhere. Building a sandbox is
the harness's job; refusing to run is ours. `runtime.evaluate` now refuses a skill with
any of `CB001`, `CB002`, `CB004`, `CB005` or `SE002`-`SE005`/`SE008` until `--trust-target`,
and reads them straight from the engines so that the skill's own `sqs-allow` cannot open
it. On this machine it would refuse 14 skills - seven of the user's own, seven from the
official marketplace. Signing and an SBOM stay unbuilt, with reasons: no installer checks a
signature today (an open feature request in Claude Code), Ed25519 is not in the standard
library, and the 19 real trees here carry no dependency manifest at all, so an SBOM would
be empty - the gap underneath it, a script importing a package nothing declares, is the
next rule worth writing.

Shipped from the second intake: **trigger queries from the user's own history** -
`sqs.py cases <skill> --from-history`, in `scripts/evaluation/history.py`. One of the ten
tools harvests past sessions to replay recurring tasks; the same transcripts hold what a
trigger set lacks, the phrasings people actually used. On this machine: 528 transcripts,
318 skill loads. Three rounds of calibration on them, each a defect watched happening:

- a prompt that named the skill it loaded ("давай /trener на сегодня", "дай konspekt
  дописать") is a lookup, not routing, and ranked as a near miss for neighbours it never
  competed with - set aside now, on both sides;
- a one-word reply ("добавляй") scored a perfect overlap, because `prompt_match` divides
  by the shorter side; a near miss now needs three stems;
- paths and attachments (`@"C:\Users\...\Downloads\..."`) put one prompt at the top of
  three skills' lists on `users`, the account name and `downl`; links, paths and `@` references are
  stripped before comparing, and the ranking is by share, not by count.

What the calibration also showed, and why it shipped as a draft: the positives for the
busiest skill restated its description 0 times in 38, against 35% in the hand-written
set, and the near misses for the video skill came out as its fork with the neighbour it
shares "разбери" with. The unit check builds a transcript that crosses every filter once;
it first passed with the first-tool rule removed, because keeping each prompt's first
occurrence hid the second load - the rule is now checked where it lives.

Found on the way and fixed on its own: the trigger set's YAML parser cut every line at
the first `#`, so `"fix issue #12"` read as `"fix issue` with a stray quote and `C#` as
`C`, with no error - the silent misreading its own docstring says it exists to refuse.

Shipped on request, 23.09.2026: **a skill created and improved from its own analysis and
the user's requests** - `sqs.py improve <skill>` and `sqs.py new <name> --seed WORD`. What
shipped is the part that could be made reliable, and the reason it stops there is a
measurement. A prototype tried to read three things off 1,058 real prompts by stems:
prompts nothing loaded for that a skill *should* have taken, prompts a neighbour won that
this skill matched better, and recurring unmet requests that want a new skill. All three
came out as noise - "два гарнира в одном приёме не должно быть!" filed as a missed request
for a writing skill, a song chorus attributed to the video skill, requests grouped by
"ничего" and "знаю". Stems measure vocabulary; which skill a request was meant for is
intent, the same gap that deferred ghost triggers. Even the extreme case - a description
covering a prompt entirely while nothing loaded - gave two hits, one real.

So `improve` reports what holds: the findings with the registry's own fix, the routes
that really happened, and the neighbours' wins ranked by shared words, labelled as such.
`new --seed` answers the question the user can steer: given words they name, which prompts
carry them and where each went - and, counting only prompts that reached a skill, whether
one skill already takes most of them. On real history, `--seed заметк` found 22 prompts, 4
routed, 3 of them to the notes skill: a new skill there would be a collision. Judging
intent is left to a model layer, which is paid and so offered in the report, never run -
the rule `SKILL.md` now states for every paid layer.

### Admitted to P2 rather than P1

- **Keyword stuffing** - a description padded with domain keywords to win semantic
  retrieval it does not deserve. Measurable offline as stem-repetition density against the
  median of the tree, but the threshold is a guess until a corpus says otherwise, which is
  the same trap item 15 is parked on. Measured since, and the corpus did not say: over the
  55 real descriptions long enough to count, the share of words repeating an earlier stem
  runs continuously from 0.00 to 0.34 (median 0.20, 90th percentile 0.30) with no cluster
  to cut at. The top of the range is honest - `plugin-dev` descriptions listing the
  wordings a user types ("create a slash command", "add a command", ...), which is
  `QL003`'s territory rather than padding. Still parked; a stuffed description would have
  to be found in the wild before a line could be drawn under it.
- **Edit budget per revision** - one source treats an unbounded rewrite as the mechanism by
  which skills drift and quietly degrade, and caps how much a single revision may change.
  `--since` gives the percentage for free. Parked because "how much is too much" is another
  unmeasured threshold.

### What this changes in the prose, not in the code

Three measured findings worth carrying into the front page and `docs/`, because they
replace things this project currently asserts without a number:

- skills raise **execution reliability, not answer quality**. In one controlled comparison
  the pass rate among tasks that produced any output was identical with and without skills
  (57.1% both), while the share of tasks producing output at all went from 46.7% to 72.7%.
  The whole gain was coverage. That is a sharper answer to "what is a skill for" than this
  project gives today;
- **skills written by a model gave no measurable gain**; human-authored ones gave +16.2
  percentage points on the same benchmark. That is the argument for this repository
  existing, and it is measured rather than asserted;
- ecosystem scale and defect rate: one audit found 26.1% of community skills carrying at
  least one vulnerability; another found 534 critical and 1,467 total defects across 3,984
  public skills, with 76 confirmed malicious payloads; a marketplace census counted 40,285
  listings. The `security` module's reason for existing is currently argued from first
  principles here and could be argued from these instead.

One more number, for item 15 whenever it is revisited: an optimization study reports a
median final skill length of roughly 920 tokens, with only one to four edits accepted into
the final file. Not a description budget - a *body* budget, and the first figure this
project has seen on that question that was measured rather than guessed. `ST006` currently
budgets 15,000 bytes for `SKILL.md` on reasoning alone.

The one note left, and it now has a price on it.

**What the trigger pass cost to make real.** Item 15 is the only item here that has to
buy its evidence, so the first thing it bought was a look at the machinery underneath -
and that machinery was broken. The trigger pass ran the agent in `--permission-mode
plan`, and in plan mode the model writes a plan and never calls the `Skill` tool at all:
three runs against a real 29-skill tree produced zero skill loads. Every query would have
read as *did not fire*, every description would have scored zero recall, and the report
would have looked exactly like a tree of skills that never trigger. A threshold measured
on top of that would have been a number with nothing behind it.

Fixed in `scripts/evaluation/providers.py` and documented in `docs/evaluation.md`: an
allow-list of four read-only tools instead of plan mode, `--strict-mcp-config` for the
hole an allow-list cannot close, and `--max-budget-usd` because the routing decision
lands in the first turn or two and everything after it is work this pass throws away.
Two layers of the same mistake had to go with it - a capped run exits non-zero *and*
sets `is_error`, and reading either one alone turned every capped run into an `unusable`
one, which is once again indistinguishable from a skill that never fires. `--restricted`
was tried and rejected on evidence: it also ignores user settings, so the run loads the
bundled skills instead of the tree under test.

**The price, measured rather than estimated.** One capped run costs $0.13-$0.19. One
measurement at the recommended twenty queries and three runs each is 60 runs, about $9.
A budget sweep needs several description lengths, so one skill is roughly 240 runs, and
this page's own rule about one example being an anecdote puts a defensible threshold at
two or three skills - 500 to 700 runs. On a subscription the dollars are notional and
the real currency is the usage window: six runs moved a five-hour window by about seven
points, so the sweep is several windows, on the same account the author is working in.

**Cheaper per run was measured too, and it is not.** One of the published description
optimisers decides at the first `tool_use` in the stream and kills the process there,
which looked like a way to cut the price. Three live runs of one query, 23.09.2026: the
capped run as the pass does it today cost $0.2118 over three turns; the same with
`--max-turns 1` cost $0.2114; the early kill reached the same decision in 5.0 s instead
of 5.8 s, inside a first turn that alone costs the $0.21. The price is the first turn:
about 25,000 tokens written to a one-hour prompt cache - the system prompt with the
skill list - and it was written afresh on each of the three consecutive runs from one
directory. Stopping after the decision saves hundredths of a cent. The one lever left
is that cache write repeating, which suggests something in the prompt changes between
runs; that is a hypothesis, not checked. Also found: `RUN_BUDGET_USD = 0.12` is below
the cost of the first turn, so the cap always fires right after the decision - harmless,
but the ceiling was never what bounded a run. Four live runs moved the five-hour window
by one point.

**So the item stays unbuilt, and the reason is now a finding rather than a shrug.** The
threshold it would produce is measured against one corpus, in one house style, in one
language, competing with one particular set of neighbours - and it would ship as a rule
to people with none of those. That is the generalisation from a single example the rest
of this project refuses everywhere else. What is worth having from the item is already
here: the pass it depends on now works, and what it costs is written down.

**Description budget (15)** is the gap the registry admits to. `QL001` fires when a
description is too short to carry triggers and `SP008` fires at the specification's 1024
characters, and between those two there is no opinion at all. Neighbouring projects have
none either, and their thresholds are guesses. This project is the one that can stop
guessing: `eval --trigger` already measures precision and recall of activation, so the
same harness run against progressively trimmed descriptions turns a house style into a
measured threshold. That is also what justifies keeping the expensive half in the same
repository as the free one - it is where the free half's rules come from.

## P2

### A second intake: tools rather than papers

A reading of ten published tools in the same space - description optimisers, evaluators,
a porter between runtimes, a large audit skill - done by reading their code, not only
their pages. What was taken is recorded as what it is here; the sources stay unnamed on
purpose, and nothing was copied.

Shipped from it: **`SP020`**, a bare `<` or `>` in a description. `SP018` covered a tag;
the validator the reference skill-creation tooling ships refuses any angle bracket, and
its packager runs that validator first, so an arrow was enough for a skill that works
locally to be refused there. No real skill on this machine carries one; the fixture and
a unit check hold both sides, including the `>-` of a block scalar, which the parser
strips.

Shipped from it: **`EV010`**, should-trigger cases that restate the description word for
word. Measured before it was built, on the one real routing set on this machine: 37 of
105 positives carry a wording their own skill's description quotes - 5 of 5 for one
skill, 5 of 6 for another. The first count said 38 and was inflated by a substring match
(`план` inside `по плану`); whole words only since, and a unit check holds that line. The
first wording of the message was too strong as well: a one-verb wording two neighbours
both list makes the case a test of the fork, which can fail - so it is a count at `info`,
not a verdict. The rule reads the suite's own two case formats; the real set is in a
tree-level format this suite does not document, so the calibration ran the same function
over it through a probe rather than through `check`.

Shipped: **fake trust indicators (admitted from the intake)** - `SE007` in
`scripts/security.py`, `info`: a skill vouching for itself - a safety guarantee, an
endorsement by a named vendor, a count of users, an invitation to skip review. The item
said a regex is the whole implementation, and the only work was in how narrow. The bare
words are everywhere in honest skills: across 308 texts of 57 real skills `verified`,
`safe`, `official`, `проверено` and their kin occur 217 times, as what a skill does ("each
verified by a panel of agents", "проверено 12.09.2026") or where a neighbour came from
("official, already installed"). Only self-certifying shapes count, and a quoted one is
exempt the way `SE003` exempts a quotation. All 217 stay silent - the negative side,
measured. The positive side is fixture-only, and said so: no skill on this machine vouches
for itself. Fixture: `tests/fixtures/trust-badges`; a unit check carries real near-misses
and was watched failing with the quotation exemption removed.

Shipped: **description written for the wrong reader** - `QL015` in `scripts/quality.py`,
`QL002` turned round. The mechanism it rests on is one row of the Claude Code skills page:
with `disable-model-invocation: true`, "Description not in context". Routing wording in
such a description - an order to fire or not to fire, the user in the third person, a
list of quoted wordings - is addressed to a reader who is not there. Only that direction
was built: the reverse, a model-invoked skill whose description reads like a menu line,
is `QL002` already.

The pattern had to be narrower than `TRIGGER_RE`, and the reason is the negation trap
again, from the other side. `use when` reads as naturally to a person as to a model, so it
proves nothing and does not count. The router's verbs are ordinary verbs: a menu entry may
say hooks "trigger on save" or "не срабатывают", so only an order counts - the imperative
or infinitive (`срабатывай`, `срабатывать`), and `trigger on`/`when` not preceded by
`that`, `which` or `who`, the same split `QL014` needed between `do not fire` and `does not
fire`. The noun `триггер` is out: "настроить триггер CI" is a menu line.

Calibrated on every user-invoked skill on this machine - five installed, one in the
official marketplace. One finding, and it is real: `vpn`, whose description is entirely a
routing fence ("Никогда не срабатывай сам — ни на упоминание VPN...") in a skill the model
never sees the description of. The other five are menu lines and stay silent. Recall was
estimated on the other side of the flag: of 51 model-invoked descriptions, which are
router-addressed by construction, the pattern recognises 43. The eight it misses all open
with `Use when`, which is the price stated above rather than a gap. Fixture:
`tests/fixtures/wrong-reader`; the menu lines about hooks are a unit check, watched failing
with the verb widened back to `срабатыв\w*`.


- **LLM review as a separate optional layer** - clarity, gaps, contradictions, missing
  edge cases: the things a regex cannot reach. Hard requirement: `DETERMINISTIC` and
  `LLM REVIEW` stay separated in the output, and the model never promotes an opinion to
  an error.

### Queued from the third reading (23.09.2026)

Found while reading two published projects - a skill framework and a security scanner -
and the research on description optimisation; the projects stay unnamed, as before. None
of these is built. Each carries what it rests on and what has to happen first.

- **A script imports a package nothing declares.** Measured: the 19 real skill trees here
  carry no dependency manifest at all, and their scripts import numpy, requests, PIL,
  pymupdf, openpyxl, yaml and more. So a skill half-works on any machine missing one of
  them, and an SBOM built from manifests would be empty. Offline and stdlib-only via
  `sys.stdlib_module_names`, which exists from Python 3.10 - older interpreters need a
  decision before this ships. Free.
- **An install command not pinned to a commit or a tag**, beside `PB014`. No installer
  checks a signature today (an open feature request in Claude Code), and the one integrity
  mechanism that works now is pinning, which is how an attested marketplace in the wild
  does it. Free.
- **The trigger surface widened on update.** A description that gained trigger wordings, or
  words such as "best" and "always", between `--since` and now - a static continuation of
  `PB012`/`PB013`. Rests on two attack papers: rewriting a tool's description moved its
  selection rate from about 20% to 81% (ToolTweak, arXiv 2510.02554), and an implicit
  version moved a skill's from 15.2% to 63.5% while human reviewers caught 2.9% of it
  (ISM, arXiv 2609.02035). Free; the word list has to be calibrated on real diffs.
- **A description that retells the procedure.** One reported case: a description that
  summarised the workflow ("code review between tasks") was followed instead of the body,
  so the agent ran one review where the body asked for two; with the description cut back
  to when-to-use, it read the body. One case is an anecdote on this page's own rules, so
  the first step is measuring how many real descriptions do this at all. Free.
- **Where a skill wastes work, read from history.** In sessions where the skill loaded:
  the same command or read repeated across sessions (a candidate for a script), the
  largest tool results, tokens spent after the load. The transcript reader already exists
  in `cases --from-history`. Free and local.
- **Description optimisation, done where it is missing.** Not a rewrite loop - the
  `skill-creator` plugin already runs one with a blinded 60/40 holdout, and a production
  study found a single rewrite from the false positives and negatives captures most of
  the gain, with iteration count moving F1 by under 0.5% against a 0.78% multi-seed noise
  floor (arXiv 2606.30775). What nothing checks is the neighbours: a description tuned to
  fire more takes requests from the skills beside it, which is the attacks above done in
  good faith. So: re-run the nearest neighbours' trigger sets after an edit and fail on
  their recall dropping; repeat runs for a noise floor, so "better" inside it reads as no
  change; and report a large train-validation gap as the study's own diagnosis - scopes
  that genuinely overlap, which wording cannot fix. The code is free, the runs are paid.

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

**Version and changelog analysis** - a version bumped with no changelog entry. Where the
evidence is not there, no finding, and on this machine it is never there: 13 plugins in
the official marketplace declare a version, and not one skill or plugin anywhere here
ships a changelog. A rule that cannot fire on any real input cannot be watched working.
The other half the item named - a breaking change with too small a bump - is `PB011`
already, which asks for more than a patch; demanding a major for every break past 1.0
would be a change of convention made with no history to calibrate it on.

**Ghost triggers** - a trigger phrase in the description that nothing in the body
serves: the skill fires on that wording and then has nothing to do about it. `CS001` reads
the outcome half of a description against the body; this would read the trigger half.

Deferred on a measurement, not on a hunch. The prototype split every trigger zone at the
same commas `QL003` uses, dropped exclusions with `EXCLUSION_RE`, and called a phrase a
ghost when none of its stems appeared anywhere in the skill's texts. On the 51
model-invoked skills on this machine it read 459 phrases and flagged 39, and not one of
the four candidates that looked real survived being checked: `commit` serves "отправь на
гитхаб" through `git push` and `github.com` - the same thing, in the other alphabet; `pdf`
serves "добавь в базу" by handing its text to `konspekt`. The rest were prose fragments
the commas cut loose ("когда он просит") and the items of an exclusion list separated from
the "НЕ запускайся на рутине:" that governed them. A trigger is served by a *procedure*,
and a stem test measures *vocabulary*; that gap is the whole false-positive rate.

The narrow version was measured too: a trigger that names a literal artefact - a file, a
`/command`, a backticked token - absent from every text of the skill. 44 such tokens in
48 trigger zones, 8 absent. Six were neighbours' names in a deferral ("это `trener`")
that the split had cut away from its lead-in, one was context rather than a promise ("after
`/maker-setup`"), and one is arguable: `yadro` answers "сделай tech.md" with a file called
`CONTRACTS.md`. One example is an anecdote on this page's own rules, so nothing shipped.

What survives for whenever this is picked up: the split has to be at the level
`branch_segments` uses - whole sentences, with named neighbours dropped - or every
disclaimer turns into a trigger; and literal artefacts are the only part checkable
without a model.
Deciding whether a procedure serves a wording is the LLM review layer's job, not a
pattern's.

**Declared against actual (20)** - compare what a skill's `allowed-tools` declares against
what its code and instructions actually need, in both directions: a tool it needs and did
not declare (the skill silently half-works), and a privilege it declared that nothing uses
(the trust boundary widened for no reason). SkillSec-Eval names the first *permission
deception*; SkillEval's behavioural-integrity check is the second built as a whole system.

Deferred because there is nothing here to calibrate it against, and this page's own rule
is that a rule is not finished until it has been watched on a real corpus rather than on a
fixture its author wrote. Both corpora on this machine were probed, and the halves sit on
opposite sides of the tree: of the 29 installed skills, **none** declares `allowed-tools`
at all, though nine bundle scripts with real capabilities; of the 31 skills in the official
plugin marketplace, **eight** declare `allowed-tools` and **none** bundles a script. Not
one skill anywhere on this machine carries both halves of the comparison.

The probe was still worth running, because it showed the rule would have been mostly
noise. Inferring *what a skill needs* from its prose is the weak half, and it failed in
both directions on the eight real declarations: the over-declaration side flagged seven of
eight, all false - `Read` is declared because the skill obviously reads things, while the
pattern only counts a need when a `references/` link resolves - and the single
under-declaration it found was false too, matching the verb in "There's **no** token to
**save**". The negation trap, twice in one day, in a second module.

What survives for whenever this is picked up: the needs side has to come from resolved
structure - a bundled script the body points at, a reference link the structure engine
already follows - and never from prose. That halves the rule and makes the remaining half
checkable.

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
