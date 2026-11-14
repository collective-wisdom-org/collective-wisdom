# CW-302: Remove the status-pane mod: plan

Spec: `docs/superpowers/specs/2026-11-14-cw-302-remove-status-pane-design.md`

1. `git mv` `groups.ts` and `groups.test.ts` from `agent-team/.claude/mods/status-pane/hooks/` to `agent-team/scripts/dashboard/`. In `groups.ts`, replace the `../types` import with exported `Row` and `Group` types (`Row`: id, title, risk, next; `Group`: name, count, rows). Rewrite the test on `node:test` and `node:assert/strict` (`assert.deepEqual`), same cases. Point `api.ts:1` at `./groups.ts`.
2. `git rm -r agent-team/.claude/mods/status-pane` and `agent-team/docs/agents/status-pane.md`; drop its row in `agent-team/docs/agents/README.md`.
3. Drop the `status-pane` entry in `.claude-plugin/marketplace.json`.
4. Edit `README.md` (lines 17, 23, 182, 184), `AGENTS.md:12`, `docs/compatibility.md` (the row, G10, the "two mods" sentence), the `register.tsx:96` comment, and the `test_approval_policy.py:239` fixture path (`agent-team/.claude/mods/m/hooks/x.ts`).
5. Verify: the Acceptance commands in the spec, plus `/usr/bin/grep -rn status-pane --exclude-dir=.git --exclude-dir=superpowers .` finds nothing.

Tests: only the moved `groups.test.ts`; no new ones.
