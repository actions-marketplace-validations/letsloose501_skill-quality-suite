#!/usr/bin/env python3
"""GitHub Copilot. Source:
https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
"""
from .base import OPTIONAL, REQUIRED, HarnessAdapter


class Copilot(HarnessAdapter):
    name = "copilot"
    title = "GitHub Copilot"
    docs = "https://docs.github.com/en/copilot/concepts/agents/about-agent-skills"
    supports_skills = True

    locations = (
        ".github/skills/<name>/SKILL.md",
        ".claude/skills/<name>/SKILL.md",
        ".agents/skills/<name>/SKILL.md",
        "~/.copilot/skills/<name>/SKILL.md",
        "~/.agents/skills/<name>/SKILL.md",
    )
    discovery = ("loaded when relevant, across the cloud agent, code review, the CLI, the "
                 "app, and agent mode in VS Code and the JetBrains IDEs")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
    }
    # The published page describes skills as folders of instructions, scripts and
    # resources without naming the directories, so none are recorded rather than assumed.
    dirs = ()
    limits = {}
    notes = (
        "The page names `.github/skills` as Copilot's own folder and reads `.claude/skills` "
        "and `.agents/skills` too.",
        "Subdirectory names are not published, so every directory inside a skill comes back "
        "UNKNOWN here. That is a gap in the documentation, not a defect in the skill.",
    )
