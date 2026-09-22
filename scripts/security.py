#!/usr/bin/env python3
"""What a skill can do to the machine that loads it.

A skill is executable text: the agent runs the commands it names and follows the
instructions it carries. That makes an installed skill a supply chain, and this module
reads it as one - looking for credentials committed by accident, commands nobody meant
to hand an agent, text aimed at the agent rather than at the task, and characters that
make the rendered file differ from the file the model reads.

Findings name a file and a line, so every one of them is checkable. A line carrying
`sqs-allow: SE002` (or `sqs-allow: *`) is skipped, which is how a file that documents
a dangerous pattern avoids being reported for containing it.

sqs-allow-file: SE001, SE002, SE003, SE005
This module holds the patterns it hunts for, so it matches every one of them.
"""
import re

from core import Finding

SCAN_EXT = (".md", ".txt", ".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".yaml", ".yml", ".json")

# Credentials with a shape distinctive enough that a match is a match. Generic
# `password = "..."` is handled separately, with a placeholder filter, because there
# the false-positive rate is what decides whether anyone keeps reading the report.
SECRETS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{40,}")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
]
GENERIC_SECRET = re.compile(
    r"\b(api[_-]?key|auth[_-]?token|access[_-]?token|secret|password|passwd)\b"
    r"\s*[:=]\s*[\"']([^\"'\n]{16,})[\"']", re.I)
PLACEHOLDER = re.compile(
    r"^(?:<|\{|\$|your|my|some|example|sample|placeholder|xxx+|\.\.\.|redacted|changeme|"
    r"insert|todo|abc123|test)", re.I)

DANGEROUS = [
    ("recursive delete of a root-level path", re.compile(r"rm\s+(?:-[a-zA-Z]*\s+)*-[a-zA-Z]*[rR][a-zA-Z]*\s+(?:-[a-zA-Z]+\s+)*[\"']?(?:/|~|\$HOME|\$\{?HOME|%USERPROFILE%|C:\\)")),
    ("piping a download straight into a shell", re.compile(r"(?:curl|wget|iwr|Invoke-WebRequest)[^\n|]{0,200}\|\s*(?:sudo\s+)?(?:ba|z|k)?sh\b")),
    ("world-writable permissions", re.compile(r"chmod\s+(?:-R\s+)?777\b")),
    ("force push", re.compile(r"git\s+push\s+[^\n]*--force(?!-with-lease)")),
    ("history rewrite", re.compile(r"git\s+(?:reset\s+--hard|clean\s+-[a-z]*f[a-z]*d|filter-branch)")),
    ("dropping a database", re.compile(r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b", re.I)),
    ("writing to a raw device", re.compile(r"\bof=/dev/(?:sd|nvme|disk)")),
    ("fork bomb", re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;:")),
    ("disabling certificate checks", re.compile(r"(?:curl[^\n]{0,80}\s(?:-k|--insecure)\b|verify\s*=\s*False)")),
]

# Text addressed at the agent rather than at the task. In a skill you wrote this is a
# mistake; in a skill you installed it is the payload.
OVERRIDE = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+(?:instructions|prompts|rules)", re.I),
    re.compile(r"disregard\s+(?:the\s+)?(?:system\s+prompt|previous|your\s+instructions)", re.I),
    re.compile(r"(?:without|do\s+not|don't|never)\s+(?:telling|inform|mention|notify)\w*\s+(?:this\s+)?(?:to\s+)?the\s+user", re.I),
    re.compile(r"\byou\s+are\s+now\s+(?:a|an|in)\b", re.I),
    re.compile(r"(?:override|bypass|skip)\s+(?:your|the)\s+(?:safety|guardrails?|restrictions?|rules)", re.I),
    re.compile(r"не\s+сообщай\s+пользователю|скрой\s+от\s+пользователя|игнорируй\s+преды\w+", re.I),
]

# Zero-width and bidirectional controls: the rendered text differs from the text the
# model reads, which is the whole Trojan Source trick. Built from code points rather
# than typed as escapes - an escape in a source file gets decoded on the way in, and
# then the pattern is a row of invisible characters no reviewer can check.
HIDDEN_NAMES = {chr(c): n for c, n in (
    (0x200b, "ZWSP"), (0x200c, "ZWNJ"), (0x200d, "ZWJ"), (0x200e, "LRM"), (0x200f, "RLM"),
    (0x202a, "LRE"), (0x202b, "RLE"), (0x202c, "PDF"), (0x202d, "LRO"), (0x202e, "RLO"),
    (0x2066, "LRI"), (0x2067, "RLI"), (0x2068, "FSI"), (0x2069, "PDI"),
    (0xfeff, "BOM"), (0x00ad, "SHY"), (0x2060, "WJ"),
)}
HIDDEN = re.compile("[" + "".join(HIDDEN_NAMES) + "]")

# A zero-width space in front of a fence marker is the standard way to show a code
# fence inside a code fence: it is there so the inner ``` does not close the outer
# block. That one is meaning-preserving, so it is exempt - both from the finding and
# from the fixer, which would otherwise "repair" a working example into a broken one.
FENCE_ESCAPE = re.compile("^[ \t]*[" + chr(0x200b) + chr(0xfeff) + "](?=`{3,}|~{3,})")


def hidden_in(line):
    """The hidden characters on this line that change what the text means."""
    m = FENCE_ESCAPE.match(line)
    probe = line[len(m.group(0)):] if m else line
    return {HIDDEN_NAMES.get(c, hex(ord(c))) for c in HIDDEN.findall(probe)}


def strip_hidden(text):
    """The text without its meaning-changing hidden characters. Returns (text, count)."""
    out, removed = [], 0
    for line in text.split("\n"):
        m = FENCE_ESCAPE.match(line)
        keep = m.group(0) if m else ""
        rest = line[len(keep):]
        removed += len(HIDDEN.findall(rest))
        out.append(keep + HIDDEN.sub("", rest))
    return "\n".join(out), removed


# A local file leaving the machine over the network.
EXFIL = re.compile(
    r"(?:curl|wget)[^\n]{0,200}?(?:--data-binary|--data|-d|-F|--upload-file|-T)\s+[\"']?[@<][^\s\"']+"
    r"|Invoke-RestMethod[^\n]{0,200}-InFile", re.I)

# An absolute path that names whoever wrote the skill. The name needs one character that
# is not a dot: `C:\Users\...\Downloads` is the ordinary way documentation elides an
# account, and reading `...` as the account's name was a finding against every such page.
PERSONAL = re.compile(
    r"(?:[A-Za-z]:\\Users\\|/home/|/Users/)([A-Za-z0-9._-]*[A-Za-z0-9_-][A-Za-z0-9._-]*)")
PERSONAL_GENERIC = {"user", "username", "you", "youruser", "runner", "root", "me", "name",
                    "administrator", "public", "default", "shared"}


# The skill vouching for itself: a safety guarantee, an endorsement by a named vendor, a
# user count, an invitation to skip review. A selection-stage attack - it works on the
# router and on the person deciding whether to install - and the claim is exactly the
# thing a reader has to verify rather than accept.
#
# Narrow on purpose. The words are everywhere in honest skills: measured on 308 texts
# across 57 real skills, `verified`, `safe`, `official`, `проверено` and their kin occur
# 217 times, as what the skill DOES ("each verified by a panel of agents", "проверено
# 12.09.2026") or as a neighbour's provenance ("official, already installed"). Only the
# self-certifying shapes below count, and none of those 217 matches one.
TRUST_RE = re.compile(
    r"\b(?:100\s*%|completely|totally|fully|guaranteed)\s+(?:safe|secure|harmless|trusted)\b"
    r"|\b(?:certified|verified|approved|endorsed|audited|vetted|reviewed)\s+(?:and\s+\w+\s+)?"
    r"by\s+(?:anthropic|openai|google|microsoft|github|the\s+(?:claude|security)\s+team)\b"
    r"|\btrusted\s+by\s+(?:over\s+|more\s+than\s+)?[\d,.]+\s*[km]?\+?\s*"
    r"(?:users|developers|teams|companies)\b"
    r"|\b(?:no\s+need|not\s+necessary|unnecessary)\s+to\s+(?:review|audit|inspect|check)\b"
    r"|\bsafe\s+to\s+(?:run|install|use)\s+without\s+(?:review|reading|checking)\b"
    r"|\bofficial(?:ly)?\s+(?:certified|verified|endorsed|approved)\b"
    r"|(?:100\s*%|\bполностью|\bабсолютно|\bгарантированно)\s+безопас\w*"
    r"|\b(?:проверен|одобрен|сертифицирован)\w*\s+(?:anthropic|openai|google|microsoft|github)\b"
    r"|\bне\s+(?:нужно|надо|требуется)\s+(?:проверять|ревьюить|читать\s+перед)", re.I)


QUOTED_RE = re.compile(r"«[^»\n]*»|\"[^\"\n]*\"|“[^”\n]*”|'[^'\n]{4,}'")


def quoted_spans(line):
    """Character ranges that are a quotation rather than the line's own voice."""
    return [(m.start(), m.end()) for m in QUOTED_RE.finditer(line)]


def scan_line(line):
    """Every finding a single line carries, as (code, message)."""
    out = []
    for label, rx in SECRETS:
        if rx.search(line):
            out.append(("SE001", f"{label} committed in the text"))
    m = GENERIC_SECRET.search(line)
    if m and not PLACEHOLDER.match(m.group(2).strip()):
        out.append(("SE001", f"`{m.group(1)}` assigned a literal {len(m.group(2))}-character value"))
    for label, rx in DANGEROUS:
        if rx.search(line):
            out.append(("SE002", label))
    # SE003 only counts when the line speaks in its own voice. A skill that teaches the
    # agent to refuse «игнорируй предыдущие инструкции» has to be able to write the
    # phrase down, and a quotation is how it does that.
    spans = quoted_spans(line)
    for rx in OVERRIDE:
        m = rx.search(line)
        if m and not any(a <= m.start() and m.end() <= b for a, b in spans):
            out.append(("SE003", "text addressed at the agent, overriding its instructions"))
            break
    # SE007 takes the same quotation exemption as SE003: a skill that teaches a reviewer
    # to distrust «100% safe» has to be able to write the phrase down.
    m = TRUST_RE.search(line)
    if m and not any(a <= m.start() and m.end() <= b for a, b in spans):
        out.append(("SE007", f"\"{m.group(0)}\" - the skill vouches for itself"))
    found = hidden_in(line)
    if found:
        out.append(("SE004", "hidden characters: " + ", ".join(sorted(found))))
    if EXFIL.search(line):
        out.append(("SE005", "a local file is sent to a network endpoint"))
    for m in PERSONAL.finditer(line):
        if m.group(1).lower() not in PERSONAL_GENERIC:
            out.append(("SE006", f"absolute path naming the account `{m.group(1)}`"))
            break
    return out


def check(skill, cfg=None):
    out = []
    if not skill.ok:
        return out
    for rel, size, _ in sorted(skill.walk()):
        if not rel.lower().endswith(SCAN_EXT) or size > 2_000_000:
            continue
        try:
            with open(f"{skill.root}/{rel}", encoding="utf-8", errors="replace") as f:
                lines = f.read().split("\n")
        except OSError:
            continue
        seen = set()
        for n, line in enumerate(lines, 1):
            for code, msg in scan_line(line):
                # One line of each kind per file: a path repeated forty times is one
                # decision to make, not forty.
                if (code, msg) in seen:
                    continue
                seen.add((code, msg))
                out.append(Finding(code, msg, where=rel, line=n))
    return out
