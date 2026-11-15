# WISE-423: Send the Approve command from the dashboard with a Return keypress to T3 Code

**Status:** Shipped
**Shipped:** in PR #425, with differences: [as-built](../as-built/2026-11-15-wise-423-approve-keypress.md)
**Ticket:** [#423](https://github.com/collective-wisdom-org/collective-wisdom/issues/423)

## Goal

One click on Approve on a dashboard card sends `approve N` to the Chief of Staff thread, with no Enter press. T3 Code only fills a draft from a `t3code://` link (WISE-421 checked T3 Code (Beta) 0.1.7). So after the link opens the draft, the dashboard server presses Return in T3 Code through macOS automation. T3's own composer sends the draft, and the message is the user's own (`createdBy: "user"`), so the approval check does not change.

## Today

From main at `3077f0f`:

- `approveCommand(r, kind)` in `agent-team/scripts/dashboard/page/app.js` builds `approve N` or `changes N: `.
- `promptLink(chiefLink, text)` turns `<t3-thread://v2/ENV/THREAD>` into `t3code://threads/ENV/THREAD?prompt=TEXT`.
- `approveControls(r, chiefLink)` draws `<a class="approve" href="t3code://..." title="...">`, or with no thread link a `<button class="approve" data-copy>`.
- `agent-team/scripts/dashboard/server.ts` checks the `Host` header (127.0.0.1 or localhost on its own port, which stops DNS rebinding), answers GET only (405 otherwise) and serves `/`, `/app.js`, `/health`, `/api`. `/` gets `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'`.
- The Chief of Staff opens the dashboard in the T3 browser pane, so a click usually comes from inside T3 Code itself.

## Design

### Page

- The Approve link (thread link case only) gains `data-return="N"`. Its title becomes `Opens the Chief of Staff thread with "approve N" typed in and presses Send for you. If it can't, press Send.`
- The click handler lets the link open as today, blurs the link (so a later Return can't land on it and click it again), then sends `POST /press-return` with header `X-Dashboard-Token: <token>` and no body.
- The page reads the token from `<meta name="dashboard-token" content="...">` in `index.html`.
- The answer is JSON `{ sent: boolean, reason?: string }`. On `sent: false`, the page writes one line in the existing `#error` status line, which stays until the next click or a reload:
  - `not-frontmost`: `Approve not sent: T3 Code was not in front. Press Send in the Chief of Staff thread.`
  - `permission`: `Approve not sent: macOS has not allowed the dashboard to press keys. In System Settings > Privacy & Security > Accessibility, turn on T3 Code (or the app that started the dashboard), then press Send in the Chief of Staff thread.`
  - `busy`: nothing shown (a second click inside the wait).
  - Anything else, or a failed request: `Approve not sent: the dashboard could not press Return. Press Send in the Chief of Staff thread.`
- Changes and Mark todo stay plain draft links. The copy button with no thread link stays as is.

### Server

- At start the server makes a random token (`randomBytes(32)`, hex) for this process and writes it into the served `index.html` as the meta tag above. The token is not in `/api` or `/health`.
- New route `POST /press-return`. Every check must pass, else nothing is pressed:
  1. The existing `Host` check.
  2. `Origin` is exactly `http://127.0.0.1:<port>` or `http://localhost:<port>`. Missing or any other origin: 403.
  3. `Sec-Fetch-Site`, when present, is `same-origin`. Otherwise 403.
  4. `X-Dashboard-Token` equals the token (compared with `timingSafeEqual`). Otherwise 403. A custom header also makes a cross-site `fetch` preflight, and the server answers no `OPTIONS` (405), so a browser blocks it.
  5. No body over 0 bytes is read; a body is ignored.
  6. One press at a time, and at most one every 3 seconds. Inside that window the answer is `{ sent: false, reason: "busy" }`.
- Any other method on `/press-return` is 405, and GET stays 405 there, so no link or image can press a key. Every other route is unchanged: still GET only.
- After the checks, the server waits 1.2 seconds (the draft lands in the composer), then runs `osascript` with a fixed script and no user text in it:

  ```applescript
  tell application "System Events"
    set front to bundle identifier of first application process whose frontmost is true
    if front is not "com.t3tools.t3code" then return "not-frontmost"
    key code 36
  end tell
  return "sent"
  ```

  It runs with `execFile` (no shell) and a 3 second timeout. Mapping: output `sent` gives `{ sent: true }`, `not-frontmost` gives `{ sent: false, reason: "not-frontmost" }`, an osascript error -1743 (not allowed to control System Events) or 1002 / -1719 / -25211 (no Accessibility) gives `reason: "permission"`, any other failure or a timeout gives `reason: "error"`. On a platform other than macOS the answer is `reason: "unsupported"` and nothing runs.
- `startServer` takes an optional `pressReturn: () => Promise<string>` (like `scheme` today) so tests swap the `osascript` call. A pure `pressResult(result)` maps the runner's output and error to the JSON answer.
- The press answers JSON with the existing `no-store` and `nosniff` headers, and no CORS headers.

### Docs

`README.md` § Local dashboard: Approve now presses Send for you when it can; the one-time macOS permission and where to grant it; what happens when T3 Code is not in front. The sentence "The page never sends a message" becomes "The page never sends a message itself: Approve presses Return in T3 Code, so T3 sends it as yours."

## Test

Table-driven, per `AGENTS.md` § Testing:

- `server.test.ts`, one table for the press route's guard: right origin and token presses once and answers `sent: true`; missing origin, other origin, `Sec-Fetch-Site: cross-site`, missing token, wrong token, wrong `Host`, GET, OPTIONS each answer 403 or 405 and do not call the runner; a second press inside 3 seconds answers `busy` and does not call it.
- `server.test.ts`, one table for `pressResult`: `sent`, `not-frontmost`, each permission error number, other error, timeout.
- `server.test.ts`: the served `/` has the token meta tag, and `/api` and `/health` do not contain the token.
- `app.test.js`: the approve-controls table gains `data-return` and the new title on the Approve link, none on Changes or on the copy button; `promptLink` cases unchanged. One table for the message line per `reason`.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and the Python suite pass.

Real run: on the user's machine, with the dashboard in the T3 browser pane, click Approve on an awaiting card (a throwaway thread, see Calls) and show in the PR that the message went out with no Enter press. Also show the `permission` line once, before Accessibility is granted.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/server.ts` | Token, `POST /press-return` with its guard, `pressResult`, injectable `pressReturn`. |
| `agent-team/scripts/dashboard/server.test.ts` | Guard, mapping and token tests. |
| `agent-team/scripts/dashboard/page/index.html` | Token meta tag placeholder. |
| `agent-team/scripts/dashboard/page/app.js` | `data-return` and title on Approve, click handler, message line. |
| `agent-team/scripts/dashboard/page/app.test.js` | Approve-controls and message rows. |
| `README.md` | § Local dashboard. |

## Non-goals

- Posting any message from the dashboard server, or any change to `cos_user_check.py`, the approval check or how a message is marked as the user's.
- The Changes control and the Mark todo button (WISE-419).
- Windows or Linux key presses.
- Typing text by automation: the only key sent is Return.

## Calls I made

- **The server presses Return, not the page.** A web page can't press keys outside itself, so the page asks its own server, which runs `osascript`. That puts a key-pressing route on a local port, guarded by Host, Origin, `Sec-Fetch-Site`, a per-process token in the page and a 3 second rate limit. A page on another site can't read the token and can't send the header without a preflight the server refuses.
- **The guard checks that T3 Code is in front by its bundle id `com.t3tools.t3code`,** read from the installed T3 Code (Beta) 0.1.7. A later T3 build with another id would make every press answer `not-frontmost`, which leaves the draft, as today.
- **A 1.2 second wait before the press,** counted on the server after the click. Not measured yet; the build tunes it on the real machine.
- **The biggest risk: where T3 puts keyboard focus after the link opens the thread.** If focus stays in the browser pane instead of the composer, Return does nothing and the draft stays. The build checks this for real. If Return can't be made to land in the composer, the PR says so and, per the ticket, the Approve link falls back to the tooltip that says Send is needed, and the press route is not shipped.
- **The check reads the frontmost app, not the focused field.** If T3 is in front but the user clicked into another T3 field within 1.2 seconds, Return goes there. I accept that: it's the user's own T3 window, Return in T3 sends or does nothing, and it's the same window the draft is in.
- **Blur the link after the click** so a Return that lands back in the page can't click Approve again and loop.
- **Messages go in the existing `#error` line,** not a new banner or a per-card note, because cards redraw every 5 seconds.
- **The permission text names T3 Code** because the Chief of Staff starts the dashboard from T3, and macOS asks on behalf of the app that started `node`. It says "or the app that started the dashboard" for a hand start from a terminal.
- **Approve on build cards too,** not only merge cards: both use the same `approve N` control. The ticket says "an awaiting card".
- **The real run never approves anything by accident.** The build proves the press against a throwaway T3 thread through a test dashboard pointed at it, never against the live Chief of Staff thread, and the PR says so. A real approval through the button happens only when the user clicks it.

- **Accepted trade-off, found in review:** macOS gives the Accessibility permission to the app at the top of the process tree, so with it granted, any process under T3 Code, an agent's shell included, could press keys too, and the route's token does not stop local code. The route defends against web pages only (and the page is not frameable). The user decides whether to grant Accessibility; the README says so.

Touches: none of data, money, auth, user email or migrations. It adds a local route that presses a key on the user's Mac, which the security review checks.
