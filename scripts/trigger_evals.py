#!/usr/bin/env python3
"""Does the skill actually fire? The official trigger-eval loop.

Every other check in this suite reads text. This one runs the agent: it sends each
query to a headless session and looks at whether the skill was loaded. That is a
stronger question than any description-reading check can answer, because a judge asked
"where would this wording route" is reasoning about the description, while this
observes the activation.

The method is the one documented in the skill-creation guidance:

    evals/eval_queries.json   [{"query": "...", "should_trigger": true}, ...]

    * about twenty queries, eight to ten on each side
    * each query run several times, because the model is not deterministic
    * a trigger rate above the threshold means "it fires"
    * a train/validation split, so a description tuned against the failures can be
      checked for generalising rather than for memorising

It costs money and minutes, so nothing here runs unless asked. `sqs.py evals --trigger`
is the only entry point.
"""
import json
import os
import random
import subprocess
import sys

QUERIES = "evals/eval_queries.json"
DEFAULT_RUNS = 3
THRESHOLD = 0.5
TRAIN_SHARE = 0.6


def load_queries(skill_root):
    path = os.path.join(skill_root, QUERIES)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def split(queries, seed=0):
    """Stratified train/validation split, fixed so iterations compare like with like.

    Stratified because a random cut can put every negative on one side, and a set with
    no negatives measures breadth only - it cannot tell you the description got greedy.
    """
    rng = random.Random(seed)
    train, valid = [], []
    for want in (True, False):
        side = [q for q in queries if q.get("should_trigger") is want]
        rng.shuffle(side)
        cut = round(len(side) * TRAIN_SHARE)
        train += side[:cut]
        valid += side[cut:]
    rng.shuffle(train)
    rng.shuffle(valid)
    return train, valid


def fired(payload, skill_name):
    """Whether the transcript shows this skill being loaded.

    Walks the whole structure instead of assuming a shape: the envelope differs between
    clients and versions, and a detector that silently matches nothing would report a
    perfect zero trigger rate and look like a description problem.
    """
    hit = False

    def walk(node):
        nonlocal hit
        if hit:
            return
        if isinstance(node, dict):
            if node.get("type") == "tool_use" and node.get("name") in ("Skill", "skill"):
                arg = node.get("input") or {}
                if arg.get("skill") == skill_name or arg.get("name") == skill_name:
                    hit = True
                    return
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(payload)
    return hit


def run_once(query, skill_name, model=None, timeout=180):
    """One headless run. Returns True/False, or None when the run itself failed."""
    cmd = ["claude", "-p", query, "--output-format", "json", "--permission-mode", "plan"]
    if model:
        cmd += ["--model", model]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"    run failed: {e}", file=sys.stderr)
        return None
    if r.returncode != 0:
        print(f"    claude exited {r.returncode}: {(r.stderr or '').strip()[:200]}",
              file=sys.stderr)
        return None
    try:
        payload = json.loads(r.stdout)
    except ValueError:
        # Not JSON: fall back to the raw text, which still carries the tool call.
        return f'"{skill_name}"' in r.stdout and "Skill" in r.stdout
    return fired(payload, skill_name)


def measure(queries, skill_name, runs, model, show):
    """[(query, should_trigger, trigger_rate, usable_runs)] for one set."""
    out = []
    for i, q in enumerate(queries, 1):
        text, want = q["query"], bool(q.get("should_trigger"))
        hits = usable = 0
        for _ in range(runs):
            got = run_once(text, skill_name, model)
            if got is None:
                continue
            usable += 1
            hits += int(got)
        rate = hits / usable if usable else None
        out.append((text, want, rate, usable))
        if show:
            ok = passed(want, rate)
            mark = "?" if rate is None else ("OK " if ok else "FAIL")
            print(f"  {mark:<5}{'+' if want else '-'} {rate if rate is None else f'{rate:.2f}'}"
                  f"  {text[:70]}")
    return out


def passed(want, rate):
    if rate is None:
        return None
    return rate > THRESHOLD if want else rate <= THRESHOLD


def pass_rate(rows):
    judged = [passed(w, r) for _, w, r, _ in rows if r is not None]
    return (sum(judged) / len(judged)) if judged else None


def report(skill_name, sets, runs):
    lines = [f"Trigger evals: {skill_name}", ""]
    worst = 0
    for label, rows in sets:
        rate = pass_rate(rows)
        unusable = sum(1 for _, _, r, _ in rows if r is None)
        shown = "n/a" if rate is None else f"{rate:.0%}"
        lines.append(f"  {label:<12}{len(rows):>3} queries x {runs} runs   pass rate {shown}"
                     + (f"   ({unusable} unusable)" if unusable else ""))
        if rate is not None and rate < 1.0:
            worst = 1
    lines.append("")
    for label, rows in sets:
        bad = [(q, w, r) for q, w, r, _ in rows if passed(w, r) is False]
        if not bad:
            continue
        lines.append(f"  {label} failures:")
        for q, w, r in bad:
            why = ("did not fire" if w else "fired when it should not")
            lines.append(f"    [{r:.2f}] {why}: {q[:78]}")
        lines.append("")
    lines.append("  Failures in the train set guide the next description; the validation "
                 "pass rate is what")
    lines.append("  says whether the change generalised. Keep validation results out of "
                 "the revision itself.")
    return "\n".join(lines), worst


def run(skill, runs=DEFAULT_RUNS, model=None, use_split=True, show=False, seed=0):
    """Returns (text report, exit code). None when the skill carries no query set."""
    queries = load_queries(skill.root)
    if queries is None:
        return None, 0
    name = skill.name or skill.folder
    total = len(queries) * runs * (1 if not use_split else 1)
    print(f"{total} headless runs against `{name}`; this costs money and time.",
          file=sys.stderr)

    if use_split and len(queries) >= 6:
        train, valid = split(queries, seed)
        sets = [("train", measure(train, name, runs, model, show)),
                ("validation", measure(valid, name, runs, model, show))]
    else:
        sets = [("all", measure(queries, name, runs, model, show))]
    return report(name, sets, runs)
