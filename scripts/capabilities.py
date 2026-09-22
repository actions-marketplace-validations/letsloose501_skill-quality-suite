#!/usr/bin/env python3
"""What a bundled script CAN do to the machine, described rather than forbidden.

`security` flags a pattern that is dangerous on its own - a piped download, a secret
committed in plain text. This module answers a narrower, calmer question underneath
that one: does a bundled script even have the *ability* to reach the network, spawn a
process, or read the environment - regardless of whether any one line looks dangerous.
A finding here names a capability and stops; the decision belongs to whoever is about
to install the skill, the same discipline `security`'s own docstring states for itself.

Python scripts are read with `ast`, which is exact: an import is an import, not a guess
from a regex. Every other extension falls back to the same kind of command-name regex
`security` already uses for its own patterns, since there is no stdlib parser for them -
`CB001`'s grading says so honestly, rather than claiming the AST half's confidence for
both.

`sqs.py capabilities <skill>` runs this module alone - the "one command, one question"
dispatch every other module already gets from `MODULES`. That plain findings list, read
as an answer instead of a list, is the manifest: nothing here invents a second report
format for the same underlying facts.
"""
import ast
import fnmatch
import re

from core import Finding

SCRIPT_EXT = (".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".rb")

# Root package names whose entire job is talking to the network - importing the
# top-level name is itself the capability, submodule or not.
NETWORK_ROOTS = {
    "socket", "httplib", "ftplib", "smtplib", "telnetlib", "poplib", "imaplib",
    "nntplib", "requests", "httpx", "aiohttp", "urllib3", "websocket", "websockets",
    "paramiko", "grpc", "boto3", "botocore",
}
# Exact dotted paths inside a package that is otherwise network-inert. `urllib` bare, or
# `urllib.parse` (pure string parsing) or `urllib.error` (exception classes only), grant
# nothing on their own - only `urllib.request` makes a connection. Watched `urllib.parse`
# reading as "can reach the network" on this project's own installed skills before this
# split existed, which is exactly the over-broad claim this module promises not to make.
NETWORK_EXACT = {
    "urllib.request", "http.client", "http.server", "xmlrpc.client", "xmlrpc.server",
}
SUBPROCESS_MODULES = {"subprocess", "multiprocessing"}
OS_SUBPROCESS_ATTRS = {
    "system", "popen", "fork", "posix_spawn",
    "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe",
    "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe",
}
ENV_ATTRS = {"environ", "getenv", "environb"}

# Non-Python scripts have no stdlib parser, so the network signal there is a command
# name instead of an import - the same kind of pattern `security.DANGEROUS` already
# matches on, and CB001's confidence grading reflects that this half is a guess.
NETWORK_CMD_RE = re.compile(
    r"\b(curl|wget|ncat|netcat|ssh|scp|sftp|telnet)\b"
    r"|\bnc\s+-[a-zA-Z]*l\b|\bnc\s+\S+\s+\d+\b"
    r"|\bInvoke-WebRequest\b|\bInvoke-RestMethod\b|\bNew-Object\s+Net\.\w+\b", re.I)


def _root(dotted):
    return dotted.split(".", 1)[0]


def _py_capabilities(text):
    """(code, message, line) from the exact syntax tree - imports and calls, not a guess.

    A script that fails to parse (a newer syntax feature, or a `.py` file that is
    actually something else) is skipped rather than reported on: a capability claim
    from a tree that was never really built would be a guess wearing `ast`'s confidence.
    """
    out = []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = _root(alias.name)
                if root in NETWORK_ROOTS or alias.name in NETWORK_EXACT:
                    out.append(("CB001", f"imports `{alias.name}` - can reach the network",
                               node.lineno))
                if root in SUBPROCESS_MODULES:
                    out.append(("CB002", f"imports `{alias.name}` - can spawn a process",
                               node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = _root(node.module)
            # `from urllib import request` names the network-capable submodule as one
            # of the imported names rather than in `module` - build the same dotted
            # path `import urllib.request` would produce, for each name, before
            # checking it against `NETWORK_EXACT`.
            dotted = {f"{node.module}.{a.name}" for a in node.names}
            if root in NETWORK_ROOTS or node.module in NETWORK_EXACT or dotted & NETWORK_EXACT:
                out.append(("CB001", f"imports from `{node.module}` - can reach the network",
                           node.lineno))
            if root in SUBPROCESS_MODULES:
                out.append(("CB002", f"imports from `{node.module}` - can spawn a process",
                           node.lineno))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id != "os":
                continue
            if node.attr in OS_SUBPROCESS_ATTRS:
                out.append(("CB002", f"calls `os.{node.attr}` - can spawn a process",
                           node.lineno))
            elif node.attr in ENV_ATTRS:
                out.append(("CB003", f"reads `os.{node.attr}` - can read whatever the "
                                     f"environment carries, commonly including API keys "
                                     f"and tokens", node.lineno))
    return out


def _other_capabilities(text):
    out = []
    for n, line in enumerate(text.split("\n"), 1):
        m = NETWORK_CMD_RE.search(line)
        if m:
            out.append(("CB001", f"runs `{m.group(0).strip()}` - can reach the network", n))
    return out


def check(skill, cfg=None):
    out = []
    if not skill.ok:
        return out
    for rel, size, _ in sorted(skill.walk()):
        if not rel.lower().endswith(SCRIPT_EXT) or size > 2_000_000:
            continue
        try:
            with open(f"{skill.root}/{rel}", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        found = (_py_capabilities(text) if rel.lower().endswith(".py")
                else _other_capabilities(text))
        seen = set()
        for code, msg, line in found:
            # One line of each distinct capability per file: a script that imports
            # `requests` in three places has one capability, not three findings.
            if (code, msg) in seen:
                continue
            seen.add((code, msg))
            out.append(Finding(code, msg, severity="info", where=rel, line=line))
    out += load_time_commands(skill)
    return out


# Claude Code runs `!`command`` in a skill's body, and every line of a block opened with
# ```!, before the model is sent the skill - the output replaces the placeholder, and the
# command never prompts: a permission rule or the skill's own `allowed-tools` lets it
# through, or the invocation aborts. Documented on the Claude Code skills page, which
# also states the inline form counts only at a line start or after whitespace.
INJECT_INLINE_RE = re.compile(r"(?:^|(?<=\s))!`([^`\n]+)`")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(!?)")


def _injections(skill):
    """[(line number, command, inside an ordinary code block)] from SKILL.md's body.

    An ordinary fence is tracked rather than skipped: the documentation says nothing
    about whether an inline injection inside one runs, and a rule that quietly assumed
    it does not would be making the claim the page declines to make.
    """
    lines = skill.text.split("\n")
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break
    out, fence, runs = [], None, False
    for i in range(start, len(lines)):
        line = lines[i]
        m = FENCE_RE.match(line)
        if m and fence is None:
            fence, runs = m.group(1)[0], bool(m.group(2))
            continue
        if m and fence is not None and m.group(1)[0] == fence and not m.group(2):
            fence, runs = None, False
            continue
        if runs:
            if line.strip():
                out.append((i + 1, line.strip(), False))
            continue
        for mm in INJECT_INLINE_RE.finditer(line):
            out.append((i + 1, mm.group(1).strip(), fence is not None))
    return out


def _preapproved(command, raw_tools):
    """Whether the skill's own `allowed-tools` lets this command through unasked."""
    from model import parse_tools                     # local: model is heavier than this
    scopes = parse_tools(raw_tools).get("Bash")
    if scopes is None:
        return False
    if not scopes:
        return True                                   # bare `Bash`: every command
    return any(fnmatch.fnmatchcase(command, s) for s in scopes)


def load_time_commands(skill):
    """CB004 - commands the skill runs on the machine the moment it loads.

    One finding per skill, not per command: a skill that documents the syntax carries
    dozens of examples, and a list of them is the report `CB001` once was per import site.
    The count that matters most is the one the skill pre-approved for itself - those run
    silently on every load, before anything has been read.
    """
    found = _injections(skill)
    if not found:
        return []
    raw = skill.fm.get("allowed-tools") or ""
    live = [f for f in found if not f[2]]
    fenced = len(found) - len(live)
    line, cmd, _ = (live or found)[0]
    parts = []
    if live:
        approved = sum(1 for _, c, _ in live if _preapproved(c, raw))
        parts.append(f"{len(live)} command(s) run when the skill loads, before the model "
                     f"reads it, without asking - first `{cmd[:60]}`")
        if approved:
            parts.append(f"{approved} of them pre-approved by its own `allowed-tools`, so "
                         f"nothing stops them")
    if fenced:
        parts.append(f"{fenced}{' more' if live else ''} inside ordinary code blocks, where "
                     f"the documentation "
                     f"does not say whether they run"
                     + ("" if live else f" - first `{cmd[:60]}`"))
    return [Finding("CB004", "; ".join(parts), severity="info", where="SKILL.md", line=line)]
