#!/usr/bin/env python3
"""Gemini CLI. Sources:
https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md
https://github.com/google-gemini/gemini-cli/blob/main/docs/extensions/index.md
"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class GeminiCLI(HarnessAdapter):
    name = "gemini-cli"
    title = "Gemini CLI"
    docs = "https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md"
    supports_skills = True

    locations = (
        ".agents/skills/<name>/SKILL.md",
        ".gemini/skills/<name>/SKILL.md",
        "~/.agents/skills/<name>/SKILL.md",
        "~/.gemini/skills/<name>/SKILL.md",
        "<extension>/skills/<name>/SKILL.md",
    )
    discovery = ("four tiers, built-in then extension then user then workspace; within a "
                 "tier `.agents/skills` wins over `.gemini/skills`. Activation goes through "
                 "an `activate_skill` call that asks the human first")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
        "metadata": OPTIONAL,
    }
    dirs = ("scripts", "references", "assets")
    # The published pages name the fields and do not state ceilings, so none are checked.
    limits = {}
    notes = (
        "Activation is consented to by the human each time, so a skill that assumes it is "
        "already loaded will misread the situation.",
        "On activation the skill's own directory is added to the agent's allowed paths, "
        "which is what makes bundled assets readable.",
    )
