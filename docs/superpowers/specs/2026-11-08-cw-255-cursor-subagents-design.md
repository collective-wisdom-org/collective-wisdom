# CW-255: Check that Cursor loads the team subagents and fix what it rejects

**Status:** Draft
**Ticket:** [#255](https://github.com/collective-wisdom-org/collective-wisdom/issues/255)

## Goal

The five team subagents (`code-reviewer`, `compacter`, `documenter`, `implementer`, `security-reviewer`) load and do their job in a Cursor session, with the read-only ones unable to edit. The docs say what Cursor does, and say plainly what was and was not run.

## What Cursor does today (read on 2026-11-08)

From <https://cursor.com/docs/subagents> and this machine:

- Cursor loads user subagents from `~/.cursor/agents/`, `~/.claude/agents/` and `~/.codex/agents/`. On a name clash `.cursor/` wins over `.claude/`. So Cursor already picks up the five files `install.sh` links into `~/.claude/agents`.
- Cursor's frontmatter has five fields: `name`, `description`, `model` (`inherit` or a Cursor model ID such as `composer-2`), `readonly` and `is_background`. It has no `tools` field: "Subagents inherit all tools from the parent."
- Our files say `model: opus` or `model: sonnet`, which are not Cursor model IDs, and the docs do not say what Cursor does with an unknown one. They limit tools with `tools:`, which Cursor ignores, so in Cursor `code-reviewer`, `documenter` and `security-reviewer` can edit files although their role files say read only.
- This machine already has a hand-made `~/.cursor/agents/implementer.md` (Composer model, a different body). It wins over the team's `implementer` in Cursor.
- `cursor agent` (Cursor's headless agent, the runtime behind a Cursor session) is installed but not logged in, so nothing has been run yet.

So nothing is rejected outright that we know of, but two things are wrong in Cursor: the model names, and read-only reviewers that can write.

## Design

### Cursor copies of the five agent files

Add `agent-team/.cursor/agents/<name>.md`, one per Claude agent file, mirroring `agent-team/.claude/agents/`:

- `name`, `description` and the body are the same as the Claude file, word for word.
- `model: inherit`: the subagent runs on the parent session's model.
- `readonly: true` on the three whose Claude `tools` list has no `Edit`, `Write` or `*`: `code-reviewer`, `documenter`, `security-reviewer`. `compacter` and `implementer` get no `readonly` line.
- No `tools` line.

The Claude files do not change, so Claude Code keeps working exactly as now.

### install.sh

Link each file in `agent-team/.cursor/agents/` into `~/.cursor/agents/` with `mlink`, the same loop as the Claude agents, and add `.cursor/agents` to the `mprune` list. Because `.cursor` wins over `.claude` on a name clash, Cursor uses these copies and Claude Code never reads them. A file the person already has at that path (like the `implementer.md` on this machine) is kept and listed, as `mlink` does for skills. `~/.cursor/agents` is a new path `install.sh` writes, so the security overlay's path list in `docs/agents/project.md` gets it.

### Tests

- `test_agent_files.py`: one table-driven test over the agent names. Each Claude file has a Cursor twin and the reverse; the twin has the same `name`, `description` and body, `model: inherit`, no `tools`, and `readonly: true` exactly when the Claude `tools` list has no `Edit`, `Write` or `*`. This catches the two copies drifting apart.
- `test_install_machine.py`: the `world` fixture gets a `.cursor/agents/ag.md`; the fresh-install test checks its link, and the kept-and-pruned test gets one dangling `~/.cursor/agents` link of ours that is removed.

### Live check in Cursor

For each of the five, start a Cursor session in a scratch clone of this repo and ask it to use the subagent on a small task: review a two-line diff (`code-reviewer`, `security-reviewer`), check it against the docs (`documenter`), tighten a short added paragraph (`compacter`), make a one-line edit (`implementer`). Then ask a read-only one to write a file and check it refuses. Record each result in the PR's `## Proof`.

The builder runs these with `cursor agent -p` (headless) from its own shell, since a child thread may not start other threads. That needs Cursor logged in on this machine: the user runs `cursor agent login` once. If it is not logged in when the build runs, the builder does the file and install changes, lists the five runs under `Not proven`, and the docs say the files are Cursor-valid but not yet run.

### Docs

- `AGENTS.md` § Agent config and `agent-team/templates/AGENTS.md`: subagents load from `~/.claude/agents` (Claude Code) and `~/.cursor/agents` (Cursor, from the copies in `agent-team/.cursor/agents/`, which keep the same name, description and body); other hosts start a general subagent with the role file as its prompt.
- `docs/compatibility.md`: the install note (subagents also link into `~/.cursor/agents`), the Cursor Subagents cell (🟢 works if all five ran, 🟡 partial naming the ones that did not and why, or 🟡 partial "installed, not yet run" if Cursor was not logged in), and G4 (Cursor taken out, or its open part stated). The "Last checked" date moves to the build day.

## Leaves out

- Codex and Antigravity subagents (out of scope in the ticket).
- Cursor's own `review-security` (G11) and the `security-review` skill's Cursor branch.
- A per-agent Cursor model choice: every copy inherits the parent's model.
- Removing or rewriting the person's own `~/.cursor/agents/implementer.md`: `install.sh` keeps and lists it, as it does any file of the person's.
- `is_background`: all five run in the foreground, as the ship loop asks.

## Calls I made

- The live runs use headless `cursor agent -p` from the builder's shell, not a Cursor thread in T3 Code: the child may not start threads. Same Cursor agent runtime, but not the T3 Code thread the ticket names. They need the user to run `cursor agent login` once; without it the five runs are `Not proven` and the cells say "not yet run".
- Probing for this spec ran `cursor agent --help`, which auto-installed the Cursor agent CLI: `~/.local/share/cursor-agent/` and the links `~/.local/bin/agent` and `~/.local/bin/cursor-agent`. Nothing else outside the worktree was written.
- Separate Cursor copies linked into `~/.cursor/agents`, rather than one file for both: one file cannot carry `model: opus` for Claude Code and a Cursor model for Cursor, and Cursor's behaviour on an unknown model is undocumented.
- `model: inherit` for every Cursor copy, so the subagent uses whatever model the Cursor session runs, rather than a pinned Composer or Claude ID.
- `readonly: true` for the three reviewers, derived from their Claude `tools` list, so their "do not edit" holds in Cursor too. Cursor's `readonly` also blocks state-changing shell commands; the reviewers only read (`git diff`, `gh pr diff`), so that fits.
- The person's own `~/.cursor/agents/implementer.md` stays and wins in Cursor, and `install.sh` lists it. On this machine the team `implementer` will not run in Cursor until that file is moved.
- A test that the two copies match, so editing one without the other fails CI.

## Touches

None of these: no data, money, auth, user email or migrations. `install.sh` writes one new path under `$HOME` (`~/.cursor/agents`).
