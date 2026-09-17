#!/usr/bin/env python3
"""Cline. Source: https://docs.cline.bot/customization/skills"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class Cline(HarnessAdapter):
    name = "cline"
    title = "Cline"
    docs = "https://docs.cline.bot/customization/skills"
    supports_skills = True

    locations = (
        ".cline/skills/<name>/SKILL.md",
        "~/.cline/skills/<name>/SKILL.md",
    )
    discovery = ("name and description at the start of a conversation, the full file when "
                 "the request matches")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
    }
    dirs = ("docs", "templates", "scripts")
    limits = {}
    notes = (
        "Documented subdirectories are `docs/`, `templates/` and `scripts/`; `references/` "
        "and `assets/` are not named.",
        "The documentation asks for the common cases first in the file, since it is read "
        "top-down.",
    )
