#!/usr/bin/env python3
"""Does the skill actually make the agent better at the work?

Every other module reasons about the text. This one runs the task twice - once with
the skill and once without it - and reports what changed. That is the only question in
the suite whose answer can be "the skill is beautifully written and changes nothing",
and it is the question a skill exists to answer yes to.

    task
     ├── baseline   the agent with no skills at all      (`claude --bare`)
     └── treatment  the agent with this one skill loaded (`--plugin-dir`)
                    ↓
              the same grading applied to both

What it measures, per side: how many graded tasks came out right, how many runs failed
outright, how many tool calls and turns it took, how long, how many tokens and how much
it cost, and whether following the skill made the agent do something destructive or
reach for a tool the task forbade.

What it does not measure: whether the answer reads well. That is a judgement, it stays
one, and the report says `ungraded` rather than guessing.

Nothing here runs by default. It costs money and minutes, it needs an agent installed,
and `sqs.py eval --runtime` is the only way in.
"""
import os
import shutil
import statistics
import tempfile

from . import tasks as taskmod


def mean(values):
    """The average of what was actually reported, or None when nothing was.

    None and 0 are different answers and the difference matters: a provider that never
    reported a token count must not average out as a free run.
    """
    vals = [v for v in values if isinstance(v, (int, float))]
    return statistics.fmean(vals) if vals else None


def total(values):
    vals = [v for v in values if isinstance(v, (int, float))]
    return sum(vals) if vals else None


class Side:
    """One arm of the comparison, aggregated over every run of every task."""

    def __init__(self, label):
        self.label = label
        self.runs = []                       # [(task, run, grade)]

    def add(self, task, run, grade):
        self.runs.append((task, run, grade))

    @property
    def usable(self):
        return [(t, r, g) for t, r, g in self.runs if r.ok]

    def metrics(self):
        usable = self.usable
        graded = [(t, r, g) for t, r, g in usable if g.graded]
        m = {
            "runs": len(self.runs),
            "failed_runs": len(self.runs) - len(usable),
            "failure_rate": (len(self.runs) - len(usable)) / len(self.runs) if self.runs else None,
            "graded_runs": len(graded),
            "ungraded_runs": len(usable) - len(graded),
            "success_rate": (sum(1 for _, _, g in graded if g.passed) / len(graded)
                             if graded else None),
            "tool_calls": mean([len(r.tools) for _, r, _ in usable]),
            "turns": mean([r.turns for _, r, _ in usable]),
            "duration_s": mean([r.duration_s for _, r, _ in usable]),
            "tokens": mean([r.tokens for _, r, _ in usable]),
            "cost_usd": total([r.cost_usd for _, r, _ in usable]),
            "unnecessary_tool_calls": sum(g.unnecessary for _, _, g in usable),
            "forbidden_tool_uses": sum(len(g.forbidden) for _, _, g in usable),
            "safety_violations": sum(len(g.unsafe) for _, _, g in usable),
        }
        return m

    def per_task(self):
        out = {}
        for t, r, g in self.runs:
            row = out.setdefault(t.id, {"runs": 0, "ok": 0, "passed": 0, "graded": g.graded})
            row["runs"] += 1
            row["ok"] += int(r.ok)
            row["passed"] += int(g.passed)
        for row in out.values():
            row["success_rate"] = (row["passed"] / row["ok"]) if row["ok"] else None
        return out


def prepare_workdir(task, skill, parent):
    work = tempfile.mkdtemp(prefix="sqs-run-", dir=parent)
    for rel in task.fixtures:
        src = os.path.join(skill.root, rel)
        if not os.path.exists(src):
            continue
        dst = os.path.join(work, os.path.basename(rel))
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
    return work


def evaluate(skill, provider, runs=1, model=None, with_baseline=True, task_filter=None,
             on_event=None):
    """Run the task set on both sides. Returns (report dict, problem).

    Every run gets its own empty working directory, so a `files:` assertion is about
    what this run created and not about what the last one left behind.
    """
    task_list, problem = taskmod.load(skill.root)
    if problem:
        return None, problem
    if task_filter:
        task_list = [t for t in task_list if t.id in task_filter]
        if not task_list:
            return None, f"no task matches {', '.join(sorted(task_filter))}"

    sides = {"treatment": Side("treatment")}
    if with_baseline:
        sides["baseline"] = Side("baseline")

    with tempfile.TemporaryDirectory(prefix="sqs-eval-") as parent:
        for task in task_list:
            for attempt in range(runs):
                for name, side in sides.items():
                    work = prepare_workdir(task, skill, parent)
                    if on_event:
                        on_event(task, name, attempt + 1, runs)
                    run = provider.run(task.prompt,
                                       skill=skill if name == "treatment" else None,
                                       cwd=work, timeout=task.timeout, model=model,
                                       workdir=work)
                    side.add(task, run, taskmod.grade(task, run))

    report = {
        "skill": skill.name or skill.folder,
        "provider": provider.name,
        "model": model,
        "runs_per_task": runs,
        "isolated": provider.isolates_skills,
        "tasks": [t.id for t in task_list],
        "ungraded_tasks": [t.id for t in task_list if not t.graded],
        "sides": {name: side.metrics() for name, side in sides.items()},
        "per_task": {name: side.per_task() for name, side in sides.items()},
        "failures": [
            {"side": name, "task": t.id, "error": r.error,
             "failed_checks": [w for w, ok, _ in g.checks if not ok]}
            for name, side in sides.items() for t, r, g in side.runs
            if not r.ok or (g.graded and not g.passed)
        ],
    }
    return report, ""


# ---- rendering -------------------------------------------------------------

ROWS = [
    ("success_rate", "task success", "pct"),
    ("failure_rate", "runs that failed", "pct"),
    ("tool_calls", "tool calls", "num"),
    ("turns", "turns", "num"),
    ("duration_s", "seconds", "num"),
    ("tokens", "tokens", "num"),
    ("cost_usd", "cost USD", "money"),
    ("unnecessary_tool_calls", "calls over budget", "int"),
    ("forbidden_tool_uses", "forbidden tools used", "int"),
    ("safety_violations", "safety violations", "int"),
]


def fmt(value, kind):
    if value is None:
        return "n/a"
    if kind == "pct":
        return f"{value:.0%}"
    if kind == "money":
        return f"{value:.4f}"
    if kind == "int":
        return str(int(value))
    return f"{value:.1f}"


def render(report):
    sides = report["sides"]
    have_baseline = "baseline" in sides
    lines = [f"Runtime evaluation: {report['skill']}",
             f"  provider {report['provider']}"
             + (f" · model {report['model']}" if report.get("model") else "")
             + f" · {report['runs_per_task']} run(s) per task"
             + f" · {len(report['tasks'])} task(s)", ""]
    if not report.get("isolated"):
        lines.append("  The provider cannot run a task with this skill absent, so the "
                     "baseline column is not")
        lines.append("  a baseline. Read the treatment column alone.")
        lines.append("")

    head = f"  {'':<24}{'treatment':>12}"
    if have_baseline:
        head += f"{'baseline':>12}{'delta':>12}"
    lines += [head, "  " + "-" * (24 + 12 * (3 if have_baseline else 1))]
    for key, label, kind in ROWS:
        t = sides["treatment"].get(key)
        row = f"  {label:<24}{fmt(t, kind):>12}"
        if have_baseline:
            b = sides["baseline"].get(key)
            row += f"{fmt(b, kind):>12}"
            if isinstance(t, (int, float)) and isinstance(b, (int, float)):
                d = t - b
                sign = "+" if d > 0 else ""
                row += f"{sign + fmt(abs(d) if kind == 'pct' else d, kind):>12}"
            else:
                row += f"{'n/a':>12}"
        lines.append(row)

    ungraded = report.get("ungraded_tasks") or []
    if ungraded:
        lines += ["", f"  {len(ungraded)} task(s) carry no assertions and no expected files "
                      f"({', '.join(ungraded[:4])}):",
                  "  they ran and were not scored. A task nobody said the success "
                  "condition for cannot pass."]

    failures = report.get("failures") or []
    if failures:
        lines += ["", "  what went wrong:"]
        for f in failures[:12]:
            what = f["error"] or ("failed: " + ", ".join(f["failed_checks"][:3]))
            lines.append(f"    {f['side']:<10}{f['task']:<14}{what[:70]}")
        if len(failures) > 12:
            lines.append(f"    ... and {len(failures) - 12} more")
    return "\n".join(lines)
