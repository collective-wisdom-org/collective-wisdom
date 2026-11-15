# WISE-419: A Mark todo button on Backlog cards

**Status:** Shipped
**Ticket:** [#419](https://github.com/collective-wisdom-org/collective-wisdom/issues/419)
**Shipped:** in PR #420, as specified

## Goal

Each card on the dashboard's Backlog tab gets a blue `Mark todo` button right after the Agents and Details control. Clicking it opens the Chief of Staff thread with `mark N todo` typed in the input, unsent. The user still presses Send.

## Today

Facts from main at `6c0a09c`, `agent-team/scripts/dashboard/page/`.

- `renderBacklog(groups, collapsed, backlogPage, open, info)` in `app.js` draws the Backlog group and calls `ticket(r, { flat: true, attn: false, group, open, info })` with no `chiefLink`.
- `renderStatus` gets the Chief of Staff link as its fifth argument and passes it to `ticket()`, where `approveControls(r, chiefLink)` builds Approve and Changes: `promptLink(chiefLink, text)` gives `t3code://threads/ENV/THREAD?prompt=TEXT`, and with no usable link the control is a `button[data-copy]` that copies the command.
- `ticket()` ends with `<div class="foot">${sw.control}<span class="meta">…</span></div>`: the Agents and Details switch, then the meta line.
- The page's `button[data-copy]` click handler copies `data-copy` and swaps a text button's label to `Copied` or `Copy failed` for 1.5 s.
- `drawStatus()` already keys its redraw on `last.chief?.threadLink`, so a new Chief of Staff link redraws the Backlog tab too.
- `a.action` in `index.html` is filled with `--accent` and `--on-accent`; `a.approve, button.approve` are outlined.
- `mark N todo` is a Chief of Staff command in `agent-team/.claude/skills/chief-of-staff/commands.md`.

## Design

### Command and control (`app.js`)

- New exported `todoCommand(r)`: `mark N todo` where N is the number at the end of the ticket id (`WISE-419` gives `mark 419 todo`), null for an id with no trailing number.
- New `todoControl(r, chiefLink)`: empty when `todoCommand` is null; else `<a class="todo" href="…">Mark todo</a>` with the `promptLink` href, or, when `promptLink` is null, `<button type="button" class="todo" data-copy="mark N todo">Mark todo</button>`. Same link-or-copy rule as `approveControls`.
- `ticket()` takes a new `markTodo` option (default false). When true, the foot row is the switch, then the `todoControl`, then the meta line.
- `renderBacklog` gains a sixth parameter `chiefLink = ''` and calls `ticket()` with `markTodo: true, chiefLink`. `renderStatus` does not set `markTodo`, so no card outside the Backlog tab gets the button.
- `drawStatus()` passes `last.chief?.threadLink` to `renderBacklog`.

### Style (`index.html`)

`a.todo, button.todo`: the size of `a.approve` (same padding, radius, font size and weight, inline-flex, `height:auto`), filled with `--accent` and `--on-accent`, no border colour of its own (`border:1px solid var(--accent)` so it lines up with the outlined buttons). Hover: `filter:brightness(1.08)`, no underline, and the accent background set again so the shared `button:hover` rule does not turn the copy button grey. On a stale Backlog the link keeps `--on-accent` (a rule after the stale rules, which colour every link `--muted`).

### Test (`app.test.js`)

One table-driven test:

- `todoCommand`: `WISE-419` gives `mark 419 todo`; `CW-7` gives `mark 7 todo`; an id with no number gives null.
- `renderBacklog` with a Chief of Staff link: each card has `<a class="todo" href="t3code://threads/ENV/THREAD?prompt=mark%20N%20todo">Mark todo</a>`, after the switch and before the meta line.
- `renderBacklog` with no link (or a malformed one): `<button type="button" class="todo" data-copy="mark N todo">Mark todo</button>`.
- `renderStatus` with the same rows in Todo, In progress and Your turn groups and a Chief of Staff link: no `class="todo"`.

## Leaves out

- Sending the command, or changing what `mark N todo` does.
- A Mark backlog button, or any new button on other tabs or cards.
- Changing Approve and Changes.

## Calls I made

- **A stale Backlog list still shows the button.** A Backlog read over an hour old greys its rows; the button stays, since the Chief of Staff reads the tracker itself when it runs `mark N todo`.
- **The button sits in the foot row, not the middle actions row.** The ticket asks for it right of Details; the actions row is above the switch.
- **A Backlog card with no ticket number gets no button**, as Approve does.
- **Class name `todo`**, a new class rather than reusing `action` or `approve`, since it is a filled button the size of the outlined ones.
- **The button is a link when there is a Chief of Staff thread link, a copy button otherwise**, reusing `promptLink` and the existing copy handler; the copy button shows `Copied` like Approve.
- **No proof click in T3.** CW-402 already confirmed T3 opens `t3code://threads/…?prompt=` as an unsent draft; the build only checks the href it renders.

## Touches

None of: data, money, auth, user email, migrations.
