# WISE-434: Focus the T3 composer before the dashboard presses Return on Approve

**Status:** Shipped
**Shipped:** in PR #450, with differences: [as-built](../as-built/2026-11-15-wise-434-focus-composer-before-approve.md)
**Ticket:** [#434](https://github.com/collective-wisdom-org/collective-wisdom/issues/434)

## Goal

Approve on a dashboard card sends `approve N` even when the T3 message box did not have keyboard focus before the click. Before it presses Return, the dashboard server puts focus in the T3 composer itself and checks that focus landed there. If it can't confirm that, it presses nothing and the page says so.

## Today

From main at `8c018e1`:

- `PRESS_SCRIPT` in `agent-team/scripts/dashboard/server.ts` is a fixed AppleScript. It checks that the frontmost app's bundle id is `com.t3tools.t3code`, then sends `key code 36` through System Events. It never checks which element has focus.
- `pressResult` maps the output to `{ sent, reason }`: `sent`, `not-frontmost`, `unsupported`, `permission` (osascript errors -1743, 1002, -1719, -25211), else `error`.
- `PRESS_MESSAGES` and `pressMessage` in `agent-team/scripts/dashboard/page/app.js` turn a reason into the `#error` line.
- A Return that lands on another element is still reported as `sent`, so the page says nothing.

What I checked on this machine (read only; nothing was focused or pressed):

- **No focus-the-composer shortcut.** The keybinding command ids in T3 Code (Beta) 0.1.9 and T3 Code (Nightly) 0.1.10-nightly.20261114 have no such command. `composer.*` is branch, cycleHost, effort, dictation, host, lock, mode, previousWorktree, send variants, stash and workspace. T3 does have an internal `focusComposer()`, but the only keybound way to reach it is `workspace.focusNext` (F6), which steps through workspace areas, one per press. Both builds use bundle id `com.t3tools.t3code`.
- **The composer is visible to Accessibility.** It is a `role="textbox"` with `data-testid="composer-editor"`. macOS shows it as an `AXTextArea` whose description is `Message <thread title>`, for example `Message WISE - Chief of Staff`.
- **The bug, seen live.** In one probe, T3 Code's focused element was an `AXButton` inside the browser pane's nested `AXWebArea` (the dashboard), not the composer.
- **Speed.** An AppleScript walk of the T3 window (System Events `UI elements`, recursive) took 15.7 seconds to reach the composer across 410 elements. `entire contents` returns nothing for this Electron window. The same walk in JXA, calling `AXUIElementCopyAttributeValue` through `ObjC.bindFunction`, took 100 ms across 258 elements.

## Design

### Focus method: Accessibility, in JXA

`PRESS_SCRIPT` becomes a fixed JXA script (`osascript -l JavaScript -e <script>`, through `execFile`, no shell, no user text, same 3 second timeout). In order:

1. If `AXIsProcessTrusted()` is false, return `permission`. Nothing is pressed.
2. Take the frontmost app from `NSWorkspace`. If its bundle id is not `com.t3tools.t3code`, return `not-frontmost`.
3. Read the app's `AXFocusedUIElement`. If it is the composer (rule below), go to step 6.
4. Otherwise search the app's `AXFocusedWindow` depth first through `AXChildren`, at most 3000 elements, and skip any `AXWebArea` nested inside another `AXWebArea` (the browser pane, where the dashboard runs). The first composer found wins. With none found, return `no-focus`.
5. Click the composer's centre: read its `AXPosition` and `AXSize`, post a synthetic left mouse down and up there (CGEvent), then warp the mouse back to where it was. Then read `AXFocusedUIElement` again, up to 10 times, 50 ms apart. If it is still not the composer (or the position or size can't be read), return `no-focus`. Setting `AXFocused` to true was tried first and returned success, but Electron ignores it and focus does not move, so the click is what ships.
6. Check again that T3 Code is frontmost (else `not-frontmost`), then press Return with System Events `keyCode(36)`, as today, and return `sent`.

The composer rule: role `AXTextArea` and description that starts with `Message `.

A failing AX call (an error code other than success) counts as "not found" at that node. It never throws past the script, so a broken tree gives `no-focus`, not `error`.

The 1.2 second wait before the script runs stays.

### Result and message

- `pressResult` accepts two more outputs: `no-focus` gives `{ sent: false, reason: "no-focus" }`, and `permission` as output gives `{ sent: false, reason: "permission" }` (step 1 returns it as text, not as an osascript error). The error-number mapping stays, because System Events still throws -1743 or 1002 when Automation is off.
- `PRESS_MESSAGES` gains `no-focus`: `Approve not sent: the dashboard could not put the cursor in the T3 message box. Press Send in the Chief of Staff thread.`
- `not-frontmost`, `permission`, `busy`, `unsupported` and `error` keep their lines and handling.

### Docs

`README.md` § Local dashboard: one sentence saying the server first puts the cursor in the T3 message box, and that when it can't, the error line says so and you press Send. Same permissions as today, no new grant.

## Test

Table-driven, per `AGENTS.md` § Testing:

- `server.test.ts`: the `pressResult` table gains `no-focus` and `permission` as plain output.
- `server.test.ts`: one press-route row with a stubbed `pressReturn` that answers `no-focus` gives `{ sent: false, reason: "no-focus" }`.
- `app.test.js`: the `pressMessage` table gains the `no-focus` row.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and the Python suite pass.

The JXA script itself can't run in CI (no macOS session, no Accessibility grant). The build proves it by hand on this Mac: from a test dashboard pointed at a throwaway T3 thread, with focus on a dashboard button, Approve sends the message. With the composer hidden or the thread closed, it shows the `no-focus` line and sends nothing. The PR's Proof section says what was run.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/server.ts` | JXA `PRESS_SCRIPT` with the focus steps; `pressReturnMac` runs it with `-l JavaScript`; `pressResult` maps `no-focus` and `permission`. |
| `agent-team/scripts/dashboard/server.test.ts` | `pressResult` rows and the stubbed route row. |
| `agent-team/scripts/dashboard/page/app.js` | `no-focus` in `PRESS_MESSAGES`. |
| `agent-team/scripts/dashboard/page/app.test.js` | `no-focus` row. |
| `README.md` | § Local dashboard sentence. |

## Non-goals

- Treating the dashboard click as the approval in place of a typed user message.
- Approve on hosts other than macOS.
- Checking that the focused composer belongs to the Chief of Staff thread (see Calls).
- Typing text by automation: Return is still the only key sent.

## Calls I made

- **Accessibility, not a shortcut.** T3 has no focus-the-composer command in Beta 0.1.9 or Nightly 0.1.10. F6 (`workspace.focusNext`) can reach the composer, but it steps one area per press, the number of presses depends on what is open, and a user can rebind it. Clicking the composer goes straight there, and the script checks the result.
- **JXA instead of AppleScript.** The AppleScript walk took 15.7 seconds, far past the 3 second timeout. JXA through the AX C functions took 100 ms. It is still one fixed script run through `osascript` with `execFile`, so the no-user-text, no-shell rule holds.
- **The composer is found by its label, `Message <thread title>`.** That label is T3's own text, not a stable API. If a later T3 build renames it, every press answers `no-focus` and the draft stays, which is no worse than today. The PR notes the T3 versions checked.
- **The search skips the browser pane** (a web area nested in another web area), so it can't pick a text box on the dashboard page.
- **The first composer found wins, and the script doesn't check it is the Chief of Staff thread's.** The link just opened that thread, so it is normally the only composer in the window. In a split view showing two threads, Return could go to the other one. The server does not know the thread's title, so it can't compare. I accept that: it is the user's own window, and the label check still rules out every non-composer field.
- **Focus is clicked, not set.** The script clicks the composer's centre, with the position and size read through AX, and warps the mouse back to where it was, so the cursor moves there and straight back. It then re-reads the focused element up to 10 times, 50 ms apart, and presses Return only if the composer has focus. Setting `AXFocused` was tried first: the call returns success, but Electron ignores it and focus does not move. A synthetic mouse click at the composer's centre does move focus, so that is the shipped method.
- **The search stops at 3000 elements** so a huge window can't run into the 3 second timeout. The composer was element 258 here.
- **Accessibility trust is checked up front** (`AXIsProcessTrusted`), so a missing grant gives the existing `permission` line instead of a confusing `no-focus`.
- **One new reason, `no-focus`,** for both "composer not found" and "focus did not take". The fix is the same for the user either way: press Send.
- **I probed only by reading.** The research for this spec only read. The later `AXFocused` and click tests were run against T3 on this Mac, and the build tests focus and Return against a throwaway thread.

Touches: none of data, money, auth, user email or migrations. It changes the local script that presses Return on the user's Mac, which the security review checks.
