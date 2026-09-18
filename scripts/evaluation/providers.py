#!/usr/bin/env python3
"""The agents this suite can drive, and what one run of one comes back as.

Everything else in the suite reads text. This layer runs an agent, which makes it the
one part that costs money, takes minutes and needs something installed. It is
therefore opt-in everywhere, and absent by default: `Provider.available()` returns a
reason rather than raising, so a machine with no agent on it gets a sentence instead
of a traceback.

The envelope a headless run prints is not part of any specification, and it differs
between clients and versions. So nothing here indexes into a fixed shape: the parser
walks whatever came back looking for what it knows, and **what it does not find stays
None**. A run whose token count is None reports "not reported by the provider", never
zero - a zero is a measurement, and inventing one is how a comparison quietly starts
lying about cost.
"""
import json
import os
import shutil
import subprocess
import time


class Run:
    """One task, run once, by one agent.

    `ok` is about the run, not about the answer: a run that crashed cannot be scored
    for or against the skill, and mixing the two is how a broken provider looks like a
    bad skill.
    """

    __slots__ = ("ok", "error", "text", "tools", "skills", "duration_s",
                 "tokens_in", "tokens_out", "cost_usd", "turns", "raw", "workdir")

    def __init__(self, ok=True, error=None, text="", tools=None, skills=None,
                 duration_s=None, tokens_in=None, tokens_out=None, cost_usd=None,
                 turns=None, raw=None, workdir=None):
        self.ok = ok
        self.error = error
        self.text = text
        self.tools = tools or []            # [(tool name, input as text)]
        self.skills = skills or []          # skills the transcript shows loading
        self.duration_s = duration_s
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_usd = cost_usd
        self.turns = turns
        self.raw = raw
        self.workdir = workdir

    @property
    def tokens(self):
        if self.tokens_in is None and self.tokens_out is None:
            return None
        return (self.tokens_in or 0) + (self.tokens_out or 0)

    def as_dict(self):
        return {"ok": self.ok, "error": self.error, "text": self.text[:4000],
                "tools": self.tools, "skills": self.skills, "duration_s": self.duration_s,
                "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
                "cost_usd": self.cost_usd, "turns": self.turns}


def walk(node, want, out):
    """Collect every value stored under any of `want`, at any depth.

    A tolerant reader for an envelope nobody promised to keep stable. The alternative -
    indexing into a shape - fails silently on the next version: the field is absent, the
    value reads as missing, and a report of zeros looks exactly like a cheap run.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            if k in want and not isinstance(v, (dict, list)):
                out.setdefault(k, []).append(v)
            walk(v, want, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, want, out)


def collect_tools(node, tools, skills):
    """Tool calls and skill loads, from anywhere in the transcript."""
    if isinstance(node, dict):
        if node.get("type") == "tool_use" and node.get("name"):
            name = node["name"]
            arg = node.get("input") or {}
            tools.append((name, json.dumps(arg, ensure_ascii=False)[:300]))
            if name in ("Skill", "skill"):
                loaded = arg.get("skill") or arg.get("name")
                if loaded:
                    skills.append(loaded)
        for v in node.values():
            collect_tools(v, tools, skills)
    elif isinstance(node, list):
        for v in node:
            collect_tools(v, tools, skills)


class Provider:
    """One way to run a task. Subclasses fill in `available` and `run`."""

    name = "none"
    title = "no agent"
    # Whether this provider can run a task with a named skill present and absent. A
    # provider that cannot is still usable for output quality, and its reports say so
    # instead of calling the comparison a baseline.
    isolates_skills = False

    def available(self):
        return False, "no provider selected"

    def run(self, prompt, skill=None, cwd=None, timeout=300, model=None, workdir=None,
            bare=True):
        """One task, once.

        `skill` loads exactly that skill and nothing else. `bare=False` runs in the
        machine's real environment instead - which is what a trigger measurement needs,
        because the question there is whether this description wins against the
        neighbours it actually competes with.
        """
        raise NotImplementedError


class ClaudeCodeProvider(Provider):
    """The Claude Code CLI in headless mode.

    Isolation rests on two documented flags. `--bare` skips auto-discovery of hooks,
    skills, commands, subagents, plugins and memory, which is what makes a baseline a
    baseline: without it the skill under test is installed on the machine doing the
    measuring, and both sides of the comparison can reach it. `--plugin-dir` then
    loads exactly one plugin from a directory, so the treatment side gets the skill
    under test and nothing else.

    Source: https://code.claude.com/docs/en/cli-reference
    """

    name = "claude"
    title = "Claude Code (headless)"
    isolates_skills = True

    def __init__(self, binary=None):
        self.binary = binary or os.environ.get("SQS_CLAUDE_BIN") or "claude"

    def available(self):
        if not shutil.which(self.binary):
            return False, (f"`{self.binary}` is not on PATH - install the Claude Code CLI, "
                           f"or point SQS_CLAUDE_BIN at it")
        return True, ""

    def plugin_dir(self, skill, workdir):
        """A one-skill plugin, so the treatment side loads this skill and nothing else."""
        plug = os.path.join(workdir, "sqs-plugin")
        target = os.path.join(plug, "skills", skill.name or skill.folder)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copytree(skill.root, target,
                        ignore=shutil.ignore_patterns("__pycache__", ".git", "evals"))
        os.makedirs(os.path.join(plug, ".claude-plugin"), exist_ok=True)
        with open(os.path.join(plug, ".claude-plugin", "plugin.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"name": "sqs-under-test", "version": "0.0.0",
                       "description": "the skill under test, isolated for one run"}, f)
        return plug

    def run(self, prompt, skill=None, cwd=None, timeout=300, model=None, workdir=None,
            bare=True):
        cmd = [self.binary, "-p", prompt,
               "--output-format", "stream-json", "--verbose",
               "--no-session-persistence"]
        # A trigger measurement wants the real tree, so the skill competes with its
        # neighbours; a task measurement wants nothing but the skill under test.
        cmd += ["--bare"] if bare else []
        # Plan mode for the trigger pass: the run only has to show which skill loaded,
        # and letting it act would mean paying for work nobody reads.
        cmd += ["--permission-mode", "bypassPermissions" if bare else "plan"]
        if model:
            cmd += ["--model", model]
        if skill is not None:
            cmd += ["--plugin-dir", self.plugin_dir(skill, workdir or cwd or ".")]
        started = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, cwd=cwd)
        except subprocess.TimeoutExpired:
            return Run(ok=False, error=f"timed out after {timeout}s",
                       duration_s=time.time() - started, workdir=cwd)
        except OSError as e:
            return Run(ok=False, error=str(e), workdir=cwd)
        elapsed = time.time() - started
        if r.returncode != 0:
            return Run(ok=False, error=f"exit {r.returncode}: {(r.stderr or '').strip()[:300]}",
                       duration_s=elapsed, workdir=cwd)
        return self.parse(r.stdout, elapsed, cwd)

    def parse(self, stdout, elapsed, cwd=None):
        """A stream of JSON objects, read for what it happens to carry."""
        events = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        if not events:
            try:
                events = [json.loads(stdout)]
            except ValueError:
                return Run(ok=bool(stdout.strip()), text=stdout.strip(), duration_s=elapsed,
                           error=None if stdout.strip() else "the provider printed nothing",
                           workdir=cwd)
        tools, skills = [], []
        collect_tools(events, tools, skills)
        found = {}
        walk(events, {"total_cost_usd", "cost_usd", "input_tokens", "output_tokens",
                      "num_turns", "duration_ms", "result", "is_error"}, found)

        def last(key, cast=None):
            vals = found.get(key)
            if not vals:
                return None
            v = vals[-1]
            try:
                return cast(v) if cast else v
            except (TypeError, ValueError):
                return None

        text = last("result") or ""
        if not isinstance(text, str):
            text = str(text)
        ms = last("duration_ms", float)
        return Run(
            ok=not bool(last("is_error")),
            error="the provider reported an error result" if last("is_error") else None,
            text=text,
            tools=tools,
            skills=skills,
            duration_s=(ms / 1000.0) if ms is not None else elapsed,
            tokens_in=sum(v for v in found.get("input_tokens", []) if isinstance(v, int)) or None,
            tokens_out=sum(v for v in found.get("output_tokens", []) if isinstance(v, int)) or None,
            cost_usd=last("total_cost_usd", float) or last("cost_usd", float),
            turns=last("num_turns", int),
            workdir=cwd,
        )


class FakeProvider(Provider):
    """A scripted agent, for testing the machinery rather than a skill.

    The reports, the confusion matrix and the regression diff are arithmetic over what
    an agent returned, and arithmetic deserves tests that do not cost money or need a
    model installed. This provider replays a script instead of thinking:

        SQS_FAKE_RUNS=runs.json sqs.py eval ./my-skill --all --provider fake

        {"default": {"text": "done", "tools": [["Read", "{}"]]},
         "rules": [{"contains": "receipt", "with_skill": true, "bare": true,
                    "run": {"text": "logged 12.40 on 2026-09-18", "cost_usd": 0.01}}]}

    A rule matches on a substring of the prompt and, optionally, on which arm of the
    comparison is running. First match wins; `default` covers the rest.

    It measures nothing about any skill, and every report it produces says `fake` in
    the provider line so a scripted number can never be mistaken for a measured one.
    """

    name = "fake"
    title = "scripted (testing only)"
    isolates_skills = True

    def __init__(self, script_path=None):
        self.path = script_path or os.environ.get("SQS_FAKE_RUNS")
        self.script = {}

    def available(self):
        if not self.path:
            return False, ("the fake provider replays a script - point SQS_FAKE_RUNS at a "
                           "JSON file. It exists to test this suite, not to measure a skill")
        if not os.path.isfile(self.path):
            return False, f"no script at {self.path}"
        try:
            with open(self.path, encoding="utf-8") as f:
                self.script = json.load(f)
        except (OSError, ValueError) as e:
            return False, f"{self.path}: {e}"
        return True, ""

    def run(self, prompt, skill=None, cwd=None, timeout=300, model=None, workdir=None,
            bare=True):
        if not self.script:
            self.available()
        spec = dict(self.script.get("default") or {})
        for rule in self.script.get("rules") or []:
            if rule.get("contains") and rule["contains"].lower() not in prompt.lower():
                continue
            if "with_skill" in rule and bool(rule["with_skill"]) != (skill is not None):
                continue
            # a trigger run and a task run both arrive with no skill attached; `bare`
            # is what tells them apart, so a script can answer them differently
            if "bare" in rule and bool(rule["bare"]) != bool(bare):
                continue
            spec.update(rule.get("run") or {})
            break
        if spec.get("error"):
            return Run(ok=False, error=spec["error"], duration_s=spec.get("duration_s"),
                       workdir=cwd)
        for rel in spec.get("creates") or []:
            full = os.path.join(cwd or ".", rel)
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write("written by the fake provider" + chr(10))
        skills = spec.get("skills")
        if skills is None and skill is not None:
            skills = [skill.name or skill.folder]
        return Run(ok=True, text=spec.get("text", ""),
                   tools=[tuple(t) for t in (spec.get("tools") or [])],
                   skills=skills or [],
                   duration_s=spec.get("duration_s"), tokens_in=spec.get("tokens_in"),
                   tokens_out=spec.get("tokens_out"), cost_usd=spec.get("cost_usd"),
                   turns=spec.get("turns"), workdir=cwd)


PROVIDERS = {p.name: p for p in (ClaudeCodeProvider, FakeProvider)}


def get(name):
    """(provider, reason it cannot run) - never raises, so a caller can report it."""
    cls = PROVIDERS.get(name)
    if not cls:
        return None, (f"no provider `{name}` - this build carries "
                      f"{', '.join(sorted(PROVIDERS))}")
    provider = cls()
    ok, why = provider.available()
    return provider, ("" if ok else why)
