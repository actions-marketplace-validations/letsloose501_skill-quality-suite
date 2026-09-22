#!/usr/bin/env python3
"""Trigger queries out of the user's own history, instead of out of the author's head.

A trigger set written by the author tends to restate the description (`EV010` counts
how often), because the author writes down the phrasings they already listed. The
phrasings that matter are the ones people actually typed, and Claude Code keeps them:
every session is a JSONL transcript under `~/.claude/projects/<project>/`. This reads
those files - locally, read-only, nothing leaves the machine - and returns drafts.

What counts as a routing decision is read off the transcript's shape, not guessed:

- a **positive** is a user prompt whose first tool call was a `Skill` load of this
  skill. The first call is the moment the router decided; a skill loaded after other
  work in the same turn is the agent's decision about its task, not routing;
- a typed `/command`, a system or meta message, a compaction summary and a subagent's
  sidechain are not prompts, and they end the prompt before them - otherwise a load
  after an explicit `/konspekt` would be credited to whatever was said earlier;
- a **near miss** is a prompt whose first call loaded a different skill, ranked by how
  much of it this skill's description also covers. The top of that list is the wording
  a neighbour won and this skill could plausibly have claimed - the negatives a trigger
  set is supposed to be made of. Ranked, not thresholded: a cut-off would be a guess.

Everything returned is the user's own words. The drafts are printed for review and
written only on request, and only where no trigger set exists yet.
"""
import glob
import json
import os
import re

# A routing set is a set of wordings. A prompt this long is a pasted document with an
# instruction attached, which tests something else; the figure is a readability cap
# chosen by eye, not a measurement.
MAX_PROMPT_CHARS = 400


def default_dir():
    return os.path.join(os.path.expanduser("~"), ".claude", "projects")


def _user_text(content):
    """The typed text of a user record, or None for a record that carries no prompt."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(parts) if parts else None       # tool_result only: not a prompt
    return None


def _not_a_prompt(rec, text):
    """A user record that ends the current prompt without being one."""
    stripped = text.lstrip()
    return (rec.get("isMeta") or rec.get("isCompactSummary")
            or stripped.startswith("<") or stripped.startswith("/"))


def routing_decisions(path):
    """[(prompt, skill)] for each prompt in one transcript whose first tool was `Skill`.

    Also yields (prompt, None) for a prompt whose first tool was anything else, so a
    caller can tell "decided against every skill" from "never decided at all".
    """
    out = []
    prompt, decided = None, True
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return out
    with f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or rec.get("isSidechain"):
                continue
            kind = rec.get("type")
            content = (rec.get("message") or {}).get("content")
            if kind == "user":
                text = _user_text(content)
                if text is None:
                    continue                  # a tool result: the turn goes on
                if _not_a_prompt(rec, text):
                    prompt, decided = None, True
                    continue
                prompt, decided = text.strip(), False
            elif kind == "assistant" and isinstance(content, list) and not decided:
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        skill = None
                        if block.get("name") == "Skill":
                            skill = (block.get("input") or {}).get("skill") or None
                        if prompt:
                            out.append((prompt, skill))
                        decided = True
                        break
    return out


def is_this(loaded, name):
    """The same two spellings `providers.loaded` accepts: bare, or behind a plugin."""
    return bool(loaded) and (loaded == name or loaded.endswith(":" + name))


def names_it(prompt, loaded):
    """Whether the prompt asked for the skill by name - `/trener`, or `konspekt` as a word.

    Such a load is a lookup, not a routing decision, and a trigger set built from it
    would measure whether the model can read a name. Watched in the first run over a real
    history: "давай /trener на сегодня" and "дай konspekt дописать" both ranked as
    near misses for neighbours they never competed with.
    """
    short = loaded.split(":")[-1]
    return re.search(r"(?<![\w-])/?" + re.escape(short) + r"(?![\w-])", prompt,
                     re.I) is not None


# A near miss has to carry a topic to compete on. `prompt_match` scores overlap against
# the shorter side, so a one-word reply ("добавляй") scores 0 or 1 and a 1 sorted to the
# top of the first real run. Three stems is the smallest prompt that says what it wants.
NEAR_MISS_MIN_STEMS = 3

# A link, a path or an attached file is not a topic. Left in, `users`, the account name and
# `downl` out of `@"C:\Users\...\Downloads\..."` were most of what put one prompt at the
# top of three different skills' near-miss lists in the second real run.
NOT_TOPIC_RE = re.compile(r"@\"[^\"]*\"|@\S+|https?://\S+|[A-Za-z]:\\\S*|(?:~|\.{0,2})/\S+")


def topic(prompt):
    return NOT_TOPIC_RE.sub(" ", prompt)


def harvest(skill, history_dir=None, limit=10):
    """{"positive": [...], "near_miss": [...], "skipped_long": n, "transcripts": n}."""
    from quality import prompt_match, stems          # local: quality is a heavy import

    name = skill.name or skill.folder
    files = glob.glob(os.path.join(history_dir or default_dir(), "*", "*.jsonl"))
    positives, others, seen, long_, named = [], [], set(), 0, 0
    for path in sorted(files):
        for prompt, loaded in routing_decisions(path):
            key = " ".join(prompt.split()).casefold()
            if key in seen:
                continue
            seen.add(key)
            if len(prompt) > MAX_PROMPT_CHARS:
                long_ += 1
                continue
            if loaded and names_it(prompt, loaded):
                named += 1
                continue
            if is_this(loaded, name):
                positives.append(prompt)
            elif loaded:
                others.append((prompt, loaded))
    own = stems(skill.description or "")
    ranked = []
    for prompt, loaded in others:
        st = stems(topic(prompt))
        if len(st) < NEAR_MISS_MIN_STEMS:
            continue
        score, _ = prompt_match(skill.description or "", st)
        if score > 0:
            ranked.append((score, len(st & own), prompt, loaded))
    # Share first, count second: ranked by count, the longest prompt won on length alone.
    ranked.sort(key=lambda r: (-r[0], -r[1]))
    return {"positive": positives[:limit],
            "near_miss": [{"query": p, "went_to": w, "overlap": round(s, 2)}
                          for s, _, p, w in ranked[:limit]],
            "skipped_long": long_, "skipped_named": named, "transcripts": len(files)}


def search(seeds, history_dir=None):
    """[(prompt, skill it loaded first or None)] for prompts carrying any of `seeds`.

    For a skill that does not exist yet there is no load to harvest, so the user names
    the need instead: a few words it would be asked with. A seed matches the start of a
    word, so `инвойс` finds `инвойсы` - Russian inflects at the end, and a whole-word
    match would miss most of it. The seeds are the user's choice; nothing here decides
    what is relevant on its own.
    """
    pats = [re.compile(r"(?<![\w-])" + re.escape(s.strip()), re.I) for s in seeds if s.strip()]
    if not pats:
        return []
    out, seen = [], set()
    files = glob.glob(os.path.join(history_dir or default_dir(), "*", "*.jsonl"))
    for path in sorted(files):
        for prompt, loaded in routing_decisions(path):
            key = " ".join(prompt.split()).casefold()
            if key in seen or len(prompt) > MAX_PROMPT_CHARS:
                continue
            seen.add(key)
            if any(p.search(prompt) for p in pats):
                out.append((prompt, loaded))
    return out


def as_query_set(harvested):
    """The drafts in `evals/eval_queries.json` form, the shape `triggers.load` reads."""
    return ([{"query": p, "should_trigger": True} for p in harvested["positive"]]
            + [{"query": n["query"], "should_trigger": False}
               for n in harvested["near_miss"]])
