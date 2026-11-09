# CW-252: Install the agent team instruction block for Cursor without a manual paste

**Status:** Shipped
**Shipped:** in PR #261, as specified
**Ticket:** [#252](https://github.com/collective-wisdom-org/collective-wisdom/issues/252)

## Goal

A fresh `./install.sh` puts the agent team instruction block where Cursor reads it, with no paste step. Today `machine_install` writes the block into `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` and only prints a TODO telling you to paste it into Cursor Settings, Rules.

## What we know about Cursor

- Cursor's user rules in Settings are account settings, not a file, so `install.sh` cannot write them.
- Cursor also loads rule files from `~/.cursor/rules/*.mdc`. A file with `alwaysApply: true` in its front matter is added to every agent's context.
- This machine already relies on that: `~/.cursor/rules/` holds `anti-ai-slop.mdc`, `planner-delegates.mdc` and `run-commands-yourself.mdc`, each with `alwaysApply: true`, and the user's `~/.claude/CLAUDE.md` imports the same three files.
- Not yet shown: that a Cursor agent in a T3 Code thread sees those rules. The Cursor CLI is not installed on this machine, and a ship loop child cannot start a Cursor thread, so the build cannot run that check itself (see Proof below).

## Design

### `install.sh`

Add a `rule` mode to `mpython`. It writes the whole file `~/.cursor/rules/collective-wisdom.mdc`:

```
---
description: collective-wisdom agent team. Where the team runs and where it does not.
alwaysApply: true
---

<contents of agent-team/templates/machine-instruction.md>
```

- The file belongs to the installer: its name is ours, so there are no marker comments and the whole file is compared and rewritten. Status words match the block mode: `created` (no file), `updated` (file differs), `present` (same bytes, no write).
- It writes through the same `write()` helper: a temp file and rename, the target's mode kept, and a file kept as a link (dotfiles) is written at the link's target.
- A folder at that path, or a file that is not UTF-8 text, prints `invalid` and adds a TODO: `Fix ~/.cursor/rules/collective-wisdom.mdc by hand: ...`. The rest of the install still runs.
- `--dry-run` writes nothing and reports what it would do, as the other modes do.
- `machine_install` calls it after the `.claude/CLAUDE.md` and `.codex/AGENTS.md` loop and counts a change the same way. The paste TODO is removed.

The template stays the one source: `machine-instruction.md` is not changed or copied.

### Docs

- `docs/agents/project.md` § Security overlays: add `~/.cursor/rules/collective-wisdom.mdc` to the paths `install.sh` writes.
- `README.md`: the install paragraph lists `~/.cursor/rules/collective-wisdom.mdc` beside `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`; the TODO list drops the Cursor paste line and adds the unreadable-file case for the new path; the dotfiles-link sentence names it too.
- `docs/compatibility.md`: the Cursor Install cell, the install note and G1 change to say the block is written to `~/.cursor/rules/collective-wisdom.mdc`. How far they go depends on the Cursor check (Proof below): with a quoted rule from a Cursor thread in T3 Code, Install becomes `🟢 works` and G1 is retired; without it, Install stays `🟡 partial` and G1 says the file is written but no Cursor thread in T3 Code has been seen reading it.

### Tests

`agent-team/scripts/test_install_machine.py`, one table-driven test for the rule file: fresh install creates it with the front matter and the template text; a rerun reports no change; a stale file is replaced; a folder at the path gives the `Fix ~/.cursor/rules/collective-wisdom.mdc by hand` TODO while the other files still install. The fresh-install test also checks the paste TODO is gone.

## Proof

The acceptance asks for an agent in a Cursor thread quoting a rule from the block. The build cannot get that by itself. The PR's `## Proof` section asks the approver (or the Chief of Staff, which can start a Cursor thread) to open a Cursor thread in T3 Code in a repo without `docs/agents/project.md` after `./install.sh`, and ask it what the collective-wisdom rule says about running the team there. Until someone posts that quote on the PR, it is listed under `Not proven`, and `docs/compatibility.md` keeps Install at `🟡 partial`.

## Leaves out

- Antigravity and Codex install (out of scope in the ticket).
- Cursor cloud agents, which do not read `~/.cursor/rules/`.
- Removing an existing hand-pasted copy from Cursor Settings, Rules. Settings are not a file; the user deletes it there if they want one copy.
- Any uninstall path (`install.sh` has none for the other files either).

## Calls I made

- **Build the file now, check Cursor after.** The ticket says to check a real Cursor session first and build only if it works. I could not run Cursor from this child, and the user's own setup already depends on `~/.cursor/rules/` `alwaysApply` files, so I build the install and leave the Cursor-thread check as a `Not proven` item. If the check fails, the fix is a small follow-up that puts the paste TODO back.
- **Whole file, not marker comments.** `collective-wisdom.mdc` is ours by name, so the installer overwrites any edits made inside it. The other two files use markers because they hold the user's own text.
- **File name** `collective-wisdom.mdc`, and the front matter `description` text above.
- **Compatibility cell** stays `🟡 partial` until a Cursor thread quote is posted, rather than marking it `🟢 works` on the strength of the file being written.
- **No change to `machine-instruction.md`.** Its text is the same for all three hosts.
