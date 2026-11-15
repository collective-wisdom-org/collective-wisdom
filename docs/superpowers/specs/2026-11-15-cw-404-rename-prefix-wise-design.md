# CW-404: Rename the ticket prefix from CW to WISE

**Status:** Draft
**Ticket:** [#404](https://github.com/collective-wisdom-org/collective-wisdom/issues/404)

## Goal

New tickets in this repo show as `WISE-N` and their branches read `feat/wise-N-...`. Every ticket that already carries `CW-N` (state entries, open PRs and branches, worktrees, spec file names, merged PR titles, release notes) keeps that id and keeps working. This is the ticket's option A, with one addition: a cutover issue number, so every issue number has exactly one id.

## Today

Facts from `main` at `7af781f`, from a full `git grep` of `agent-team/scripts`, `mods/` and `install.sh` (tests excluded).

- The prefix has one source, the `Issue identifier prefix` row of `docs/agents/project.md`, read by `project_config.prefix()`. `ticket_re()` builds the id regex from it alone. `cos_state.ID` and the `TICKET` regexes of `cos_head_check`, `cos_merged_check`, `cos_ready_check` and `cos_review_check` are built once at import; `approval_policy`, `cos_approve_pr`, `cos_child_read`, `cos_handoff` and `cos_worktree_check` call it inline.
- Three Python sites turn an issue number into an id with `f"{prefix()}-{number}"`: `cos_untracked_check.py` (open `agent` issues, and PR branches), `pm_hygiene.py` `ticket_id` and `ticket_of` (branch or `(ABC-N)` title). After a plain row change these would name issue 386 `WISE-386` while state holds `CW-386`, and the untracked check would report it as a new, untracked ticket.
- Branch names come from the id: every site that matches a ticket's branch builds it from `tid.lower()` (`cos_handoff`, `cos_merged_check`, `cos_ready_check`, `agent_usage --ticket`). Those work for any id as long as the id is right.
- The dashboard reads the row itself (`titles.ts` `prefixFromProject`) and uses the one prefix in `merged.ts` (branch and `(PREFIX-N)` title suffix), `api.ts` `ticketOf` (branch) and `cleanTeamSnapshot` (`^PREFIX-N$`), `lists.ts` (saved backlog lists drop ids of another prefix) and `backlog.ts` (`${prefix}-${number}` for each issue). `api.ts` line 109 uses the row only for Linear links.
- The agent-gantt mod has no prefix logic. Its `FILED` regex in `snapshot.ts` takes any `[A-Z][A-Z0-9]*-\d+`. It needs no change.
- `chief_thread_title()` gives `<PREFIX> - Chief of Staff`. `startup.md` § Thread title renames the Chief of Staff thread to it at `start the team`, take over and `resume`. No script matches on the title.
- Literal `CW` in script code (not comments or docstrings): the error text `is not like CW-57` in `agent_usage.py` `ticket_id`, and the user-visible note `priced before the CW-220 rate fix` in `dashboard/page/app.js:635`. Lower-case `cw` appears in the `.cw-install-` temp file prefix in `install.sh` and the `cw-dashboard-collapsed` storage key in `app.js`; both are product short names, not ticket ids. Everything else is comments, docstrings and test fixtures.
- Release notes: merged PR bodies and titles feed `RELEASE_NOTES.md`; the old files under `docs/superpowers/release-notes/cw-N.md` sort by `natural()`, which takes any prefix. Neither builds an id from the prefix.
- Each child reads `project.md` from its own worktree (`app_root.root()` is the worktree top). The Chief of Staff reads the root checkout's. The machine install `~/.collective-wisdom` links to the root checkout's `agent-team/`, so scripts and the root `project.md` change together when `merge_pr.py` fast-forwards the root checkout.

In flight at spec time: #385 (PR #403, `feat/cw-385-clock-stamped-times`), #386 (PR #405, `feat/cw-386-find-merge-after-relay`), #387, #388, #394, #401, #402 (In Progress), and this ticket #404. The highest issue or PR number is 405.

## Design

### The project.md row

A new Identity row after `Issue identifier prefix`:

```
| Retired issue prefixes | `CW<414`. Earlier prefixes and the issue number where each one stopped: issues numbered below 414 keep `CW-N`, later ones use the current prefix. `none` when the prefix never changed |
```

- The value is one backticked token: comma-separated `PREFIX<N` pairs, oldest first, for example `AB<100,CW<414`. Each prefix matches `[A-Z][A-Z0-9]*` and differs from the current prefix and the others; the numbers rise strictly.
- A missing row, `none` or an empty cell means no retired prefixes: every repo that never renamed keeps its behavior.
- A row that is set but does not parse raises `SystemExit` with a `project.md: 'Retired issue prefixes' row ...` message, like `prefix()`. The scripts never guess an id.
- `agent-team/templates/project.md` gets the row with `none`, so `set up this repo` renders it. The template note says the row is for the GitHub tracker, where the id is built from the issue number. On Linear and Jira a key change renames every issue in the tracker, so the row stays `none`.
- The number is one more than the highest issue or PR number on GitHub at the final push before `MERGE READY`: `414`.

`docs/agents/project.md` changes the prefix row to `WISE`, adds the retired row, changes the Branch pattern note to `<prefix>` is `wise`, and changes the Repo invariants bullet to `feat/wise-N-*` or `infra/wise-N-*`, and `feat/cw-N-*` or `infra/cw-N-*` for tickets numbered below the cutover. `CONTRIBUTING.md` line 4 changes the same way.

### project_config.py

- `retired_prefixes(rows=None)`: the parsed pairs as a tuple of `(prefix, below)`, oldest first. Empty when unset.
- `prefixes()`: the current prefix, then the retired ones.
- `ticket_re(anchored=False)`: matches `<P>-\d+` for any `P` in `prefixes()`, as one escaped alternation, longest prefix first, so a prefix that starts another one never wins the match.
- `ticket_id(number)`: the id of issue `number`. The first retired pair whose `below` is greater than `number` gives its prefix; otherwise the current prefix.
- `ticket_number(tid)`: the issue number of an id with any known prefix, or None.
- `branch_ticket_re()`: `<heads>(<lower-case prefixes>)-(\d+)` as a regex, for the scripts that read a ticket from a branch name.
- `chief_thread_title()` stays `f"{prefix()} - Chief of Staff"`: the current prefix.
- The CLI gains `project_config.py prefixes`, printing one line per prefix (current first) with its cutover, for skills that need to read it. Optional for the build; skip it if no skill needs it.

### Scripts that map a number to an id or back

- `cos_untracked_check.py`: `prs_by_ticket` reads branches with `branch_ticket_re()` and names the ticket `ticket_id(number)`; the issue loop uses `ticket_id(issue["number"])`. `known` also counts a ticket whose number is already in state under any prefix, so an issue never shows up twice even if it was started under the other prefix.
- `pm_hygiene.py`: `ticket_id` uses `project_config.ticket_id(number)`; `ticket_of` reads the branch with `branch_ticket_re()` and the title with `ticket_re()`, and returns `ticket_id(number)`.
- `agent_usage.py`: the `ticket_id` error text drops the literal: `is not a ticket id like <PREFIX>-57`, with the current prefix read from `project_config` when it is readable.
- `cos_state.py`, the four `TICKET` checks and the inline `ticket_re` callers need no code change: they pick up both prefixes from `ticket_re()`.

### Dashboard

- `titles.ts`: `prefixFromProject` stays; a new `retiredFromProject(markdown)` parses the same row with the same rules (a row that does not parse gives no retired prefixes and the dashboard reads only the current one, since the dashboard must not crash), and `idForNumber(number, prefix, retired)` mirrors `ticket_id`.
- `merged.ts`: the branch regex and the `(PREFIX-N)` title suffix accept every prefix; the entry id is `idForNumber(n)`.
- `api.ts`: `ticketOf` reads the branch for any prefix and names the ticket `idForNumber(n)`; `cleanTeamSnapshot` keeps a helper's filed ticket when it matches any prefix.
- `lists.ts`: a saved list keeps ids of any known prefix.
- `backlog.ts`: each issue's id is `idForNumber(number)`.
- `server.ts` passes the retired list where it passes the prefix today.

### Chief of Staff thread title and pick-up

- The merge fast-forwards the root checkout, which updates the machine install and the root `project.md` together. The running Chief of Staff's next script call reads `WISE` with `CW<414` retired; its state keys (`CW-N`) still parse.
- The thread title stays `CW - Chief of Staff` until the next `start the team`, take over or `resume`, when § Thread title renames it to `WISE - Chief of Staff`. Nothing matches on the title, so the old title breaks nothing. No new step is added.
- A child branched before the merge reads its own worktree's `project.md` with `CW` and no retired row. It handles only its own `CW-N` ticket, and the newer scripts read that copy correctly (no retired row means none). After it merges or rebases onto `main`, it reads the new rows.
- A child branched after the merge reads `WISE` and the retired row.

### Hardcoded-prefix test

`agent-team/scripts/test_prefix_free.py`, two tests:

1. One table-driven test against a `project.md` fixture with prefix `ZZ` and `Retired issue prefixes` `YY<10`: `ticket_id(5)` is `YY-5`, `ticket_id(10)` is `ZZ-10`, `ticket_re(anchored=True)` matches `YY-5` and `ZZ-10` and not `CW-5`, `ticket_number` round-trips both, `branch_ticket_re()` reads `feat/yy-5-x` and `infra/zz-10-x`, `chief_thread_title()` is `ZZ - Chief of Staff`, and the untracked check run on a fixture state with `YY-5` and an open issue 5 reports nothing. A bad row (`YY<x`, `ZZ<10` naming the current prefix, falling numbers) raises `SystemExit`.
2. A source scan of `agent-team/scripts/**/*.{py,ts,js,sh}`, `mods/**/*.{ts,tsx}` and `install.sh`, test files excluded, that fails on `\bCW\b` or `\bcw-\d` in code. Python is read with `tokenize`, dropping comments and docstrings; TS, JS and shell drop `//`, `/* */` and `#` comments by line. The test lists each hit with file and line.

The dashboard gets one row added to its existing table test in `api.test.ts` (or `merged.test.ts`): a `ZZ` project with `YY<10`, where `feat/yy-5-x` and a title ending `(YY-5)` give `YY-5` and issue 12 gives `ZZ-12`.

### Before and after scan

The PR body lists the result of `git grep -nE 'CW-|cw-|"CW"'` before and after. Left on purpose: spec, plan, as-built and release note file names and text under `docs/superpowers/`, `docs/compatibility.md`, comments and docstrings that cite old tickets, test fixtures, `.cw-install-`, `cw-dashboard-collapsed`, and the `CW<N>` value of the retired row.

## In-flight plan

| Work | What happens |
|---|---|
| Open PRs #403 and #405 on `feat/cw-385-*` and `feat/cw-386-*` | Untouched. Their ids stay `CW-385` and `CW-386` (below the cutover), and the merge and review checks match their branches by `tid.lower()`. |
| `.agent-team/state.json` entries `CW-N` | Untouched. `cos_state.ID` accepts both prefixes, so every key still parses. |
| Worktrees named for `cw-N` | Untouched. The dashboard and `agent_usage` match them by branch, which reads either prefix. |
| Children started before the merge (#385, #386, #387, #388, #394, #401, #402) | Keep their `CW-N` id, branch and spec name. They read `CW` from their own worktree until they rebase, which is correct for their own ticket. |
| Tickets filed before the final push | Numbered below the cutover, so they keep `CW-N`, whatever the Chief of Staff called them. |
| Tickets filed between the final push and the merge | Numbered at or above the cutover, so `WISE-N` after the merge. If the Chief of Staff starts one before the merge under `CW-N`, its state key still parses, the untracked check does not list it twice (it counts known tickets by number), and its branch `feat/cw-N-*` still resolves. Only its display id differs from the new rule. The `MERGE READY` asks for no new ticket to start between it and the merge. |
| `release-notes` branch and `RELEASE_NOTES.md` | Untouched. `merge_pr.py` publishes from PR bodies and titles as written; old notes keep `CW-N`, new ones carry `WISE-N`. |
| This ticket, #404 | Keeps `CW-404`: branch `feat/cw-404-rename-prefix-wise`, this spec's file name, and the PR title. |

The PR body lists the in-flight tickets at merge time and how each was handled, per the ticket's acceptance.

## Testing

- `python3 -I -m pytest -q agent-team/scripts`.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, since the dashboard is touched.
- Existing tests that use `CW-N` fixtures keep passing unchanged. Their fixtures use the repo's own `project.md` or a fixture prefix, and both still accept those ids.

## Non-goals

- Options B (migrate live state) and C (rewrite history).
- Changing issue numbers, the repo, the org, the product name or `~/.collective-wisdom`.
- Rewriting historical prose that names `CW-N`.
- Renaming the running Chief of Staff thread outside its existing start-up step.
- Changing the agent-gantt mod.

## Calls I made

- **A cutover number in the retired row (`CW<414`).** The ticket's option A only lists retired prefixes. Without a number, the three scripts that turn an issue number into an id would name old in-flight issues `WISE-N` and report them as untracked. The cutover gives each issue number one id forever.
- **The cutover is set at the final push, not now.** It is one more than the highest issue or PR number on GitHub then. Tickets filed after that push but before the merge become `WISE-N`.
- **Known tickets count by issue number in the untracked check.** A guard for a ticket started under `CW-N` in the window above, so it is never listed twice.
- **This ticket keeps `CW-404`** for its branch, spec name and PR title, since it is below the cutover.
- **The running Chief of Staff thread keeps its title** until the next start, take over or `resume`. No extra rename step.
- **A bad retired row stops the Python scripts but not the dashboard.** The scripts raise like `prefix()` does; the dashboard falls back to the current prefix only, so a typo cannot crash the page.
- **The retired row is for the GitHub tracker.** The template says Linear and Jira keep it `none`, since a key change there renames every issue.
- **Two literal `CW` strings in code change:** the `agent_usage.py` error text and the dashboard's `CW-220 rate fix` note (to `the token rate fix`).
- **`.cw-install-` and `cw-dashboard-collapsed` stay.** They are short names for the product, not ticket ids, and the source scan does not flag them.
- **The agent-gantt mod is not changed.** The ticket listed it, but it has no prefix logic.
- **The `project_config.py prefixes` CLI is optional** and built only if a skill needs it.
