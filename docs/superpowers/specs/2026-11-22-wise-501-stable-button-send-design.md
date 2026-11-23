# WISE-501: a stable way for dashboard buttons to send their message

Ticket: [WISE-501](https://github.com/collective-wisdom-org/collective-wisdom/issues/501)

## Goal

Clicking Approve or Start shipping on the dashboard sends `approve N` or `start shipping N` into the Chief of Staff thread as the user's own message (`createdBy: "user"`), every time, in the conditions the user works in. Today the click fills the T3 message box and the send often never happens.

The ticket is an experiment first and a build second: measure every way to send that could count as the user, keep the one with the best count, and build it into the dashboard.

## Today

- `approveControls` and `todoControl` (`agent-team/scripts/dashboard/page/app.js`) render Approve and Start shipping as `t3code://threads/ENV/THREAD?prompt=TEXT` links with `data-return`. A click opens the link (a draft only), then `pressReturn(command)` POSTs `/press-return`.
- `press` (`agent-team/scripts/dashboard/server.ts`) checks origin and token, the once-per-3-seconds limit and the fixed command shape (`PRESS_COMMAND`), then runs `PRESS_SCRIPT` through `pressReturnMac(prefix)`: JXA that needs Accessibility, T3 Code in front, no sheet, finds the `Message <PREFIX> - Chief of Staff` text area, clicks it, re-reads focus and presses Return (key code 36). It retries `not-frontmost` and `not-open` for 5 seconds. `confirm` then polls `cos_user_check.py latest` for 3 seconds and answers `not-recorded` or `unchecked` when the message did not land.
- `t3 thread send` and the MCP `t3_thread_send` record `createdBy: "agent"` and must keep failing `cos_user_check.py`.
- On this machine: T3 Code (Beta) 0.1.9 and T3 Code (Nightly) 0.1.10-nightly.20261114.4695, both bundle id `com.t3tools.t3code`; the `t3` CLI at `~/.t3/bin/t3`; keybindings in `~/.t3/userdata/keybindings.json` (`composer.sendAlternate`, `composer.sendBackground`, `composer.sendAndNewThread`, plus the plain send). `t3 browser` only has `setup` (Linux) on this build.

## Builds

### 1. Diagnosis

Click Approve and Start shipping (against a harmless test target, see § Harness) from the dashboard in T3's built-in browser pane and in an external browser (Safari or Chrome), on T3 Beta and T3 Nightly. For each click record: the server's answer (`sent` or the reason), whether the text landed in the box, whether a `createdBy: "user"` message arrived. Name the cause of the failures. The likely suspects to confirm or rule out, in order:

- the press runs before the link's draft is in the box (the link dialog in the built-in browser, or T3 still switching threads), so Return sends nothing or an empty box;
- Return lands while the built-in browser pane, not the composer, holds keyboard focus, even after the click;
- `frontId()` reads the browser, not T3, when the dashboard is in an external browser, so every press ends `not-frontmost`;
- Return in the composer inserts a newline or is swallowed while a turn is running, under the user's keybindings;
- two T3 apps running at once with the same bundle id, and the script driving the wrong one.

### 2. Harness

`agent-team/scripts/dashboard/press_harness.ts`, run by hand, never by CI or the dashboard:

```
node agent-team/scripts/dashboard/press_harness.ts --candidate <name> --runs 10 --thread <chief thread id> --prefix <PREFIX>
```

- Each run puts a unique harmless test message (`press test <run id>`, a command the Chief of Staff ignores) in the box through the candidate, sends it, then waits up to 5 seconds for a `createdBy: "user"` message with that exact text after the run's start, using `cos_user_check.py latest` (the same check the Chief of Staff makes). It prints one row per run and a total: candidate, condition, runs, arrived as user, misses with their reason.
- Candidates are small functions in the harness that share the server's JXA helpers, so the one that wins moves into `server.ts` without a rewrite.
- The condition (built-in pane or external browser, T3 in front or not, Beta or Nightly) is set up by hand and named with `--condition`.
- The Chief of Staff thread gets the test messages, so a run says in the thread first that a test is starting and that `press test` lines are not commands. The Chief of Staff already ignores text that is not one of its commands; the harness does not change that.

### 3. Candidates

Each runs at least 10 times in each condition it supports:

1. Baseline: link, then the current focus click plus Return.
2. Link, then click T3's Send button through Accessibility (find the button next to the Chief of Staff composer, check it is enabled, `AXPress` it).
3. Link, then T3's own send shortcut after focus is confirmed, for each `composer.send*` binding that sends in the same thread (not `sendAndNewThread`, not `sendBackground` unless it records the same message).
4. No link: focus the Chief of Staff composer through Accessibility, set its value (`AXValue`) or paste from the clipboard (save and restore the user's clipboard), check the box holds exactly the command, then send with the best of 1 to 3.
5. No link, no keyboard: open the Chief of Staff thread with a bare `t3code://threads/ENV/THREAD` link (no prompt) or by Accessibility, then 4.
6. Retry after `not-recorded`: only measured in combination with a candidate that checks the box is empty or no longer holds the command before it presses again, so a command can never be sent twice.
7. A real client of T3: the T3 web client (`t3 serve` or the desktop app's own server, the address in `~/.t3/userdata/server-runtime.json`) in a browser, driven by the same Accessibility or by a page script, and the T3 WebSocket API with the desktop owner's session, if a message sent that way records `createdBy: "user"`. Measured read only first: one message, then a look at what `createdBy` it recorded. A path that needs a pairing token or a secret stores nothing in the repo and is dropped if it needs the user to paste a secret each time.
8. Any other way found during diagnosis (for example `AXConfirm` on the text area, or the composer's own submit through the web area's AX actions).

### 4. Choose and build

- Pick the candidate with the best count, then the fewest conditions (no Accessibility beats Accessibility; works with T3 not in front beats needs it in front). Ties go to the one with the smaller change to `server.ts`.
- Build it into `/press-return`. Keep: the origin and token check, the once-per-3-seconds limit and the `pressing` lock, the fixed command shapes (`approve N`, `start shipping N`), the Chief of Staff thread check (the composer label or the thread id), `confirm` through `cos_user_check.py`, and the failure lines. A new failure reason gets its own line on the page saying why and what to do.
- When the winner does not use the link's draft, Approve and Start shipping stop filling the box through `?prompt=` (the link still opens the thread, so a failed send leaves the user one click from pressing Send themselves with the command copied, or the box filled by the press itself). Changes stays a draft-only link.
- Tests: one table each in `server.test.ts` (press answers for the new path and its reasons, through the injected `pressReturn`), `api.test.ts` if the API shape changes, and `app.test.js` (the new failure lines and the link shape). The harness itself is not tested.

### 5. Docs

README dashboard text, the control tooltips (`data-tip` on Approve and Start shipping), and the comments on `PRESS_SCRIPT`, `pressReturnMac`, `promptLink` and `confirm`.

## Proof in the PR

- A table of every candidate: condition, runs, arrived as `createdBy: "user"`, cause of each miss, plus the T3 versions, apps and browsers used.
- A real click of Approve and Start shipping on the dashboard that sent the command and that the Chief of Staff accepted (against a test ticket, so nothing real is approved).
- The existing `cos_user_check.py` test that an agent, child or CLI message is not the user's still passes, unchanged.

## Leaves out

- Any change to `cos_user_check.py` or the approval check, including No Hands and auto-approvals.
- Changes to T3 Code itself.
- The Changes control.
- Non-macOS hosts.
- Running the harness in CI.

## Calls I made

- **The real-click proof uses a test ticket, not a real one.** The acceptance asks for `approve N` and `start shipping N` accepted by the Chief of Staff. I'll open a throwaway test issue, have it in the Chief of Staff's view, click Start shipping and Approve on it, and close it straight after; nothing real gets approved or started. If the Chief of Staff can't be pointed at a throwaway ticket without starting real work, the proof stops at "the user's message arrived" and the PR lists the acceptance step under Not proven.
- **The harness posts test messages into the live Chief of Staff thread.** Measuring `createdBy: "user"` needs the real thread. The messages are `press test <id>`, which is not a Chief of Staff command, and the harness says first that a test is starting. If this bothers the Chief of Staff, the fallback is a second thread titled `<PREFIX> - Chief of Staff` in a scratch project, which the label check accepts too.
- **The harness drives the user's real T3 window.** It moves focus and, for the clipboard candidates, uses the clipboard (saved and restored). Runs need the user away from the keyboard, and I'll run them in batches.
- **Clipboard candidates save and restore the clipboard,** text only; an image or file on the clipboard would be lost, so those candidates skip a run when the clipboard holds non-text.
- **A real-client path needing a stored secret is out.** If sending as the user through T3's web client or WebSocket needs a pairing token, the dashboard would have to keep a credential that can post as the user; I'll measure it but not build it unless it works with the session the desktop app already has, with nothing new stored.
- **If no candidate sends every time,** I build the best one, the page says why each miss happened and what to press, and the PR says which conditions it doesn't cover. I won't loosen any check to get a better count.
- **The harness lives in the repo** (`press_harness.ts`) so the next T3 update can be measured again the same way.

Touches: user-facing dashboard controls and the code that sends a message as the user into the Chief of Staff thread (the approval path's input, not its check). No data, money, user email or migrations.
