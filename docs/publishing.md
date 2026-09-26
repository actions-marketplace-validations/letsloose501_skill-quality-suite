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

## Should the person who installed it take this update

The same diff, read from the other side. PB010 and PB011 ask whether the author's number
describes their change; these two ask whether somebody who read and trusted the earlier
copy is still looking at the same thing. A skill keeps the trust it earned on install
while its content moves underneath, and nothing else in the suite watches that.

| Rule | What it catches |
|---|---|
| `PB012` | the update pre-approves a tool or scope the earlier copy did not, or a bundled script gained network access (`CB001`) or process spawning (`CB002`) |
| `PB013` | the declared version is lower than the one at `--since` |

`PB012` fires whatever the version did, including a correct minor bump: the number can be
right and the reader can still never have agreed to the new reach. It compares
`allowed-tools` entry by entry, with the scope: `Bash(git log *)` becoming `Bash(git *)` is
growth, and the reverse is not, because a scope covers a narrower one that matches it as a
glob. A rewrite that only *looks* narrower and does not match that way is reported as new -
a glance for the reader, where the other mistake would be a widening waved through. Reading
the environment (`CB003`) does not count as reach on its own: it is reported on every
`check` anyway, and getting a secret off the machine takes one of the other two.

`PB013` reads only numbers that both parse as `major.minor.patch`. A rollback shipped as a
new, higher version carrying the old content says what happened; a number that goes down
is how a fixed hole comes back without anybody editing anything.

```bash
sqs.py publish ./skills --since v2.0.0     # everything this release gained since the last
```

## Does the README send people to the right place

`PB014` reads the README as payload rather than as a box to tick: it is the file that
tells a stranger what to type. A project that moved while its install instructions did
not sends every new user to an account that is no longer the author's, and whoever
registers that name next receives the installs.

Two shapes, both checked against what is on disk and nothing else:

- an install command - `npx skills add`, `/plugin marketplace add`, `git clone`, a
  `raw.githubusercontent.com` URL - naming this project's repository under an owner that
  none of the checkout's git remotes, and no marketplace entry beside it, know;
- `/plugin install <this plugin>@<marketplace>` naming a marketplace other than the one
  that lists the plugin.

Only a disagreement about *this* project counts: the repository name has to match one the
checkout is known to live under. A README that installs somebody else's repository is a
catalogue doing its job and is never reported. A fork that tells people to install from
upstream is correct, and says so to the rule once upstream is a git remote. The README is
read beside the skill, one level up, and at the plugin root; one shared by several skills
is reported on the first of them.

## Does the repository ship inside the skill

`PB015` fires when `SKILL.md` sits at the root of its git repository beside `tests/`,
`docs/`, `examples/` or `.github/`. The cross-agent installer copies a skill's folder, and
a `SKILL.md` at the root shadows anything nested below it, so the folder is the whole
repository: the test corpus, the documentation site and CI land in every user's skills
directory.

That matters more than disk space. Skill marketplaces run security scanners over what a
skill ships, and a scanner reads a test fixture of an attack as an attack. This project
learned it on itself: on skills.sh, two of three partner audits failed it. One cited a
real flaw, since fixed - the suite imported a check script out of the folder it was
analysing - and, beside it, the fixture of a malicious skill the corpus tests against and
the way the test runner assembled a fake token and hidden characters. The other rated that
fixture as malware. Material the agent never loads decided most of both verdicts.

The fix is layout: move the skill into `skills/<name>/` and keep tests, docs and CI beside
it. `.sqsignore` does not help here; it hides a path from this suite, not from the
installer or anybody else's scanner. The rule stays silent for a nested skill, even one
with a `docs/` of its own, because that folder is not the repository.

Two facts about marketplace audits worth knowing before you publish, from the
[skills.sh API documentation](https://www.skills.sh/docs/api): audit results are public at
`/api/v1/skills/audit/{owner}/{repo}/{skill}`, one row per partner with `status`,
`riskLevel` and `auditedAt`; and they "are generated automatically after a skill is
installed for the first time". Commits alone did not move this project's audit date across
fifty of them; an install of the new version on 26.09.2026 brought a fresh audit from all
three partners within three minutes - Gen Agent Trust Hub `SAFE`, Socket with no alerts,
Snyk `LOW`, where two of them had failed the old layout. Whether every install re-audits,
or only a changed version, the page does not say. Either way the version that gets
installed is the version that gets judged: run `sqs.py all --strict` before publishing.

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
   [`references/writing-rubric.md`](https://github.com/letsloose501/sqs-skills/blob/main/skills/skill-quality-suite/references/writing-rubric.md).

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

- [`references/publishing.md`](https://github.com/letsloose501/sqs-skills/blob/main/skills/skill-quality-suite/references/publishing.md)
- [Skill validation](skill-validation.md) · [Skill security](skill-security.md) · [Evaluation](evaluation.md)
