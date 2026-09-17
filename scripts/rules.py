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
RULES = {
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
              "The spec requires them equal; some loaders index by folder and resolve by name, "
              "so a mismatch makes the skill unreachable without any error.",
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
    "SP012": ("warning", "Non-spec top-level directory",
              "The spec names `scripts/`, `references/`, `assets/`. A fourth directory is "
              "invisible to tools that walk the standard layout.",
              "Move the files under a standard directory, or allow the name in the config.", False),
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
              "`rm -rf`, `curl | sh`, `chmod 777`, a force push: the agent runs what the skill "
              "tells it to run.",
              "Narrow the command, or make the step ask the human first.", False),
    "SE003": ("error", "Instruction-override text",
              "`ignore previous instructions`, `you are now`, `disregard the system prompt`. In a "
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
}


def module_of(code):
    return MODULES.get(code[:2], "?")


def severity_of(code, default="warning"):
    row = RULES.get(code)
    return row[0] if row else default


def audit(emitted):
    """Codes an engine emitted that have no row here. Empty means the two agree."""
    return sorted(c for c in emitted if c not in RULES)
