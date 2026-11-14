# CW-306: Allow infra/ branches for ticket work

**Status:** Draft
**Ticket:** [#306](https://github.com/collective-wisdom-org/collective-wisdom/issues/306)

## Goal

A ticket's branch may be `infra/<prefix>-N-short-title` as well as `feat/<prefix>-N-short-title`. The Chief of Staff checks, the cost line and the dashboard treat both the same, and a child told to use `infra/` can create and push it.

## Today

Facts from `main` at `e6cb50b`.

- `project_config.branch_head()` returns the text before `<prefix>` in the first backticked token of the Branch pattern row, else `FALLBACK_BRANCH_HEAD = "feat/"`.
- This repo's row is `` `feat/cw-N-short-title` ``. It has no `<prefix>`, so the scripts here already read it as the fallback `feat/`.
- Callers of `branch_head()`: `cos_handoff.branch_re()` (used by `cos_worktree_check.py`), `cos_merged_check.py:115`, `cos_ready_check.branch_prefix()` (open PR match at `:161`, spec refs at `:126` and `:184`), `cos_untracked_check.prs_by_ticket()`, and the merge target refusal in `project_config.py:216`.
- Hardcoded `feat/`: `agent_usage.py:303` (Cursor `Branch:` line), `:416` and `:417` (`own` and `mine` in `ticket_line()`), `cos_brief.py:38` (`BRANCH_RE`), `dashboard/api.ts:179` (`ticketOf`) and `dashboard/merged.ts:23` (`byBranch`).
- The dashboard reads the prefix from the project.md text with `prefixFromProject` in `dashboard/titles.ts`.
- Prose that names `feat/` for a ticket branch: `ship-loop/SKILL.md:46` and `:201`, `kickoff-feature/SKILL.md:23` and `:30`, `build-from-plan/SKILL.md:46`, `chief-of-staff/SKILL.md:457`, `:458` and `:468`, `chief-of-staff/state-keys.md:21`, `docs/agents/org-chart.md:103`, `agent-team/templates/project.md:35` and `:70`, and this repo's `docs/agents/project.md:30` and `:56`.

## Design

1. **Row syntax.** The Branch pattern row may list several heads in braces: `` `{feat,infra}/<prefix>-N-short-title` ``. A plain head (`feat/<prefix>-...`, `work/<prefix>-...`) still means that one head, and a row with no `<prefix>` or no row still means `feat/`. So an app's `project.md` keeps working with no edit, and gets `infra/` only when its row lists it.
2. **`project_config.branch_heads(rows=None)`** returns the heads as a tuple, in row order: `{a,b}/` gives `("a/", "b/")`. Each name must be `[a-z0-9-]+`; a brace list that doesn't parse falls back to `("feat/",)`. `branch_head()` stays and returns the first head, the one a new branch uses by default. `FALLBACK_BRANCH_HEAD` stays.
3. **Python scripts** match any head:
   - `cos_handoff.branch_re(tid)`: an alternation of the escaped heads, then `<tid lower>-[a-z0-9-]+`. `cos_worktree_check.py` gets it through `branch_re`.
   - `cos_merged_check.py`: `startswith` any `head + tid.lower() + "-"`.
   - `cos_ready_check.py`: `branch_prefix(tid)` becomes `branch_prefixes(tid)`, one per head. The open PR match accepts any of them. The spec ref lookup calls `matching-refs` once per head and joins the results; the fixture path stays one list per ticket.
   - `cos_untracked_check.prs_by_ticket()`: the escaped heads in an alternation.
   - `project_config.py:216`: a merge target that starts with any head is refused.
   - `agent_usage.py`: the `Branch:` regex, `own` and `mine` use the heads from `project_config.branch_heads()`, escaped. The `[-"]` and `(-.*)?` tails stay, so `infra/cw-1-x` never counts for CW-11.
   - `cos_brief.py` `BRANCH_RE`: built from the heads.
4. **Dashboard.** `titles.ts` gets `headsFromProject(markdown)`, which parses the Branch pattern row the same way as step 2 and returns `['feat/']` when it can't. `server.ts` passes the heads next to the prefix. `api.ts` `ticketOf` and `merged.ts` `byBranch` build their regex from the escaped heads. With no project text the heads are `['feat/']`.
5. **Prose.** The skills and role docs say a ticket branch is `<head><prefix>-N-short-title`, where `<head>` is one of the heads in the Branch pattern row, `feat/` unless the task names another:
   - `ship-loop` `:46` and `:201`, `kickoff-feature` `:23` and `:30`: the `git switch` and `git worktree add` lines use `<head>`, with one sentence saying what `<head>` is.
   - `build-from-plan:46`: "Push only this ticket's own branch (the one the task names)."
   - `chief-of-staff/SKILL.md` child template: `Branch:` uses the first head unless the user or ticket asked for another; the "push only your" rule reads `push only your <head><prefix>-<N>-* branch` with the same head as the `Branch:` line.
   - `state-keys.md:21` keeps its `feat/` example and adds that `infra/` is allowed when the row lists it.
   - `org-chart.md:103`: "on its own ticket branch".
   - `templates/project.md:35`: `` `{feat,infra}/<prefix>-N-short-title` `` with a note that heads are in braces and the first is the default; `:70` says "push only the ticket's own branch (a head from the Branch pattern row)".
6. **This repo's `project.md`**: the Branch pattern row becomes `` `{feat,infra}/<prefix>-N-short-title` `` (`<prefix>` is `cw`, the issue prefix in lower case), and the invariant at `:56` says "push only the ticket's own `feat/cw-N-*` or `infra/cw-N-*` branch".
7. **Tests**, table-driven, each with an `infra/` row:
   - `branch_heads` parsing: plain head, brace list, no `<prefix>`, missing row, a bad brace list.
   - Ticket branch match across `branch_re`, `cos_merged_check`, `cos_ready_check` and `cos_untracked_check`: `feat/cw-1-x` and `infra/cw-1-x` match CW-1, `infra/cw-1-x` does not match CW-11, `fix/cw-1-x` does not match.
   - Merge target refusal: `infra/cw-1-x` is refused when the row lists `infra`.
   - Dashboard: one `infra/` case in the existing `api.test.ts` and `merged.test.ts` tables, and a `headsFromProject` table.

## Leaves out

- Other heads (`fix/`, `docs/`) in this repo's row, and picking the head from the ticket's type label.
- Commit types.
- Rewriting old specs and plans that say `feat/`.
- `pm_hygiene.py`, which already finds the ticket anywhere in the branch name.

## Calls I made

- The heads are listed in braces in the one Branch pattern row, `{feat,infra}/...`, not as a second row or a hardcoded `infra/`. An app gets `infra/` only after its row lists it; the template lists it for new apps.
- This repo's row gains `<prefix>`, which it lacks today. Without it the scripts can't read the row and fall back to `feat/` only.
- The first head in the row is the default for a new branch. The Chief of Staff uses it unless the user or the ticket asks for another head.
- The brace names allow `[a-z0-9-]+`, so the parser accepts heads beyond `feat` and `infra`; this repo just doesn't list any.
- `cos_ready_check` makes one `matching-refs` call per head, since the API takes one prefix.
- `agent_usage.py` and `cos_brief.py` start reading the Branch pattern row; today they don't read it at all.
- `docs/agents/project.md` is on the approval path, so this ticket can't take an auto-approval. Tolerance is `strict` here, so that changes nothing today.
