# WISE-495: Fix dashboard thread links that deselect the open T3 Code thread and leave a blank window

**Status:** Draft
**Ticket:** [#495](https://github.com/collective-wisdom-org/collective-wisdom/issues/495)
**Shipped:** in PR #498, with differences: [as-built](../as-built/2026-11-22-wise-495-dashboard-links-blank-window.md)

## Goal

Approve, Changes and Start shipping on the dashboard open the Chief of Staff thread with the command typed in. They never deselect the thread the user is on and never leave a blank window. The one-click press (`/press-return`) still sends only into the Chief of Staff thread.

## What I found before the build

I read the code of both installed apps (T3 Code (Beta) 0.1.9 and T3 Code (Nightly) 0.1.10-nightly.20261114). Both have the same link handling.

- **The link shape is still read.** The desktop shell and the window both run `promptLinkAppPath`: `t3code://threads/ENV/THREAD?prompt=…` becomes the in-app route `/ENV/THREAD?prompt=…`, and the window calls `router.navigate({ href })`. With no `prompt` the route is the same. So "the 0.1.7 comment is stale" is not the cause by itself.
- **macOS sends the link to the running app.** Both apps share the bundle id `com.t3tools.t3code`, and LaunchServices lists Nightly (the running one) as the default for `t3code:`, with Beta as the other candidate. Today the link goes to the right app. The shared bundle id makes this fragile, but it is not what breaks now.
- **The environment id matches.** `dashboard.json` and the running server both report `fa8d9b7c-…`.
- **The dashboard runs in T3's built-in browser**, so the click is not a plain macOS link open. The built-in browser treats `t3code:` as an external protocol: it shows a modal dialog "Open this t3code link?" (Open / Cancel, Return picks Cancel). Only after Open does macOS hand the link back to T3, which then navigates the main window. Meanwhile the dashboard's one-click press waits 1.2 s and presses Return in whatever T3 composer it can focus, which can be the dialog or the thread the user was on, not the Chief of Staff thread.
- **The route's own page is empty.** `/_chat/$environmentId/$threadId` renders `null`; the thread view comes from the layout, which looks the thread up by the route params. A route whose thread the window cannot resolve leaves the sidebar with nothing selected and the main pane blank, which matches the report.
- **Ids are not encoded the way T3 encodes them.** T3's own thread-link builder percent-encodes each segment (`encodeURIComponent`, plus `.!~*'()`), and it decodes route segments with `decodeURIComponent`. The dashboard puts ids in raw. The Chief of Staff id is `mcp:0319eb45-…`, and child ids look like `thread:delegated-task:command%3Amcp%3A…`. A raw `%3A` in an id is decoded to `:` on the way in, so the window looks for a thread that does not exist: a blank pane.

I did not click the live links in the spec phase: that would move the user's own T3 window while the team is running. The build starts with that reproduction.

## Change

1. **Reproduce** (build step 1, on the running Nightly, from the dashboard tab in T3's built-in browser). For Approve, Changes and Start shipping, and for `t3code://threads/ENV/THREAD` with no `prompt`, record: whether the "Open this t3code link?" dialog shows, which app handles the link, which thread is selected after it, whether the pane is blank, and where the one-click Return lands. Also open the same link with `open` from a terminal, which skips the built-in browser. The results go in the PR's `## Proof`.
2. **Link shape** (`page/app.js`, `promptLink`): encode the environment and thread segments the way T3 does (`encodeURIComponent`, then `.!~*'()` as `%XX`), so an id that holds `%` or `:` comes back unchanged after T3 decodes it. Update the comment to say the link was checked against T3 Code 0.1.9 and 0.1.10-nightly, and that it opens through the built-in browser's "Open this t3code link?" dialog.
3. **Press only after the thread is open** (`server.ts`, the press script). The one-click Return must not fire into the dialog or the old thread. Before pressing, the script checks that no modal dialog is up on T3's front window and that the focused composer is the Chief of Staff thread's. If it can't tell, it presses nothing and answers a new reason, `not-open`, whose line reads "`<action>` not sent: the Chief of Staff thread was not open yet. Press Send there." The wait before the check grows from 1.2 s to a poll of up to 5 s, so the user has time to click Open in the dialog. How the script tells the Chief of Staff composer from another one comes from step 1: the window title, or the composer's prompt text holding the thread's draft. If neither tells them apart, the press goes away and Approve and Start shipping become plain links like Changes, with the tooltip saying to press Send.
4. **Fallback when step 1 shows T3 cannot open the thread at all**, even after step 2: the three controls become the copy button the dashboard already shows when there is no thread link (`data-copy`), and the tooltip says to paste the command into the Chief of Staff thread. No link is offered that blanks the window.
5. **Tests**
   - `page/app.test.js`: the existing `promptLink` table gains rows for an id with `:` and one with `%3A`, expecting T3's encoding.
   - `server.test.ts`: the `pressResult` / press-message table gains the `not-open` reason. The JXA script itself has no unit test (it runs against the live app); step 1's proof covers it.

## Leaves out

- New dashboard controls.
- Changes to T3 Code. Its upstream takes no feature PRs.
- The thread cards' copy buttons. They copy a `<t3-thread://…>` link and open nothing, so they cannot blank the window.
- The Beta/Nightly shared bundle id. It is the user's install choice; this ticket only notes it in the `promptLink` comment.

## Calls I made

- **The build starts with a live click, not the spec.** The fix branches on what that click shows (steps 3 and 4), so the spec gives the rule for each outcome instead of guessing the cause. The click moves the user's T3 window once per control.
- **The one-click press may go away.** If step 1 shows the script cannot tell the Chief of Staff composer from another, Approve and Start shipping stop pressing Return for you and become links like Changes. That costs one click, and it is the only way to keep a Return from landing in the wrong thread.
- **The press waits up to 5 s instead of 1.2 s**, to cover the time it takes to click Open in the built-in browser's dialog.
- **Encode ids like T3 does, even if step 1 shows the Chief of Staff id works raw.** Child ids hold `%3A`, and T3's own links are encoded, so matching T3 costs nothing and removes one way to blank the pane.
- **No server-side `open` of the link.** Opening it from the dashboard server would skip the dialog, but it adds a new endpoint that launches apps, and with two apps sharing a bundle id it could pick the wrong one. I'd do it only if step 1 shows the dialog path cannot work.
