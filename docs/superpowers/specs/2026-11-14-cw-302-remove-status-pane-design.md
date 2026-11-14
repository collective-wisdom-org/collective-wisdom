# CW-302: Remove the status-pane mod

**Status:** Shipped
**Shipped:** in PR #PRN, as specified
**Ticket:** [#302](https://github.com/collective-wisdom-org/collective-wisdom/issues/302)

## Goal

The `status-pane` mod is gone from the repo and the marketplace. The dashboard keeps grouping tickets exactly as it does today, from a `groups.ts` that now lives with the dashboard.

## Today

Facts from `main` at `0a6c545`.

- The mod sits in `agent-team/.claude/mods/status-pane/`: `.claude-plugin/plugin.json`, `hooks/register.tsx`, `hooks/hooks.json`, `hooks/groups.ts`, `hooks/groups.test.ts`, `types/index.d.ts`, `tsconfig.json`. It is the only folder under `agent-team/.claude/mods/`.
- `agent-team/scripts/dashboard/api.ts:1` imports `groupTickets` from `../../.claude/mods/status-pane/hooks/groups.ts`.
- `groups.ts` imports its `Row` and `Group` types from the mod's `types/index.d.ts` (`StatusPaneRow`, `StatusPaneGroup`).
- `groups.test.ts` uses `claude-code/testing`, so CI's `node --test agent-team/scripts/dashboard/*.test.ts ...` does not run it today.
- `server.test.ts:333` checks that `codeFiles` follows the import to `groups.ts` (by file name only).
- Mentions of the mod outside `docs/superpowers/`:
  - `.claude-plugin/marketplace.json`: the `status-pane` plugin entry.
  - `README.md:17`, `:23`, `:182`, `:184`: the `agent-team/.claude/mods/` line, the marketplace line, the install paragraph, the update line.
  - `AGENTS.md:12`: "The marketplace also lists `status-pane` ..." (the ticket does not list this one).
  - `agent-team/docs/agents/status-pane.md` and its row at `agent-team/docs/agents/README.md:15`.
  - `docs/compatibility.md:40` (row), `:57` ("The two mods are the only open cells"), `:165` (G10).
  - `agent-team/scripts/test_approval_policy.py:239`: the fixture path `agent-team/.claude/mods/status-pane/hooks/x.ts`.
  - `mods/agent-gantt/hooks/register.tsx:96`: a doc comment, "The root checkout the way status-pane finds it" (the ticket does not list this one).
- `install.sh` never installs or copies the mod, so it needs no change.

## Design

1. **Move the grouping code.** `git mv` `groups.ts` and `groups.test.ts` to `agent-team/scripts/dashboard/`.
   - `groups.ts` defines its own `Row` (`id`, `title`, `risk`, `next`) and `Group` (`name`, `count`, `rows`) types in place of the mod's types import, and exports them. The logic does not change.
   - `groups.test.ts` moves to `node:test` and `node:assert/strict`, like the other dashboard tests, imports `./groups.ts`, and keeps the same cases and expectations. CI's existing glob now runs it.
   - `api.ts:1` imports `./groups.ts`.
2. **Delete the mod**: the rest of `agent-team/.claude/mods/status-pane/`, which leaves `agent-team/.claude/mods/` empty and so gone from git.
3. **Delete the role doc** `agent-team/docs/agents/status-pane.md` and its row in `agent-team/docs/agents/README.md`.
4. **Marketplace**: drop the `status-pane` entry from `.claude-plugin/marketplace.json`; `agent-gantt` stays the only plugin.
5. **README.md**: drop the `agent-team/.claude/mods/` bullet and the marketplace sentence about `status-pane`, the install paragraph at `:182`, and make the update line name `agent-gantt` and `mods/agent-gantt/` only.
6. **AGENTS.md**: drop the sentence about `status-pane` in the Product section.
7. **docs/compatibility.md**, kept to the lines below so CW-298 and CW-300 rebase cleanly:
   - Remove the `status-pane` row.
   - G10 says only `agent-gantt`: "`agent-gantt` is a Claude Code plugin, so Codex, Cursor and Antigravity threads do not run it, and whether T3 Code shows its pane for Claude Code is unchecked."
   - Line 57 becomes "The `agent-gantt` mod is the only open cell." (it counts the two mods, so it would be wrong after the row goes).
8. **Fixture**: `test_approval_policy.py:239` uses `agent-team/.claude/mods/m/hooks/x.ts`, so `.claude/mods/` stays covered by the hands path test. `approval_policy.py` and `remove_app_copies.py` keep `.claude/mods/`: an app may still have its own mods or an old copy to remove.
9. **agent-gantt comment**: `register.tsx:96` reads "The root checkout, found only in the plain `<root>/.git` layout; else the session's own folder." A comment change only, so no plugin version bump.
10. **Release note** in the PR body: the `status-pane` mod is removed; a machine that installed it runs `claude plugin uninstall status-pane`; the Chief of Staff status is in the dashboard and the `status` answer.

## Leaves out

- Rewriting old specs, plans and as-built docs that mention the pane.
- A replacement status view inside the chat. After this, status is in the dashboard and the Chief of Staff `status` answer only.
- Uninstalling the plugin from machines: `install.sh` never installed it, so it does not remove it either. The release note tells the user how.
- `.claude/mods/` in `approval_policy.py`, `approvals.md` and `remove_app_copies.py`.

## Calls I made

- `docs/compatibility.md:57` changes too, beyond the row and G10 the task named, because "The two mods" is wrong once one is gone. One line; it may need a small rebase against CW-298 or CW-300.
- `AGENTS.md:12` and the `register.tsx:96` comment change though the ticket does not list them, because the acceptance grep must come back empty.
- The moved test switches from `claude-code/testing` to `node:test`, so CI runs it for the first time. Same cases.
- `groups.ts` defines its own types instead of keeping a separate types file.
- No plugin version bump for `agent-gantt`: the only change there is a comment.
- `.claude/mods/` stays on the hands path and in the app copy removal, since apps can still hold mods.
- No uninstall step in `install.sh`; the release note gives the command.

## Acceptance

- `/usr/bin/grep -rn status-pane --exclude-dir=.git .` finds nothing outside `docs/superpowers/` (this spec and the plan are under it).
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes, including the moved `groups.test.ts`.
- `python3 -I -m pytest -q agent-team/scripts` passes.
- The dashboard groups tickets as before: `groups.ts` logic is unchanged and its test keeps the same expectations.

## Risk

Touches the hands path (`mods/`, `.claude/mods/`, `.claude-plugin/`, `AGENTS.md`, `test_approval_policy.py`), so it waits for the user under any tolerance. No data, money, auth, user email or migrations.
