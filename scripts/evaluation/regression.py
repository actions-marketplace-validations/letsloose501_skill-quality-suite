#!/usr/bin/env python3
"""Did the last edit to this skill make it worse?

An evaluation you run once is a number. An evaluation you can compare is a gate. This
module stores a run under a label and diffs two of them - so "I shortened the
description" can be answered with "trigger recall went 0.94 → 0.81 and these three
cases are the ones that stopped firing", instead of a feeling.

    sqs.py eval ./my-skill --runtime --save v1
    ... edit the skill ...
    sqs.py eval ./my-skill --runtime --save v2
    sqs.py eval ./my-skill --compare v1 v2

Runs live in `.sqs/evals/<skill>/<label>.json` beside the skills, out of the skill
itself: an evaluation result is a measurement of a version, not a file that should
ship inside it.

Two kinds of worse, deliberately kept apart. **Quality** - task success, trigger
precision and recall - fails the gate: the skill stopped doing its job. **Cost** -
tokens, money, wall time, tool calls - is reported and does not fail by default,
because a skill that got 18% more expensive and 20% more reliable is a trade somebody
has to look at, not a build to break. `--fail-on-cost` moves the line when a budget
depends on it.
"""
import datetime
import json
import os

STORE = os.path.join(".sqs", "evals")
# How much worse a ratio has to get before it counts. Below this, the model's own
# variance is louder than the change: three runs of twenty queries move a rate by a
# few points on their own, and a gate that fires on that gets switched off.
QUALITY_DROP = 0.05
COST_RISE = 0.15

QUALITY = [
    ("runtime", ("sides", "treatment", "success_rate"), "task success"),
    ("trigger", ("sets", "validation", "metrics", "precision"), "trigger precision"),
    ("trigger", ("sets", "validation", "metrics", "recall"), "trigger recall"),
    ("trigger", ("sets", "all", "metrics", "precision"), "trigger precision"),
    ("trigger", ("sets", "all", "metrics", "recall"), "trigger recall"),
]
COST = [
    ("runtime", ("sides", "treatment", "tokens"), "token usage"),
    ("runtime", ("sides", "treatment", "cost_usd"), "cost"),
    ("runtime", ("sides", "treatment", "duration_s"), "wall time"),
    ("runtime", ("sides", "treatment", "tool_calls"), "tool calls"),
]


def dig(payload, path):
    node = payload
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node if isinstance(node, (int, float)) else None


def store_dir(root, skill_name):
    return os.path.join(root, STORE, skill_name)


def save(root, skill_name, label, payload):
    d = store_dir(root, skill_name)
    os.makedirs(d, exist_ok=True)
    payload = dict(payload, saved=datetime.datetime.now().isoformat(timespec="seconds"),
                   label=label)
    path = os.path.join(d, f"{label}.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def load(root, skill_name, label):
    path = os.path.join(store_dir(root, skill_name), f"{label}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def labels(root, skill_name):
    d = store_dir(root, skill_name)
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def affected_tasks(before, after):
    """Task ids whose success rate fell between the two runs."""
    out = []
    b = ((before.get("runtime") or {}).get("per_task") or {}).get("treatment") or {}
    a = ((after.get("runtime") or {}).get("per_task") or {}).get("treatment") or {}
    for task_id, row in sorted(a.items()):
        old = (b.get(task_id) or {}).get("success_rate")
        new = row.get("success_rate")
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and new < old:
            out.append((task_id, old, new))
    return out


def affected_queries(before, after):
    """Trigger cases whose verdict flipped the wrong way."""
    def index(payload):
        out = {}
        for block in ((payload.get("trigger") or {}).get("sets") or {}).values():
            for case in block.get("cases", []):
                out[case["prompt"]] = case
        return out
    old, new = index(before), index(after)
    flipped = []
    for prompt, case in new.items():
        was = old.get(prompt)
        if not was or case["rate"] is None or was["rate"] is None:
            continue
        want = case["expected"] == "trigger"
        before_ok = (was["rate"] > 0.5) == want
        after_ok = (case["rate"] > 0.5) == want
        if before_ok and not after_ok:
            flipped.append((prompt, was["rate"], case["rate"], case["expected"]))
    return flipped


def compare(before, after, quality_drop=QUALITY_DROP, cost_rise=COST_RISE):
    """What moved between two stored runs, split into quality and cost."""
    moves, regressions, cost_moves = [], [], []
    seen = set()
    for section, path, label in QUALITY:
        b = dig(before.get(section) or {}, path)
        a = dig(after.get(section) or {}, path)
        if b is None or a is None or label in seen:
            continue
        seen.add(label)
        moves.append((label, b, a))
        if b - a > quality_drop:
            regressions.append((label, b, a))
    for section, path, label in COST:
        b = dig(before.get(section) or {}, path)
        a = dig(after.get(section) or {}, path)
        if b is None or a is None or not b:
            continue
        rise = (a - b) / b
        cost_moves.append((label, b, a, rise))
    return {
        "before": before.get("label"), "after": after.get("label"),
        "quality": moves,
        "regressions": regressions,
        "cost": cost_moves,
        "cost_regressions": [row for row in cost_moves if row[3] > cost_rise],
        "tasks": affected_tasks(before, after),
        "queries": affected_queries(before, after),
    }


def render(diff, fail_on_cost=False):
    head = "REGRESSION DETECTED" if diff["regressions"] or (
        fail_on_cost and diff["cost_regressions"]) else "no regression"
    lines = [f"{head}   {diff['before']} → {diff['after']}", ""]
    for label, b, a in diff["quality"]:
        arrow = "→"
        mark = "  " if (b - a) <= QUALITY_DROP else "! "
        lines.append(f"  {mark}{label:<22}{b:.0%} {arrow} {a:.0%}")
    for label, b, a, rise in diff["cost"]:
        mark = "! " if rise > COST_RISE else "  "
        sign = "+" if rise >= 0 else ""
        lines.append(f"  {mark}{label:<22}{b:.4g} → {a:.4g}   {sign}{rise:.0%}")
    if diff["tasks"]:
        lines += ["", "  tasks that got worse:"]
        for task_id, old, new in diff["tasks"]:
            lines.append(f"    {task_id:<24}{old:.0%} → {new:.0%}")
    if diff["queries"]:
        lines += ["", "  trigger cases that flipped:"]
        for prompt, was, now, expected in diff["queries"]:
            lines.append(f"    [{was:.2f} → {now:.2f}] should {expected}: {prompt[:56]}")
    if not diff["regressions"] and diff["cost_regressions"] and not fail_on_cost:
        lines += ["", "  Cost rose past the threshold and quality did not fall. That is a "
                      "trade, not a break;",
                  "  `--fail-on-cost` makes it one when a budget depends on it."]
    return "\n".join(lines)


def failed(diff, fail_on_cost=False):
    return bool(diff["regressions"]) or (fail_on_cost and bool(diff["cost_regressions"]))
