# WISE-456 plan: keep a quiet ticket helper in Writing tickets

**Spec:** [design](../specs/2026-11-15-wise-456-quiet-helper-visible-design.md)

## Task 1: helper window in `api.ts`

- Add `const HELPER_RUNNING_MS = 30 * 60_000` beside `RUNNING_MS` in `agent-team/scripts/dashboard/api.ts`.
- Next to `isRunning`, add `helperRunning = (i: TeamItem) => i.open && (i.cursor === true || now - i.session.updatedAt <= HELPER_RUNNING_MS)` and use it, not `isRunning`, in the `writing` filter. Leave the chief and project manager uses of `isRunning` alone.

## Task 2: test

In the `where a root checkout TICKET HELPER snapshot lands` table in `agent-team/scripts/dashboard/api.test.ts`:

- Add a case: an open helper last written 5 minutes ago (`NOW - 300_000`) is a placeholder in Writing tickets.
- In `finished, no ticket: nowhere`, change the quiet helper's age from `NOW - 61_000` to `NOW - 31 * 60_000`.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
