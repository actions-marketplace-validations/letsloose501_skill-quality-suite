---
title: "Agent Skill compatibility - will the skill work on another agent"
description: >-
  Cross-runtime portability for Agent Skills: how a skill is classified per harness
  (Claude Code, Codex, Cursor, Gemini CLI, Antigravity, OpenCode, Cline, Roo Code,
  Windsurf, GitHub Copilot) and why UNKNOWN is never NOT_SUPPORTED.
---

# Compatibility

*This is the check your own machine can never make for you. It works here; whether it
works anywhere else is a question your own setup cannot answer.*

```bash
python scripts/sqs.py compat ./my-skill --harness all
python scripts/sqs.py compat ./my-skill --harness cursor,codex --format json
python scripts/sqs.py harnesses --show     # every adapter and the page it rests on
```

## How it works

The skill is reduced to a list of **features** - a frontmatter field, a directory, a
tool name, a hard-coded path into someone's skill folder - and each feature is put to
ten harness adapters:

```
Skill -> normalized model -> harness adapters -> compatibility engine -> report
```

| Verdict | Meaning |
|---|---|
| `PORTABLE` | documented as read here |
| `ADAPTABLE` | works, or works after a mechanical change |
| `HARNESS_SPECIFIC` | real here, dead or meaningless elsewhere |
| `INVALID` | this harness refuses it |
| `UNKNOWN` | the documentation does not say |

## UNKNOWN is never NOT_SUPPORTED

Every row in the registry rests on that project's own documentation. Where the
documentation is silent, the answer is `UNKNOWN` rather than an invented
incompatibility.

This is the whole discipline of the module. An invented incompatibility reads exactly
like a real one, and a reader has no way to tell them apart - so one invented row makes
every other row worth less. An empty limits table means **unchecked**, which is not the
same as **passed**.

## The ten harnesses

Claude Code, OpenAI Codex, Cursor, Gemini CLI, Antigravity, OpenCode, Cline, Roo Code,
Windsurf, GitHub Copilot. `sqs.py harnesses` lists them with the documentation page each
one rests on.

Adding a harness is one file in `scripts/harnesses/` and nothing above it changes: the
registry finds it, the engine classifies through it, the report prints it. Its
declarations come from that project's own documentation, and what the documentation does
not state is left out.

## What travels badly

- **A hard-coded path into a harness's skill tree** (`~/.claude/skills/other/...`). The
  one portability failure that survives every other check: the skill runs perfectly on
  the machine it was written on, and on another harness the path resolves to nothing -
  in silence, because a missing reference is a skipped step, not an error.
- **A frontmatter field outside the specification** (`CP002`). Real harnesses warn and
  load; the strict reference validator refuses. The suite names which harnesses read the
  field rather than telling you to delete it, because deleting it switches the behaviour
  off.
- **A value a runtime cannot read** (`CP001`), for instance `disable-model-invocation:
  maybe`.
- **A directory the harness does not document** (`CP006`, `CP007`). Usually fine, since
  a skill's own folder becomes readable once the skill activates - which is exactly what
  the recommendation says, rather than reporting it as breakage.

## Reading the report

```
AI Skill Compatibility

Skill: my-skill

  Claude Code     ✓ Compatible
  Cursor          ⚠ Adaptation required
  Antigravity     ✓ Compatible
  GitHub Copilot  ? Unknown

  Portability:
    Portable:          82%
    Adaptable:          2%
    Harness-specific:  15%
```

`--format json` gives the same analysis for another tool to consume, feature by feature
and harness by harness.

## See also

- [`references/agent-compatibility.md`](https://github.com/letsloose501/skill-quality-suite/blob/main/references/agent-compatibility.md)
  - the full table, the source behind each row, and how to add a harness without guessing
- [Publishing](publishing.md) - the rest of what has to be true before a skill leaves your machine
