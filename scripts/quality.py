#!/usr/bin/env python3
"""Whether the instructions read like instructions.

Structure and spec checks answer "is the skill intact". This one answers "is it worth
loading" - and it is the module with the most room to lie, so every rule here reports
something countable and names where it is. A heuristic that cannot point at a line
does not belong in a linter; it belongs in `references/writing-rubric.md`, which a
human reads with judgement.

The vocabulary is bilingual. These scripts run over skills written in Russian and in
English, and a matcher that knows one language does not report less - it silently
reports nothing, which is the failure this whole suite exists to prevent.
"""
import re
import unicodedata

from core import Finding, strip_code

# A description does two jobs: name the material, and list the branches that should
# trigger reaching it. These are the words that do the second job.
TRIGGER_RE = re.compile(
    r"\b(use when|trigger|triggers? on|when the user|when you|call this|reach for|"
    r"invoke when|before |after |asks? (?:for|to|about)|if the user|"
    r"срабатыв\w*|когда|если|триггер\w*|вызывай|зови|по словам|при\b)",
    re.I)

# Kept narrow on purpose. `WIP`, `ПОТОМ` and `ЗАГЛУШКА` were in this set: they matched a
# bad-commit example, the ordinary Russian word for "afterwards", and a sentence
# explaining what a placeholder looks like. A marker that also reads as content is not
# a marker, so only the unambiguous ones survive.
PLACEHOLDER_RE = re.compile(
    r"\b(TODO|FIXME|TBD|lorem ipsum)\b|<[a-z-]*placeholder[a-z-]*>", re.I)

# Instructions with no completion criterion: the agent cannot tell done from not-done.
VAGUE_RE = re.compile(
    r"\b(be thorough|as needed|as appropriate|if appropriate|where appropriate|"
    r"use (?:your |good )?judg?ment|make it good|write clearly|be concise|be careful|"
    r"do your best|properly|as necessary|"
    r"по необходимости|при необходимости|как следует|по возможности|"
    r"качественно|аккуратно|внимательно|живо|естественно)\b",
    re.I)

# Steering by prohibition. Counted, not judged: a hard guardrail is a legitimate use,
# and only the author knows which of these are guardrails.
NEGATION_RE = re.compile(
    r"(?:^|[.;:!?]\s|\n\s*[-*]\s*)\s*(?:never |do not |don't |avoid |no longer |"
    r"не\s+(?:пиши|делай|используй|добавляй|трогай|бери|зови|ставь)|никогда не|"
    r"не\s+надо|запрещ\w+)",
    re.I | re.M)
NEGATION_MIN = 10

# A disclaimer in the description that names a neighbouring skill.
NEIGHBOUR_RE = re.compile(
    r"[`/]([a-z][a-z0-9-]{2,63})[`\b]|\b(?:не подменяет|not to be confused|instead of|"
    r"это |а не )\s*`?([a-z][a-z0-9-]{2,63})`?")

WORD_RE = re.compile(r"[^\W\d_]{4,}", re.U)


def stems(text):
    """Rough stems: the first five letters of every word of four letters or more.

    Crude on purpose. Russian inflection puts `разгрузка` and `разгружено` in one
    family and no stdlib stemmer knows that; five characters does, and the rule that
    uses this is only ever an info-level nudge.
    """
    return {unicodedata.normalize("NFC", w).casefold()[:5]
            for w in WORD_RE.findall(text)}


SEGMENT_RE = re.compile(r"[,;·]|\.\s|«|»|\"")


def near_duplicates(desc, threshold=0.6):
    """Pairs of trigger phrases that name one branch twice.

    Counting commas was the first version of this rule and it fired on eleven skills
    out of twenty-three, because a long trigger list is not the same thing as a
    redundant one. What actually costs context is two phrases that overlap in meaning,
    so the rule compares the phrases instead of counting them - and can therefore print
    the pair, which is what makes the finding checkable.
    """
    segs = [s.strip(" -—:") for s in SEGMENT_RE.split(desc)]
    known = [(s, stems(s)) for s in segs if len(s) > 8]
    pairs = []
    for i, (a, sa) in enumerate(known):
        for b, sb in known[i + 1:]:
            small = min(len(sa), len(sb))
            if small >= 3 and len(sa & sb) / small >= threshold:
                pairs.append((a[:48], b[:48]))
    return pairs


def lines_of(pattern, text, limit=3):
    """Line numbers of the first `limit` matches, for a message that can be checked."""
    out = []
    for m in pattern.finditer(text):
        out.append(text.count("\n", 0, m.start()) + 1)
        if len(out) >= limit:
            break
    return out


def check(skill, cfg=None, registry=None):
    """`registry` maps skill name -> whether that skill is user-invoked only."""
    cfg = cfg or {}
    registry = registry or {}
    out = []
    if not skill.ok:
        return out
    desc = skill.description

    # QL002 / QL003 / QL009 - the description as a context pointer
    if desc and not skill.slash_only:
        if not TRIGGER_RE.search(desc):
            out.append(Finding("QL002", "description says what the skill is and never when "
                                        "to reach for it", where="SKILL.md"))
        for a, b in near_duplicates(desc)[:2]:
            out.append(Finding("QL003", f"\"{a}\" and \"{b}\" are the same branch written "
                                        f"twice", where="SKILL.md"))
        if re.search(r"\b" + re.escape(skill.folder) + r"\b", desc, re.I):
            out.append(Finding("QL009", f"description repeats `{skill.folder}`", where="SKILL.md"))

        # QL008 - a disclaimer that can only attract. A neighbour with
        # `disable-model-invocation` cannot intercept anything, so naming its topic here
        # buys nothing and makes this skill a candidate for that topic.
        named = {g for m in NEIGHBOUR_RE.finditer(desc) for g in m.groups() if g}
        harmless = sorted(n for n in named
                          if n != skill.folder and registry.get(n) is True)
        if harmless:
            out.append(Finding("QL008", "names " + ", ".join(f"`{n}`" for n in harmless) +
                                        " - user-invoked, so it cannot intercept anything; the "
                                        "boundary belongs in the body", where="SKILL.md"))

        # QL004 - the description fires on wording the instructions never use
        d, b = stems(desc), stems(skill.body)
        if len(d) >= 8:
            overlap = len(d & b) / len(d)
            if overlap < 0.25:
                out.append(Finding("QL004", f"{overlap:.0%} of the description's words appear in "
                                            f"the body - the description has drifted from what "
                                            f"the skill grew into", where="SKILL.md"))

    # The prose checks. Fenced blocks are blanked first: a `rm -rf` inside a
    # `bad -> good` pair is teaching material, not an instruction.
    for rel, text in skill.texts():
        prose = strip_code(text)

        hits = lines_of(PLACEHOLDER_RE, prose)
        if hits:
            out.append(Finding("QL007", f"placeholder at line{'s' if len(hits) > 1 else ''} "
                                        f"{', '.join(map(str, hits))}", where=rel, line=hits[0]))

        vague = lines_of(VAGUE_RE, prose, limit=4)
        if vague:
            words = {m.group(0).lower() for m in VAGUE_RE.finditer(prose)}
            out.append(Finding("QL006", f"{', '.join(sorted(words)[:4])} - line"
                                        f"{'s' if len(vague) > 1 else ''} "
                                        f"{', '.join(map(str, vague))}", where=rel, line=vague[0]))

        neg = [m.start() for m in NEGATION_RE.finditer(prose)]
        if len(neg) >= NEGATION_MIN:
            first = [prose.count("\n", 0, i) + 1 for i in neg[:3]]
            out.append(Finding("QL005", f"{len(neg)} prohibitions (lines "
                                        f"{', '.join(map(str, first))}, ...) - check which of "
                                        f"them have a positive form",
                               where=rel, line=first[0]))
    return out
