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

# Component directories the official plugin layout documents beside `skills/`. `scripts/`
# is deliberately left out: a skill legitimately carries its own, so a bare mention of it
# says nothing about whether the path escapes this skill's own folder.
PACKAGE_DIRS = ("commands", "agents", "workflows", "hooks", "monitors", "bin")
SIBLING_RE = re.compile(
    r"\$\{CLAUDE_PLUGIN_ROOT\}[/\\][\w./\\-]*"
    r"|(?:\.\./)+(?:" + "|".join(PACKAGE_DIRS) + r")/[\w./-]+")


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


def plugin_root(skill):
    """The directory holding `.claude-plugin/`, walking up from the skill, or None.

    That is where `hooks/`, `commands/`, `agents/` and the manifest live - one level
    above the skill folder itself, or more when the skill sits under `skills/<name>/`.
    A skill written for itself, with no `.claude-plugin/` above it anywhere, has no
    package context to report, and PB007-PB009 stay silent.
    """
    here = skill.root
    for _ in range(4):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        if os.path.isdir(os.path.join(here, ".claude-plugin")):
            return here
    return None


def _load_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def hook_findings(root):
    """PB007 - hooks the package wires beside this skill, whether or not it fires.

    `hooks/hooks.json` nests events under a top-level `hooks` key. A hook runs on its
    event regardless of whether the model ever routed to this skill, so a clean verdict
    printed next to an unread `hooks/` directory is the misleading half of the report.
    """
    data = _load_json(os.path.join(root, "hooks", "hooks.json"))
    events = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(events, dict):
        return []
    fired, total = [], 0
    for event, entries in events.items():
        if not isinstance(entries, list):
            continue
        n = sum(1 for entry in entries if isinstance(entry, dict)
                for h in entry.get("hooks", [])
                if isinstance(h, dict) and h.get("type") == "command")
        if n:
            fired.append(event)
            total += n
    if not total:
        return []
    return [Finding("PB007",
                    f"package also wires {total} hook command(s) on {', '.join(sorted(fired))} "
                    f"(hooks/hooks.json) - they run on the event whether or not this skill is "
                    f"ever invoked")]


def sibling_findings(skill):
    """PB008 - the skill points at a package component outside its own folder.

    The structure rules only resolve a pointer that stays inside the skill, so a link
    through `${CLAUDE_PLUGIN_ROOT}` or a `../` into a sibling component directory is
    invisible to them today - and breaks in silence the moment the skill is copied out
    of the plugin, which is exactly what installing it standalone does.
    """
    out = []
    for rel, text in skill.texts():
        for n, line in enumerate(text.split("\n"), 1):
            m = SIBLING_RE.search(line)
            if m:
                out.append(Finding("PB008",
                    f"`{m.group(0)}` points at a package sibling, not at this skill",
                    where=rel, line=n))
    return out


def origin_finding(root, plugin_name):
    """PB009 - the marketplace's declared source for this plugin, printed as a fact.

    A local `\"./...\"` source is a checkout of the same repository and is not reported:
    the interesting case is a remote source - `github`, `url`, `git-subdir`, `npm`,
    `archive`, `command` - where the files under review may be a checkout nobody has
    looked at.
    """
    data = _load_json(os.path.join(root, ".claude-plugin", "marketplace.json"))
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, list):
        return []
    entry = next((p for p in plugins if isinstance(p, dict) and p.get("name") == plugin_name),
                 None)
    if entry is None and len(plugins) == 1 and isinstance(plugins[0], dict):
        entry = plugins[0]
    source = entry.get("source") if entry else None
    if not isinstance(source, dict):
        return []
    kind = source.get("source", "?")
    where = source.get("repo") or source.get("url") or source.get("package") or "?"
    detail = source.get("path") or source.get("ref") or ""
    return [Finding("PB009", f"installed from {kind}: {where}"
                             + (f" ({detail})" if detail else ""))]


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

    # PB007 / PB008 / PB009 - the skill arrived inside a plugin: what else is in the
    # package, what it assumes the package provides, and where the package came from
    root = plugin_root(skill)
    if root:
        out += hook_findings(root)
        out += sibling_findings(skill)
        manifest = _load_json(os.path.join(root, ".claude-plugin", "plugin.json"))
        plugin_name = manifest.get("name") if isinstance(manifest, dict) else None
        out += origin_finding(root, plugin_name or skill.name or skill.folder)
    return out
