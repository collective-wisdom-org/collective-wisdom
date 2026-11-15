# CW-370: Every dashboard row as a card: plan

Spec: `docs/superpowers/specs/2026-11-14-cw-370-every-row-a-card-design.md`. Files are under `agent-team/scripts/dashboard/page/`.

## Task 1: markup (`app.js`)

- `ticket()`: class is `ticket` + ` attn` (attn) + ` compact` (compact row) + ` blocked` (blocked flat row). Update the doc comment.
- `renderStatus`: every band's list is `<ul class="cards">`.
- `renderMerged` and `teamList`: `<ul class="cards">` and `<li class="ticket compact">`.

## Task 2: CSS (`index.html`)

- Delete the `ul.rows > li.row`, `:first-child` and `.blocked` rules; drop `li.row .head + .meta` from the `.cos-card .meta` selector.
- Add `.ticket.blocked { background:var(--red-tint); box-shadow:inset 3px 0 0 var(--red), 0 1px 2px var(--shadow); }`.
- Grep that no `ul.rows`, `li.row` or `class="row"` is left anywhere in the page files.

## Task 3: test (`app.test.js`)

- One table-driven test: Your turn, In progress, Up next, Not started (`renderStatus`), Done (`renderMerged`) and project manager (`renderChief`) rows are `li.ticket` in `ul.cards`; no `class="row"` or `class="rows"`; blocked Up next row has `ticket blocked`; Your turn row has `ticket attn`.
- Update the pager test that counts `<li class="row">`.

## Verify

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
