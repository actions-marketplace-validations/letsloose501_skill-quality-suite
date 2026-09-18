# Security

## Reporting

Open an issue, or mail the address on the GitHub profile if the finding should not be
public first. There is no bounty and no SLA; this is one person's project.

## What this repository does with untrusted input

The suite is pointed at skills nobody has vouched for. That is the advertised use, so
the trust boundary is a design constraint rather than a footnote:

- **The static half never executes the tree it reads.** It parses files. The structure
  engine it imports is the `scripts/check_skills.py` it ships, not a `check_skills.py`
  found in the target; a target's `evals/run_evals.py` is reported as not executed
  (`EV006`) instead of run. `--trust-target` turns both on for a tree you own, and
  nothing turns them on by itself.
- **The evaluation half does run an agent**, with whatever permissions you give it. It
  costs money, it needs a CLI installed, and nothing in it runs unless you ask for it by
  name. Do not point `eval` at a skill you have not read.
- **No network in the static half**, no dependencies outside the standard library.

## Scanner false positives

A tool that detects secrets, destructive commands and prompt injection has to contain
examples of all three, or its rules have never been watched firing. Automated scanners
read those examples and report the detector as the thing it detects. Two consequences,
and the second is the one worth stating:

- the attack-shaped strings are **not checked into git**. `tests/fixtures/malicious/`
  holds an inert skill; the six patterns under test are assembled from parts by
  `tests/run_tests.py` at run time, so cloning this repository does not put a
  credential-shaped literal or an `rm -rf` line into your tree;
- the **rule documentation** in `docs/quality-rules.md`, `docs/how-to-secure-agent-skills.md`
  <!-- sqs-allow: SE003, SE004 -->
  and `references/` quotes override wordings (`ignore previous instructions` and its
  relatives) as examples of what `SE004` matches. They are documentation of a detector.
  A scanner reporting them as prompt injection has found the manual, not an attack.

If a scan of this repository reports either, that is the expected reading of the
material and not a finding about the code. Anything else, please report it.
