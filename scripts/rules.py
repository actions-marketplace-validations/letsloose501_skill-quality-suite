#!/usr/bin/env python3
"""The rule registry: one row per finding the suite can emit.

A rule code is the join key of the whole suite. `sqs.py explain ST005` looks a code
up here, a config file switches a code off here, CI annotations group by it, and the
report prints it. That only works while this file is the single place a code is
defined - an engine that invents a code without a row here fails `sqs.py rules
--audit`, which is what keeps the two from drifting.

Severity here is the DEFAULT. The structure engine (check_skills.py) decides error vs
warning itself, because it knows the case; everything else takes the default, and a
config file overrides either.

Modules map one-to-one onto code prefixes, so a finding routes to its module without
a lookup:

    SP  spec        Agent Skills specification conformance
    ST  structure   links, orphans, budgets, layout
    QL  quality     whether the instructions read like instructions
    CP  compat      which runtime reads which frontmatter field
    SE  security    secrets, dangerous commands, injection, hidden characters
    PB  publish     what has to be true before the skill leaves your machine
    EV  evals       whether the skill fires on the wording a human actually uses

sqs-allow-file: SE002
Every rule row spells out the pattern it is about, so this file matches its own
security rules by construction.
"""

MODULES = {
    "SP": "spec",
    "ST": "structure",
    "QL": "quality",
    "CP": "compat",
    "SE": "security",
    "PB": "publish",
    "EV": "evals",
}

# code: (severity, title, why it matters, how to fix, fixable by `sqs.py fix`)
_ROWS = {
    # ---- SP: Agent Skills specification -------------------------------------
    "SP001": ("error", "No frontmatter",
              "Without a `---` block the file is plain markdown and never loads as a skill.",
              "Open the file with `---`, put `name` and `description` inside, close with `---`.", False),
    "SP002": ("error", "Required field `name` missing",
              "The loader keys the skill by `name`; without it there is nothing to invoke.",
              "Add `name: <folder-name>`.", True),
    "SP003": ("error", "Required field `description` missing",
              "The description is the skill's only context pointer. No description, no triggering.",
              "Add a description stating what the skill does and when to reach for it.", False),
    "SP004": ("error", "`name` does not match the folder",
              "The specification requires them equal. What actually happens is split, and the "
              "client-implementation guide states both halves: a lenient client warns and "
              "loads the skill anyway, while `skills-ref validate` and publication reject it. "
              "So it works on your machine and fails the moment the skill leaves it.",
              "Rename the folder or the field so the two agree.", True),
    "SP005": ("warning", "`name` longer than 64 characters",
              "Over the spec limit. Claude Code tolerates it, `skills-ref validate` and "
              "publication do not.", "Shorten the name.", False),
    "SP006": ("warning", "`name` off-spec",
              "The spec allows lowercase latin letters, digits and single inner hyphens only.",
              "Rewrite as `lower-case-with-hyphens`.", True),
    "SP007": ("error", "`description` empty",
              "An empty description is the same as none: the skill never triggers.",
              "Write the description.", False),
    "SP008": ("warning", "`description` over 1024 characters",
              "Over the spec limit. It works locally and is rejected on publication.",
              "Cut restated identity and synonym triggers; keep one trigger per branch.", False),
    "SP009": ("warning", "`compatibility` over 500 characters",
              "Over the spec limit.", "Shorten it.", False),
    "SP010": ("warning", "Unknown frontmatter key",
              "A typo in a key is not a syntax error: the field silently vanishes along with "
              "its meaning, and the skill keeps loading as if nothing happened.",
              "Fix the spelling, or drop the key.", False),
    "SP011": ("error", "Unclosed code fence",
              "Everything after the unclosed fence reads as code, so the instructions that "
              "follow it stop being instructions.", "Close the fence.", False),
    "SP012": ("info", "Directory outside the conventions",
              "The specification permits any directory beside SKILL.md and calls "
              "`scripts/`, `references/` and `assets/` recommendations, so this is not a "
              "violation. It is a portability note: tools that walk the conventional "
              "layout will not see the directory, and harnesses document different sets - "
              "Cline names `docs/` and `templates/`, Antigravity names `examples/` and "
              "`resources/`.",
              "Leave it if the skill links it from SKILL.md; `compat` says what each "
              "harness makes of it. Add the name to `allow_dirs` to stop being told.", False),
    "SP013": ("info", "Extraneous file at the skill root",
              "README.md, CHANGELOG.md, Makefile and friends are repository furniture. Inside a "
              "published skill they ship as payload nobody reads.",
              "Keep them outside the skill folder, or accept the cost knowingly.", False),
    "SP014": ("error", "No body",
              "Frontmatter present, instructions absent: the skill activates and says nothing.",
              "Write the instructions.", False),
    "SP015": ("info", "Multiline description",
              "A folded or literal block scalar (`>-`, `|`) is valid YAML and Claude Code reads "
              "it. It is flagged as non-portable by the vendor-neutral validators, which is as "
              "far as the evidence goes: whether a given other runtime reads it has to be tried, "
              "not assumed.",
              "Put the description on one line if the skill has to be portable; leave it if "
              "Claude Code is the only target.", False),
    "SP016": ("warning", "Oversized or binary asset",
              "Every byte in the skill folder travels with it. A large binary is paid for by "
              "everyone who installs the skill and read by nobody.",
              "Host it elsewhere and link, or shrink it.", False),
    "SP017": ("warning", "Reference nested too deep",
              "Progressive disclosure is one hop: SKILL.md names the file. Three levels down, "
              "nothing reaches the file but a reader who already knew it was there.",
              "Flatten to `references/<file>.md`, or link the intermediate level explicitly.", False),

    "SP018": ("error", "XML tag in `name` or `description`",
              "The Agent Skills validation rules forbid XML tags in either field. The "
              "description is injected into a system prompt, where a stray tag changes how "
              "the surrounding text is read.",
              "Remove the angle brackets; name the tag in prose instead.", False),
    "SP019": ("error", "Reserved word in `name`",
              "`anthropic` and `claude` are reserved in a skill name by the validation rules, "
              "and the refusal comes at upload time, after the skill is finished.",
              "Rename the skill after what it does.", False),

    # ---- ST: structure -------------------------------------------------------
    "ST001": ("error", "Link to a file that does not exist",
              "The agent does not crash on a broken pointer: it skips the step in silence, and "
              "the only symptom is that the work came out worse than usual.",
              "Restore the file or correct the link.", False),
    "ST002": ("error", "Broken sibling link",
              "Same silent skip, in the short `[text](neighbour.md)` form that a path-shaped "
              "check cannot see.", "Restore the file or correct the link.", False),
    "ST003": ("error", "Link to a skill that does not exist",
              "A rename elsewhere left this pointer aimed at nothing.",
              "Point at the new name, or drop the link.", False),
    "ST004": ("error", "Linked skill has no such file",
              "The skill is there, the file inside it is not.",
              "Correct the path, or restore the file in the other skill.", False),
    "ST005": ("warning", "Orphan file",
              "Nothing links to it. Either it was never wired up, or it is no longer needed. An "
              "orphan is a pruning candidate, not a defect.",
              "Link it from SKILL.md, or delete it.", False),
    "ST006": ("warning", "SKILL.md over budget",
              "SKILL.md is loaded whole on every activation, so its length is a permanent tax on "
              "the context window.",
              "Move what only some branches need into `references/`, and keep the routing - "
              "which reference to open when - in SKILL.md.", False),
    "ST007": ("warning", "Reference over budget",
              "A reference is opened whole too, just later. A 30 KB file cancels the point of "
              "two-stage loading.", "Split it by branch.", False),
    "ST008": ("warning", "Pointer to a section that is gone",
              "The file is in place, so an ordinary link check stays quiet while the agent opens "
              "the reference and does not find what it came for. Renaming a heading is enough.",
              "Restore the heading, or correct the pointer - copying the section name from the "
              "file verbatim, never from memory.", False),
    "ST009": ("warning", "Path naming no folder in this skill",
              "Almost always an example path from somebody else's repository rather than a route "
              "of your own.", "Leave it if it is an example; fix it if it was meant to be a route.", False),
    "ST010": ("warning", "Path with no skill name",
              "The file lives in a different skill, and the bare relative path resolves there "
              "only by accident.", "Spell out `~/.claude/skills/<skill>/<path>`.", False),
    "ST011": ("error", "Outbound path does not exist",
              "A skill that reads a note before working degrades silently when the note is "
              "renamed: the theory is gone and the work goes on anyway.",
              "Update the path. Cyrillic is compared NFC/NFD-insensitively, so a hit here is a "
              "real miss, not a normalisation artefact.", False),
    "ST012": ("warning", "Code as prose",
              "A long executable block sitting in the text is retyped by the model every run - "
              "probabilistically, and for tokens. It cannot be run, and it cannot be fixed once.",
              "Move it into `scripts/`; leave the call and how to read its output in the text.", False),
    "ST013": ("warning", "Body nearly empty",
              "Enough text to load, not enough to act on.", "Write the instructions.", False),
    "ST014": ("error", "Duplicate `name` across skills",
              "One shadows the other and which one wins is not knowable in advance.",
              "Rename one of them.", False),
    "ST015": ("error", "No SKILL.md",
              "The folder is in the skills tree and holds no skill.",
              "Add SKILL.md, or move the folder out.", False),
    "ST016": ("warning", "External link unreachable",
              "A dead URL in a reference sends the agent to fetch nothing.",
              "Update or remove the link. 403 is reported separately: it usually means the site "
              "blocks bots, not that the page is gone.", False),

    # ---- QL: instruction quality --------------------------------------------
    "QL001": ("warning", "Description too short to carry triggers",
              "Trigger conditions are the only thing the agent uses to decide whether to open "
              "the skill. Two words hold none.",
              "State what the skill is and list the distinct branches that should reach it.", False),
    "QL002": ("warning", "Description states what, never when",
              "A pointer does two jobs: name the material and list the branches that trigger "
              "reaching it. This one does the first only, so firing is left to chance.",
              "Add the trigger conditions: `Use when ...`, `Trigger on ...`.", False),
    "QL003": ("warning", "One branch written twice",
              "Two trigger phrases that name the same branch cost context on every turn and "
              "sharpen nothing. The rule prints the pair, so you can judge it.",
              "Collapse the pair into one trigger. Deliberately high-precision and therefore "
              "low-recall: it catches word-level repetition only, and the judgement-level pass "
              "over a description lives in `references/writing-rubric.md`.", False),
    "QL004": ("info", "Description and body barely overlap",
              "The skill fires on wording that its own instructions never mention, which usually "
              "means the description drifted from what the skill grew into.",
              "Re-read the body and rewrite the description from it.", False),
    "QL005": ("warning", "Steering by prohibition",
              "A ban drags the forbidden behaviour into context and makes it more available, not "
              "less. The negation is a weak modifier that the strongly-activated concept "
              "overruns, so the ban half-reads as an instruction to do the thing.",
              "State the target behaviour positively, so the banned one is never spoken. Keep a "
              "prohibition only as a hard guardrail you cannot phrase positively - and pair it "
              "with the positive target.", False),
    "QL006": ("info", "Unverifiable instruction",
              "`be thorough`, `write clearly`, `as needed`: the agent cannot tell done from "
              "not-done, and neither can you.",
              "Replace with a checkable bound, or with a `bad -> good` pair the reader can "
              "compare.", False),
    "QL007": ("warning", "TODO or placeholder left in the text",
              "The agent reads it as instruction, not as a note to self.",
              "Finish the sentence or cut it.", False),
    "QL008": ("info", "Disclaimer naming a neighbouring skill's topic",
              "A description is a shop window, not a fence. Naming a neighbour's topic makes "
              "this skill a candidate for it; negation does not reliably reverse that.",
              "Move the boundary into the body, which is read after activation and does not "
              "affect the choice. Keep it in the description only when the neighbour can fire "
              "on its own.", False),
    "QL009": ("info", "Description repeats the skill's own name",
              "Identity the body already carries, paid for on every turn.",
              "Cut the restatement and spend the room on a trigger.", False),

    "QL010": ("warning", "Description talks about itself",
              "The description is an instruction to the agent about when to act, not a "
              "paragraph about the skill. `Use when the user ...` outperforms `This skill "
              "does ...`, and first or second person (`I can help you ...`) is injected "
              "into a system prompt where the point of view does not fit.",
              "Rewrite in the imperative, third person: what it does, then the situations "
              "that should reach it.", False),
    "QL011": ("error", "Bundled script waits for input",
              "Agents run in non-interactive shells. A script that blocks on a prompt does "
              "not fail - it hangs until something kills it, and the skill looks broken for "
              "reasons nothing explains.",
              "Take every input from flags, environment variables or stdin, and fail with a "
              "message naming the missing one.", False),
    "QL012": ("info", "Unpinned one-off command",
              "`npx eslint` resolves to whatever is newest today. The skill's behaviour then "
              "changes without the skill changing, which is the hardest kind of drift to "
              "trace.", "Pin the version: `npx eslint@9.0.0`.", False),
    "QL013": ("info", "Description rules out a topic",
              "A description is matched on topic, and a negation does not reverse a match. "
              "Spelling out the work the skill will not take puts that work's vocabulary in "
              "the one place the router reads, so the clause meant as a fence reads as one "
              "more reason to fire. `QL008` is this same trap when a neighbouring skill is "
              "named; this is the version with only a topic in it, which is the common one.",
              "Move the boundary into the body, which is read after the skill has already "
              "been chosen. Keep it in the description only when a model-invoked neighbour "
              "would otherwise take the work, and then name that neighbour rather than its "
              "topic.", False),

    # ---- CP: agent compatibility --------------------------------------------
    "CP001": ("warning", "Field value the runtime cannot read",
              "The field is read; the value is not one of the ones it accepts, so the runtime "
              "falls back to its default and says nothing.",
              "Use one of the accepted values.", False),
    "CP002": ("warning", "Field rejected by the strict reference validator",
              "`skills-ref` refuses unknown top-level fields. Real clients warn and load anyway, "
              "so the breakage only shows on publication.",
              "Nest it under `metadata:`, which is the spec's escape hatch.", False),

    "CP006": ("warning", "Feature that does not travel",
              "The feature is real on one harness and inert or absent on another target. "
              "Nothing fails loudly: the instruction simply has no effect there.",
              "Keep it if that harness is the only target; otherwise state the behaviour in "
              "the instructions, where every harness reads it.", False),
    "CP007": ("info", "Undocumented on a target harness",
              "The harness's official documentation does not say what it does with this. "
              "That is a gap in the documentation, not a defect in the skill, and it is "
              "reported as unknown rather than as an incompatibility.",
              "Try it once on that harness and record what happened, or avoid relying on it.",
              False),
    "CP008": ("error", "Target harness refuses the skill",
              "A rule the harness publishes is broken - a required field missing, a "
              "documented ceiling exceeded, a name that has to match its folder and does not.",
              "Fix the field, or drop the harness from the targets.", False),
    "CP009": ("warning", "No adapter for the named harness",
              "The target is not in the registry, so nothing about it was checked. Silence "
              "here would read as a pass.",
              "Use a name from `sqs.py harnesses`, or add an adapter under "
              "`scripts/harnesses/`.", False),

    # ---- SE: security --------------------------------------------------------
    "SE001": ("error", "Secret in the skill text",
              "An API key, token or private key committed into a skill travels with every copy "
              "of it.", "Revoke the credential, then remove it and read it from the environment.", False),
    "SE002": ("warning", "Destructive command in an instruction",
              "A recursive delete, a download piped into a shell, world-writable permissions, a "
              "force push: the agent runs what the skill "
              "tells it to run.",
              "Narrow the command, or make the step ask the human first.", False),
    "SE003": ("error", "Instruction-override text",
              "An instruction to disregard what came before, a claimed change of role, an order to "
              "keep something from the user. In a "
              "skill you wrote it is a mistake; in a skill you installed it is the payload.",
              "Remove it. If the skill came from elsewhere, read the whole file before using it.", False),
    "SE004": ("error", "Hidden or bidirectional Unicode",
              "Zero-width and bidi control characters make the rendered text differ from the text "
              "the model reads - the Trojan Source trick.",
              "Strip the characters. `sqs.py fix` removes them.", True),
    "SE005": ("warning", "Outbound network call carrying local data",
              "A step that posts file contents to a host is exfiltration whether or not it was "
              "meant as one.", "Confirm the host is yours and that the human agreed to the send.", False),
    "SE006": ("info", "Absolute path naming a user account",
              "`C:\\Users\\<name>`, `/home/<name>`: the skill only works on one machine, and it "
              "publishes whose machine that is.",
              "Use `~`, or an environment variable.", False),

    # ---- PB: publishing ------------------------------------------------------
    "PB001": ("warning", "No license",
              "Without one, nobody may legally reuse the skill.",
              "Add a `license:` field, or a LICENSE file beside the skill.", False),
    "PB002": ("info", "No README",
              "The SKILL.md talks to the agent. A human deciding whether to install needs a page "
              "that talks to them.", "Add README.md next to the skill folder.", False),
    "PB003": ("error", "Personal path in a skill about to be published",
              "It leaks your directory layout and breaks on every other machine.",
              "Replace with `~`, or with a path the reader supplies.", False),
    "PB004": ("warning", "Text not in the declared publication language",
              "A published skill documented in another language than its repository is read by "
              "nobody it was published for.",
              "Translate, or drop `--lang`.", False),
    "PB005": ("warning", "Version drift",
              "The version in the plugin or marketplace manifest disagrees with the skill's own.",
              "Make them agree; the manifest is usually the one that went stale.", False),
    "PB006": ("info", "Private material in a skill about to be published",
              "A path into a personal vault, a private repository name, an email address.",
              "Strip it, or keep the skill unpublished.", False),
    "PB007": ("info", "Package wires hooks beside this skill",
              "`hooks/hooks.json` runs a command on its event whether or not the model ever "
              "routes to this skill. A clean verdict on SKILL.md next to an unread hooks/ "
              "directory is the most convincing wrong answer the suite can give.",
              "Not a defect - read hooks/hooks.json before trusting the package, the way you "
              "would read a script this skill calls.", False),
    "PB008": ("warning", "Skill points at a package sibling",
              "A command, agent or script one directory above `skills/<name>/`, or a path "
              "through `${CLAUDE_PLUGIN_ROOT}`. The structure rules only resolve pointers "
              "inside the skill, so this one is invisible to them and breaks in silence the "
              "moment the skill is copied out of the plugin.",
              "Declare the dependency in prose, or bring what it needs inside the skill.", False),
    "PB009": ("info", "Package installed from an unreviewed checkout",
              "The marketplace entry's `source` names a remote repository, archive or command "
              "- the files under review may be a checkout nobody has looked at.",
              "Not a defect - a fact about where the package came from.", False),

    # ---- EV: evals -----------------------------------------------------------
    "EV001": ("error", "Routing invariant broken",
              "Two skills claim the same wording and only one can win, or a skill claims wording "
              "its own instructions do not serve.",
              "Run `run_evals.py` for the detail; the fix is in the descriptions, not here.", False),
    "EV002": ("info", "Skill has no routing cases",
              "Nothing verifies that this skill fires on the wording a human would actually use, "
              "so every description edit moves it blind.",
              "Add cases to `evals/cases/`.", False),
    "EV003": ("error", "Live routing run below threshold",
              "The judge sent wording to the wrong skill.",
              "Read the failing cases: usually one description is claiming a neighbour's branch.", False),
    "EV004": ("warning", "Malformed evals",
              "An `evals/` directory that does not parse is worse than none: it looks like "
              "the skill is tested.",
              "`evals/evals.json` is `{skill_name, evals: [{id, prompt, expected_output, "
              "assertions}]}`; `evals/eval_queries.json` is `[{query, should_trigger}]`.",
              False),
    "EV005": ("info", "Thin trigger set",
              "A trigger set with few cases on one side measures almost nothing. The "
              "negatives matter most, and the useful ones are near-misses: queries sharing "
              "keywords with the skill that need something else.",
              "Aim for about twenty queries, eight to ten on each side.", False),
    "EV006": ("info", "Routing runner in the tree was not executed",
              "The routing report comes from a script that lives in the tree being "
              "checked. Running it would mean executing code out of the directory the "
              "suite was handed to read, which is the thing reading it was meant to "
              "avoid.",
              "If the tree is yours, pass `--trust-target`. If it is not, a missing "
              "routing report is the correct outcome.", False),
}

# ---- rule metadata ---------------------------------------------------------
#
# Two gradings per rule, and they answer different questions:
#
#   confidence      does the check reliably find the thing it names? A filesystem
#                   fact or a parse is `high`; a regex over prose is `medium`; a
#                   similarity heuristic is `low`.
#   false_positive  when the thing IS there, how often is it nonetheless intended?
#                   `README.md` inside a skill folder is a finding and also exactly
#                   what a repository-shaped skill does, so SP013 is `high`.
#
# Both are about the mechanism, not about how much the finding matters - severity
# already carries that. They exist so a report can be filtered by how much a machine
# should be trusted with the judgement: `--min-confidence high` is a gate you can
# leave on in CI, and a `high` false-positive rule is one to read before believing.
#
# A code with no row here fails `sqs.py rules --audit`. `unrated` is the honest value
# for a rule whose engine has not been written yet, and it is not the same as `high`.
GRADES = {
    # spec: frontmatter parsing and filesystem layout, so the detection is a fact
    "SP001": ("high", "low"),    "SP002": ("high", "low"),    "SP003": ("high", "low"),
    "SP004": ("high", "low"),    "SP005": ("high", "low"),    "SP006": ("high", "low"),
    "SP007": ("high", "low"),    "SP008": ("high", "low"),    "SP009": ("high", "low"),
    "SP010": ("high", "medium"),  # a key this suite does not know may be a new one
    "SP011": ("high", "low"),
    "SP012": ("high", "medium"),  # `allow_dirs` exists because the spec permits any
    "SP013": ("high", "high"),    # a repository-shaped skill ships its own README
    "SP014": ("high", "low"),    "SP015": ("high", "low"),
    "SP016": ("high", "medium"), "SP017": ("high", "medium"),
    "SP018": ("high", "low"),    "SP019": ("high", "low"),

    # structure: links resolved against the filesystem, except the text heuristics
    "ST001": ("high", "low"),    "ST002": ("high", "low"),    "ST003": ("high", "low"),
    "ST004": ("high", "low"),
    "ST005": ("high", "medium"),  # an orphan a bundled script opens is not an orphan
    "ST006": ("high", "low"),    "ST007": ("high", "low"),
    "ST008": ("medium", "medium"),
    "ST009": ("medium", "medium"), "ST010": ("medium", "medium"),
    "ST011": ("high", "low"),
    "ST012": ("medium", "high"),  # prose that looks like code is a judgement call
    "ST013": ("high", "low"),    "ST014": ("high", "low"),    "ST015": ("high", "low"),
    "ST016": ("unrated", "unrated"),  # documented gap: no engine emits it yet

    # quality: mostly regex over prose, and two similarity heuristics
    "QL001": ("high", "low"),
    "QL002": ("medium", "medium"),
    "QL003": ("low", "high"),     # stem overlap between two trigger phrases
    "QL004": ("low", "high"),     # stem overlap between description and body
    "QL005": ("medium", "high"),  # a hard guardrail is a legitimate prohibition
    "QL006": ("medium", "medium"),
    "QL007": ("high", "low"),
    "QL008": ("medium", "medium"),
    "QL009": ("high", "medium"),
    "QL010": ("medium", "low"),
    "QL011": ("medium", "medium"),
    "QL012": ("high", "low"),
    "QL013": ("medium", "medium"),

    # compat: every verdict comes from an adapter's declared support table
    "CP001": ("high", "low"),    "CP002": ("high", "low"),
    "CP006": ("medium", "medium"),
    "CP007": ("high", "low"),     # "undocumented" is a statement about the docs
    "CP008": ("high", "low"),    "CP009": ("high", "low"),

    # security: shaped secrets and codepoints are facts, command patterns are not
    "SE001": ("high", "medium"), "SE002": ("medium", "medium"),
    "SE003": ("medium", "medium"), "SE004": ("high", "low"),
    "SE005": ("medium", "medium"), "SE006": ("high", "medium"),

    # publish: half of these are correct-and-intended for a skill that stays home
    "PB001": ("high", "low"),    "PB002": ("high", "low"),    "PB003": ("high", "low"),
    "PB004": ("high", "medium"), "PB005": ("high", "low"),    "PB006": ("medium", "medium"),
    "PB007": ("high", "low"),    # hooks.json is read, not inferred
    "PB008": ("medium", "medium"),  # a sibling path can be prose about the pattern, not a use of it
    "PB009": ("high", "low"),    # the source shape is read straight off the manifest

    # evals: file parsing and a delegated runner
    "EV001": ("high", "low"),    "EV002": ("high", "low"),    "EV003": ("high", "low"),
    "EV004": ("high", "low"),    "EV005": ("high", "low"),
    "EV006": ("high", "low"),
}

CONFIDENCE_ORDER = ("unrated", "low", "medium", "high")


class Rule:
    """One row of the registry, with its metadata attached.

    Indexable like the tuple it grew out of, so the older unpacking still reads the
    same: `severity, title, why, how, fixable = RULES[code]`.
    """

    __slots__ = ("code", "severity", "title", "why", "how", "fixable",
                 "confidence", "false_positive_risk")

    def __init__(self, code, row, grade):
        self.code = code
        self.severity, self.title, self.why, self.how, self.fixable = row
        self.confidence, self.false_positive_risk = grade or ("unrated", "unrated")

    @property
    def module(self):
        return module_of(self.code)

    @property
    def category(self):
        return module_of(self.code)

    @property
    def autofix(self):
        return self.fixable

    def __getitem__(self, i):
        return (self.severity, self.title, self.why, self.how, self.fixable)[i]

    def __iter__(self):
        return iter((self.severity, self.title, self.why, self.how, self.fixable))

    def as_dict(self):
        return {"id": self.code, "severity": self.severity, "category": self.category,
                "title": self.title, "confidence": self.confidence, "autofix": self.fixable,
                "false_positive_risk": self.false_positive_risk}


RULES = {code: Rule(code, row, GRADES.get(code)) for code, row in _ROWS.items()}


def module_of(code):
    return MODULES.get(code[:2], "?")


def severity_of(code, default="warning"):
    row = RULES.get(code)
    return row.severity if row else default


def confidence_of(code, default="unrated"):
    row = RULES.get(code)
    return row.confidence if row else default


def at_least(confidence, floor):
    """Whether `confidence` clears the `floor` on the confidence ladder."""
    if floor not in CONFIDENCE_ORDER:
        return True
    return CONFIDENCE_ORDER.index(confidence) >= CONFIDENCE_ORDER.index(floor)


def audit(emitted):
    """Codes an engine emitted that have no row here. Empty means the two agree."""
    return sorted(c for c in emitted if c not in RULES)


def ungraded():
    """Codes with no metadata row. A rule nobody has graded is a rule nobody has read."""
    return sorted(c for c in _ROWS if c not in GRADES)
