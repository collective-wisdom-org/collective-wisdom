# CW-307: Copy icon for the thread link next to each ticket title

**Status:** Draft
**Ticket:** [#307](https://github.com/collective-wisdom-org/collective-wisdom/issues/307)

## Goal

Copying a ticket's thread link is the most common action on a dashboard card, and the `Copy thread link` text button sits at the far right of the `.sub` line, away from the title. Put a small copy icon right after the title instead, so each ticket has one copy control, next to the name you are looking at.

## Today

- `ticket()` in `agent-team/scripts/dashboard/page/app.js` draws each ticket card and flat row. The `.head` div holds the id and `<span class="title">`. When `r.threadLink` is set, a `<button class="copy" data-copy="...">Copy thread link</button>` goes at the end of the `.sub` line, pushed right by `button.copy { margin-left:auto; }` in `page/index.html`.
- One document click handler (near the end of `app.js`) copies for every `button[data-copy]`. It sets the button's `textContent` to `Copied` or `Copy failed` and restores the old text after 1.5 seconds.
- `threadButton` (Chief of Staff and project manager cards) uses the same `copy` class and handler, with the text `Thread`.
- The page only rebuilds the status HTML when it changed, so a button's feedback state survives a poll that changes nothing.

## Design

### 1. The icon button in `ticket()`

- When `r.threadLink` is set, `.head` ends with `<button type="button" class="copy-icon" data-copy="<escaped link>" aria-label="Copy thread link" title="Copy thread link"><svg ...></svg></button>`, right after the title span (or after the id when there is no title).
- The SVG is inline, `aria-hidden="true"`, drawn with `stroke="currentColor"`: two overlapping rounded rectangles, the usual copy glyph. A 14px icon in a 1.5rem square button.
- No `threadLink`, no button.
- The `Copy thread link` text button leaves the `.sub` line. Ticket helper cards get the icon the same way, after their request title.

### 2. Feedback in the click handler

- The handler stays one handler for every `button[data-copy]`.
- For a `copy-icon` button it never touches `textContent`. On success it sets `data-state="copied"` and the `aria-label` and `title` to `Copied`; on failure `data-state="failed"` and `Copy failed`. After 1.5 seconds it removes `data-state` and puts the label and title back to `Copy thread link`.
- Text buttons (`Thread`) keep today's text swap.

### 3. Style in `page/index.html`

- `button.copy-icon`: square, 1.5rem, no padding, transparent with no border, `color:var(--muted)`, `vertical-align:middle`, a small left margin from the title. Hover uses the existing button hover (`--b-neutral` background) and `color:var(--fg)`.
- `data-state="copied"` colors the icon `var(--bar)` (the green token); `data-state="failed"` colors it `var(--err)`. Both tokens already switch for light and dark.
- The existing `button:focus-visible` ring applies unchanged, so the button is reachable by Tab with the same outline as the others.

### 4. Tests (`page/app.test.js`)

- `threadLink becomes a copy button carrying the exact link` checks for the icon button inside `.head`, with `aria-label="Copy thread link"` and the escaped link in `data-copy` unchanged, and no `Copy thread link` text button. A row with no link still has no button.
- The ticket helper assertion on `data-copy` stays and still passes; the Chief of Staff and project manager `Thread` assertions are untouched.
- The click handler's feedback is browser behavior with no test harness on this page today; it is checked by hand in the dashboard (see Proof in the PR).

### 5. README

`README.md` § Local dashboard: the sentence about thread copy buttons says a ticket's copy button is an icon right after its title.

## Leaves out

- The Chief of Staff and project manager `Thread` buttons.
- Merged list rows, which carry no thread link.
- Thread links inside the Agents chart.
- The thread link line in a ticket's `Details`, which stays.
- Coordination with #266 (PR #267, dashboard redesign), which moves the same button into Details. Whichever lands second rebases on the other.

## Calls I made (surprising first)

- **Copied and failed feedback is a color change plus a changed accessible name, not a swapped glyph.** The icon turns green on success and red on failure, and `aria-label`/`title` say `Copied` or `Copy failed` for screen readers and hover. Swapping to a check or cross glyph would need a second and third SVG in the handler for little gain.
- **A new class, `copy-icon`, instead of reusing `copy`.** `copy` carries `margin-left:auto` and the text-swap behavior the `Thread` buttons still need; the handler branches on the class.
- **No test for the click handler.** It runs only in a browser, and `AGENTS.md` § Testing skips small UI interactions. The render test covers what can break silently: the link reaching `data-copy` intact.
- **The icon follows the id when a ticket has no title**, so a link is never dropped because the title is empty.
- **The inline SVG is hand-written, two rectangles**, with no icon library, since the page loads nothing external.
- **One README sentence changes**, though the ticket names no doc.

## Touches

None of: data, money, auth, user email, migrations.
