# skill-quality-suite

A quality suite for [Agent Skills](https://agentskills.io): eight checks over a
`SKILL.md`, one command each. No dependencies, Python standard library only.

```
python scripts/sqs.py check ./my-skill
python scripts/sqs.py compat ./my-skill --harness all
python scripts/sqs.py explain ST008
```

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
| `evals` | whether the skill fires on the wording a human uses | when a neighbour's description moves |
| `publish` | personal paths, missing license, version drift | the moment it leaves your machine |
| `fix` | the repairs with exactly one correct answer | - |

## Install

As a skill, so your agent can run it on itself:

```bash
git clone https://github.com/letsloose501/skill-quality-suite \n  ~/.claude/skills/skill-quality-suite
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
fix; `sqs.py rules` lists all 65.

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
```

A target is a path or a skill name. Pointed at a plugin, the suite finds the skills
inside it and says plainly that the plugin's other components were not analysed:
checking `plugin.json`, hooks, commands and agents is a different tool's job, and a
half-done version of it would imply the rest had been looked at.

Flags: `--format text|json|github`, `--strict` (warnings count as failures), `--quiet`,
`--skills-dir`, `--config`.

Exit codes: `0` clean, `1` findings that count as failures, `2` usage error. So
`--strict` is what a CI step wants:

```yaml
- run: python scripts/sqs.py check . --harness all --strict --format github
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

Write down *why* next to the entry. A silenced rule with no reason gets un-silenced by
the next person who reads the file, including you.

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
`sqs.py rules --audit` fails when an engine emits a code the registry does not carry, or
the registry carries a row nothing emits.

**`scripts/check_skills.py` is the structure engine**, imported rather than shelled out
to. It also runs standalone as the single-file linter this repository used to be, and
works as a `PostToolUse` + `Stop` hook pair - `--mark` records which skills a turn
touched, `--stop` checks those and blocks the stop on breakage.

## References

- [writing-rubric.md](references/writing-rubric.md) - the reading pass no script can do:
  the description as a context pointer, the two loads, the information hierarchy,
  completion criteria, leading words, pruning. The vocabulary is Matt Pocock's, from
  [`writing-for-agents`](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents).
- [creating-a-skill.md](references/creating-a-skill.md) - the order for building a new
  skill, and for reworking an old one.
- [agent-compatibility.md](references/agent-compatibility.md) - the harness table and
  what each row rests on.
- [publishing.md](references/publishing.md) - the gate before a skill leaves the
  machine.

## Notes

`sqs.py evals` delegates to an `evals/run_evals.py` beside your skills if you keep one.
This repository ships no routing harness, so without one the module reports that nothing
verifies your descriptions, and stops.
