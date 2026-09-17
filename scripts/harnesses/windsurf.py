#!/usr/bin/env python3
"""Windsurf (Cascade). Source: https://docs.windsurf.com/windsurf/cascade/skills"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class Windsurf(HarnessAdapter):
    name = "windsurf"
    title = "Windsurf"
    docs = "https://docs.windsurf.com/windsurf/cascade/skills"
    supports_skills = True

    locations = (
        ".windsurf/skills/<name>/SKILL.md",
        ".agents/skills/<name>/SKILL.md",
        ".claude/skills/<name>/SKILL.md",
        "~/.codeium/windsurf/skills/<name>/SKILL.md",
        "~/.agents/skills/<name>/SKILL.md",
        "~/.claude/skills/<name>/SKILL.md",
    )
    discovery = ("name and description only, until Cascade decides to invoke the skill or "
                 "it is named with `@skill-name`")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
        "metadata": OPTIONAL,
    }
    dirs = ("scripts", "references", "assets")
    limits = {}
    notes = (
        "Reads `.claude/skills` and `.agents/skills` as well as its own folder.",
        "There is a machine-wide tier for managed installs: `/etc/windsurf/skills` on "
        "Linux, `C:\\\\ProgramData\\\\Windsurf\\\\skills` on Windows.",
    )
