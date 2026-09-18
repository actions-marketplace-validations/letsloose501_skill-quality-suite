#!/usr/bin/env python3
"""Cursor. Source: https://cursor.com/docs/context/skills

An earlier version of this adapter was built from Cursor's plugins page and claimed
skills reach Cursor only inside a plugin. Cursor's own skills page says otherwise: it
scans `.cursor/skills` and `.agents/skills` at both scopes, and reads `.claude/skills`
and `.codex/skills` as legacy locations. The wrong table reported a `.claude/skills`
path as unreadable here, which is an invented incompatibility - the one output this
module must never produce.
"""
from .base import EXTENSION, OPTIONAL, REQUIRED, HarnessAdapter


class Cursor(HarnessAdapter):
    name = "cursor"
    title = "Cursor"
    docs = "https://cursor.com/docs/context/skills"
    supports_skills = True

    locations = (
        ".cursor/skills/<name>/SKILL.md",
        ".agents/skills/<name>/SKILL.md",
        ".claude/skills/<name>/SKILL.md",
        ".codex/skills/<name>/SKILL.md",
        "~/.cursor/skills/<name>/SKILL.md",
        "~/.agents/skills/<name>/SKILL.md",
        "<plugin>/skills/<name>/SKILL.md",
    )
    discovery = ("the plugin is installed, then its components are found in their default "
                 "directories or at paths named in the manifest")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
        "metadata": OPTIONAL,
        "disable-model-invocation": EXTENSION,
        "paths": EXTENSION,
        "icon": EXTENSION,
        "color": EXTENSION,
    }
    dirs = ("skills", "scripts", "references", "assets")
    limits = {}
    notes = (
        "Reads `.claude/skills` and `.codex/skills` as legacy locations, so a skill written "
        "for either is found without moving.",
        "`paths` limits a skill to files matching a glob; `icon` and `color` are badge "
        "settings for Custom Modes. All four are Cursor's own.",
        "Skills also travel inside a plugin (`plugin.json` at the root or in "
        "`.cursor-plugin/`), which is a packaging choice rather than a second format.",
        "`rules/*.mdc` with `globs` and `alwaysApply` is Cursor's other mechanism; it is "
        "not a skill and this suite does not check it.",
    )
