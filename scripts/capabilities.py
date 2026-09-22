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
    return out
