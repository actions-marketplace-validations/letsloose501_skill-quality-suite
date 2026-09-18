#!/usr/bin/env python3
"""skill-quality-suite - one command for every check a skill can be put through.

    sqs.py check                     structure + spec + quality + compat + security
    sqs.py check my-skill --strict   one skill, warnings count as failures
    sqs.py structure|spec|quality|compat|security|publish|evals|fix  one module
    sqs.py explain ST008             what a code means and how to fix it
    sqs.py rules --module quality    the registry
    sqs.py new my-skill              scaffold a skill that already passes

The modules are separate because they fail at different moments. Structure breaks
today, silently. Spec breaks on publication. Compat breaks on somebody else's machine.
Evals break when a neighbouring description moves. Running them as one pass would
report all four with the same urgency, which is how a report stops being read.

Output: `--format text` (default), `json`, or `github` for CI annotations.
Exit codes: 0 clean · 1 findings that count as failures · 2 usage error.

A line carrying `sqs-allow: SE002` (or `sqs-allow: *`) is exempt from that code - the
escape hatch for a file that documents a pattern rather than using it.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import compat                                                   # noqa: E402
import evalcheck                                                # noqa: E402
import fix as fixer                                             # noqa: E402
import portability                                              # noqa: E402
import publish                                                  # noqa: E402
import quality                                                  # noqa: E402
import security                                                 # noqa: E402
import spec                                                     # noqa: E402
import trigger_evals                                            # noqa: E402
from core import Finding, Skill, discover                       # noqa: E402
from harnesses import registry as harness_registry              # noqa: E402
from model import SkillModel                                    # noqa: E402
from rules import MODULES, RULES, module_of, severity_of        # noqa: E402

_CODES = r"([A-Z]{2}\d{3}(?:\s*,\s*[A-Z]{2}\d{3})*|\*)"
SUPPRESS_RE = re.compile(r"sqs-allow:\s*" + _CODES)
SUPPRESS_FILE_RE = re.compile(r"sqs-allow-file:\s*" + _CODES)
RANK = {"error": 0, "warning": 1, "info": 2}
SIGIL = {"error": "⛔", "warning": "⚠️ ", "info": "· "}
CHECK_MODULES = ("structure", "spec", "quality", "compat", "security")


def skills_dir(arg=None):
    """Where the skills live: the flag, then the environment, then the default."""
    if arg:
        return os.path.abspath(os.path.expanduser(arg))
    env = os.environ.get("CLAUDE_SKILLS_DIR")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    up = os.path.dirname(os.path.dirname(HERE))
    if os.path.isdir(up) and any(
            os.path.isfile(os.path.join(up, d, "SKILL.md")) for d in os.listdir(up)
            if os.path.isdir(os.path.join(up, d))):
        return up
    return os.path.expanduser("~/.claude/skills")


def resolve_targets(args, root):
    """(skills, notes) for whatever the user pointed at.

    A target is a path or a name, because both are how people arrive here: a path when
    they are working on one skill or a checkout, a name when they are sweeping their own
    tree. A path that turns out to be a plugin is unwrapped to the skills inside it -
    the plugin's commands, agents and hooks are somebody else's tool's business.
    """
    import glob
    if not args:
        return discover(root), []
    skills, notes = [], []
    for arg in args:
        path = os.path.abspath(os.path.expanduser(arg))
        if not os.path.isdir(path):
            named = os.path.join(root, arg)
            if os.path.isfile(os.path.join(named, "SKILL.md")):
                skills.append(Skill(named))
            else:
                notes.append(f"no skill named `{arg}` and no directory at that path")
            continue
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            skills.append(Skill(path))
            continue
        inside = sorted(glob.glob(os.path.join(path, "skills", "*", "SKILL.md")))
        if inside:
            found = [Skill(os.path.dirname(p)) for p in inside]
            skills += found
            notes.append(f"plugin container `{os.path.basename(path)}`: "
                         f"{len(found)} skill(s) checked, other plugin components "
                         f"(commands, agents, hooks, manifest) were not analysed")
            continue
        loose = sorted(glob.glob(os.path.join(path, "*", "SKILL.md")))
        if loose:
            skills += [Skill(os.path.dirname(p)) for p in loose]
        else:
            notes.append(f"no SKILL.md under `{arg}`")
    return skills, notes


def load_config(root, path=None):
    """`sqs.config.json` beside the skills, unless a path is given.

    Keys: `rules` (code -> off/info/warning/error), `ignore` (skill names),
    `agents` (runtimes the skills target), `lang`, `allow_dirs`.
    """
    path = path or os.path.join(root, "sqs.config.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print(f"config {path}: {e}", file=sys.stderr)
        return {}


def load_structure_engine(root):
    """check_skills.py, imported rather than shelled out to.

    It is the structure engine and it already carries the rule codes; parsing its
    printed output back into findings would be a second, drifting source of truth.
    """
    for candidate in (os.path.join(root, "check_skills.py"),
                      os.path.join(HERE, "check_skills.py")):
        if os.path.isfile(candidate):
            os.environ.setdefault("CLAUDE_SKILLS_DIR", root)
            sp = importlib.util.spec_from_file_location("check_skills", candidate)
            mod = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(mod)
            return mod
    return None


_warned_no_engine = False


def structure_findings(skill, engine):
    if engine is None:
        # A missing tool is not a finding about the skill: giving it a rule code would
        # put "your linter is not installed" in the same list as "your links are
        # broken", and the reader would have to tell them apart.
        global _warned_no_engine
        if not _warned_no_engine:
            _warned_no_engine = True
            print("check_skills.py not found beside the skills - the structure module is "
                  "skipped", file=sys.stderr)
        return []
    errors, warnings, _, _ = engine.check(skill.folder)
    return ([Finding(f.code, f.msg, severity="error") for f in errors] +
            [Finding(f.code, f.msg, severity="warning") for f in warnings])


def evals_findings(root, live=False, names=()):
    """Routing checks, delegated to the runner that owns them."""
    runner = os.path.join(root, "evals", "run_evals.py")
    if not os.path.isfile(runner):
        return [Finding("EV002", "no evals/ beside the skills - nothing verifies that any "
                                 "description still fires on the wording a human uses",
                        severity="info")]
    cmd = [sys.executable, runner, "--quiet"]
    if live:
        cmd.append("--live")
    for n in names:
        cmd += ["--skill", n]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0:
        return []
    detail = (r.stderr or r.stdout or "").strip() or f"exit {r.returncode}"
    code = "EV003" if live and r.returncode == 1 else "EV001"
    return [Finding(code, detail.replace("\n", "\n        "), severity="error")]


_LINE_CACHE = {}


def _lines(path):
    if path not in _LINE_CACHE:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                _LINE_CACHE[path] = fh.read().split("\n")
        except OSError:
            _LINE_CACHE[path] = []
    return _LINE_CACHE[path]


def _waives(text, code):
    m = SUPPRESS_RE.search(text) or SUPPRESS_FILE_RE.search(text)
    return bool(m) and (m.group(1) == "*" or code in m.group(1))


def suppressed(skill, f):
    """Whether the file or the line waives that code.

    Two scopes, because two different things need waiving. A line-scoped `sqs-allow`
    covers one quotation of a pattern. A file-scoped `sqs-allow-file` in the header
    covers a file whose whole job is to hold the patterns - a rule registry trips every
    rule it describes, and annotating each occurrence would be noise pretending to be
    care.
    """
    if not f.where:
        return False
    lines = _lines(os.path.join(skill.root, f.where))
    if any(SUPPRESS_FILE_RE.search(ln) and _waives(ln, f.code) for ln in lines[:25]):
        return True
    if not f.line:
        return False
    for n in (f.line - 1, f.line - 2):          # the line itself, or the one above it
        if 0 <= n < len(lines) and SUPPRESS_RE.search(lines[n]) and _waives(lines[n], f.code):
            return True
    return False


def collect(skill, modules, cfg, skill_registry, engine, world=None):
    out = []
    for name in modules:
        if name == "structure":
            out += structure_findings(skill, engine)
        elif name == "spec":
            out += spec.check(skill, cfg)
        elif name == "quality":
            out += quality.check(skill, cfg, skill_registry)
        elif name == "compat":
            out += compat.check(skill, cfg, world)
        elif name == "security":
            out += security.check(skill, cfg)
        elif name == "publish":
            out += publish.check(skill, cfg)
        elif name == "evals":
            out += evalcheck.check(skill, cfg)
        elif name == "fix":
            out += fixer.check(skill, cfg)
    for f in out:
        f.skill = skill.folder
        if f.severity is None:
            f.severity = severity_of(f.code)
    # the config has the last word on severity, including switching a rule off
    overrides = cfg.get("rules", {})
    out = [f for f in out if overrides.get(f.code) != "off" and not suppressed(skill, f)]
    for f in out:
        if f.code in overrides:
            f.severity = overrides[f.code]
    return sorted(out, key=lambda f: (RANK.get(f.severity, 3), f.code, f.where or ""))


def render_text(results, strict, show_clean):
    lines = []
    for folder, found in results:
        if not found:
            if show_clean:
                lines.append(f"✅ {folder}")
            continue
        worst = min(RANK.get(f.severity, 3) for f in found)
        lines.append(f"{SIGIL[['error', 'warning', 'info'][worst]].strip()} {folder}")
        for f in found:
            place = f" ({f.where}:{f.line})" if f.where and f.line else (
                f" ({f.where})" if f.where else "")
            lines.append(f"     {SIGIL[f.severity]} {f.code} {f.msg}{place}")
    return "\n".join(lines)


def render_github(results):
    out = []
    for folder, found in results:
        for f in found:
            level = {"error": "error", "warning": "warning", "info": "notice"}[f.severity]
            title = RULES.get(f.code, ("", f.code))[1]
            where = f"file={folder}/{f.where}" + (f",line={f.line}" if f.line else "") \
                if f.where else ""
            out.append(f"::{level} {where},title={f.code} {title}::{f.msg}")
    return "\n".join(out)


def render_json(results):
    return json.dumps({
        "findings": [
            {"skill": folder, "code": f.code, "module": module_of(f.code),
             "severity": f.severity, "message": f.msg, "file": f.where, "line": f.line}
            for folder, found in results for f in found
        ]
    }, ensure_ascii=False, indent=2)


def cmd_explain(code):
    code = code.upper()
    row = RULES.get(code)
    if not row:
        near = sorted(c for c in RULES if c.startswith(code[:2]))
        print(f"no rule {code}." + (f" {code[:2]}xx holds: {', '.join(near)}" if near else ""))
        return 2
    severity, title, why, how, fixable = row
    print(f"{code}  {title}")
    print(f"module   {module_of(code)}")
    print(f"severity {severity}" + ("  ·  `sqs.py fix` can repair it" if fixable else ""))
    print(f"\nwhy      {why}")
    print(f"fix      {how}")
    return 0


def cmd_rules(module=None, audit=False):
    if audit:
        # Every code an engine can emit has to have a row here. This is the check that
        # keeps the registry from drifting away from the engines that use it.
        # A code-shaped literal anywhere in an engine counts as emitted. Matching only the
        # constructor call would miss every engine that builds the code first and
        # constructs the finding after - which is most of them.
        literal = re.compile(r'"([A-Z]{2}\d{3})"')
        engines = [os.path.join(HERE, p) for p in sorted(os.listdir(HERE))
                   if p.endswith(".py") and p != "rules.py"]
        engines.append(os.path.join(os.path.dirname(os.path.dirname(HERE)), "check_skills.py"))
        emitted = set()
        for path in engines:
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                emitted |= set(literal.findall(f.read()))
        orphan = sorted(emitted - set(RULES))
        # ST016 is the opt-in external-link check, which has no engine yet: it is the
        # one row here that documents a gap rather than a rule in force.
        unused = sorted(set(RULES) - emitted - {"ST016"})
        if orphan:
            print("emitted with no row in rules.py: " + ", ".join(orphan))
        if unused:
            print("rows nothing emits: " + ", ".join(unused))
        if not orphan and not unused:
            print(f"registry and engines agree · {len(RULES)} rules")
        return 1 if orphan else 0
    for code in sorted(RULES):
        if module and module_of(code) != module:
            continue
        severity, title, _, _, fixable = RULES[code]
        print(f"{code}  {severity:<7}  {module_of(code):<9}  {title}"
              + ("  [fixable]" if fixable else ""))
    return 0


# One line, not a block scalar: a scaffold that trips its own linter teaches the wrong
# thing on the first run.
QUERY_TEMPLATE = [
    {"query": "TODO a realistic prompt that should reach this skill, in the words a "
              "human would actually type - file paths, a bit of backstory, the odd typo",
     "should_trigger": True},
    {"query": "TODO a near-miss: shares vocabulary with the skill and needs something "
              "else. These are the ones that test precision", "should_trigger": False},
]

CASE_TEMPLATE = {
    "skill_name": "",
    "evals": [
        {"id": 1,
         "prompt": "TODO a realistic task for this skill",
         "expected_output": "TODO what success looks like, in a sentence",
         "assertions": ["TODO something checkable about the output"]},
    ],
}


def cmd_init_evals(skills):
    """Scaffold the two documented eval files for each named skill."""
    import json as _json
    made = 0
    for s in skills:
        d = os.path.join(s.root, "evals")
        os.makedirs(d, exist_ok=True)
        for rel, payload in (("eval_queries.json", QUERY_TEMPLATE),
                             ("evals.json", dict(CASE_TEMPLATE,
                                                 skill_name=s.name or s.folder))):
            path = os.path.join(d, rel)
            if os.path.exists(path):
                print(f"{s.folder}: evals/{rel} already exists, left alone")
                continue
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(payload, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"{s.folder}: wrote evals/{rel}")
            made += 1
    if made:
        print("\nFill the TODOs, then `sqs.py evals <skill> --trigger`. Aim for about "
              "twenty queries,\neight to ten on each side; the negatives are what test "
              "precision.")
    return 0


def cmd_harnesses(world, verbose=False):
    """The adapter registry: what a `--harness` name can be, and what it rests on."""
    for a in world:
        support = {True: "skills", False: "no skills", None: "undocumented"}[a.supports_skills]
        print(f"{a.name:<14}{a.title:<16}{support:<14}{a.docs}")
        if verbose:
            for loc in a.locations:
                print(f"    {loc}")
            if a.discovery:
                print(f"    discovery: {a.discovery}")
            for note in a.notes:
                print(f"    note: {note}")
            print()
    if not verbose:
        print(f"\n{len(world)} harnesses · `--harness <name>` or `--harness all` · "
              f"`sqs.py harnesses --show` for locations and caveats")
    return 0


def cmd_compat_report(skills, world, names, fmt):
    """The compatibility report: the one view that is per harness, not per finding."""
    adapters, missing = world.select(names)
    for m in missing:
        print(f"no adapter for `{m}` - known harnesses are {', '.join(world.names())}",
              file=sys.stderr)
    if not adapters:
        return 2
    blobs, worst = [], 0
    for s in skills:
        model = SkillModel(s, world)
        results = portability.analyse(model, adapters, world)
        if fmt == "json":
            blobs.append(portability.report_json(model, results))
        else:
            blobs.append(portability.report_text(model, results))
        if any(r.verdict == portability.INCOMPATIBLE for r in results):
            worst = 1
    if fmt == "json":
        print(json.dumps(blobs if len(blobs) > 1 else blobs[0],
                         ensure_ascii=False, indent=2))
    else:
        print(("\n\n" + "-" * 60 + "\n\n").join(blobs))
    return worst


TEMPLATE = """---
name: {name}
description: TODO one sentence on what this skill is, then the branches that should trigger it - the wordings a human actually uses, one per distinct branch, because synonyms that rename one branch are one branch written twice.
---

# {title}

TODO the steps, in the order the agent performs them. Each one ends on a condition the
agent can check: "every modified model accounted for", not "understanding reached".

## When to open which reference

TODO name each reference and the branch that reaches it. Material every branch needs
stays here; material only some branches reach goes into references/ behind a pointer.
"""


def cmd_new(root, name):
    target = os.path.join(root, name)
    if os.path.exists(target):
        print(f"{target} already exists", file=sys.stderr)
        return 2
    os.makedirs(os.path.join(target, "references"))
    with open(os.path.join(target, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(name=name, title=name.replace("-", " ").capitalize()))
    print(f"created {target}/SKILL.md")
    print("Next: fill it from a real run of the work, not from an idea of the work, then")
    print(f"      python {os.path.relpath(__file__, os.getcwd())} check {name}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sqs.py", add_help=True,
                                 description="quality suite for Agent Skills")
    ap.add_argument("command", help="check | all | " + " | ".join(sorted(MODULES.values()))
                    + " | fix | explain | rules | harnesses | new")
    ap.add_argument("args", nargs="*", help="skill names, a rule code, or a new skill's name")
    ap.add_argument("--skills-dir")
    ap.add_argument("--config")
    ap.add_argument("--format", choices=("text", "json", "github"), default="text")
    ap.add_argument("--strict", action="store_true", help="warnings count as failures")
    ap.add_argument("--quiet", action="store_true", help="print nothing when clean")
    ap.add_argument("--harness", action="append", default=[],
                    help="target environment; repeatable, comma-separated, or `all`")
    ap.add_argument("--agents", help="deprecated alias for --harness")
    ap.add_argument("--show", action="store_true",
                    help="harnesses: locations, discovery and caveats for each")
    ap.add_argument("--lang", help="the language the published docs are written in")
    ap.add_argument("--trigger", action="store_true",
                    help="evals: run the agent against evals/eval_queries.json (costs money)")
    ap.add_argument("--init", action="store_true",
                    help="evals: scaffold the two documented eval files")
    ap.add_argument("--runs", type=int, default=3, help="evals --trigger: runs per query")
    ap.add_argument("--no-split", action="store_true",
                    help="evals --trigger: measure one set instead of train/validation")
    ap.add_argument("--live", action="store_true", help="evals: ask the model, not the invariants")
    ap.add_argument("--apply", action="store_true", help="fix: write the repairs")
    ap.add_argument("--module", help="rules: only this module")
    ap.add_argument("--audit", action="store_true", help="rules: registry against the engines")
    a = ap.parse_args(argv)

    if a.command == "explain":
        return cmd_explain(a.args[0]) if a.args else cmd_rules()
    if a.command == "rules":
        return cmd_rules(a.module, a.audit)
    world = harness_registry()
    if a.command == "harnesses":
        return cmd_harnesses(world, a.show)

    root = skills_dir(a.skills_dir)
    if not os.path.isdir(root):
        print(f"no skills directory at {root}", file=sys.stderr)
        return 2
    if a.command == "new":
        return cmd_new(root, a.args[0]) if a.args else 2

    cfg = load_config(root, a.config)
    picked = []
    for chunk in list(a.harness) + ([a.agents] if a.agents else []):
        picked += [s.strip() for s in chunk.split(",") if s.strip()]
    if picked:
        cfg["harnesses"] = picked
    if a.lang:
        cfg["lang"] = a.lang

    if a.command == "check":
        modules = list(CHECK_MODULES)
    elif a.command == "all":
        modules = list(CHECK_MODULES) + ["publish"]
    elif a.command in set(MODULES.values()) | {"fix"}:
        modules = [a.command]
    else:
        print(f"unknown command {a.command!r}", file=sys.stderr)
        return 2

    ignore = set(cfg.get("ignore", []))
    names = [n for n in a.args if n not in ignore]
    skills, notes = resolve_targets(names, root)
    skills = [s for s in skills if s.folder not in ignore]
    for note in notes:
        print(note, file=sys.stderr)
    skill_registry = {s.name or s.folder: s.slash_only for s in discover(root)}

    # The compatibility report is a different view of the same analysis, not a
    # different analysis: per harness rather than per finding. `check --harness` still
    # folds the same verdicts into the ordinary report, so CI can fail on them.
    if a.command == "compat" and compat.harness_names(cfg) and skills:
        return cmd_compat_report(skills, world, compat.harness_names(cfg), a.format)

    # evals is a whole-tree check: it compares descriptions against each other, so it
    # has no per-skill form and runs once.
    eval_findings = []
    if a.command in ("evals", "all"):
        # Routing is a property of the whole tree, so it runs once rather than per skill.
        eval_findings = evals_findings(root, a.live, names)

    # The trigger loop runs the agent, so it is opt-in and never part of `check`.
    if a.command == "evals" and a.trigger:
        rc = 0
        ran = False
        for s in skills:
            text, code = trigger_evals.run(s, runs=a.runs, model=cfg.get("live_model"),
                                           use_split=not a.no_split, show=a.show)
            if text is None:
                print(f"{s.folder}: no evals/eval_queries.json - "
                      f"`sqs.py evals {s.folder} --init` writes one", file=sys.stderr)
                continue
            ran = True
            print(text)
            rc = max(rc, code)
        return rc if ran else 2

    if a.command == "evals" and a.init:
        return cmd_init_evals(skills)

    engine = load_structure_engine(root) if "structure" in modules else None

    if a.command == "fix":
        rc = 0
        for s in skills:
            entries = fixer.plan(s)
            if not entries:
                continue
            for code, what, _ in entries:
                print(f"{'fixed' if a.apply else 'would fix'}  {s.folder}  {code}  {what}")
            if a.apply:
                fixer.apply(s, entries)
            else:
                rc = 1
        if rc == 0 and not a.quiet:
            print("nothing to fix" if not a.apply else "done")
        return rc

    results = [(s.folder, collect(s, modules, cfg, skill_registry, engine, world))
               for s in skills]

    # A duplicate `name` is only visible from above: one skill shadows the other and
    # which one wins is not knowable in advance.
    by_name = {}
    for s in skills:
        by_name.setdefault(s.name or s.folder, []).append(s.folder)
    dupes = [Finding("ST014", f"`name: {n}` in {', '.join(d)} - one shadows the other",
                     severity="error") for n, d in sorted(by_name.items()) if len(d) > 1]
    if dupes or eval_findings:
        results.append(("(all skills)", dupes + eval_findings))

    flat = [f for _, found in results for f in found]
    failures = sum(1 for f in flat
                   if f.severity == "error" or (a.strict and f.severity == "warning"))

    if a.format == "json":
        print(render_json(results))
    elif a.format == "github":
        out = render_github(results)
        if out:
            print(out)
    elif not (a.quiet and not flat):
        body = render_text(results, a.strict, show_clean=not a.quiet)
        if body:
            print(body)
        if not a.quiet and skills:
            counts = {k: sum(1 for f in flat if f.severity == k)
                      for k in ("error", "warning", "info")}
            print(f"\n{len(skills)} skill(s) · {counts['error']} error · "
                  f"{counts['warning']} warning · {counts['info']} info"
                  f"  ·  `sqs.py explain <CODE>` for any of them")
        elif not a.quiet and not flat:
            print("✅ routing clean")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
