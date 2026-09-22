#!/usr/bin/env python3
"""The eval files a skill carries, checked against the two documented shapes.

The official skill-creation guidance puts evals inside the skill directory in two
files with different jobs:

    evals/eval_queries.json   [{query, should_trigger}]          does it fire at all
    evals/evals.json          {skill_name, evals: [{...}]}       is the output any good

This module only reads them. Running them costs money and lives in `evaluation/`,
behind `sqs.py eval`: `--trigger` for the query set, `--runtime` for the task set.
Reading the outputs afterwards stays a human's job, and no linter should pretend
otherwise.

An `evals/` directory that does not parse is worse than none, because from the outside
it looks like the skill is tested.
"""
import json
import os

from core import Finding
from evaluation import tasks as taskmod

QUERIES = "evals/eval_queries.json"
CASES = "evals/evals.json"
# The guidance asks for about twenty queries, eight to ten on each side.
SIDE_MIN = 8


def _load(skill, rel):
    path = os.path.join(skill.root, rel)
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except (OSError, ValueError) as e:
        return None, str(e)


def check(skill, cfg=None):
    out = []
    if not skill.ok:
        return out

    data, err = _load(skill, QUERIES)
    if err:
        out.append(Finding("EV004", f"{QUERIES} does not parse: {err}", where=QUERIES))
    elif data is not None:
        if not isinstance(data, list):
            out.append(Finding("EV004", f"{QUERIES} is not a list of "
                                        f"{{query, should_trigger}}", where=QUERIES))
        else:
            bad = [i for i, q in enumerate(data)
                   if not isinstance(q, dict) or "query" not in q
                   or not isinstance(q.get("should_trigger"), bool)]
            if bad:
                out.append(Finding("EV004", f"{QUERIES}: {len(bad)} entr"
                                            f"{'y' if len(bad) == 1 else 'ies'} without a "
                                            f"`query` and a boolean `should_trigger` "
                                            f"(first at index {bad[0]})", where=QUERIES))
            else:
                pos = sum(1 for q in data if q["should_trigger"])
                neg = len(data) - pos
                if pos < SIDE_MIN or neg < SIDE_MIN:
                    out.append(Finding("EV005", f"{pos} should-trigger and {neg} "
                                                f"should-not-trigger queries; the negatives "
                                                f"are what test precision, and the useful "
                                                f"ones are near-misses", where=QUERIES))

    data, err = _load(skill, CASES)
    if err:
        out.append(Finding("EV004", f"{CASES} does not parse: {err}", where=CASES))
    elif data is not None:
        if not isinstance(data, dict) or not isinstance(data.get("evals"), list):
            out.append(Finding("EV004", f"{CASES} is not "
                                        f"{{skill_name, evals: [...]}}", where=CASES))
        else:
            missing = [e.get("id", i) for i, e in enumerate(data["evals"])
                       if not isinstance(e, dict) or not e.get("prompt")
                       or not e.get("expected_output")]
            if missing:
                out.append(Finding("EV004", f"{CASES}: case(s) {missing[:3]} lack a `prompt` "
                                            f"or an `expected_output`", where=CASES))
            out += _preflight(skill)
    return out


def _preflight(skill):
    """EV008 / EV009 - the pre-flight gate `eval --runtime` applies, run for free.

    The same reading the paid pass refuses to spend on, so an author sees it on every
    `check` rather than on the one run that would have cost money. `EV004` already
    covers the first two things a case needs - an objective and an expected outcome;
    these are the other two: a decidable pass criterion, and a case that can run as
    written in both arms.
    """
    task_list, problem = taskmod.load(skill.root)
    if problem:
        return []                        # EV004 has already said why
    out = []
    for task_id, kind, why in taskmod.preflight(skill.root, task_list):
        code = "EV009" if kind == "unrunnable" else "EV008"
        out.append(Finding(code, f"case `{task_id}`: {why}", where=CASES))
    return out


def has_evals(skill):
    return os.path.isdir(os.path.join(skill.root, "evals"))
