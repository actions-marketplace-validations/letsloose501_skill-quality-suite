#!/usr/bin/env python3
"""Cursor. Source: https://prod.cursor.com/docs/plugins

Cursor reads skills through its plugin system rather than from a bare skills folder,
so the locations below are all inside a plugin. Cursor's `.cursor/rules/*.mdc` files
with `globs` and `alwaysApply` are rules, a different mechanism, and a skill is not
converted into one by this suite.
"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class Cursor(HarnessAdapter):
    name = "cursor"
    title = "Cursor"
    docs = "https://prod.cursor.com/docs/plugins"
    supports_skills = True

    locations = (
        "<plugin>/skills/<name>/SKILL.md",
        "~/.cursor/plugins/local/<plugin>/skills/<name>/SKILL.md",
    )
    discovery = ("the plugin is installed, then its components are found in their default "
                 "directories or at paths named in the manifest")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
        "metadata": OPTIONAL,
    }
    dirs = ("skills", "scripts", "references", "assets")
    limits = {}
    notes = (
        "A skill reaches Cursor inside a plugin: a `plugin.json` at the root (agent-plugin "
        "schema) or in `.cursor-plugin/`. A loose skill folder is not picked up.",
        "`rules/*.mdc` with `globs` and `alwaysApply` is Cursor's other mechanism; it is "
        "not a skill and this suite does not check it.",
    )
