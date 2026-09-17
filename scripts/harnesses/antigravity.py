#!/usr/bin/env python3
"""Google Antigravity. Source: https://antigravity.google/docs/ide/skills/"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class Antigravity(HarnessAdapter):
    name = "antigravity"
    title = "Antigravity"
    docs = "https://antigravity.google/docs/ide/skills/"
    supports_skills = True

    locations = (
        ".agents/skills/<name>/SKILL.md",
        ".agent/skills/<name>/SKILL.md",
        "~/.gemini/antigravity/skills/<name>/SKILL.md",
    )
    discovery = ("names and descriptions at the start of a conversation, the full SKILL.md "
                 "when the task looks relevant or the skill is named")

    fields = {
        # The one harness in the registry where `name` is optional: left out, it is taken
        # from the folder. A skill relying on that is invalid everywhere else.
        "name": OPTIONAL,
        "description": REQUIRED,
        "license": OPTIONAL,
        "metadata": OPTIONAL,
    }
    dirs = ("scripts", "examples", "resources")
    limits = {}
    notes = (
        "`.agent/skills` is kept working for older layouts; `.agents/skills` is the "
        "current one.",
        "Documented subdirectories are `scripts/`, `examples/` and `resources/` - not the "
        "`references/` and `assets/` other harnesses name.",
    )
