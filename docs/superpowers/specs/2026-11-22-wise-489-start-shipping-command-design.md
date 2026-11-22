# WISE-489: Make the Start shipping button send "start shipping N"

**Status:** Shipped
**Ticket:** [#489](https://github.com/collective-wisdom-org/collective-wisdom/issues/489)
**Shipped:** in PR #490, as specified

## Goal

The Start shipping button on a Backlog card types `start shipping N` into the Chief of Staff thread instead of `mark N todo`. The Chief of Staff treats `start shipping N` the same as `mark N todo`: it moves the ticket to Todo and refreshes the dashboard. The button's words then match what it does.

## Today

- `agent-team/scripts/dashboard/page/app.js`: `todoCommand(r)` builds `mark 419 todo` from the ticket id. `todoControl` puts it in the link's prompt, its `data-return`, the copy button's `data-copy` and the tooltip. `pressAction(command)` returns `Start shipping` when the command starts with `mark `, else `Approve`.
- `agent-team/scripts/dashboard/server.ts`: `PRESS_COMMAND = /^(approve \d{1,7}|mark \d{1,7} todo)$/` is the only shape `POST /press-return` accepts. The accepted command is the words the server hands `cos_user_check.py latest` to confirm the message was sent.
- `agent-team/.claude/skills/chief-of-staff/commands.md`: the row `mark N todo`, `move N to backlog`, or any other request to set a ticket to Todo or Backlog runs `set-state`, then the dashboard refresh. § Commands lists the commands that get the strict short-words user check; `mark N todo` is not on it, so it gets the whole-message check.
- `cos_user_check.py` has no list of commands. Both checks look for negation around the words; the strict check gives only the short words, so "don't start shipping 419 yet" is negated, while a whole-message check matches the whole message and ignores its own negation.

## Change

1. `app.js`
   - `todoCommand` returns `start shipping 419` for `WISE-419`, `start shipping 7` for `CW-7`, null for an id with no trailing number. Update its doc comment.
   - `pressAction` returns `Start shipping` for a command starting `start shipping `, else `Approve`. Update its doc comment.
   - `todoControl` needs no code change; the tooltip, prompt and copy text follow `todoCommand`.
2. `server.ts`: `PRESS_COMMAND = /^(approve \d{1,7}|start shipping \d{1,7})$/`. `mark N todo` is no longer accepted. Update the `pressCommand` doc comment.
3. `commands.md`
   - The Todo/Backlog row starts `` `start shipping N`, `mark N todo`, `move N to backlog`, or any other request ... ``, with the same effect as today.
   - § Commands user check: add `start shipping N` to the strict short-words list (and to the matching list in the exit 2 fallback sentence), because it starts work like `approve N`.
4. `ticket-helper.md` keeps pointing at "the `mark N todo` row": the row keeps that phrase, so the name still finds it.
5. Tests:
   - `page/app.test.js`: the `todoCommand` rows expect `start shipping N`; the `pressAction` row uses `start shipping 419`.
   - `server.test.ts`: the press-body table accepts `start shipping 419` and rejects `mark 419 todo`, `start shipping`, `start shipping 5; rm` and `start shipping 12345678`.
   - `cos_user_check.py` tests: add one row to the existing negation table that `start shipping 419` as the words in "don't start shipping 419 yet" prints `not-user negated`, only if the table has no equivalent case already. No code change to the script unless that row fails.
6. `README.md` § Local dashboard: the press commands line (`approve 402` or `start shipping 419`) and the Backlog bullet (`start shipping 419` typed in).

The press error lines still start `Start shipping not sent` or `Start shipping may not have sent`, since `pressAction` still names the action `Start shipping`.

## Leaves out

- The button label, which stays `Start shipping`.
- What moving a ticket to Todo does.
- Older specs and plans that name `mark N todo`; they record what shipped.

## Overlap with WISE-488

WISE-488 (shrinks the skills and role docs, including `commands.md`) is open and in progress. The ticket says to merge 488 first and rebase this onto the shortened `commands.md`. The build rebases onto `origin/main` before the `commands.md` edit and again before opening the PR. If 488 has not merged when the PR is otherwise ready, I report `MERGE READY` anyway and say in it that 488 should merge first; the Chief of Staff orders the merges.

## Calls I made

- **`mark N todo` stays a Chief of Staff command but is no longer a press command.** The ticket asks the server to reject it. Someone typing `mark 419 todo` by hand still gets the ticket moved; only the dashboard's one-click press stops accepting it. A dashboard page loaded before the update would send `mark N todo` and get a refused press until reload; the page reloads itself on a new server version, so this is brief.
- **`start shipping N` gets the strict check; `mark N todo` keeps the whole-message check.** The ticket names only the new command for the strict list. Leaving `mark N todo` alone keeps this change to the one row and avoids touching 488's command list more than needed.
- **The row keeps the literal phrase `mark N todo`**, so `ticket-helper.md`'s pointer stays valid without an edit.
- **Not waiting for WISE-488 before building.** The edit to `commands.md` is two small inserts, so a rebase after 488 merges is cheap; waiting would stall the ticket for no gain.
- **No new test for `cos_user_check.py` unless its negation table lacks a short-words case.** The script has no command list, so the new words need no code, and an extra row would only restate an existing rule.
