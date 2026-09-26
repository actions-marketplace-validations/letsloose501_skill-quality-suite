# Security

## Reporting

Open an issue, or mail the address on the GitHub profile if the finding should not be
public first. There is no bounty and no SLA; this is one person's project.

## What this repository does with untrusted input

The suite is pointed at skills nobody has vouched for. That is the advertised use, so
the trust boundary is a design constraint rather than a footnote:

- **The static half never executes the tree it reads.** It parses files. The structure
  engine is the `scripts/check_skills.py` the skill ships, imported like any other module
  of the suite; no file from the target is ever imported. A target's
  `evals/run_evals.py` is reported as not executed (`EV006`) instead of run, and only
  `--trust-target` turns that on, for a tree you own.
- **The evaluation half does run an agent**, with whatever permissions you give it. It
  costs money, it needs a CLI installed, and nothing in it runs unless you ask for it by
  name. It refuses a skill that can reach the network or spawn processes unless you pass
  `--trust-target`. Do not point `eval` at a skill you have not read.
- **No network in the static half**, no dependencies outside the standard library.
- **Your history stays local.** `cases --from-history`, `improve` and `discover` read
  Claude Code transcripts from your own disk and print to your terminal; nothing is sent
  anywhere and nothing is written.

## What an install gives you

The skill is `skills/skill-quality-suite/`: `SKILL.md`, `references/` and `scripts/`. An
installer copies that folder and nothing else. The test corpus, the documentation site and
CI live beside it in the repository, because a detector's test corpus has to contain what
it detects, and marketplace scanners read everything in a skill's folder as the skill.
CI copies the skill folder out on its own and requires `security` to report nothing on it
(`tests/run_tests.py`), so that cannot quietly change.

## Scanner reports on this repository

A tool that detects secrets, destructive commands and prompt injection has to contain
examples of all three, or its rules have never been watched firing:

- the attack-shaped strings are **not checked into git**. `tests/fixtures/malicious/`
  holds an inert skill; the patterns under test are assembled from parts by
  `tests/run_tests.py` at run time;
- the detection patterns themselves are regular expressions in `scripts/security.py`, which
  is what a detector is made of.

A scan of the whole repository that reports the corpus or the rule documentation has
found the test material, not an attack. Anything else, please report it.
