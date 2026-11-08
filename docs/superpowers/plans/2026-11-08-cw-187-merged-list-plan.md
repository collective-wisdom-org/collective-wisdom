# CW-187 plan: replace the dashboard Agents pane with a paginated Merged list

Spec: `docs/superpowers/specs/2026-11-08-cw-187-merged-list-design.md`. Tests per `AGENTS.md` § Testing: one table-driven test per rule.

## Task 1: merged reader

- New `agent-team/scripts/dashboard/merged.ts`: pure `parseMerged(json, cfg)` and `createMerged({ run, now })` with `want`, `get` and `idle`, patterned on `titles.ts`. The read runs `pr list --repo <slug> --state merged --limit 200 --json number,title,headRefName,mergedAt,url` through `ghRunner`, at most once every 60 seconds, and keeps the last good list on any failure.
- New `merged.test.ts`: one table test of `parseMerged` and one test of the reader (good read, failed read keeps the list, no new read before 60 seconds).

## Task 2: api and server

- `api.ts`: drop the top-level `gantt` array from `Api` and `buildApi`; add `merged` as an input and an output. Snapshot cleaning and matching stay; unmatched snapshots are dropped.
- `server.ts`: take the slug from the Repo row's GitHub URL whatever the tracker, call `merged.want` on each `/api` call and pass `merged.get()` to `buildApi`. Status titles still need GitHub issues.
- `api.test.ts` and `server.test.ts`: the checks that read `.gantt` read the matched card's `gantt` instead; `/api` answers with `merged: []` and no `gantt` key.

## Task 3: page

- `index.html`: `Agents` and `#gantt` become `Merged` and `#merged`; small `.pager` CSS.
- `app.js`: pure `renderMerged(list, page, size = 10)` returning `{ html, page }`; `draw()` stops touching `#gantt`; a `drawMerged` that redraws only when the html changed and keeps the page across polls; the click handler also serves `button[data-page]`.
- `app.test.js`: one table test of paging, clamping, pager ends and escaping.

## Task 4: docs

- `README.md` § Local dashboard: replace the Agents list sentence with one on the Merged list.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
