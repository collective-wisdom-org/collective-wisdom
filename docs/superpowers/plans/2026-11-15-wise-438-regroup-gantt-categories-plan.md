# WISE-438 plan: regroup Gantt bar categories

Spec: `../specs/2026-11-15-wise-438-regroup-gantt-categories-design.md`

## Task 1: classifier, colors, tests, README

Files: `agent-team/scripts/dashboard/page/app.js`, `agent-team/scripts/dashboard/page/index.html`, `agent-team/scripts/dashboard/page/app.test.js`, `README.md`.

- `app.js`: drop `['docs', 'Docs and cleanup']` from `CATEGORIES`. Rules in order: `planning` `/^(?:spec\b|(?:[A-Z][A-Z0-9]*-\d+\s+)?changes$)/i`; `review` `/\b(?:review|security|changes|documenter|docs? check)\b|^fix\b/i`; `building` `/\b(?:build|implement|implementer|code|docs?|compact|compacter|slop|cleanup)\b/i`; then `merge` and `planning` as today (the old docs rule goes).
- `index.html`: `--cat-review:light-dark(#eda100, #c98500)`; remove `--cat-docs` and `.cat-docs`.
- `app.test.js`: update the `barCategory` table per the spec (no `docs` key).
- `README.md`: drop `Docs and cleanup` from the category list.
- Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
