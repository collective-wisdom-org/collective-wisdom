# WISE-440: Bring the compatibility doc up to date with main and add the rows it is missing

**Status:** Shipped
**Ticket:** [#440](https://github.com/collective-wisdom-org/collective-wisdom/issues/440)
**Shipped:** in PR #447, as specified
**Related:** [#441](https://github.com/collective-wisdom-org/collective-wisdom/issues/441), [#442](https://github.com/collective-wisdom-org/collective-wisdom/issues/442), [#443](https://github.com/collective-wisdom-org/collective-wisdom/issues/443), [#342](https://github.com/collective-wisdom-org/collective-wisdom/issues/342), [#343](https://github.com/collective-wisdom-org/collective-wisdom/issues/343)

Written after the fact: the sweep was a hand run asked for by the user, and this spec records what it changed and why.

## Goal

`docs/compatibility.md` matches `main`. Every cell, note and gap says what the code does today, every feature whose answer differs by harness or by tracker has a row, and every open Cursor gap names the ticket that closes it.

## Today

Facts from `main` at `3157d1e`, read again at `5e0d044` after four more merges.

- The doc was last edited by CW-341 (#361) on 2026-11-14. 36 PRs merged after it without touching it.
- Cells that no longer match the code: the Cursor cells of Ticket helper in the gantt (CW-288 made the hook write `ticket` and `request`, and G21 still said it did not), Ship loop child threads (since CW-280 a Cursor Chief of Staff starts Cursor children, so the 2026-11-09 run with Claude Code children no longer backs the cell) and Context reset (CW-341 reads the size, CW-353 makes the hook send back an unfinished take over). In Matrix 2, the dashboard links row and G15 (CW-334 built Linear and Jira links) and the Todo and Backlog list row and G22 (CW-347, CW-355 and WISE-431 added save points).
- Gaps resolved by merged work but still listed as open: G20 (CW-276), G21 (CW-288), G27 (CW-328). G23 was deleted by CW-299 with no line saying so.
- Ticket lines that pointed nowhere: G1, G3 and G9 named "the follow-up for the Cursor trial run", which was never filed. G28 said `none yet` although #342 and #343 exist.
- Features with no row: model routing per harness (CW-280), the No Hands run (a note only), the background waits (CI wait, merge wait from CW-386, run wait from CW-406), the Chief of Staff thread title (CW-380, unchecked on Cursor), the dashboard ticket owner (WISE-424, WISE-428), the Mark todo button (WISE-419), the `Retired issue prefixes` row (CW-404, GitHub only) and the untrusted author check (GitHub adapter only).
- No test reads the doc. The documenter's living docs list in `docs/agents/project.md` § Docs check does not name it, which is how it fell behind.

## Design

Docs only: `docs/compatibility.md`.

1. **Matrix 1 (harnesses).** New rows: Model routing, Background waits, Chief of Staff thread title, No Hands run. Changed cells: the Cursor cells of Ship loop child threads (`partial` to `untested`), Context reset and Ticket helper in the gantt; the Codex and Antigravity Chief of Staff thread cells (they start no child or helper); the Codex Security review cell.
2. **Matrix 2 (trackers).** The row "Dashboard issue links, titles and update order" splits into "Dashboard ticket and backlog links" and "Dashboard title refresh and update order". New rows: Untrusted author check on tickets, Ticket prefix rename, Dashboard ticket owner, Dashboard Mark todo button. Changed cells: the Jira Chief of Staff and ship loop cell (G13) and the Linear Todo and Backlog list cell.
3. **Gaps.** G20, G21, G23 and G27 become resolved lines. G2, G13, G14, G15 and G22 are rewritten to match the code. New gaps G31 to G37, one per new non-`works` reason. Ticket lines: #441 on G1, G3, G4, G9, G31 and G32; #442 on G8 and G9; #443 on G33; #342 and #343 on G28, G29 and G30.
4. **Notes and Full compatibility lines** follow the cells. The Cursor line lists the five tickets that cover it.
5. **Keeping it current** gains one sentence: a PR that ships a feature whose answer differs by harness or by tracker adds its row in the same PR.

## Calls I made (surprising first)

- **The Cursor Ship loop child threads cell goes from `partial` to `untested`.** It was `partial` because a Cursor Chief of Staff drove Claude Code children to merge. The skills no longer allow that (CW-280), so nothing shows a Cursor child either way.
- **The untrusted author check is `not supported` on Linear and Jira.** Neither adapter has an author rule. The gate there is membership of the workspace or project, and the cell and G37 say so.
- **Two `works` cells rest on code alone, and a note says so:** the Claude Code No Hands cell (no run is recorded, and No Hands is off in this repo) and the Linear Mark todo cell.
- **The one-click send of Approve and Mark todo is a note and a gap (G34), not a row.** It depends on macOS and T3 Code, and the matrices have no operating system column.
- **Mark todo is a row in Matrix 2 only.** The button itself is the same on every harness; what differs is the tracker write behind `mark N todo`.
- **G25, G29 and G30 keep `none yet` for a Claude Code repeat run.** #342 covers the Cursor side only.

## Leaves out

- Code and skill changes. The stale pointer "follow-up check 3" in `chief-of-staff/models.md` § Cursor stays; #441 rewrites that paragraph.
- Adding `docs/compatibility.md` to the documenter's living docs list.
- A new recorded run on any harness or tracker.
- Tickets for the Codex, Antigravity, Linear, Jira and Azure DevOps gaps.
