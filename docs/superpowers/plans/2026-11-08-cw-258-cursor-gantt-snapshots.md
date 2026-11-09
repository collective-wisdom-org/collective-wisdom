# CW-258: Cursor gantt snapshots, plan

**Spec:** [spec](../specs/2026-11-08-cw-258-cursor-gantt-snapshots-design.md)

Test command: `python3 -I -m pytest -q agent-team/scripts`, `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`, and `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.

CW-253 merged (#262), so its `cursor-hook` merge is on `main` and merged into this branch.

## Tasks

1. `mods/agent-gantt/hooks/cursor.ts` and `cursor.test.ts`: `applyEvent`, `cursorSnapshot`, `hookOutput` (spec § 1). One table over event sequences; one over `hookOutput`.
2. `agent-team/scripts/cursor_gantt_hook.ts` (spec § 2): stdout answer first, root and safety checks as in `register.tsx`, lock, state in `gantt/cursor/`, atomic writes. Run by hand once with Cursor-shaped payloads from a scratch worktree and check the dashboard `/api` shows the row.
3. `install.sh` `mpython cursor-hook`: take a list of (event, command, marker) entries, gantt `stop` entry before the rotation one (spec § 3). Extend the table in `test_install_machine.py`. Add a case to `agent-team/scripts/dashboard/api.test.ts` that a Cursor snapshot on a ticket worktree reaches the ticket's `gantt`.
4. Docs (spec § 5): `docs/compatibility.md` (Local dashboard cell for Cursor, G9), `README.md`, one sentence in `docs/agents/project.md` § Security overlays.
