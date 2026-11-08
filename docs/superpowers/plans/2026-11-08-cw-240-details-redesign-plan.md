# CW-240 plan: dashboard Details redesign, markdown render, stage-picked details

Spec: `docs/superpowers/specs/2026-11-08-cw-240-details-redesign-design.md` (approved at 0927244). Tests per `AGENTS.md` § Testing: one table per rule, test lines no more than feature lines. Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js` (Node 24+). All paths below are under `agent-team/scripts/dashboard/`.

## Task 1: `specUrl` and stage-picked details (server side)

- `details.ts`: `validSpecPath` becomes the strict `^docs/superpowers/specs/[A-Za-z0-9._-]+\.md$` (no `..`); `validSha` accepts 7 to 40 hex. Export a `specUrlOf(repoUrl, specPath, specSha)` used by `api.ts`. `want` maps stages to kinds: `awaiting-build`, `build`, `build-queued` give spec; `awaiting-merge`, `merge`, `merge-queued` give changes. Add a `merged` kind: `DetailWant` takes an optional `merged: true` with `pr` and `id`; same PR cache (keyed by PR number, once a minute). `prDetail` also reads `mergeCommit.oid` and the matching spec file (spec § 4 "Spec link on a merged row": exactly one file matching the strict path and containing `-<prefix lower>-<n>-` for the ticket) and returns `specPath` and `mergeSha`; the `gh pr view` call asks for `body,files,comments,mergeCommit`. `get()` returns details for merged ids too, with the extra fields.
- `merged.ts`: `parseMerged` keeps each entry's PR `number` on the entry (internal); `MergedEntry` gains `specUrl?` and `detail?`.
- `api.ts`: `StatusRow.specUrl`, set per spec § 3 with no stage filter; spec `detail.url` is `specUrl`; the `branch` check goes. Merged entries get `detail` and `specUrl` from the `details` input.
- `server.ts`: pass every ticket in the six stages as a want; parse `?mergedPage=N` (integer 0..19, else 0) from the `/api` url and want a merged PR detail for the ten entries of that page.
- Tests: `details.test.ts` stage-to-kind table and merged spec recovery table; `api.test.ts` `specUrl` table; `server.test.ts` `mergedPage` table.

## Task 2: markdown and layout (page side)

- `page/app.js`: `renderMarkdown(text)` per spec § 2 (escape first, `link()` for http(s) only). New `renderDetails` layout per spec § 1 (links line, two fact grids, `section.detail` with rendered sections, review badges, files grid). `ticket()` and `renderMerged` add the `Spec` span before `PR` when `specUrl` is http(s). `renderMerged(list, page, size, open, info)` adds the Details section with `data-merged`; the shell sends `?mergedPage=`, keeps merged info open across a rewrite, and `draw()` refreshes `.info-body[data-merged]` only when its html changed.
- `page/index.html`: styles for the new layout using existing tokens; remove `.info-list`, `.detail-text`, `.detail-review`.
- Tests in `page/app.test.js`: markdown elements table, hostile input table, Spec link render table (card, flat row, merged row, none, `javascript:`), and update the existing Details tests to the new layout.

## Task 3: close out

Run the full test command above and `python3 -I -m pytest -q agent-team/scripts`. Then the compaction pass.
