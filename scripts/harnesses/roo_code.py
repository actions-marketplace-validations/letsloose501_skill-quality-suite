#!/usr/bin/env python3
"""Roo Code. Source: https://docs.roocode.com/features/skills"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class RooCode(HarnessAdapter):
    name = "roo-code"
    title = "Roo Code"
    docs = "https://docs.roocode.com/features/skills"
    supports_skills = True

    locations = (
        ".roo/skills/<name>/SKILL.md",
        ".agents/skills/<name>/SKILL.md",
        "~/.roo/skills/<name>/SKILL.md",
        "~/.agents/skills/<name>/SKILL.md",
    )
    discovery = ("indexed at startup by a file watcher that also picks up edits; `.roo/` "
                 "paths outrank `.agents/` ones")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
        "metadata": OPTIONAL,
    }
    dirs = ("scripts", "references", "assets")
    limits = {"name": 64, "description": 1024}
    name_matches_dir = True
    notes = (
        "A `skills-<mode>/` folder targets one Roo mode, which has no equivalent elsewhere.",
    )
