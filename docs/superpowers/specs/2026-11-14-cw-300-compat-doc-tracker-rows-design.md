# CW-300: Add tracker support for the Todo and Backlog list and the ticket helper gantt to the compatibility doc

**Status:** Shipped
**Shipped:** in PR #301, as specified
**Ticket:** [#300](https://github.com/collective-wisdom-org/collective-wisdom/issues/300)
**Related:** [#298](https://github.com/collective-wisdom-org/collective-wisdom/issues/298), [#299](https://github.com/collective-wisdom-org/collective-wisdom/issues/299)

## Goal

Matrix 2 (trackers) in `docs/compatibility.md` says, per tracker, whether the dashboard's Todo and Backlog list works and whether a ticket helper's session reaches the ticket it filed in the gantt. Each cell that is not `works` points at a gap with its ticket.

## Today

Facts from `main` at `0a6c545`.

- Matrix 1 has a `Ticket helper in the gantt` row (CW-290). Its note under Matrix 1 holds the only tracker limit: "A session joins a ticket's gantt only when that ticket has a row on the board; a just-filed ticket gets its row from the Not started band, which reads GitHub Issues only, so on Linear or Jira the session reaches the ticket's chart once the ticket is in state. Spend does not depend on the board."
- Matrix 2 has no row for either feature. G15 covers the dashboard's issue links, titles and update order, not the Todo and Backlog list.
- `agent-team/scripts/dashboard/backlog.ts` reads open issues with `gh issue list`, and `server.ts` gives it a config only when the `Tracker` row is `github` (`repo.isGithubIssues`). On Linear and Jira the list is empty.
- `agent-team/scripts/dashboard/api.ts` `buildApi` adds a helper session to a ticket's gantt only through `addHelper`, which skips a ticket with no board row (`rowById`). Board rows come from state, the merged list (read from GitHub PRs, so on every tracker) and the Todo and Backlog list (GitHub only). `ledgerSessions` puts the helper in the ticket's spend whether or not it has a row.
- Jira is untested everywhere (G12). Azure DevOps has no adapter (G19).
- G21 is the last gap number in use, so G22 and G23 are free.

## Design

Docs only: `docs/compatibility.md`.

1. **Two new Matrix 2 rows**, after `Dashboard issue links, titles and update order`:

   | Feature | GitHub Issues | Linear | Jira | Azure DevOps (ADO) |
   |---|---|---|---|---|
   | Dashboard Todo and Backlog list | 🟢 works | 🔴 not supported: GitHub only (G22) | 🔴 not supported: GitHub only (G22) | 🔴 not supported: no adapter in `trackers/` (G19) |
   | Ticket helper in the gantt | 🟢 works | 🟡 partial: spend and history attach, the session shows on the ticket's chart only once the ticket is in state (G23) | 🟡 partial: as Linear (G23); untested (G12) | 🔴 not supported: no adapter in `trackers/` (G19) |

2. **New gaps**, after G21:
   - **G22.** The dashboard's Todo and Backlog list reads GitHub Issues only (`backlog.ts` calls `gh issue list`, and `server.ts` configures it only for a `github` tracker), so on Linear and Jira it is empty. Ticket: [#298](https://github.com/collective-wisdom-org/collective-wisdom/issues/298).
   - **G23.** A ticket helper's session joins a ticket's gantt only when the ticket has a board row. A just-filed ticket gets its row from the Todo and Backlog list, which is GitHub only (G22), so on Linear and Jira the session shows on the ticket's chart once the ticket is in state. Spend does not depend on the board. Ticket: [#299](https://github.com/collective-wisdom-org/collective-wisdom/issues/299).
3. **Move the tracker note.** The Matrix 1 note for `Ticket helper in the gantt` loses the two board sentences and gets a pointer instead: "On Linear and Jira the session reaches the ticket's chart late; see Matrix 2 (G23)." Matrix 2's notes get a line for the helper row carrying the moved sentences, with the plugin version left in the Matrix 1 note.
4. **Full compatibility, Matrix 2:**
   - Linear: done when the dashboard reads Linear tickets as it reads GitHub issues, including the Todo and Backlog list and the helper's chart, and the untracked check does too, and `trackers/linear.md` carries a verification line.
   - Jira: the same dashboard clause is added beside the checklist and `pm_hygiene.py`.
   - GitHub Issues: "Every row works" stays true; the sentence on which reads only GitHub supports names the Todo and Backlog list too.
5. **Last checked** line: dated the build day, naming CW-300.

## Leaves out

- Building the Linear and Jira reads (#298, #299). Those PRs update their own cells when they ship.
- The harness matrix (Matrix 1), apart from the moved note and its pointer.
- G21's state after CW-288 merged; that cell is not this ticket's.
- The Todo and Backlog list cell CW-298 edits: this PR adds the row and gap, and CW-298's PR changes its Linear and Jira cells and gap when it ships. Whichever merges second rebases onto the other.

## Calls I made

- The Jira helper cell is `partial`, not `untested`, with G12 named beside G23: the board rule is in the dashboard code and does not depend on the adapter, so the part that does not work is known; the adapter itself is untested.
- Azure DevOps cells point at G19 (no adapter), not at G22 or G23, as every other ADO cell does.
- The Matrix 2 helper note keeps the board explanation and drops the plugin version, which is a harness fact and stays in Matrix 1.
- The gap wording says "once the ticket is in state", as the current note does, though a ticket whose PR merged also gets a row from the merged list. That case is after the helper's work matters, so the doc does not name it.
- G15 is left as is; the new list gets its own gap, because it has its own ticket (#298).

## Acceptance

- Matrix 2 shows both rows; each cell that is not `works` has a gap number; G22 and G23 each carry a ticket link.
- Every claim matches `main` at the build.
- The doc follows its own "Keeping it current" section.
- No code changes. `python3 -I -m pytest -q agent-team/scripts` passes.
