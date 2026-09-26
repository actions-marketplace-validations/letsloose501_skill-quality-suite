# From your history to a proposal

Which skill to write next, and which existing one keeps missing, read off what the agent
actually did in the user's Claude Code sessions. Open this before running `sqs.py
discover`, or when `improve` reports scripts that ran while the skill never loaded.

`discover` and `improve` read the agent's actions out of the user's Claude Code
transcripts - the scripts it ran, the files it changed, the skills it loaded - because
the wording of a request alone was measured as noise. They print evidence and decide
nothing. The deciding is yours, in this conversation, and it costs nothing extra:

1. Run `sqs.py discover`. Section 1 names the skills whose own scripts ran in sessions
   that never loaded them; section 2, the documents and scripts the user returned to in
   several sessions with no skill loaded.
2. Read the prompts under each row. Group the rows that are one task; drop a row whose
   prompts are conversation, or a project being built rather than a task being repeated.
3. Propose, one line each, and wait for a yes before writing anything:
   - a skill in section 1 - `sqs.py improve <skill>`, then the description change that
     would have caught those prompts. Check first that no `CLAUDE.md` or hook sends the
     agent to the script directly: then the routing is working, just not through the skill;
   - a task in section 2 - a new skill: its name, the two or three words it would be
     asked with (`sqs.py new <name> --seed <word>` shows where those requests go today),
     and the existing skill it would sit beside. If one skill already takes most of them,
     propose a branch in that skill instead of a neighbour.
4. On a yes, build it through [creating-a-skill.md](references/creating-a-skill.md): from
   one real run of the work, not from the rows.

Bad: "Created skill `budget` from your history." Good: "`plans/budget.md` was edited in nine
sessions with no skill loaded, each time to move a deadline or a limit. A branch in your
planning skill, or a skill of its own? Say which, and I will write it from the next such
edit." The first acted on a list; the second names the evidence, the choice and who makes it.

## What the two readings count, and what they cannot see

- **Scripts run while the skill never loaded** (`discover` section 1, `improve` section 2):
  a script inside `.claude/skills/<skill>/` run from the shell, in a session that had not
  loaded that skill up to that turn and never edited it. A session that edits a skill is
  building it, and running its scripts there is testing them. A typed `/command` counts as
  a load.
- **Work repeated with no skill** (`discover` section 2): a script run, or a document
  changed, in two or more sessions none of which had loaded any skill up to that turn.
  Left out on evidence from a real history: a script that was itself edited anywhere (the
  project under development, not a tool in use), source-code files, the harness's own
  files (`MEMORY.md`, `CLAUDE.md`, anything under `.claude/`), scratch and temp files,
  and a script name that only appears inside text - a heredoc, a commit message.
- **Not visible**: intent. Two rows can be one task, one row can be two, and a document
  edited often may be the output of a skill that simply was not asked for. The prompts are
  printed so that judgement is made by whoever reads them, which is the step above.
- Everything is read locally from `~/.claude/projects/` (`--history-dir` for another <!-- sqs-allow: PB006 -->
  place); nothing leaves the machine, and nothing is written.
