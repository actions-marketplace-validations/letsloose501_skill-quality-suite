#!/usr/bin/env python3
"""The golden corpus, run against the suite.

Every case under `fixtures/` is a small skills tree with an `expect.json` beside it:
what the suite has to say about that tree, by rule code. The runner executes the suite
exactly the way a user would - a subprocess, `--format json` - and compares the codes.

    python tests/run_tests.py                 every case, then the unit checks
    python tests/run_tests.py clean malicious only those cases
    python tests/run_tests.py --list          what each case is for
    python tests/run_tests.py --coverage      which rules no case observes firing

Two kinds of case, and the second one is the point:

- **positive** - `expect` lists codes the run must report. A rule with no positive case
  has never been observed firing, which is not the same as working.
- **negative** - `reject` lists codes the run must NOT report, and `exact: true` says
  the run must report nothing else at all. `clean/` and `escape-hatches/` are the two
  that matter: a linter is judged by what it stays quiet about.

`expect.json` keys: `note`, `command` (default `check`), `args`, `expect`, `reject`,
`exact`, `generate`. The last one materialises files too heavy to check in - a corpus
carrying a megabyte of filler is a corpus nobody clones.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")
SQS = os.path.join(REPO, "scripts", "sqs.py")
sys.path.insert(0, os.path.join(REPO, "scripts"))

HIDDEN_LINE = "\nSee the " + chr(0x200b) + "setup" + chr(0x202e) + " notes for the rest.\n"
# Assembled here rather than written into a fixture file, for the same reason the
# hidden characters are: a literal that looks like a credential makes the whole
# repository unpushable through somebody else's secret scanner, and then nobody can
# run the corpus at all. It is not a real token and never was - the shape is what
# SE001 matches on.
SECRET_LINE = (chr(10) + "The shared token is `gh" + "p_"
               + "0123456789abcdefghijklmnopqrstuvwxyzAB`." + chr(10))


def cases(only=()):
    for name in sorted(os.listdir(FIXTURES)):
        path = os.path.join(FIXTURES, name)
        spec_path = os.path.join(path, "expect.json")
        if not os.path.isfile(spec_path):
            continue
        if only and name not in only:
            continue
        with open(spec_path, encoding="utf-8") as f:
            yield name, path, json.load(f)


def materialise(path, spec, workdir):
    """A copy of the case with its generated files written in.

    Generation is for the two things a repository should not carry: a file big enough
    to break a budget, and a line of invisible control characters. Both are written
    from code points here, so what the fixture contains is readable in this file.
    """
    if not spec.get("generate"):
        return path
    target = os.path.join(workdir, os.path.basename(path))
    shutil.copytree(path, target)
    for item in spec["generate"]:
        full = os.path.join(target, item["path"].replace("/", os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if "bytes" in item:
            with open(full, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\0" * (item["bytes"] - 8))
        elif "pad_to" in item:
            with open(full, "a", encoding="utf-8", newline="\n") as f:
                filler = ("\nThe rule list continues; this paragraph is filler so the file "
                          "crosses its budget without the repository carrying the weight.\n")
                while os.path.getsize(full) < item["pad_to"]:
                    f.write(filler)
                    f.flush()
        elif item.get("append_hidden") or item.get("append_secret"):
            with open(full, "a", encoding="utf-8", newline=chr(10)) as f:
                if item.get("append_hidden"):
                    f.write(HIDDEN_LINE)
                if item.get("append_secret"):
                    f.write(SECRET_LINE)
    return target


def run_case(path, spec):
    """(codes reported, stderr) for one case."""
    cmd = [sys.executable, SQS, spec.get("command", "check"),
           "--skills-dir", path, "--format", "json"] + list(spec.get("args", []))
    env = dict(os.environ, CLAUDE_SKILLS_DIR=path, PYTHONIOENCODING="utf-8")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, cwd=REPO)
    try:
        payload = json.loads(r.stdout or "{}")
    except ValueError:
        return None, (r.stdout + r.stderr)[:2000]
    return [f["code"] for f in payload.get("findings", [])], r.stderr


def judge(name, spec, codes):
    """[] when the case passes, else the lines explaining what differed."""
    got = set(codes)
    problems = []
    missing = [c for c in spec.get("expect", []) if c not in got]
    if missing:
        problems.append(f"expected and not reported: {', '.join(missing)}")
    forbidden = [c for c in spec.get("reject", []) if c in got]
    if forbidden:
        problems.append(f"reported and must not be: {', '.join(forbidden)}")
    if spec.get("exact"):
        extra = sorted(got - set(spec.get("expect", [])))
        if extra:
            problems.append("reported and not expected: " + ", ".join(
                f"{c} x{codes.count(c)}" for c in extra))
    return problems


# ST015 is reachable only by calling the structure engine directly: `sqs.py` builds its
# work list from folders that HAVE a SKILL.md, so a folder without one is never handed
# to it. The unit check below covers it, and the coverage table counts it here.
# ST016 is the opt-in external-link check, which has no engine yet - a documented gap,
# not a rule waiting for a fixture.
def _declared():
    try:
        with open(os.path.join(HERE, "coverage.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


UNIT_COVERED = set(_declared().get("unit_covered", {}))
NO_ENGINE = set(_declared().get("no_engine", {}))


def unit_checks():
    """What a fixture cannot express: the registry's own invariants.

    These are about the suite rather than about any skill, and they are the checks that
    catch a rule added without a row, or a grading left off.
    """
    import rules
    out = []

    ungraded = rules.ungraded()
    if ungraded:
        out.append(f"rules with no confidence/false-positive grading: {', '.join(ungraded)}")

    for code, rule in rules.RULES.items():
        if rule.confidence not in rules.CONFIDENCE_ORDER:
            out.append(f"{code}: confidence `{rule.confidence}` is not on the ladder")
        if rule.false_positive_risk not in ("unrated", "low", "medium", "high"):
            out.append(f"{code}: false-positive risk `{rule.false_positive_risk}` unknown")
        if rules.module_of(code) == "?":
            out.append(f"{code}: prefix maps to no module")

    # the audit is the gate that keeps registry and engines together
    r = subprocess.run([sys.executable, SQS, "rules", "--audit"],
                       capture_output=True, text=True, encoding="utf-8", cwd=REPO)
    if r.returncode != 0:
        out.append("`sqs.py rules --audit` fails: " + (r.stdout or r.stderr).strip()[:300])

    # ST015: the folder with no SKILL.md, which only the structure engine ever sees.
    # The engine is bundled in `scripts/` in a checkout and sits beside the skills when
    # the suite is installed as one, so the probe looks in both.
    engine_dir = next((d for d in (os.path.join(REPO, "scripts"), os.path.dirname(REPO))
                       if os.path.isfile(os.path.join(d, "check_skills.py"))), None)
    if engine_dir is None:
        out.append("check_skills.py is neither bundled nor beside the skills - the "
                   "structure engine cannot be reached from here")
        return out
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "empty-folder"))
        env = dict(os.environ, CLAUDE_SKILLS_DIR=tmp, PYTHONIOENCODING="utf-8")
        probe = ("import check_skills, json;"
                 "e, w, _, _ = check_skills.check('empty-folder');"
                 "print(json.dumps([f.code for f in e]))")
        r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                           encoding="utf-8", env=env, cwd=engine_dir)
        try:
            codes = json.loads(r.stdout)
        except ValueError:
            codes = []
        if "ST015" not in codes:
            out.append("a folder with no SKILL.md did not produce ST015: "
                       + (r.stdout + r.stderr).strip()[:200])

    # the evaluation layer, driven by the scripted provider: the confusion matrix, the
    # two arms, the storage and the regression gate are arithmetic, and arithmetic that
    # only runs when somebody pays a model is arithmetic nobody tests
    out += evaluation_checks()

    # a skill pointed at directly, with the skills dir pointing at the skill itself.
    # The structure engine resolves a skill by name under the skills dir, and when the
    # two disagree it used to report the skill as having no SKILL.md at all.
    r = subprocess.run([sys.executable, SQS, "check", REPO, "--skills-dir", REPO,
                        "--format", "json"], capture_output=True, text=True,
                       encoding="utf-8", cwd=REPO)
    try:
        codes = [f["code"] for f in json.loads(r.stdout).get("findings", [])]
    except ValueError:
        codes = ["(no json)"]
    if "ST015" in codes:
        out.append("checking a skill with --skills-dir pointing at it reported ST015")

    # every documented format has to produce parseable output on a real skill
    for fmt, parse in (("json", json.loads), ("sarif", json.loads)):
        r = subprocess.run([sys.executable, SQS, "check", REPO, "--format", fmt],
                           capture_output=True, text=True, encoding="utf-8", cwd=REPO)
        try:
            parse(r.stdout)
        except ValueError as e:
            out.append(f"`--format {fmt}` did not produce parseable output: {e}")

    # Code scanning refuses a whole SARIF file over one result without a location
    # ("expected at least one location"), so the finding that has no line to point at -
    # a duplicate `name`, a routing invariant - is the one that breaks the upload for
    # everything else. It is checked on the case that produces exactly that finding.
    # Two cases: `duplicate-name` for a finding about a skill rather than a line, and
    # `routing-static` for one about the whole tree, which has no file of its own at all.
    # The second is the one that broke the upload.
    for case_name, command in (("duplicate-name", "check"), ("routing-static", "evals")):
        case = os.path.join(FIXTURES, case_name)
        r = subprocess.run([sys.executable, SQS, command, "--skills-dir", case,
                            "--format", "sarif"], capture_output=True, text=True,
                           encoding="utf-8", env=dict(os.environ, CLAUDE_SKILLS_DIR=case,
                                                      PYTHONIOENCODING="utf-8"), cwd=REPO)
        try:
            sarif = json.loads(r.stdout)
        except ValueError as e:
            out.append(f"SARIF over {case_name} did not parse: {e}")
            continue
        results = sarif["runs"][0]["results"]
        if not results:
            out.append(f"SARIF over {case_name} carried no results at all")
        placeless = [x["ruleId"] for x in results
                     if not x.get("locations")
                     or not (x["locations"][0].get("physicalLocation", {})
                             .get("artifactLocation", {}).get("uri"))]
        if placeless:
            out.append(f"SARIF results with no location in {case_name}, which makes code "
                       f"scanning reject the whole file: " + ", ".join(placeless))
    return out


def evaluation_checks():
    """The runtime layer against the scripted provider, in a copy nothing else touches."""
    out = []
    src = os.path.join(HERE, "evaluation")
    if not os.path.isdir(src):
        return ["tests/evaluation is missing - the evaluation layer is untested"]
    with tempfile.TemporaryDirectory() as tmp:
        tree = os.path.join(tmp, "evaluation")
        shutil.copytree(src, tree)

        def run_eval(script, *extra):
            env = dict(os.environ, PYTHONIOENCODING="utf-8",
                       SQS_FAKE_RUNS=os.path.join(tree, script))
            cmd = [sys.executable, SQS, "eval", "ledger-lite", "--skills-dir", tree,
                   "--all", "--provider", "fake", "--runs", "2"] + list(extra)
            return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", env=env, cwd=REPO)

        r = run_eval("script-v1.json", "--format", "json")
        try:
            payload = json.loads(r.stdout)
        except ValueError:
            return [f"eval --provider fake produced no JSON: {(r.stdout + r.stderr)[:300]}"]
        metrics = payload["trigger"]["sets"]["train"]["metrics"]
        if metrics["false_positive"] or metrics["false_negative"]:
            out.append(f"the scripted v1 run should trigger cleanly, got {metrics}")
        sides = payload["runtime"]["sides"]
        if "baseline" not in sides:
            out.append("the run carries no baseline arm - there is nothing to compare against")
        if sides.get("treatment", {}).get("success_rate") != 1.0:
            out.append(f"scripted v1 treatment success "
                       f"{sides.get('treatment', {}).get('success_rate')}, expected 1.0")
        if sides.get("baseline", {}).get("success_rate") != 0.0:
            out.append(f"scripted v1 baseline success "
                       f"{sides.get('baseline', {}).get('success_rate')}, expected 0.0 - "
                       f"the two arms are not being told apart")
        if sides.get("treatment", {}).get("tokens") is None:
            out.append("token usage came back None from a script that reports tokens")

        # v2 is deliberately asymmetric - one false positive, no false negatives - so
        # precision and recall have different values here. A symmetric case cannot tell
        # them apart, and a report that swapped the two would pass it.
        r = run_eval("script-v2.json", "--format", "json", "--no-split")
        try:
            m2 = json.loads(r.stdout)["trigger"]["sets"]["all"]["metrics"]
        except (ValueError, KeyError) as e:
            m2 = {}
            out.append(f"the v2 run produced no single-set metrics: {e}")
        want = {"true_positive": 4, "false_positive": 1, "false_negative": 0,
                "true_negative": 3}
        for key, value in want.items():
            if m2 and m2.get(key) != value:
                out.append(f"v2 {key} is {m2.get(key)}, expected {value}")
        if m2 and abs((m2.get("precision") or 0) - 0.8) > 1e-9:
            out.append(f"v2 precision is {m2.get('precision')}, expected 0.8 "
                       f"(4 of the 5 that fired were right)")
        if m2 and (m2.get("recall") or 0) != 1.0:
            out.append(f"v2 recall is {m2.get('recall')}, expected 1.0 "
                       f"(nothing that should fire was missed)")
        if m2 and abs((m2.get("f1") or 0) - 8 / 9) > 1e-9:
            out.append(f"v2 F1 is {m2.get('f1')}, expected 0.889")

        run_eval("script-v1.json", "--save", "v1")
        run_eval("script-v2.json", "--save", "v2")
        cmp = subprocess.run([sys.executable, SQS, "eval", "ledger-lite", "--skills-dir",
                              tree, "--compare", "v1", "v2"],
                             capture_output=True, text=True, encoding="utf-8", cwd=REPO)
        if cmp.returncode != 1:
            out.append(f"a regression between v1 and v2 exited {cmp.returncode}, expected 1")
        for expected in ("REGRESSION DETECTED", "task success", "ledger-02",
                         "trigger cases that flipped"):
            if expected not in cmp.stdout:
                out.append(f"the regression report never mentions {expected!r}")

    # the trigger dataset parser must refuse what it cannot read rather than guess
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    from evaluation import triggers
    nl = chr(10)
    unreadable = ["- prompt: |" + nl + "    two lines" + nl,
                  "key: value" + nl,
                  "- prompt: [a, b]" + nl]
    for bad in unreadable:
        try:
            triggers.parse_simple_yaml(bad, "probe.yaml")
        except triggers.DatasetError:
            continue
        out.append(f"the trigger parser accepted YAML it cannot read: {bad!r}")
    return out


def coverage(all_specs):
    """{code: (positive cases, negative cases)} across the corpus."""
    from rules import RULES
    counts = {c: [0, 0] for c in RULES}
    for _, _, spec in all_specs:
        for c in spec.get("expect", []):
            counts.setdefault(c, [0, 0])[0] += 1
        for c in spec.get("reject", []):
            counts.setdefault(c, [0, 0])[1] += 1
        if spec.get("exact"):
            # a case that must report nothing is a negative case for every rule
            for c in counts:
                counts[c][1] += 1
    for c in UNIT_COVERED:
        counts.setdefault(c, [0, 0])[0] += 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description="the golden corpus")
    ap.add_argument("cases", nargs="*", help="only these fixture directories")
    ap.add_argument("--list", action="store_true", help="what each case is for")
    ap.add_argument("--coverage", action="store_true", help="rule coverage across the corpus")
    ap.add_argument("--no-units", action="store_true", help="fixtures only")
    a = ap.parse_args(argv)

    all_specs = list(cases())
    if a.list:
        for name, _, spec in all_specs:
            print(f"{name}\n    {spec.get('note', '')}\n")
        return 0
    if a.coverage:
        counts = coverage(all_specs)
        unobserved = [c for c, (pos, _) in sorted(counts.items())
                      if not pos and c not in NO_ENGINE]
        for code, (pos, neg) in sorted(counts.items()):
            tail = ""
            if code in NO_ENGINE:
                tail = "   <- no engine emits it yet"
            elif not pos:
                tail = "   <- never observed firing"
            elif code in UNIT_COVERED:
                tail = "   (unit check)"
            print(f"{code}  positive {pos}  negative {neg}{tail}")
        print(f"\n{len(counts) - len(unobserved)}/{len(counts)} rules have a positive case")
        return 1 if unobserved else 0

    picked = list(cases(set(a.cases))) if a.cases else all_specs
    failures = 0
    with tempfile.TemporaryDirectory() as work:
        for name, path, spec in picked:
            root = materialise(path, spec, work)
            codes, err = run_case(root, spec)
            if codes is None:
                print(f"FAIL  {name}\n      the run produced no JSON:\n      {err}")
                failures += 1
                continue
            problems = judge(name, spec, codes)
            if problems:
                failures += 1
                print(f"FAIL  {name}")
                for p in problems:
                    print(f"      {p}")
            else:
                print(f"pass  {name}  ({len(codes)} finding(s))")

    if not a.no_units:
        problems = unit_checks()
        if problems:
            failures += len(problems)
            print("FAIL  unit checks")
            for p in problems:
                print(f"      {p}")
        else:
            print("pass  unit checks")

    print(f"\n{len(picked)} case(s) · {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
