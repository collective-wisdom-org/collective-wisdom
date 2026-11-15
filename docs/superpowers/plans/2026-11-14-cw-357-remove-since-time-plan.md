# CW-357 plan: remove "since HH:MM" from dashboard ticket cards

Spec: `docs/superpowers/specs/2026-11-14-cw-357-remove-since-time-design.md`. Main now shows times as `9:05 am` (CW-359), so the text to remove reads `since 9:05 am`.

## Task 1: app.js
In `agent-team/scripts/dashboard/page/app.js`:
- Delete `since()`.
- `stageSentence(stage)` takes one argument and returns the sentence only. Fix its doc comment.
- Add `SECTION_STAGES = new Set(['build','build-queued','spec','spec-queued','merge','merge-queued'])`. In `ticket()`, `status` is empty for those stages.
- Flat row `phrase`: `group === 'Other' ? stageSentence(r.stage) : ''`.
- Update the `ticket()` doc comment if it mentions the status sentence/time.

## Task 2: app.test.js
- `stageSentence` table: drop `stageAt`, no time suffix; `renderStatus` check: `build` card has no `<p class="status">`, `awaiting-merge` card has one.
- Band test queued row meta ends after the risk badge.
- Other assertions that pin `since <time>` (line ~663 regex, ~512) stay valid or are tightened.
- One table-driven test: for every group name the page knows, with `stageAt` set, rendered output has no `/since \d{1,2}:\d\d [ap]m/`.

## Verify
`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
