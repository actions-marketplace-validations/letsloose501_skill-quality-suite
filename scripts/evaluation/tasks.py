#!/usr/bin/env python3
"""The task set a runtime evaluation runs, and how one run of one task is graded.

The file is the one the skill-creation guidance already asks for - `evals/evals.json` -
read a little more strictly, because a grader needs something it can check:

    {"skill_name": "pdf-to-xlsx",
     "evals": [{"id": "pdf-to-xlsx-03",
                "prompt":  "Convert quarterly.pdf into a spreadsheet",
                "expected_output": "an .xlsx with one sheet per table",
                "assertions": ["xlsx", "re:\\\\b3 tables?\\\\b", "not:could not"],
                "fixtures": ["evals/files/quarterly.pdf"],
                "files": ["quarterly.xlsx"],
                "forbidden_tools": ["WebSearch"],
                "max_tool_calls": 8}]}

An assertion is a substring by default, a regex behind `re:`, and a prohibition behind
`not:`. `files` names what the run has to have created in its working directory - the
only assertion form that survives a model rewording its answer.

A case with no assertions and no `files` is **ungraded**, and stays that way in the
report. Counting it as a pass would turn "nobody said what success is" into evidence
of success, which is the one number this module must never produce.
"""
import json
import os
import re

CASES = os.path.join("evals", "evals.json")


class Task:
    __slots__ = ("id", "prompt", "expected", "assertions", "files", "fixtures",
                 "forbidden_tools", "max_tool_calls", "timeout")

    def __init__(self, raw, index):
        self.id = str(raw.get("id") or index)
        self.prompt = raw.get("prompt") or ""
        self.expected = raw.get("expected_output") or ""
        self.assertions = [a for a in (raw.get("assertions") or []) if isinstance(a, str)]
        self.files = [f for f in (raw.get("files") or []) if isinstance(f, str)]
        # input files, copied from inside the skill into the run's working directory:
        # a task about a PDF needs the PDF, and a task the agent cannot start is not a
        # measurement of anything
        self.fixtures = [f for f in (raw.get("fixtures") or []) if isinstance(f, str)]
        self.forbidden_tools = raw.get("forbidden_tools") or []
        self.max_tool_calls = raw.get("max_tool_calls")
        self.timeout = raw.get("timeout") or 300

    @property
    def graded(self):
        return bool(self.assertions or self.files)


class Grade:
    __slots__ = ("checks", "graded", "passed", "unnecessary", "forbidden", "unsafe")

    def __init__(self, checks, graded, unnecessary=0, forbidden=(), unsafe=()):
        self.checks = checks                # [(what, ok, detail)]
        self.graded = graded
        self.passed = graded and all(ok for _, ok, _ in checks)
        self.unnecessary = unnecessary
        self.forbidden = list(forbidden)
        self.unsafe = list(unsafe)

    def as_dict(self):
        return {"graded": self.graded, "passed": self.passed,
                "checks": [{"what": w, "ok": ok, "detail": d} for w, ok, d in self.checks],
                "unnecessary_tool_calls": self.unnecessary,
                "forbidden_tools_used": self.forbidden,
                "safety_violations": self.unsafe}


def _dangerous_patterns():
    """The security module's own command patterns, reused on what the agent actually ran.

    A static check reads what a skill *says*; this reads what following the skill made
    the agent *do*. Same patterns, so a rule that is reported at rest is the same rule
    that is reported in flight - and neither list can drift away from the other.
    """
    try:
        from security import DANGEROUS
        return DANGEROUS
    except ImportError:                                            # pragma: no cover
        return []


def grade(task, run):
    checks = []
    text = run.text or ""
    low = text.lower()
    for a in task.assertions:
        if a.startswith("not:"):
            body = a[4:]
            if body.startswith("re:"):
                hit = re.search(body[3:], text, re.I | re.S) is not None
            else:
                hit = body.lower() in low
            checks.append((a, not hit, "found in the answer" if hit else ""))
        elif a.startswith("re:"):
            hit = re.search(a[3:], text, re.I | re.S) is not None
            checks.append((a, hit, "" if hit else "no match in the answer"))
        else:
            hit = a.lower() in low
            checks.append((a, hit, "" if hit else "not in the answer"))
    for rel in task.files:
        full = os.path.join(run.workdir or ".", rel)
        there = os.path.exists(full)
        checks.append((f"file:{rel}", there, "" if there else "never created"))

    used = [name for name, _ in run.tools]
    forbidden = sorted({t for t in task.forbidden_tools if t in used})
    unnecessary = 0
    if task.max_tool_calls is not None and len(run.tools) > task.max_tool_calls:
        unnecessary = len(run.tools) - task.max_tool_calls

    unsafe = []
    for label, rx in _dangerous_patterns():
        for name, arg in run.tools:
            if rx.search(arg):
                unsafe.append(f"{label} (via {name})")
                break
    return Grade(checks, task.graded, unnecessary, forbidden, sorted(set(unsafe)))


def load(skill_root, path=None):
    """(tasks, problem) - the task set, or why there is none to run."""
    full = path or os.path.join(skill_root, CASES)
    if not os.path.isfile(full):
        return [], (f"no {CASES} - `sqs.py evals <skill> --init` scaffolds one, and it "
                    f"has to hold real tasks before a runtime run means anything")
    try:
        with open(full, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        return [], f"{CASES} does not parse: {e}"
    raw = data.get("evals") if isinstance(data, dict) else data
    if not isinstance(raw, list) or not raw:
        return [], f"{CASES} carries no cases"
    tasks = [Task(r, i + 1) for i, r in enumerate(raw) if isinstance(r, dict)]
    tasks = [t for t in tasks if t.prompt]
    if not tasks:
        return [], f"{CASES}: no case carries a `prompt`"
    return tasks, ""
