# The reading pass

What no script can check. `sqs.py quality` reports what it can count and point at; this
is the rest, and it is where most of the improvement actually is.

Work through the sections in order, on one skill at a time, with the file open. Each
question is answered with evidence from the file - a line number, a quoted phrase - or
it is not answered. "Looks fine" is the answer that makes this pass worthless.

The vocabulary below (context pointer, the two loads, information hierarchy,
completion criteria, leading words, sediment) is Matt Pocock's, from
[`writing-for-agents`](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents).
The rest is what this suite has learned from skills that broke.

## 1. The pointer

The description is a **context pointer**: a reference held in the agent's context that
names material out of context and encodes the condition for reaching it. Its *wording*,
not its target, decides when the agent reaches the material and how reliably.

- Does the pointer do both jobs - say what the material is, **and** list the branches
  that should trigger reaching it? A pointer that only does the first leaves firing to
  chance.
- Is there one trigger per **branch**? A branch is a distinct case the skill handles.
  Synonyms that rename one branch are one branch written twice.
- Does the leading word come first? The front of the description is where it does its
  triggering work.
- Is there identity the body already carries - the skill's own name, a restatement of
  its purpose? Cut it. Every word of an always-loaded pointer costs on every turn.

**The trap that costs the most.** A description **attracts** on topic match; it does not
repel. Writing "this skill does not do X" names X, and the skill becomes a candidate
for X. Negation does not reliably reverse a topic match. So:

- A boundary belongs in the description **only when the neighbour can fire on its own**.
  Against a neighbour with `disable-model-invocation`, naming its topic is pure cost -
  it cannot intercept anything. `QL008` reports exactly that case.
- Every other boundary goes in the **body**, which is read after activation and does
  not affect the choice.
- "Never fire on your own" is `disable-model-invocation: true`, not a sentence asking
  nicely.

After any description edit, re-run the routing checks: one word moves the routing of
every neighbouring skill.

## 2. The two loads

Every document and pointer spends one of two budgets:

- **Context load** - always-loaded material on the agent's window. A description, a line
  in `AGENTS.md`. Paid every turn whether or not it fires.
- **Cognitive load** - the cost on the human: knowing which documents exist and when to
  reach for each. Not a cost to minimise; it is the price of human agency. Spend it
  where human judgement matters.

Material behind a pointer escapes context load at the price of the pointer's own line.
Material with no pointer rides entirely on cognitive load.

Ask: is this skill model-invoked because the agent must reach it on its own, or because
that is the default? A skill that only ever fires by hand should be user-invoked and pay
no context load at all.

## 3. Where each piece sits

Three rungs, ranked by how immediately the agent needs the material:

1. **In-file step** - what the agent does, in order.
2. **In-file reference** - consulted on demand. A flat peer-set (every rule of a review
   on one rung) is a fine arrangement, not a smell.
3. **Disclosed reference** - pushed into a separate file behind a pointer, loaded only
   when the pointer fires.

**Progressive disclosure** is the move down the ladder so the top stays legible. The
cleanest test is branching: inline what *every* branch needs, disclose what only *some*
branches reach. When a document has steps, in-file reference that should be disclosed
buries them and turns attending to them into a coin-flip.

- **Co-location**: the ladder decides how far down a piece sits; co-location decides
  what sits beside it. A concept's definition, rules and caveats belong under one
  heading. The test: the file should read like documentation written for the agent.
- **Sprawl** is the failure here - a document simply too long, even when every line is
  live. Attention thins across the excess. The cure is the ladder, plus splitting by
  branch so each path carries only what it needs.

`ST006` and `ST007` are the byte-count shadow of this section. They tell you something
is too big; only this pass tells you what to move.

## 4. Steps and completion criteria

Every step ends on a **completion criterion** - the condition that tells the agent the
work is done. Two properties make it a lever:

- **Clarity**: can the agent tell done from not-done? A vague bound ("understanding
  reached") invites **premature completion**, the step ending while attention slips to
  being done. The visible steps still ahead supply the pull; the criterion's clarity is
  the resistance. Sharpen the bound first - it is local and cheap. Only if the bound is
  irreducibly fuzzy *and* you observe the rush, split the sequence so the later steps
  are out of view, and only across a real context boundary (a hand-off or a subagent);
  an inline call leaves them in context and clears nothing.
- **Demand**: how much it requires. "Every modified model accounted for" forces thorough
  work where "produce a change list" does not. Demand is not step-bound: "every rule
  applied" binds a body of flat reference the same way.

The strongest criteria are both checkable and exhaustive. `QL006` catches the crudest
failures of clarity by vocabulary; the rest is here.

## 5. Leading words, and the negation trap

A **leading word** is a compact concept already in the model's pretraining that the
agent thinks with while running the document (*lesson*, *tracer bullets*, *tight*,
*red*). Repeated as a token, never as a sentence, it anchors a region of behaviour in
the fewest tokens by recruiting priors the model already holds. Coining your own works
if you define it clearly, but a made-up word recruits nothing: you pay in definition
tokens what a pretrained word gives free.

Hunt for passages begging to collapse into one token: a triad spelled out at three
sites, a pointer spending a sentence to gesture at one idea.

- "fast, deterministic, low-overhead" -> *tight*
- "a loop you believe in" -> *red*, which turns a fuzzy gate into a binary observable

**Negation** is the failure mode beside this lever. Steering by prohibition drags the
forbidden behaviour into context and makes it *more* available. The negation is a weak
modifier the strongly-activated concept overruns, so the ban half-reads as an
instruction to do the thing. Prompt the **positive**: state the target behaviour so the
banned one is never spoken. Keep a prohibition only as a hard guardrail you cannot
phrase positively - and pair it with the positive target. `QL005` counts prohibitions;
deciding which of them are guardrails is this pass.

## 6. Pruning

- **Single source of truth.** Each meaning lives in one authoritative place, so changing
  the behaviour is a one-place edit. Duplication costs maintenance and tokens, and
  inflates a meaning's rank on the ladder past its real one.
- **The environment is a source of truth too** - `package.json` scripts, config files,
  the directory layout, `--help` output. A document that restates it is a **cache**,
  earning its load only when the lookup is expensive. Cache what the agent cannot find
  by looking: the unwritten convention, the reason behind a choice, the gotcha no config
  confesses.
- **Relevance, line by line.** A line loses it by never bearing on the task, or by going
  stale. Without pruning the default fate is **sediment**: stale layers that settle
  because adding feels safe and removing feels risky.
- **No-ops.** An instruction the model already obeys by default pays load to say
  nothing. The test - does it change behaviour versus the default? - is model-relative,
  not reader-relative, and is settled by running the document, not by debate. When a
  sentence fails, delete the whole sentence rather than trim words from it. The test
  also grades leading words: a word too weak to beat the default (`be thorough`, when
  the agent is already thorough-ish) is a no-op, and the fix is a stronger word, not a
  different technique.

## 7. How the skill was built

These four decide whether the skill keeps working, and no script sees any of them.

- **Written from a run, not from an idea of a run.** The skill is drafted after one real
  piece of the work has been done with the user, and the rules are extracted from that
  run. Rules derived from finished work carry the traps; rules derived from imagining
  the work carry good intentions only.
- **Fix the principle, not the example.** When the skill misbehaves, find the passage
  that produced the behaviour and rewrite it so the whole class of cases falls under it.
  Appending "and if X arrives, do Y" is overfitting the scaffolding: cheaper now, and in
  six months the patches argue with each other and nobody dares touch the file.
  More than two or three new "and if" clauses in one edit means the edit should have
  been a general rule.
- **Unverifiable requirements become pairs.** "Write vividly", "be honest, not
  flattering" pass or fail on the author's opinion. Replace each with a *bad -> good*
  pair plus the reason they differ: a pair can be compared.
- **A step always performed the same way is a script.** Prose that describes a fixed
  procedure is retyped by the model every run - probabilistically, and for tokens. It
  cannot be run, and it cannot be fixed once. `ST012` catches the blatant case; this
  pass catches the procedure written as paragraphs.

## 8. Closing the edit

An edit is finished when you can name what it fixes: today's case **and at least one
older one**. If it only fixes today's, it is a patch, not a rule - go back to section 7.

Before starting, search the history for the same trap: it may already have been analysed
once, and the second analysis will disagree with the first.
