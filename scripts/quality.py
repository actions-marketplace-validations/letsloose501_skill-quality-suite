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
#
# Three shapes, and each of the first two used to be one expression that could not do
# both jobs. `[`/]name[`\b]` looks like "a backtick or a word boundary" and is not: `\b`
# inside a character class is a backspace, so the name had to be followed by a literal
# backtick and `/mistake,` was invisible. Splitting them lets the slash form carry its
# own guard - `(?<![\w/:])` keeps `https://host/docs` and `a/b` out, which a bare
# boundary would have swept in as neighbours called `docs` and `b`.
#
# The lead-ins are case-insensitive because a description states them at the start of a
# sentence: `Не подменяет konspekt` is how the phrase is actually written, and the
# lower-case-only pattern could therefore never match a Russian one.
NEIGHBOUR_RE = re.compile(
    r"`([a-z][a-z0-9-]{2,63})`"
    r"|(?<![\w/:])/([a-z][a-z0-9-]{2,63})\b"
    r"|(?i:\b(?:не подменяет|не путать с|not to be confused|instead of|это |а не ))"
    r"\s*[`/]?([a-z][a-z0-9-]{2,63})`?")

# A negative-scope clause in the description: the skill naming work it will not take.
# The topic such a clause names is the whole problem - see QL013.
# The verb has to be the one that selects a skill, and the negation has to attach to it.
# A looser pattern read `commands that must never reach an agent unreviewed` as a scope
# fence, when it was the subject the skill teaches - so `reach` only counts as `reach
# for`, and a bare `not` is out: on its own it lands in the middle of ordinary prose.
NEGATIVE_SCOPE_RE = re.compile(
    r"(?:\b(?:do not|don't|never)\s+(?:use|trigger|fire|apply|invoke|reach\s+for)\b"
    r"|\bnot\s+for\b|\bdoes\s+not\s+(?:handle|cover|do)\b"
    r"|\bне\s+(?:использу|применя|срабат|для|берис|путат|подменя))"
    r"[^.;·]{0,90}",
    re.I)

# Something named rather than described: a slash command or a backticked identifier.
# A boundary that points at one of these is aimed at a thing, not spelling out a topic
# for the router to match on, so it is outside QL013 even when the thing is not a skill
# in this tree - `/mistake` and `/clean-memory` are commands, and naming them is the fix
# the rule would otherwise ask for.
NAMED_THING_RE = re.compile(r"[`/][a-z][a-z0-9-]{2,63}\b")

# Polarity markers, for telling an opposite branch from a repeated one. Both halves of
# `use when X` / `do not use when X` stem to the same set, because `stems()` keeps only
# words of four letters or more and every negation below is shorter than that.
POLARITY_RE = re.compile(
    r"\b(?:not|don't|dont|never|avoid|except|unless)\b|\bне\b|\bнельзя\b|\bкроме\b",
    re.I)

# A description is an instruction to the agent about when to act. `This skill does X`
# is a paragraph about itself, and first or second person does not fit the system prompt
# the description is injected into. Both are named in the official guidance.
SELF_TALK_RE = re.compile(
    r"^\s*(?:this|the)\s+skill\b|\bthis\s+skill\s+(?:does|is|will|can|provides|helps|"
    r"handles|allows)\b|^\s*I\s+(?:can|will|help)\b|\byou\s+can\s+use\s+this\b|"
    r"^\s*[Ээ]тот\s+скилл\b",
    re.I)

# Agents run in non-interactive shells, so a script that blocks on a prompt hangs until
# something kills it. `sys.stdin.read()` is deliberately absent: taking input from stdin
# is what the guidance asks for, and only a prompt at a terminal is the failure.
INTERACTIVE_RE = re.compile(
    r"(?<![\w.])(?:input|raw_input)\s*\(|\bgetpass\b|\bRead-Host\b|"
    r"\bread\s+-[a-zA-Z]*p\b|\bclick\.(?:prompt|confirm)\b|\binquirer\.|"
    r"\bquestionary\.|\bprompts?\.(?:confirm|select)\b|\bConfirm-Host\b")

# `npx eslint` resolves to whatever is newest today. A scoped package needs the version
# after the package name, so `@scope/pkg` on its own is still unpinned.
UNPINNED_RE = re.compile(
    r"\b(npx|bunx|uvx)\s+(?:--?\S+\s+)*(@?[\w.-]+(?:/[\w.-]+)?)(?![\w./-]*@)")

SCRIPT_EXT = (".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".rb")

WORD_RE = re.compile(r"[^\W\d_]{4,}", re.U)
WORD_RE_LONG = re.compile(r"[^\W\d_]{6,}", re.U)


def stems(text):
    """Rough stems: the first five letters of every word of four letters or more.

    Crude on purpose. Russian inflection puts `разгрузка` and `разгружено` in one
    family and no stdlib stemmer knows that; five characters does, and the rule that
    uses this is only ever an info-level nudge.
    """
    return {unicodedata.normalize("NFC", w).casefold()[:5]
            for w in WORD_RE.findall(text)}


# The stems of `TRIGGER_RE`'s own lead-in words, read out of that pattern rather than
# copied by hand so the two cannot drift apart. `срабатывай`/`триггер`/`вызывай` and
# `trigger`/`invoke` are all six letters or longer, so they survive `content_stems`'s
# length floor - and, being the literal words every skill in this house style opens its
# trigger clause with, they are shared by construction between any two skills that use
# it. Watched turning into a false `EV007` between two otherwise unrelated skills before
# this set existed: both open with "Срабатывай", and that one shared scaffolding word
# was most of what crossed the threshold.
TRIGGER_LEAD_STEMS = {unicodedata.normalize("NFC", w).casefold()[:6]
                      for w in WORD_RE_LONG.findall(TRIGGER_RE.pattern)}


def content_stems(text):
    """Stems of words carrying topical weight - short scaffolding words dropped.

    `stems()`'s four-letter floor is right for comparing segments of ONE description:
    the topic word is what differs there, and connective scaffolding - "when", "user",
    "asks", "where" - repeats identically across every segment of that same skill and
    cancels out of the comparison. Between two DIFFERENT skills the scaffolding is what
    repeats - it is the shared house style of writing a trigger clause - and the topic
    word is what would actually prove a collision. Watched on this project's own test
    fixtures: an invoice skill and a downloads skill, both phrased "use when ... or when
    the user asks where ... went", cleared the four-letter threshold on `when`/`user`/
    `asks`/`where`/`went` alone with no topic word shared at all. Six letters is short
    enough to keep real topic words in both languages and long enough to drop those;
    `TRIGGER_LEAD_STEMS` catches the lead-in words long enough to survive that floor too.
    """
    return ({unicodedata.normalize("NFC", w).casefold()[:6]
            for w in WORD_RE_LONG.findall(text)} - TRIGGER_LEAD_STEMS)


SEGMENT_RE = re.compile(r"[,;·]|\.\s|«|»|\"")


def near_duplicates(desc, threshold=0.6):
    """Pairs of trigger phrases that name one branch twice.

    Counting commas was the first version of this rule and it fired on eleven skills
    out of twenty-three, because a long trigger list is not the same thing as a
    redundant one. What actually costs context is two phrases that overlap in meaning,
    so the rule compares the phrases instead of counting them - and can therefore print
    the pair, which is what makes the finding checkable.

    Polarity is compared separately because the stems cannot carry it. `use when the
    user says` and `do not use when the user says` are opposite branches, and every word
    that distinguishes them is too short for `stems()` to keep - so by stems alone they
    are identical, and the rule called one of the commonest description shapes a
    duplicate. A pair whose two halves disagree about polarity is two branches.
    """
    segs = [s.strip(" -—:") for s in SEGMENT_RE.split(desc)]
    known = [(s, stems(s), bool(POLARITY_RE.search(s))) for s in segs if len(s) > 8]
    pairs = []
    for i, (a, sa, na) in enumerate(known):
        for b, sb, nb in known[i + 1:]:
            if na != nb:
                continue
            small = min(len(sa), len(sb))
            if small >= 3 and len(sa & sb) / small >= threshold:
                pairs.append((a[:48], b[:48]))
    return pairs


SENTENCE_RE = re.compile(r"[.;]\s+|\n")


def branch_segments(desc):
    """(sentence, content stems, has-negation) for the trigger-branch part of a description.

    House style - the `TEMPLATE` in `sqs.py` states it directly - is one sentence on
    what the skill is, then the branches that should trigger it. `TRIGGER_RE` finds the
    lead-in into that second part; everything before it is the topic sentence and stays
    out of the comparison, because two skills sharing a topic word is not a collision
    and two skills whose *branches* cover one wording is.

    Split at sentence boundaries, not `near_duplicates`' comma-level ones: a real corpus
    of skills that name their own neighbours (`⚠️ Not this, see `other-skill``)
    keeps that whole disclaimer in one sentence, and `NAMED_THING_RE` then drops the
    sentence entirely. Splitting on commas instead cut a disclaimer like `X - see
    `konspekt`, and not this` into a bare quoted trigger phrase in one fragment and the
    neighbour's name in the next, which is how the first version of this function turned
    every skill that disambiguates against a neighbour into a false collision with that
    neighbour - watched happening on the 28 skills actually installed here.
    """
    m = TRIGGER_RE.search(desc)
    if not m:
        return []
    zone = desc[m.start():]
    out = []
    for s in SENTENCE_RE.split(zone):
        s = s.strip(" -—:*")
        if len(s) <= 8 or NAMED_THING_RE.search(s):
            continue
        out.append((s, content_stems(s), bool(POLARITY_RE.search(s))))
    return out


def cross_overlap(skills, threshold=0.6):
    """EV007 - pairs of skills whose trigger branches claim the same wording.

    The within-one-description version of this comparison is `QL003`/`near_duplicates`;
    this runs the identical stem-overlap-with-polarity test between the branch segments
    of every pair of *different* skills instead of between segments of one description.
    A skill compares against itself constantly by construction (every segment shares
    stems with the rest of its own list) - `na == nb` is what keeps that out.
    """
    entries = []
    for s in skills:
        if not s.ok or s.slash_only or not s.description:
            continue
        name = s.name or s.folder
        for seg, st, neg in branch_segments(s.description):
            entries.append((name, s.folder, s.root, seg, st, neg))
    out, seen = [], set()
    for i, (na, fa, ra, sa, sta, nega) in enumerate(entries):
        for nb, fb, rb, sb, stb, negb in entries[i + 1:]:
            if na == nb or nega != negb:
                continue
            small = min(len(sta), len(stb))
            if small < 3 or len(sta & stb) / small < threshold:
                continue
            pair = tuple(sorted((na, nb)))
            key = pair + (sa[:48], sb[:48])
            if key in seen:
                continue
            seen.add(key)
            f = Finding("EV007",
                       f"`{na}` \"{sa[:48]}\" and `{nb}` \"{sb[:48]}\" claim the same "
                       f"wording - only one can win", severity="warning",
                       where="SKILL.md", skill=fa)
            f.root = ra
            out.append(f)
    return out


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
        m = SELF_TALK_RE.search(desc)
        if m:
            out.append(Finding("QL010", f'"{m.group(0).strip()}" - a description is read as '
                                        f'an instruction about when to act, not as a '
                                        f'paragraph about the skill', where="SKILL.md"))

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

        # QL013 - the same trap as QL008 without a name to hang it on, which is the
        # common shape: the description rules out a topic rather than a named skill.
        # QL008 needs the neighbour to be named *and* registered as user-invoked, so a
        # clause like "do not use for optimising code" is invisible to it - while being
        # the version that actually costs, because the topic is spelled out for the
        # router to match on and the negation does not reverse the match.
        for m in NEGATIVE_SCOPE_RE.finditer(desc):
            clause = " ".join(m.group(0).split())
            # A clause that names a skill in this tree is QL008's case, reported by it
            # or deliberately not. The check runs against the registry rather than
            # `named`, because `NEIGHBOUR_RE` only sees a name in backticks or after one
            # of its lead-ins in lower case - so `Не подменяет konspekt, razbor` slipped
            # past it, and this rule then told an author who had named five neighbours
            # to name the neighbour instead of the topic.
            low = clause.casefold()
            if any(n in low for n in named) or any(n.casefold() in low
                                                   for n in registry if n != skill.folder):
                continue
            if NAMED_THING_RE.search(clause):
                continue        # `/mistake` or `other-skill`: a name, not a bare topic
            if len(stems(clause)) < 3:
                continue        # no topic in it, so nothing for the router to match
            out.append(Finding("QL013", f'"{clause[:60]}" names work this skill will not '
                                        f'take - a description attracts on topic match and '
                                        f'does not repel, so the topic belongs in the body',
                               where="SKILL.md"))

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

        # QL012 - an unpinned one-off command. It lives inside a fence, so the raw text
        # is searched: blanking code here would blank the thing being checked.
        for m in UNPINNED_RE.finditer(text):
            out.append(Finding("QL012", f"`{m.group(1)} {m.group(2)}` has no version",
                               where=rel, line=text.count("\n", 0, m.start()) + 1))

    # QL011 - the worst failure mode in the set: the agent waits forever and nothing
    # explains why. Bundled scripts are read directly; texts() only carries prose.
    for rel, size, _ in sorted(skill.walk()):
        if not rel.lower().endswith(SCRIPT_EXT) or size > 2_000_000:
            continue
        try:
            with open(f"{skill.root}/{rel}", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().split("\n")
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith(("#", "//", "*")):
                continue
            m = INTERACTIVE_RE.search(line)
            if m:
                out.append(Finding("QL011", f"`{m.group(0).strip()}` waits for a human",
                                   where=rel, line=n))
                break
    return out
