# CW-394 plan: PR link on open

Spec: `docs/superpowers/specs/2026-11-15-cw-394-pr-link-on-open-design.md`. Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js` after each task.

1. `agent-team/scripts/dashboard/open.ts`: `parseOpen`, `createOpenPrs`, modelled on `merged.ts`. Test in `open.test.ts` (one table test for `parseOpen`, one for the refresh and keep-last-good rule).
2. `api.ts`: optional `openPrs` input; `prUrl` falls back to it when state `pr` is not an integer. One table test in `api.test.ts`.
3. `server.ts`: create `createOpenPrs` with `ghRunner(root)`, call `want(mergedCfg)` in `api()`, pass `get()` to `buildApi`.
