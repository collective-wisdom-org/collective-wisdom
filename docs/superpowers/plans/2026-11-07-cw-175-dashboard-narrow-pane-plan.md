# CW-175 Dashboard narrow pane and row titles Implementation Plan

**Goal:** Dashboard fits a 300 to 400px pane, and every Status row has a title.

**Spec:** `docs/superpowers/specs/2026-11-07-cw-175-dashboard-narrow-pane-design.md`

**Tests:** per `AGENTS.md` § Testing: one table-driven test per rule, no CSS tests. Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: Title rule in state (`cos_state.py`, docs)

- [ ] `op_start`: `title` required; after `clean_title`, an empty result raises `Reject("title must be a non-empty string")`. Update `need(...)` so `title` is required, and the module docstring line 20.
- [ ] `test_cos.py`: give `START` (and any other `start` op in tests) a title; add rows to `test_ticket_title` for a missing title and `"  "`, both exit 1.
- [ ] `startup.md` § State rebuild: the `start` op passes the title from the `list-tickets` read. `SKILL.md` § Adopt step 3: `get-ticket` for the title (reuse the sweep's read on Linear or Jira), pass it in `start`; on a failed read write nothing. `state-keys.md` `title`: `start` requires it.
- [ ] Run pytest. Commit `feat: require a title on every state start (CW-175)`.

## Task 2: Title fallback (`api.ts`, `titles.ts`, `server.ts`)

- [ ] `api.ts`: `buildApi` input gains `titles: Record<string, string>`; row title is state title if non-empty, else `titles[id]`, else `''`.
- [ ] `titles.ts` as the spec § 2: cache, serial background reads via an injectable runner (default `execFile` of `join(import.meta.dirname,'..','gh.sh')` with args `issue view N --repo <owner>/<repo> --json title --jq .title`, cwd root, 10 s timeout), prefix guard `^<PREFIX>-\d+$`, clean like `clean_title`, failures retried after 5 minutes. Prefix comes from `project.md` Identity row (`Issue identifier prefix`); repo slug from the existing Repo URL. GitHub-issues repos only.
- [ ] `server.ts`: one cache per server; on each `/api`, `want` the IDs with empty state titles, pass `titles` to `buildApi`.
- [ ] Tests: `api.test.ts` one table for the title rule (update existing `build` helper for `titles`); `titles.test.ts` one table with a fake runner (read once and cached, wrong prefix never read, failure retried only after 5 minutes, control characters cleaned).
- [ ] Commit `feat: fall back to the tracker title on the dashboard (CW-175)`.

## Task 3: Layout and styling (`index.html`, `app.js`)

- [ ] Rewrite per spec § 1: Status cards (grid `repeat(auto-fill, minmax(min(100%, 22rem), 1fr))`), stage and risk badges (risk class from first word: low, medium, high, else neutral; light and dark colours), group header pills, Gantt stacked rows with a container query (`container-type: inline-size` on `.session`, table layout and header from `48rem`), `overflow-wrap: anywhere`, body padding `.75rem` below 30rem. Keep the CSP-safe inline styles, `esc`, `link`, the `data-copy` button, and the exported function names. A row with an empty title omits the title line.
- [ ] Keep `app.test.js` passing; add no CSS tests.
- [ ] Commit `feat: fit the dashboard to a narrow side pane (CW-175)`.

## Task 4: Verify

- [ ] Start the server against the root-like fixture (copy the machine state file's shape into a temp root with `.agent-team/state.json` including blank and missing titles); open at 320, 400 and 1280px widths; assert `scrollWidth <= innerWidth` and screenshot. Keep screenshots out of the repo (save under /tmp).
- [ ] Run both test commands and `shellcheck` is not needed (no shell changes).
