# CW-323: CI wait on the agent gantt: plan

Spec: `docs/superpowers/specs/2026-11-14-cw-323-ci-wait-gantt-design.md`. Follow it; this plan only orders the work.

Verify with: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` (Node 24+) and `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: `agent-team/scripts/dashboard/ci.ts` + `ci.test.ts`

- `requiredFromProject(markdown)`: `{ none: boolean; names: string[] }` from the `Required CI checks` row (cell starting with `none` gives `none: true`; otherwise every backticked token, split on commas; missing or `TODO(` cell gives no names).
- `ciWait(json, required)` per spec § 1, returning `[number, number|null][]` or `null` for bad JSON / no PR. The GraphQL query string is exported as `CI_QUERY`.
- `createCi({ run, now })` per spec § 2: `want(wants, cfg)` with `{ id, pr, merged }` wants and `cfg = { slug }`, `get()` keyed `<id>#<pr>`, `idle()`. The query runs as `['api','graphql','-f','query=...','-f','o=<owner>','-f','r=<repo>','-F','n=<pr>']`. One read at a time. Open PR re-read after 60 s, merged PR once, failed read keeps the last spans and retries after 60 s, unwanted entries dropped after 60 s.
- Tests: table-driven `ciWait` and one reader test, as listed in spec § 5.

## Task 2: wire the api

- `api.ts`: `buildApi` takes `ci?: Record<string, [number, number|null][]>`; set `ci` on `StatusRow` (key `<id>#<pr from state>`) and `MergedEntry` (key `<id>#<number>`, before `number` is stripped) only when non-empty. Add the field to both types. Test in `api.test.ts`.
- `server.ts`: create `createCi({ run: ghRunner(root) })`; each tick, build wants from board tickets with a `pr` (not merged) and the shown merged entries, skip when `requiredFromProject(...).none`, pass `required` names to the reader, pass `ci: ci.get()` to `buildApi`.

## Task 3: the chart

- `page/app.js`: `renderGantt(sessions, now, ci)` adds the `CI wait` row under `Total` per spec § 4 (merged length with `union`, open span runs to `now`, `Total` unchanged, row only where a chart is drawn). `drawCharts` passes `entry.ci` for ticket and merged charts. Style in `page/index.html` only if the existing `.grow`/`.gtotal` classes do not do.
- Test in `app.test.js`.

## Task 4: README

One sentence in `README.md` § Local dashboard, after the sentence about the waterfall's total line.
