# WISE-421: Send the prefilled command automatically when Approve is clicked on the dashboard

**Status:** Draft
**Ticket:** [#421](https://github.com/collective-wisdom-org/collective-wisdom/issues/421)

## Goal

The ticket asks for one click on Approve to send `approve N` to the Chief of Staff thread, with no Enter. It also says: find out whether T3 Code's `t3code://threads/...` link can send. If it can't, say so, pick the nearest option that works, and tell the user before building anything that goes around T3.

Short answer: **T3 Code's link can't send.** This spec reports that, builds only the small change that stays inside T3, and leaves the choice of going around T3 to the user (§ Options).

## Today

Facts from main at `6c0a09c`, `agent-team/scripts/dashboard/page/app.js`:

- `approveCommand(r, kind)` gives `approve N` or `changes N: ` for an `awaiting-merge` or `awaiting-build` card.
- `promptLink(chiefLink, text)` turns `<t3-thread://v2/ENV/THREAD>` into `t3code://threads/ENV/THREAD?prompt=TEXT`.
- `approveControls(r, chiefLink)` draws `<a class="approve" href="t3code://...">` with a thread link, else `<button class="approve" data-copy="...">`.

## What T3 Code supports

Checked by unpacking the installed app, T3 Code (Beta) `0.1.7` (the only T3 install on this machine today), `Contents/Resources/app.asar`:

- The desktop app maps `t3code://threads/<env>/<thread>?<query>` to the route `/<env>/<thread>?<query>` (`tW()` in the web bundle). The only other `t3code://` hosts are `new`, `pair` and `auth`.
- The thread route reads one query parameter, `prompt`. If present, it checks the text (8000 characters at most, hidden-character check), writes it into that thread's composer draft, and strips `prompt` from the URL. Nothing else is read: no `send`, `submit` or `auto` flag.
- The link-opening screen says so in its own copy: "Open this prompt. It opens as a draft. Nothing runs until you press Send."

So the draft is a deliberate T3 safety rule (a link from anywhere must not run a prompt), not a missing feature we can switch on. No link we can build sends the message.

## Options

1. **Stay inside T3 (this spec builds this).** Keep the draft link, and make the button say what it does: its tooltip reads `Opens the Chief of Staff thread with "approve N" typed in. Press Send to approve.` The acceptance ("no Enter needed") is not met; the PR says so.
2. **Go around T3 (not built; the user's call).** The dashboard server would post `approve N` into the Chief of Staff thread itself, through T3's server API or the T3 tools. This collides with the approval gate: `cos_user_check.py` accepts an approval only when the message's `createdBy` is `"user"`, which is the proof that the user typed it. A message the dashboard posts either is not `createdBy: "user"` (so the Chief of Staff rejects it, and the button does nothing useful) or is made to look like one (so the proof no longer means anything, and any page that can reach the local dashboard port could approve a merge). Either way it changes how approvals work, which needs its own ticket and the user's say, and it would put the dashboard on the approval path.
3. **Ask T3 Code for a send flag.** A request upstream to `pingdotgg/t3code`. Outside this repo; mentioned so the user can choose it.

## Design (option 1)

`approveControls()` gives each `t3code://` link a `title`:

- Approve: `Opens the Chief of Staff thread with "approve N" typed in. Press Send to approve.`
- Changes: `Opens the Chief of Staff thread with "changes N: " typed in. Add what to change, then press Send.`

`N` is the number from `approveCommand()`. The title goes through `esc()` like the href. The copy button (no thread link) keeps its label and `Copied` feedback, with no title change. `promptLink()` is unchanged; its doc comment gains one line naming the T3 check above (no send parameter as of T3 Code 0.1.7).

## Test

In `page/app.test.js`, the existing approve-controls table gains the expected `title` per kind for the link case, and asserts no `title` on the copy button. `promptLink()` behavior does not change, so its test stays as is.

`node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | `title` on the Approve and Changes links; one line in the `promptLink()` doc comment. |
| `agent-team/scripts/dashboard/page/app.test.js` | Title rows in the approve-controls test. |

## Non-goals

- Posting any message from the dashboard or its server (option 2).
- Any change to `cos_user_check.py`, the `createdBy: "user"` check or other approval gates.
- Changing the commands, or the copy-button fallback.

## Calls I made

- **I don't meet the acceptance.** T3 has no way to send from a link, and the only other route goes around T3 and around the approval proof, which the ticket says to bring to the user first. If you want option 2, it needs its own ticket that changes how approvals are checked.
- **The nearest working option is a clearer button, not a new mechanism.** One click still opens the thread with the command typed; the tooltip now says Send is still needed, so the click isn't a surprise.
- **Changes gets the same tooltip treatment,** worded for typing the change. Same code path, no extra work, which the ticket allows.
- **I checked only T3 Code (Beta) 0.1.7,** the one T3 install on this machine now. A later T3 release could add a send flag; the PR records the version checked.
- **No upstream T3 request is filed by this ticket.** It's listed as option 3 for you to decide.
