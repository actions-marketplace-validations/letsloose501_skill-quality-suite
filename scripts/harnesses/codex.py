#!/usr/bin/env python3
"""OpenAI Codex. Source: https://developers.openai.com/codex/skills"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class Codex(HarnessAdapter):
    name = "codex"
    title = "Codex"
    docs = "https://developers.openai.com/codex/skills"
    supports_skills = True

    locations = (
        ".agents/skills/<name>/SKILL.md",
        "<repo-root>/.agents/skills/<name>/SKILL.md",
        "~/.agents/skills/<name>/SKILL.md",
        "/etc/codex/skills/<name>/SKILL.md",
    )
    discovery = ("explicit with `$skill-name`, or selected from the description; the "
                 "discovery listing is capped at 2% of the context window or 8000 characters")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
        "metadata": OPTIONAL,
    }
    dirs = ("scripts", "references", "assets", "agents")
    limits = {}
    name_matches_dir = None
    notes = (
        "`agents/openai.yaml` is the Codex-side switch: `allow_implicit_invocation: false` "
        "leaves the skill reachable by name only.",
        "The 8000-character discovery budget is shared by every installed skill's "
        "description, so a long description here costs the other skills their visibility.",
    )
