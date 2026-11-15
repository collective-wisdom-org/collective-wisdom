# WISE-445: Say on the dashboard Approve and Changes links when the Approve press works

**Status:** Shipped
**Shipped:** in PR #448, as specified
**Ticket:** [#445](https://github.com/collective-wisdom-org/collective-wisdom/issues/445)

## Goal

Dashboard Approve sends only under two conditions the page never states. David tested WISE-423 and it worked only when the dashboard was open in an external browser (not T3's browser pane) and the T3 message box already had keyboard focus. Say both on the Approve and Changes hover text and in the README, and make the failure lines say what to try before pressing Send by hand. No behaviour changes: the press, its checks and its reasons stay as they are.

## Today

From main at `1f4aca7`:

- `approveControls(r, chiefLink)` in `agent-team/scripts/dashboard/page/app.js` builds the `title` of each control. Approve with a thread link: `Opens the Chief of Staff thread with "approve N" typed in and presses Send for you. If it can't, press Send.` Changes: `Opens the Chief of Staff thread with "changes N: " typed in. Add what to change, then press Send.`
- `PRESS_MESSAGES` has `not-frontmost` (`Approve not sent: T3 Code was not in front. Press Send in the Chief of Staff thread.`) and `permission`. `pressMessage` adds `busy` and a generic `Approve not sent: the dashboard could not press Return. Press Send in the Chief of Staff thread.`
- A Return that lands on something other than the message box comes back `sent`, so the page shows nothing. Detecting that is WISE-434's job, not this ticket's.
- `README.md` § Local dashboard (the long paragraph under `start the team`) names the Accessibility and Automation permissions and the frontmost check, and nothing about the browser or the focused message box.
- `app.test.js`: the Approve and Changes case builds each expected link with `prompt(t, tip, ret)`; the `pressMessage` table checks each line.

## Design

### Hover text

One constant in `app.js` holds the shared condition, so it is one edit to drop when David's T3 change ships:

```js
/** Approve's press works only in these conditions today (WISE-445). Drop this when T3 focuses the message box itself. */
const PRESS_TIP = 'Works best with the dashboard open in an external browser (not T3\'s browser pane) and the T3 message box clicked first.'
```

- Approve (thread link): `Opens the Chief of Staff thread with "approve N" typed in and presses Send for you. If it can't, press Send. Works best with the dashboard open in an external browser (not T3's browser pane) and the T3 message box clicked first.`
- Changes (thread link): `Opens the Chief of Staff thread with "changes N: " typed in. Add what to change, then press Send. Opens most reliably from the dashboard in an external browser (not T3's browser pane).` The message-box half does not apply: Changes presses nothing, and the user clicks the box to type anyway.
- The copy buttons (no thread link) keep no title, as today.

### Failure lines

- `not-frontmost`: `Approve not sent: T3 Code was not in front. Open the dashboard in an external browser (not T3's browser pane), click the T3 message box, then try Approve again, or press Send in the Chief of Staff thread.`
- Generic (any other reason, or a failed request): `Approve not sent: the dashboard could not press Return. Press Send in the Chief of Staff thread yourself.`
- `permission` and `busy` keep their lines. No new `reason`.

### README

In `README.md` § Local dashboard, right after the Accessibility and Automation sentence, one sentence:

`Approve works best with the dashboard open in an external browser rather than the T3 browser pane, and with the T3 message box clicked first; otherwise the Return can land somewhere else and the draft waits for you to press Send.`

## Test

Per `AGENTS.md` § Testing, by updating the two tables that exist:

- `app.test.js`, Approve and Changes case: the `tip` argument for Approve and Changes gains the new sentences, so the test fails if either title drops a condition.
- `app.test.js`, `pressMessage` table: the `not-frontmost` and generic rows take the new text.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts` pass.

No real run beyond a hover check: the text is static, and the conditions themselves come from David's report.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | `PRESS_TIP`, Approve and Changes titles, `not-frontmost` and generic lines. |
| `agent-team/scripts/dashboard/page/app.test.js` | The two tables above. |
| `README.md` | One sentence in § Local dashboard. |

## Builds

- The Approve hover text says the press works best from an external browser with the T3 message box clicked first.
- The Changes hover text says the link opens most reliably from an external browser.
- The `not-frontmost` red line says what to try, then to press Send; the generic line says to press Send yourself.
- One README sentence with the same two conditions.

## Leaves out

- Focusing the message box, or detecting a Return that landed nowhere (WISE-434).
- Any change to `cos_user_check.py`, the approval check, or how a message is marked as the user's.
- Sending through `t3 thread send` or any CLI.
- Changes to T3 Code itself (David's change).
- Changing where `start the team` opens the dashboard (still the T3 browser pane).

## Calls I made

- **`start the team` still opens the dashboard in the T3 browser pane**, though Approve works best outside it. The ticket doesn't ask to move it, and the pane still works for reading and for Changes. The README sentence says to open it in an external browser for Approve.
- **Changes gets only the external-browser half.** The ticket says to add the conditions "where they apply". Changes presses nothing, so the message-box condition doesn't apply. Whether opening a `t3code://` link fails from the pane wasn't checked, so the Changes text says "most reliably" rather than "only".
- **"T3 message box", not "text box".** WISE-434's spec calls the composer the T3 message box, so the two tickets' lines read the same.
- **The generic line gets no tips.** It covers osascript errors and failed requests, where the browser and message box don't help; it only adds "yourself".
- **One `PRESS_TIP` constant** for the Approve sentence, so trimming it after David's T3 change is one edit. The Changes sentence and the two failure lines are separate strings to keep each reading naturally; they still need their own edits then.
- **WISE-434 overlap.** WISE-434 adds a `no-focus` line to `PRESS_MESSAGES` next to the `not-frontmost` line this ticket edits. Whichever merges second resolves a small conflict there; neither changes the other's meaning.
- **The PR says the text assumes the behaviour David reported** (external browser, focused message box) and was not reproduced from T3's source.

## Touches

None of these (no data, money, auth, user email or migrations).
