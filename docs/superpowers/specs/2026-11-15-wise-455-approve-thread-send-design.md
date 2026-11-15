# WISE-455: Send dashboard Approve through t3 thread send and settle who the send is recorded as

**Status:** Shipped
**Ticket:** [#455](https://github.com/collective-wisdom-org/collective-wisdom/issues/455)
**Shipped:** in PR #457, with differences: [as-built](../as-built/2026-11-15-wise-455-approve-thread-send-as-built.md)

## Goal

The dashboard's Approve and Mark todo controls open a `t3code://` link and then press Return with a synthesized keypress. When the press lands nowhere, or on the wrong element, the page still says nothing, and the command sits unsent in the composer. The ticket asks to send through `t3 thread send` instead, and to find out what `cos_user_check.py` can safely trust.

The finding (below) is that no route the dashboard can take records a message as the user's without also being open to an agent, and a CLI send is recorded as an agent's, so an Approve sent by the CLI would be ignored by the Chief of Staff. So this ticket keeps the keypress for both controls and fixes the real harm: after the press, the dashboard server checks T3's message store with the same `cos_user_check.py` the Chief of Staff runs, and the page says so when the command did not arrive as the user's message.

## Today

Facts from main at `d0b1b9f`, T3 `v0.1.10-nightly.20261114.4695`.

- `approveControls` and `todoControl` in `agent-team/scripts/dashboard/page/app.js` build links with `data-return="approve 402"` or `data-return="mark 419 todo"`. A click opens the link and runs `pressReturn(command)`, which POSTs `/press-return` with the token header and no body. `pressMessage` and `PRESS_MESSAGES` turn the answer into the error line.
- `press` in `agent-team/scripts/dashboard/server.ts` checks origin, `Sec-Fetch-Site` and the token, allows one press per 3 seconds, waits 1.2 s, runs `pressReturnMac()` (fixed JXA in `PRESS_SCRIPT`) and maps its output with `pressResult`. A Return that reached another element, or reached the composer before the link had filled it, is reported as `sent`.
- `cos_user_check.py latest <thread> [--after ISO]` accepts a message only when its `createdBy` is exactly `"user"`. The Chief of Staff runs it on `approve N` (strict, short words) and on `mark N todo` (whole message) before acting (`chief-of-staff/commands.md` § Commands).
- The server already holds the Chief of Staff thread id (`chiefThreadId` in the state it reads, cleaned by `cleanThreadId` in `api.ts`).

## Finding: who T3 records a send as

Checked on T3 `v0.1.10-nightly.20261114.4695` by reading `t3 --help`, `t3 thread send --help`, `t3 auth --help` and the `orchestration_v2_projection_messages` table of `~/.t3/userdata/statev2.sqlite` (read only). No forged message was sent into any thread.

| Route | `createdBy` | `creationSource` |
|---|---|---|
| Typed in the composer (desktop or browser) | `user` | `web` |
| Typed on the phone | `user` | `mobile` |
| `t3 thread send` (CLI) | `agent` (from the ticket, seen on this machine) | not confirmed |
| T3 MCP `t3_thread_send` | `agent` | `mcp` |
| Delegated-task notices | `agent` | `server` |
| Provider-injected turns | `agent` | `provider` |

There are also two `user`/`server` rows from 2026-10-30 whose route is unknown; the build checks whether a current route still writes them, and the PR reports it.

- `t3 thread send` has no flag or environment variable that changes the author: its only flags are `--base-dir`, `--wait` and `--json`.
- The only routes recorded as `user` are a client typing into the composer, which needs a signed-in client session. `t3 auth session issue` mints a bearer session for a headless client, and `t3 pair` mints a pairing token. Either one lets a program act as a client, but any agent running as the same OS user can run the same commands, so a dashboard that used them would give agents the same route. The bar in the ticket rules this out.
- So nothing the dashboard server can do programmatically is safe to accept as the user's approval, and the check must not change. What remains is a human or human-like action in the T3 window: the user pressing Send, or the dashboard pressing Return for them.
- A known gap, not opened by this ticket and not closed by it: the `createdBy: "user"` rule trusts T3's client path, and an agent that minted a bearer session or ran its own Accessibility script could reach it too. Closing that needs a T3 change (an author T3 sets only from real input, or a signed approval), which is out of scope. The PR names this in its description.

## Design

### 1. Keep the keypress, and confirm the send

- Approve and Mark todo keep opening the link and asking the server to press Return. The Accessibility permission, the frontmost check and the 1.2 s wait stay, because the keypress still needs them.
- The page sends the command with the press: `POST /press-return` with a JSON body `{"command": "approve 402"}`. The server reads at most 256 bytes and accepts only a command that fully matches `approve <digits>` or `mark <digits> todo` (1 to 7 digits). Anything else, or a body that is not that JSON, is `400` and presses nothing. The origin, `Sec-Fetch-Site` and token checks and the 3 second limit come first, as today.
- The command never reaches the press script, which stays fixed text. It is used only as the words on stdin of the read-only check below.
- After the press script returns `sent`, the server runs `cos_user_check.py latest <chiefThreadId> --after <time the request arrived>` with the command as stdin (`execFile` with `python3 -I`, no shell, 2 s timeout per run). It reads `agent-team/scripts/cos_user_check.py` beside the dashboard (the machine install has it at the same relative path). It retries every 300 ms for up to 3 s, because T3 writes the message a moment after the Return.
  - Exit 0: `{ "sent": true }`. The Chief of Staff will accept that message.
  - Still exit 1 after 3 s: `{ "sent": false, "reason": "not-recorded" }`.
  - Exit 2, a timeout or a spawn error: `{ "sent": false, "reason": "unchecked" }`.
  - No usable Chief of Staff thread id in state: `{ "sent": false, "reason": "unchecked" }` (the page has no link to press on then anyway).
- Press script outcomes other than `sent` (`permission`, `not-frontmost`, `no-focus`, `error`, `unsupported`, `busy`) answer as today and skip the check.
- `startServer` gains an injectable `checkSent(thread, command, after)` beside `pressReturn`, so tests run without T3 or Python.

### 2. Page lines

New entries in `PRESS_MESSAGES` (`app.js`), with `<action>` as today:

- `not-recorded`: `<action> not sent: no new message with the command reached the Chief of Staff thread. If it is still in the message box, press Send there.`
- `unchecked`: `<action> may not have sent: the dashboard could not read T3's messages to check. Look in the Chief of Staff thread and press Send if it is still there.`

A send that was confirmed still shows nothing. `pressReturn` in the page sends the command in the body with `Content-Type: application/json`.

### 3. README and tooltips

- `README.md` dashboard bullets: Approve and Mark todo still press Return for you, and the page now checks that T3 recorded the message as yours; when it did not, the error line says so. Add one sentence on why the CLI is not used: T3 records a `t3 thread send` as an agent's message, and the Chief of Staff acts only on yours.
- The Approve and Mark todo `title` text gains "and checks it arrived".

### 4. Tests

- `server.test.ts`: the existing press-guard test sends a valid body; one table-driven test covers the body rule (missing, bad JSON, too long, `approve 402; rm`, `changes 402`, valid `approve 402` and `mark 419 todo`) and one covers the check outcomes (`user` → sent, never `user` → `not-recorded`, check error → `unchecked`, press `no-focus` → no check run).
- `app.test.js`: the `pressMessage` table gains `not-recorded` and `unchecked`.
- `api.test.ts`: no change, since the API shape does not change.
- `test_cos.py` `test_user_check` already has the forgery the acceptance asks for: row `a2` is an agent message with the user's exact words `approve 9`, newer than the user's own, and it is rejected (`not-user agent`); `a5` (full-width digits) and `a6` (a relayed copy) cover look-alikes. No new row; the PR points at them.

## Non-goals

- Sending Approve or Mark todo through `t3 thread send` or `t3_thread_send`.
- Any change to `cos_user_check.py` or to the `createdBy: "user"` rule, including an exception for Mark todo, No Hands or auto-approvals.
- Changes to T3 Code.
- The Changes control, which only fills the composer.
- Closing the bearer-session or Accessibility gap in the `createdBy` rule.

## Calls I made

- Approve keeps the keypress. The ticket's Part 1 (send through the CLI) is not built: a CLI send is recorded as `createdBy: "agent"`, so the Chief of Staff would treat a dashboard Approve as data, and loosening the check is ruled out. This is the ticket's fallback ("keep the keypress for Approve").
- Mark todo keeps the keypress too, instead of moving to the CLI. `mark N todo` also goes through `cos_user_check.py` (whole-message words), and letting the CLI through for it would be an exception to the `createdBy: "user"` rule, which the ticket puts out of scope. A forged `mark N todo` would also start a spec child.
- The fix for the silent failure is a check after the press, using the same `cos_user_check.py latest --after` the Chief of Staff runs, so "sent" on the page means the Chief of Staff will accept it.
- The page now sends the command text to the server, which the press route refused before. It is held to two exact shapes and goes only to a read-only check, never to the press script.
- Timing: 300 ms retries for up to 3 s after the press, 2 s per run. A slow machine may see `not-recorded` for a message that lands later; the line tells the user to look.
- The bearer-session and Accessibility gap in the `createdBy` rule is written down in the spec and the PR but not ticketed here; the Chief of Staff can ticket it.
- The finding was made from help text and the message store, without sending a forged message into a thread.
- No new `cos_user_check.py` test: the existing `a2` row is exactly the forged message the acceptance describes.
