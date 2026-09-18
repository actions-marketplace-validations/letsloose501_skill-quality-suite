---
title: "Agent Skill security - scanning a skill before you install it"
description: >-
  An installed Agent Skill is a supply chain. How to scan a SKILL.md for committed
  secrets, destructive commands, prompt injection, data exfiltration and hidden Unicode
  before an agent reads it for work.
---

# Agent Skill security

*A skill is executable text. The agent runs the commands it names and follows the
instructions it carries, which makes an installed skill a supply chain.*

```bash
python scripts/sqs.py security ./downloaded-skill    # BEFORE the agent reads it
```

Run it before `check`, and before the skill is anywhere your agent will look. The
scanner reads text; it never executes anything.

## What it looks for

### Secrets (`SE001`)

Credentials committed by accident: AWS access keys, GitHub tokens, Anthropic and OpenAI
keys, Slack tokens, Google API keys, private key blocks, and generic
`api_key = "..."` assignments with a placeholder filter so `your-key-here` does not
become a finding.

### Destructive commands (`SE002`)

Commands nobody meant to hand an agent: a recursive delete of a root-level path, a
download piped straight into a shell, `chmod` to world-writable, a force push, a history rewrite, a
dropped database, a write to a raw device, a fork bomb, disabled certificate checks.

### Prompt injection (`SE003`)

Text addressed at the **agent** rather than at the task. In a skill you wrote this is a
mistake; in a skill you installed it is the payload:

- instruction override: an order to disregard whatever came before;
- fake authority over the system prompt;
- instructions to hide an action from the user;
- attempts to switch off a guardrail.

A quotation is exempt. A skill that teaches an agent to refuse an injection has to be
able to write the phrase down, and a scanner that cannot tell the two apart is a scanner
people switch off.

### Exfiltration (`SE005`)

A local file leaving the machine: a request that posts a credentials file as its body,
an upload of a path the skill just read, a PowerShell upload with an input file.

### Hidden and bidirectional Unicode (`SE004`)

Zero-width spaces, bidirectional overrides, soft hyphens, word joiners. **The rendered
text differs from the text the model reads** - the Trojan Source trick, and the one
finding on this page that no amount of careful reading would have caught. A zero-width
space in front of a fence marker is recognised as fence escaping and left alone, both by
the finding and by the fixer.

### Personal paths (`SE006`)

An absolute path naming whoever wrote the skill. Harmless at home, and information
disclosure once published.

## What a finding looks like

Every one of them names a file and a line, so every one is checkable:

```
$ sqs.py security ./helpful-helper
⛔ helpful-helper
     ⛔ SE001 GitHub token committed in the text (SKILL.md:18)
     ⛔ SE003 text addressed at the agent, overriding its instructions (SKILL.md:12)
     ⛔ SE004 hidden characters: ZWSP, RLO (SKILL.md:21)
     ⚠️  SE002 piping a download straight into a shell (SKILL.md:8)
     ⚠️  SE002 recursive delete of a root-level path (SKILL.md:9)
     ⚠️  SE005 a local file is sent to a network endpoint (SKILL.md:10)
     ·  SE006 absolute path naming the account `alexeyivanov` (SKILL.md:19)
```

That output is real, and it is regenerated on every commit from
[`tests/fixtures/malicious/`](https://github.com/letsloose501/skill-quality-suite/tree/main/tests/fixtures/malicious) -
a fixture that reads as a helpful bootstrap skill and does all six things at once. The
dangerous lines are assembled when the corpus runs rather than checked in: this
repository is itself a skill, so anything in it ships into everyone's skills directory,
and a fixture that reads as an attack has no business sitting in a stranger's tree. The
[examples page](https://github.com/letsloose501/skill-quality-suite/tree/main/examples)
shows the whole run.

## What it cannot tell you

A static scanner reads what a skill **says**. It does not run the skill, so it cannot
see what a bundled script does at run time, what a URL serves when fetched, or what an
instruction means in a context it has not seen.

Two things narrow that gap:

- `sqs.py eval --runtime` applies the same command patterns to what the agent **actually
  ran** while following the skill, so a rule reported at rest and a rule reported in
  flight are the same rule.
- Reading the skill yourself. A scanner is a filter, not a verdict.

## In CI

```yaml
- uses: letsloose501/skill-quality-suite@v1
  with:
    command: security
    upload-sarif: "true"   # needs security-events: write
```

The SARIF goes to GitHub code scanning, so a new finding in a skill repository appears
where the rest of your security findings already are. Every rule ships its confidence
and false-positive risk as SARIF properties, so a dashboard can filter the heuristics
out and keep the facts.

## See also

- [Skill validation](skill-validation.md) - what to run after the skill is trusted
- [The full rule list](quality-rules.md)
- [Compatibility](compatibility.md) - and what a hard-coded path into one harness's tree gives away
