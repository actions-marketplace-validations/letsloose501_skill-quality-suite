---
title: "Publishing an Agent Skill - the gate before it leaves your machine"
description: >-
  What has to be true before an AI Agent Skill is published: personal paths, private
  material, licensing, version drift, whether the version still describes the content,
  documentation language, and what the publish check cannot see.
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

## Does the version still say what this is

`PB005` above catches two files contradicting each other. The failure nobody notices is
the opposite one: the instructions moved, the number did not, and nothing in the
repository contradicts anything. A skill that was improved and still carries its old
version cannot be told apart from the one somebody already installed, and that stays
true until they read the diff - which is what a version number exists to save them.

Two rules, both opt-in behind `--since`, because a comparison needs a stated *before*:

| Rule | What it catches |
|---|---|
| `PB010` | files under the skill changed since `--since` and the declared version did not move |
| `PB011` | `name`, the invocation mode or `allowed-tools` changed, and only the patch digit moved |

```bash
sqs.py publish ./my-skill --since v1.3.0            # a git ref: since the last release
sqs.py publish ./my-skill --since ~/.claude/skills  # a directory: the copy already installed
```

The directory form is the one worth knowing about. Git answers *did I bump it since the
last tag*; a directory answers *the copy I ship and the copy I edit have drifted - which
one is `1.2.0`*, and that is the question a version number was invented for. A relative
path is looked for beside the skills directory first, so it can live in a config.

Neither rule rewrites anything, and `fix --apply` will not touch a version either. The
number is a claim about your own work, and a tool that makes the claim on your behalf has
told your users something you never said. The convention the rules assume is the usual
one: instructions change, bump the patch `0.0.1` at a time; the way the skill is called
changes, bump more than that.

Three things they deliberately stay quiet about. A skill that did not exist at `--since`
- there is no claim yet to go stale. A skill that declares no version at all - there is
no claim to go stale either, and inventing one is the author's decision, not a lint
finding. And a file hidden by `.sqsignore` is not a change, the same way it is not
anything else: what the suite does not read, it makes no claim about.

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
