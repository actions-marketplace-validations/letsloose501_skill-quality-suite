#!/usr/bin/env python3
"""Claude Code. Source: https://github.com/anthropics/claude-code"""
from .base import EXTENSION, OPTIONAL, REQUIRED, HarnessAdapter


class ClaudeCode(HarnessAdapter):
    name = "claude-code"
    title = "Claude Code"
    docs = "https://github.com/anthropics/claude-code"
    supports_skills = True

    locations = (
        ".claude/skills/<name>/SKILL.md",
        "~/.claude/skills/<name>/SKILL.md",
        "<plugin>/skills/<name>/SKILL.md",
    )
    discovery = ("name and description are held in context; the body and its references "
                 "load when the description matches, or when the name is typed")

    fields = {
        "name": REQUIRED,
        "description": REQUIRED,
        "license": OPTIONAL,
        "compatibility": OPTIONAL,
        "metadata": OPTIONAL,
        "allowed-tools": OPTIONAL,
        "model": EXTENSION,
        "argument-hint": EXTENSION,
        # Not Claude Code's alone: Cursor documents the same field.
        "disable-model-invocation": EXTENSION,
        "user-invocable": EXTENSION,
    }
    dirs = ("references", "scripts", "assets")
    limits = {"name": 64, "description": 1024, "compatibility": 500}
    name_matches_dir = True
    tool_namespace = "claude-code"
    notes = (
        "`disable-model-invocation: true` removes the description from the agent's reach: "
        "the skill costs no context and only a human can call it.",
    )
