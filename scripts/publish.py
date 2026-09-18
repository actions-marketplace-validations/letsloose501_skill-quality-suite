#!/usr/bin/env python3
"""What has to be true before a skill leaves the machine it was written on.

Everything here is invisible while the skill only ever runs at home, and obvious the
moment somebody else installs it: a path into a directory only you have, a vault note
nobody else can read, a version that disagrees with the manifest, documentation in a
language the repository is not written in.

This module is not part of `sqs.py check`. It runs when you ask for it, because half
its findings are correct-and-intended for a private skill.
"""
import json
import os
import re

from core import Finding
from security import PERSONAL, PERSONAL_GENERIC

LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
# A path into somewhere only the author can reach. `~/.claude/skills/...` is exempt:
# that is where a skill legitimately points at its neighbours.
PRIVATE_PATH = re.compile(r"[`\"']?(~|\$env:USERPROFILE|%USERPROFILE%)[/\\]"
                          r"(?!\.claude[/\\]skills)([^\s`\"'\n]{2,80})")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
EMAIL_GENERIC = re.compile(r"@(?:example\.|test\.|localhost|domain\.|email\.)", re.I)
# Backtick, double quote, apostrophe: what a quoted path is wrapped in.
QUOTES = "`" + chr(34) + chr(39)
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
SCRIPTS = {"en": CYRILLIC}


def manifest_version(skill):
    """(version, manifest path) from the nearest plugin manifest, or (None, None)."""
    here = skill.root
    for _ in range(4):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        for rel in (".claude-plugin/plugin.json", "plugin.json", ".claude-plugin/marketplace.json"):
            p = os.path.join(here, rel)
            if not os.path.isfile(p):
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and data.get("version"):
                return str(data["version"]), p
    return None, None


def check(skill, cfg=None):
    cfg = cfg or {}
    lang = cfg.get("lang")
    out = []
    if not skill.ok:
        return out
    parent = os.path.dirname(skill.root)

    # PB001 / PB002 - what a stranger needs before they can use or reuse the skill
    has_license = bool(skill.fm.get("license")) or any(
        os.path.isfile(os.path.join(d, n))
        for d in (skill.root, parent) for n in LICENSE_NAMES)
    if not has_license:
        out.append(Finding("PB001", "no `license:` field and no LICENSE file beside the skill"))
    if not any(os.path.isfile(os.path.join(d, "README.md")) for d in (skill.root, parent)):
        out.append(Finding("PB002", "no README.md - SKILL.md talks to the agent, nothing here "
                                    "talks to the human deciding whether to install"))

    # PB005 - the manifest and the skill disagree about which version this is
    version, mpath = manifest_version(skill)
    own = skill.fm.get("version")
    if version and own and version != own:
        out.append(Finding("PB005", f"`version: {own}` in SKILL.md, `{version}` in "
                                    f"{os.path.relpath(mpath, parent)}"))

    for rel, text in skill.texts():
        for n, line in enumerate(text.split("\n"), 1):
            # PB003 - the path only resolves on one machine, and names whose
            for m in PERSONAL.finditer(line):
                if m.group(1).lower() not in PERSONAL_GENERIC:
                    out.append(Finding("PB003", f"`{m.group(0)}` - absolute path naming an "
                                                f"account", where=rel, line=n))
                    break
            # PB006 - a pointer into material the reader has no copy of
            m = PRIVATE_PATH.search(line)
            if m:
                # The quotes are stripped through a module-level constant rather than
                # inline: a backslash inside an f-string expression is only legal from
                # Python 3.12, and this file has to parse on the oldest version the
                # suite claims to run on.
                out.append(Finding("PB006", f"`{m.group(0).strip(QUOTES)}` points into "
                                            f"the author's own files", where=rel, line=n))
            m = EMAIL.search(line)
            if m and not EMAIL_GENERIC.search(m.group(0)):
                out.append(Finding("PB006", f"email address `{m.group(0)}`", where=rel, line=n))

        # PB004 - documented in a language the repository is not written in
        rx = SCRIPTS.get(lang)
        if rx:
            hits = rx.findall(text)
            if len(hits) > 20:
                out.append(Finding("PB004", f"{len(hits)} characters outside `{lang}`",
                                   where=rel))
    return out
