# WISE-429: Send Mark todo from the dashboard with one click

**Status:** Draft
**Ticket:** [#429](https://github.com/collective-wisdom-org/collective-wisdom/issues/429)

## Goal

One click on Mark todo on a Backlog card sends `mark N todo` to the Chief of Staff thread, with no Enter press. It reuses the Return keypress that Approve got in WISE-423: the link opens the draft, then the page asks `POST /press-return` to press Return in T3 Code. The route and its guards do not change.

## Today

From main at `a1ab8ed`, in `agent-team/scripts/dashboard/page/app.js`:

- `todoControl(r, chiefLink)` draws `<a class="todo" href="t3code://...">Mark todo</a>` with no title, or `<button class="todo" data-copy>` with no usable thread link.
- `approveControls` gives the Approve link `data-return="N"` (the ticket number) and the title `... and presses Send for you. If it can't, press Send.`
- The document click handler finds `a[data-return]`, blurs it, and on a plain left click calls `pressReturn(ticket)`. `pressReturn` sets `repeat` when the ticket equals the last one pressed (`pressedTicket`), POSTs `/press-return`, and puts `pressMessage(answer, repeat)` in the error line.
- `pressMessage` and `PRESS_MESSAGES` start every failure with `Approve not sent:`, and the busy line says `another Approve was still being sent`.

## Design

### Page

- `data-return` holds the whole command instead of the ticket number: `data-return="approve 429"` on Approve, `data-return="mark 429 todo"` on Mark todo. That one value tells the handler both which ticket and which command, so the two never mix.
- `todoControl`, with a thread link, draws `<a class="todo" href="..." title="..." data-return="mark N todo">Mark todo</a>`. The title is `Opens the Chief of Staff thread with "mark N todo" typed in and presses Send for you. If it can't, press Send.`, the same wording as Approve. The copy button with no usable link is unchanged.
- The click handler is unchanged except that it passes the command: `pressReturn(link.dataset.return)`.
- `pressReturn(command)` keeps the last command pressed (`pressedCommand`, renamed from `pressedTicket`). A second click is a repeat only when its command is the same string: a second Mark todo on the same ticket is a repeat, like a second Approve; an Approve after a Mark todo is not.
- `pressMessage(answer, repeat, action)` takes the control's name, `Approve` or `Mark todo`, from a new exported `pressAction(command)`: `Mark todo` for a command starting `mark `, `Approve` otherwise. Every line starts `<action> not sent:`. The lines:
  - `not-frontmost`: `<action> not sent: T3 Code was not in front. Press Send in the Chief of Staff thread.`
  - `permission`: the same text as today, with `<action>` in front.
  - `busy`, not a repeat: `<action> not sent: another one-click send was still running. Press Send in the Chief of Staff thread.` (The server's 3 second limit is shared, so a Mark todo right after an Approve can hit it.)
  - `busy` on a repeat, or `sent: true`: nothing.
  - anything else, or a failed request: `<action> not sent: the dashboard could not press Return. Press Send in the Chief of Staff thread.`
- The code comment about the press message names both controls.

### Server

No change. `/press-return` takes no ticket or command, so it presses Return the same way for both.

### Docs

`README.md` § Local dashboard: the Mark todo sentence says that with a Chief of Staff thread it opens the thread with `mark 419 todo` typed in and presses Send for you, the same way as Approve and with the same permission; and the error line says `Mark todo not sent` and why when it can't. The line "The page never sends a message itself: `Approve` presses Return" names both controls.

## Test

Table-driven, per `AGENTS.md` § Testing, in `app.test.js`:

- The Mark todo table: the link case now expects `title` and `data-return="mark N todo"`; the copy cases stay.
- The approve-controls table: `data-return` now holds `approve N`. Changes and the copy button still have none.
- The `pressMessage` table gains the action: each reason row runs for `Approve` and `Mark todo` and checks the line starts with that name; repeat-busy and sent stay empty for both. One row each for `pressAction`.
- The repeat rule (same command is a repeat, other command is not) lives in the click-handler closure, which has no test harness today; I keep it a one-line string compare and leave it untested rather than add a DOM harness.
- `server.test.ts` is not touched, so no guard test changes.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and the Python suite pass.

Real run: the build can't click in the user's T3 window, so the PR says plainly that the one-click send was not run on a real machine unless the user tries it before merge (a Mark todo click on a real Backlog card only moves that ticket to Todo, which is easy to undo).

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | `data-return` holds the command; Mark todo link gets title and `data-return`; `pressAction`; `pressMessage` takes the action; `pressedCommand`. |
| `agent-team/scripts/dashboard/page/app.test.js` | Mark todo, approve-controls and message rows. |
| `README.md` | § Local dashboard, Mark todo and the "never sends" line. |

## Non-goals

- Any change to `/press-return`, its guards, `server.ts`, `cos_user_check.py` or the approval check.
- The Changes control, which stays a draft.
- Any automation beyond pressing Return in T3 Code.

## Calls I made

- **`data-return` carries the whole command, not the ticket number plus a second attribute.** One attribute keeps the repeat check and the message name from ever disagreeing, and it is what the ticket's "must not mix the two commands up" asks for.
- **A repeat is the same command string,** so Approve then Mark todo is never treated as a repeat. They can't both show on one card today anyway (Mark todo is Backlog only, Approve is awaiting only).
- **The busy line no longer names Approve as the other press.** The server's 3 second limit is shared across both controls, so the line says "another one-click send was still running" instead of guessing which one.
- **The click-handler repeat rule gets no new test.** It's a string compare inside the page's event closure, which no test drives today; adding a DOM harness for one line breaks the test budget.
- **No real-machine run by the build.** The PR says so; the user can click Mark todo on a real Backlog card to check it.

Touches: none of these. It sends one more command through the existing local Return press.
