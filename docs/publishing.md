---
title: "Publishing an Agent Skill - the gate before it leaves your machine"
description: >-
  What has to be true before an AI Agent Skill is published: personal paths, private
  material, licensing, version drift, documentation language, and what the publish
  check cannot see.
---

# Publishing

*Everything on this page is invisible while the skill only ever runs at home, and
obvious the moment somebody else installs it.*

```bash
python scripts/sqs.py all ./my-skill --strict --harness all
python scripts/sqs.py publish ./my-skill --lang en
```

`publish` is deliberately **not** part of `sqs.py check`: half its findings are
correct-and-intended for a skill that stays private.

## The gate

| Rule | What it catches |
|---|---|
| `PB003` | an absolute path naming your account - it resolves on one machine only, and tells everyone your username |
| `PB006` | a pointer into material the reader has no copy of: a private vault, an internal repository, an email address |
| `PB001` | no `license:` field and no LICENSE file - nobody can legally reuse it |
| `PB002` | no README: `SKILL.md` talks to the agent, and nothing talks to the human deciding whether to install |
| `PB005` | the manifest and the skill disagree about which version this is |
| `PB004` | documentation in a language the repository does not declare |

Plus, from the other modules and worth re-reading before a release:

- `SP013` - repository furniture (README, Makefile, `package.json`) shipping inside the
  skill folder, where every install carries it.
- `SP016` - an asset over a megabyte. It travels with every install.
- `SE006` - the same personal path, from the security side.
- `ST005` - orphans. A published skill carrying files nothing loads is a published skill
  nobody can maintain.

## The order that works

1. `sqs.py fix ./my-skill --apply` - the mechanical repairs.
2. `sqs.py all ./my-skill --strict` - everything, warnings counting as failures.
3. `sqs.py compat ./my-skill --harness all` - see [Compatibility](compatibility.md).
4. `sqs.py eval ./my-skill --trigger` - a skill that never fires is worth nothing,
   however good its instructions. See [Evaluation](evaluation.md).
5. Read the skill yourself, against
   [`references/writing-rubric.md`](https://github.com/letsloose501/skill-quality-suite/blob/main/references/writing-rubric.md).

## What the publish check cannot see

- Whether the **description** claims a branch the instructions do not serve. That is a
  reading job, and the rubric is the tool for it.
- Whether a **bundled script** is something a stranger should run. The security module
  reads the text; it does not execute anything.
- Whether the skill is **worth installing**. `sqs.py eval --runtime` is the closest a
  machine gets: the same task with the skill and without it. A skill that changes
  nothing is load the agent pays for and gets nothing back.

## Turning the gate on for an existing repository

A suite switched on over a tree that already has findings reports three hundred of them,
the build goes red, and the gate is turned off the same afternoon. That is what the
findings baseline is for:

```bash
python scripts/sqs.py baseline create      # record what is already there
python scripts/sqs.py check --baseline     # from now on, fail on NEW findings only
python scripts/sqs.py baseline show        # the queue, dated
```

The recorded findings stay in the file, counted and dated. It is a queue, not a bin.

## See also

- [`references/publishing.md`](https://github.com/letsloose501/skill-quality-suite/blob/main/references/publishing.md)
- [Skill validation](skill-validation.md) · [Skill security](skill-security.md) · [Evaluation](evaluation.md)
