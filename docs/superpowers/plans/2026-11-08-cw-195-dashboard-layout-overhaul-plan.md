# CW-195 dashboard layout overhaul: plan

**Spec:** [2026-11-08-cw-195-dashboard-layout-overhaul-design.md](../specs/2026-11-08-cw-195-dashboard-layout-overhaul-design.md)
**Ticket:** [#195](https://github.com/collective-wisdom-org/collective-wisdom/issues/195)

All edits are in `agent-team/scripts/dashboard/page/` (`app.js`, `index.html`, `app.test.js`). Verify with `node --test agent-team/scripts/dashboard/page/app.test.js` and the dashboard suite from `AGENTS.md`.

## Task 1: Bands, card markup, compact rows (`app.js`)

- Add a band table: `Needs you` (Awaiting merge approval, Awaiting build approval), `In progress` (Awaiting teammate review, Merging, Speccing, Building, unknown names), `Queued` (Queued to merge, Queued to build, Other). `renderStatus` sorts groups into bands, keeps `/api` order inside a band, draws a band heading, skips empty bands.
- Group `<section>` gets a modifier class (`needs-merge`, `needs-build`) so cards and count pills take the colors; a `blocked` card in `Other` gets the red edge class.
- Card: line 1 id plus title; line 2 muted: risk badge, PR link, copy button (same `data-copy` and text); line 3 muted `next`; Agents disclosure last. Stage badge only in `Other`, plain words (`blocked`, `spec queued`).
- Queued band groups and `renderMerged` render as flat compact rows (`ul.rows`, `li.row`), same fields.
- `renderBadges`: queue badge gets a quiet class.
- `renderGantt`: drop the header row; per row line 1 name, track, cost; line 2 meta `repo · start to end · tokens · model · harness`, empty parts skipped; session heading shows cwd in a small monospace line with the total.

## Task 2: Styles (`index.html`)

Rewrite the CSS: 4px spacing scale, four type sizes, bands, needs-you edges and tints, compact rows, one button style with focus ring and hover, error banner, quiet empty states, outline queue badge, Gantt two-line layout (14rem name column at container width 36rem and up, track under the name below that). Light and dark, WCAG AA text pairs.

## Task 3: Tests (`app.test.js`)

Update only what the new markup breaks (Gantt header row and model/harness cell test, merged card class). Add one table-driven test for bands: order across bands, `/api` order inside a band, unknown group to In progress, empty band not drawn, stage badge only in `Other`.

## Task 4: Contrast check and screenshots

One-off script outside the repo computes the contrast ratio of every text and badge pair against the page and card backgrounds in light and dark; report the ratios in the PR. Capture the live `/api` JSON once, serve it next to the old (`main`) and new page with a throwaway script outside the repo, and take headless Chrome screenshots at 360px and 1280px, light and dark, before and after (eight images) for the PR.
