# skill-quality-suite

[![quality](https://github.com/letsloose501/skill-quality-suite/actions/workflows/quality.yml/badge.svg)](https://github.com/letsloose501/skill-quality-suite/actions/workflows/quality.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python: 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://github.com/letsloose501/skill-quality-suite/actions/workflows/quality.yml)
[![no dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#install)
[![skills.sh](https://skills.sh/b/letsloose501/skill-quality-suite)](https://skills.sh/letsloose501/skill-quality-suite)
[![GitHub Marketplace](https://img.shields.io/badge/marketplace-skill--quality--suite-2ea44f?logo=github&logoColor=white)](https://github.com/marketplace/actions/skill-quality-suite)

**A quality, linting, security and validation toolkit for AI Agent Skills.** It
validates a `SKILL.md` against the [Agent Skills specification](https://agentskills.io/specification),
lints the instructions an agent will actually follow, scans a skill for secrets and
prompt injection before you install it, checks whether it will work on another agent,
and measures whether it improves the agent's work at all.

No dependencies: the static half is Python standard library only, offline and
deterministic. The evaluation half runs an agent, costs money, and never runs unless you
name it.

```bash
python scripts/sqs.py check    ./my-skill                # skill lint: the everyday five
python scripts/sqs.py security ./my-skill                # before you install a stranger's skill
python scripts/sqs.py compat   ./my-skill --harness all  # will it work anywhere else
python scripts/sqs.py eval     ./my-skill --trigger      # does it actually fire
python scripts/sqs.py explain  ST008                     # what a finding means, and the fix
```

Use it when:

- a skill **does not fire**, fires on a neighbour's work, or half-works and silently
  skips steps;
- you are about to **install a skill somebody else wrote**, and want to know what it can
  do to your machine first;
- you **renamed** a file, a heading or a skill, and something now points at nothing;
- you are about to **publish** a skill and need the personal paths, the licence and the
  version drift caught before it leaves;
- you changed a description and want to know whether the skill got **better or worse**.

Harnesses it classifies portability for: **Claude Code, OpenAI Codex, Cursor, Gemini
CLI, Antigravity, OpenCode, Cline, Roo Code, Windsurf, GitHub Copilot.**

📖 **[Documentation](https://letsloose501.github.io/skill-quality-suite/)** ·
🧪 **[Worked examples with real output](examples/)** ·
📋 **[All 70 rules](docs/quality-rules.md)**

| Question | Command |
|---|---|
| Can it load? Is it valid? | `check` (structure, spec) |
| Is it worth loading? | `quality` |
| Is it safe to install? | `security` |
| Is it portable? | `compat` |
| Does it fire? | `eval --trigger` |
| Does it actually help? | `eval --runtime` |
| Did the last change make it worse? | `eval --compare v1 v2` |
| Can it be published? | `publish` |

## Why

A skill loads in two stages: `SKILL.md` first, then its references through the links
inside it. When a link breaks, **nothing crashes and nothing complains.** The agent
silently skips the step, and the only symptom is that the work came out worse than
usual, with no explanation.

That is the shape of almost every skill defect. It survives for months because there is
nothing to notice. The suite turns each class of silent breakage into a loud one, and
sorts them by *when* they would have bitten:

| Module | What it catches | When it bites |
|---|---|---|
| `structure` | broken links, orphans, section pointers, budgets | today, silently |
| `spec` | layout, unclosed fences, reserved words, asset weight | on publication |
| `quality` | a description that never says *when*, vague bounds, placeholders | every run, a little |
| `compat` | what will not survive a move to another agent | on somebody else's machine |
| `security` | secrets, destructive commands, injection, hidden characters | when you install a stranger's skill |
| `evals` | the eval files and the routing invariants | when a neighbour's description moves |
| `eval` | does it fire, does it help, did the last edit make it worse | after every change, if you let it |
| `publish` | personal paths, missing license, version drift | the moment it leaves your machine |
| `fix` | the repairs with exactly one correct answer | - |

## Install

As a skill, through the cross-agent installer - it works for Claude Code, Cursor,
Codex, Windsurf, Gemini and the rest of the agents `skills` supports:

```bash
npx skills@1 add letsloose501/skill-quality-suite
```

Or as a plain clone, if you would rather see what lands:

```bash
git clone https://github.com/letsloose501/skill-quality-suite \
  ~/.claude/skills/skill-quality-suite
```

Or as a plain tool: clone anywhere and call `scripts/sqs.py`. It finds the skills folder
on its own, or takes `--skills-dir`.

## Multi-harness compatibility

The one thing about a skill you cannot check on your own machine. It works here; whether
it works anywhere else is a question your own setup can never answer.

```
python scripts/sqs.py compat ./my-skill --harness all
```

```
AI Skill Compatibility

Skill: my-skill

  Claude Code     ✓ Compatible
  Cursor          ⚠ Adaptation required
  Antigravity     ✓ Compatible
  GitHub Copilot  ? Unknown

  Issues:   0
  Warnings: 2
  Unknown:  1

  Portability:
    Portable:          82%
    Adaptable:         2%
    Harness-specific:  15%
```

Ten harnesses: Claude Code, Codex, Cursor, Gemini CLI, Antigravity, OpenCode, Cline,
Roo Code, Windsurf, GitHub Copilot. Each feature of the skill - a frontmatter field, a
directory, a tool name, a hard-coded path into someone's skill folder - is classified
per harness as `PORTABLE`, `ADAPTABLE`, `HARNESS_SPECIFIC`, `INVALID` or `UNKNOWN`.

**`UNKNOWN` is not `NOT_SUPPORTED`.** Every row in the registry rests on that project's
own documentation, and where the documentation is silent the answer is `UNKNOWN` rather
than an invented incompatibility. An invented one reads exactly like a real one, and
that is how a compatibility tool stops being believed.

Adding a harness is one file in `scripts/harnesses/`. The engine above it does not
change:

```
Skill -> normalized model -> harness adapters -> compatibility engine -> report
```

See [references/agent-compatibility.md](references/agent-compatibility.md) for the
table, the source behind each row, and how to add one without guessing.

## Reading the output

```
⛔ SP004  `name: video-tools` does not match the folder `video` (SKILL.md)
⚠️  ST006  SKILL.md is 21370 B > the 15000 B budget (SKILL.md)
·   QL006  as needed - lines 191, 295 (SKILL.md:191)
```

- **⛔ error** - fix it. Nothing here is cosmetic.
- **⚠️ warning** - a decision, not a defect. An orphan file is either unwired or no
  longer needed, and only you know which.
- **· info** - a nudge. Real, small, safe to leave.

Every finding carries a rule code. `sqs.py explain ST008` prints the reasoning and the
fix; `sqs.py rules` lists all 70.

## Commands

```
sqs.py check [target]        structure + spec + quality + compat + security
sqs.py all [target]          the above plus publish
sqs.py <module> [target]     one module on its own
sqs.py compat . --harness cursor,codex
sqs.py fix . --apply         the mechanical repairs
sqs.py explain <CODE>        what a code means and how to fix it
sqs.py rules [--module X]    the registry
sqs.py harnesses [--show]    the harness adapters and their sources
sqs.py new <name>            scaffold a skill that already passes
sqs.py evals . --init        scaffold the eval files
sqs.py eval ./s --trigger    does it fire, and only when it should
sqs.py eval ./s --runtime    the task set, with the skill and without it
sqs.py eval ./s --compare v1 v2    what the last edit moved
sqs.py baseline create       record what a tree already has, so new findings stand out
```

`eval` is the only command here that spends money, and it says so before it does.
`sqs.py eval ./my-skill` with no layer named runs nothing: it prints how many agent runs
each layer would take and stops.

- `--trigger` sends each query to a headless session and counts what loaded. It reports
  the confusion matrix - true and false positives and negatives, precision, recall, F1 -
  beside the cases it came from, split 60/40 into train and validation so a description
  tuned on the failures can be checked for generalising. **F1 is printed, not scored**:
  it weighs a miss and a false fire equally, and in a tree of skills they are not equal.
- `--runtime` runs the task set twice - `claude --bare` for the baseline, `--plugin-dir`
  with the skill alone for the treatment - and reports task success, tool calls, turns,
  time, tokens, cost, forbidden tools and safety violations. A task with no assertions
  comes back `ungraded`, never as a pass; a metric the provider never reported comes
  back `n/a`, never as zero.
- `--save <label>` stores a run and `--compare` diffs two. Quality falling fails the
  gate; cost rising is reported and does not, unless `--fail-on-cost`.

Every other check reads text, costs nothing and works offline.

A target is a path or a skill name. Pointed at a plugin, the suite finds the skills
inside it and says plainly that the plugin's other components were not analysed:
checking `plugin.json`, hooks, commands and agents is a different tool's job, and a
half-done version of it would imply the rest had been looked at.

Flags: `--format text|json|github|sarif|board`, `--strict` (warnings count as failures),
`--quiet`, `--changed` (only what the diff touched), `--baseline`, `--min-confidence`,
`--score`, `--skills-dir`, `--config`.

Exit codes: `0` clean, `1` findings that count as failures, `2` usage error.

## In CI

```yaml
- uses: letsloose501/skill-quality-suite@v1
  with:
    path: .
    strict: "true"
    harness: all
    upload-sarif: "true"        # needs security-events: write on the job
```

The action is on the [GitHub Marketplace](https://github.com/marketplace/actions/skill-quality-suite).

The action annotates the diff, writes SARIF for code scanning, and fails the job on the
findings that count. `changed: "true"` checks only the skills the diff touched, and
`baseline: "true"` reports only what the baseline file does not already carry - which is
how the gate goes on over a tree with three hundred existing findings without turning
the build red on day one.

Or plainly, with no action at all:

```yaml
- run: python scripts/sqs.py check . --harness all --strict --format github
```

Before the commit, rather than after:

```yaml
repos:
  - repo: https://github.com/letsloose501/skill-quality-suite
    rev: v1
    hooks:
      - id: skill-quality-suite            # the skills this commit touches
      - id: skill-quality-suite-security   # for a skill that arrived from elsewhere
```

## Silencing a finding

Three scopes, for findings that are correct-and-intended:

- **a line** - `sqs-allow: SE002` on it or just above it, for one quotation of a
  pattern;
- **a file** - `sqs-allow-file: SE001, SE002` in its first 25 lines, for a file whose
  whole job is to hold the patterns;
- **the tree** - `sqs.config.json` beside the skills:

```json
{
  "rules": { "ST005": "off" },
  "ignore": ["scratch-skill"],
  "allow_dirs": ["templates"],
  "harnesses": ["claude-code", "cursor"],
  "lang": "en"
}
```

A fourth scope, for material that is not skill payload at all: `.sqsignore` at the skill
root, one path glob per line. What it lists is not read, so nothing about it is checked
and nothing about it is claimed - the difference from `sqs-allow`, which says "found it,
and it is meant to be there". This repository's own `.sqsignore` carries `tests/`,
because the corpus is full of deliberately broken skills.

Write down *why* next to the entry. A silenced rule with no reason gets un-silenced by
the next person who reads the file, including you.

`--baseline` and `--min-confidence` are the other two ways to make a report survive
contact with an existing tree, and neither hides anything: the baseline keeps every
recorded finding in a dated file that `sqs.py baseline show` prints, and the confidence
floor filters by how much of the judgement is the machine's, not by how much you want to
hear it. Every rule carries a detection confidence and a false-positive risk, printed by
`sqs.py explain <CODE>`.

## License

MIT. See [LICENSE](LICENSE).

## Design notes

**Precision over coverage.** A rule earns its place by being checkable: it names a file
and a line, or it does not ship. Heuristics that cannot point at anything live in
[references/writing-rubric.md](references/writing-rubric.md), where a human applies
judgement. A linter that cries wolf stops being read, and then the real findings go
unread with it.

Several rules here were narrowed after they fired on correct code: a keyword-stuffing
check that counted commas and flagged half a skill tree now compares phrases and prints
the pair; instruction-override detection ignores quotations, so a skill that teaches an
agent to refuse an injection can write the phrase down; a zero-width space in front of a
fence is recognised as fence escaping rather than a Trojan Source attack, and the fixer
leaves it alone.

**One registry.** `scripts/rules.py` is the single place a rule code is defined.
`sqs.py rules --audit` fails when an engine emits a code the registry does not carry,
when the registry carries a row nothing emits, or when a rule has no confidence and
false-positive grading.

**Every rule has been watched firing.** `tests/fixtures/` holds small skills trees with
an `expect.json` beside each: the codes the run must report, and the codes it must not.
All 69 rules with an engine have a positive case, and the two cases that matter most -
`clean/` and `escape-hatches/` - must report **nothing at all**. A linter is judged by
what it stays quiet about.

```
python tests/run_tests.py              every case, then the unit checks
python tests/run_tests.py --coverage   which rules no case observes firing
```

**The evaluation layer is tested without a model.** `--provider fake` replays canned runs
from a JSON script, so the confusion matrix, the baseline/treatment split and the
regression gate have tests that cost nothing. What that cannot test is whether a real
agent behaves the way the script says, and the reports never pretend otherwise.

**`scripts/check_skills.py` is the structure engine**, imported rather than shelled out
to. It also runs standalone as the single-file linter this repository used to be, and
works as a `PostToolUse` + `Stop` hook pair - `--mark` records which skills a turn
touched, `--stop` checks those and blocks the stop on breakage.

## Documentation

The [documentation site](https://letsloose501.github.io/skill-quality-suite/) is the
same material organised for someone arriving from a search engine:

- [Skill validation](docs/skill-validation.md) - validating `SKILL.md` against the
  Agent Skills specification, the pointers that break in silence, and the
  instruction-quality rules a strict validator does not cover
- [Skill security](docs/skill-security.md) - secrets, destructive commands, prompt
  injection, exfiltration and hidden Unicode in a skill you did not write
- [Quality rules](docs/quality-rules.md) - all 70, generated from the registry
- [Compatibility](docs/compatibility.md) - the ten harnesses, the five verdicts, and why
  `UNKNOWN` is never `NOT_SUPPORTED`
- [Evaluation](docs/evaluation.md) - trigger evals, the baseline/treatment comparison,
  the regression gate
- [Publishing](docs/publishing.md) - the gate before a skill leaves your machine

Two walkthroughs rather than references:

- [How to validate an AI Agent Skill](docs/how-to-validate-an-agent-skill.md)
- [How to secure Agent Skills](docs/how-to-secure-agent-skills.md)

## References

The working detail, written for whoever is editing a skill rather than choosing a tool:

- [writing-rubric.md](references/writing-rubric.md) - the reading pass no script can do:
  the description as a context pointer, the two loads, the information hierarchy,
  completion criteria, leading words, pruning. The vocabulary is Matt Pocock's, from
  [`writing-for-agents`](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents).
- [creating-a-skill.md](references/creating-a-skill.md) - the order for building a new
  skill, and for reworking an old one.
- [agent-compatibility.md](references/agent-compatibility.md) - the harness table and
  what each row rests on.
- [evaluating.md](references/evaluating.md) - the three eval questions: triggering with
  its train/validation split, the baseline/treatment comparison, the regression gate,
  and the part that stays a human's job.
- [publishing.md](references/publishing.md) - the gate before a skill leaves the
  machine.

## Notes

`sqs.py evals` delegates to an `evals/run_evals.py` beside your skills if you keep one.
This repository ships no routing harness, so without one the module reports that nothing
verifies your descriptions, and stops.
