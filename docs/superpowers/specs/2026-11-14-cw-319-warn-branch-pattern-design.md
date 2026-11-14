# CW-319: Warn when the Branch pattern row does not parse

**Status:** Proposed
**Ticket:** [#319](https://github.com/collective-wisdom-org/collective-wisdom/issues/319)

## Goal

A `Branch pattern` row that the scripts can't read says so, both when a script falls back to `feat/` and in `setup_repo.py status`, so a repo with a prose row finds out at setup instead of from a later `reject: branch`.

## Today

Facts from `main` at `bb4bd36`.

- `project_config.branch_heads(rows=None)` (`agent-team/scripts/project_config.py:92`) reads the row with `value()`, the first backticked token. It returns the brace heads, a plain head, or `(FALLBACK_BRANCH_HEAD,)` = `("feat/",)` with no message when the token has no `<prefix>`, the brace list doesn't parse, the cell has no backticks, or the row is missing.
- A prose row such as `feat or infra branches named after the ticket` has no backticks, so `value()` returns `None` and the scripts read `feat/`.
- `setup_repo.py status` prints line 1 as `missing`, `set` or `placeholders: <rows>` from `unset_rows()`. `unset_rows()` checks only the `REQUIRED` rows (Tracker, Tracker scope, Issue identifier prefix, Repo, Test) and Linear team name. Branch pattern can't join `REQUIRED`: its template value holds `<prefix>`, which `_ph()` reads as a placeholder.
- `chief-of-staff/startup.md` step 0 sends `missing` and `placeholders: ...` to `setup.md` and carries on only on `set`. In `setup.md`, `write` runs `repair()` when `unset_rows()` is not empty. `repair()` takes the template's row only for rows that still hold a placeholder, so today it would leave a prose Branch pattern row as it is.

## Design

1. **`project_config.branch_pattern_error(rows=None)`** returns `None` when the row is fine and a one-line message when it is not. "Not fine" means the row is present, its cell is not empty and does not start with `TODO(` (the `setting()` rule, so a bare cell counts as present), and the heads `branch_heads()` would parse from it are the fallback because nothing parsed. A missing, empty or TODO row returns `None`: that is the default `feat/`, as meant. The message names the row and the accepted forms:

   `project.md: the Branch pattern row does not parse (<cell>), so the scripts use feat/. Write it as {feat,infra}/<prefix>-N-short-title, or a plain head such as work/<prefix>-N-short-title.`

   The parse rules themselves don't change. The parse moves into a small helper that returns `None` when nothing parsed, and `branch_heads()` and `branch_pattern_error()` both call it.
2. **Warning.** `branch_heads()` prints the message to stderr once per process (a module flag) when it falls back because of a bad row. It still returns `("feat/",)`. No exit code changes. `branch_head()` and `branch_heads_re()` go through `branch_heads()`, so every caller warns.
3. **`setup_repo.py status`.** `unset_rows()` appends `Branch pattern` when `branch_pattern_error(rows)` is set, so line 1 reads `placeholders: ..., Branch pattern` (or `placeholders: Branch pattern`). A valid or missing row leaves line 1 as it is today. Status uses `branch_pattern_error`, not `branch_heads`, so it doesn't also print the stderr warning.
4. **Re-setup fixes it.** Because the row now shows in `placeholders`, `startup.md` sends the repo to `setup.md`, and `write` runs `repair()`. `repair()` then replaces a Branch pattern row that does not parse with the template's row (`{feat,infra}/<prefix>-N-short-title` plus its note), the same way it fills a placeholder row. The user sees the new row in the setup PR and can change the heads there. Without this step the repo would loop: status says `placeholders`, write changes nothing, status says it again.
5. **`setup.md`.** One sentence in the `placeholders` paragraph: `Branch pattern` has no question; `write` puts the template's row in its place, and the PR walk-through tells the user the old row did not parse and that they can edit the heads in the PR.
6. **Tests**, table-driven, in the existing files:
   - `test_project_config.py`: one table of rows (prose with no backticks, a backticked token with no `<prefix>`, a bad brace list, a valid brace row, a valid plain head, a missing row, an empty row, a TODO row) with the expected heads and whether stderr has the warning. One more case calls `branch_heads()` twice on a bad row and sees the warning once.
   - `test_setup_repo.py`: two rows in the `STATUS` table (a prose Branch pattern row gives `placeholders: Branch pattern`; a valid brace row gives `set`), and one `write` case where re-setup replaces a prose row with the template row and leaves a valid row alone.

## Leaves out

- Changing the parse rules or the `feat/` fallback value.
- A non-zero exit on a bad row, from any script.
- The dashboard's `headsFromProject` in `dashboard/titles.ts`, which parses the same row in TypeScript and also falls back silently. A follow-up can add the same warning there.
- Asking the user a new setup question for the heads.

## Calls I made

- `status` reports the bad row in the `placeholders:` list on line 1. That means the Chief of Staff in that repo stops at startup and routes to setup until the row is fixed, instead of running with `feat/` only. The ticket asks for it in "the same output that lists unset rows", and line 1 is that output; the startup stop is what makes it loud.
- Re-setup replaces the bad row with the template's `{feat,infra}/` row (step 4). The ticket only asks to report it, but reporting it in `placeholders` without a repair would leave setup in a loop. The user reviews the new row in the setup PR.
- A row whose cell is empty or starts with `TODO(` stays silent, like a missing row: both mean "use the default".
- The stderr warning prints once per process, keyed on nothing: a script that reads two project.md files with different bad rows prints only the first. No script does that today.
- `branch_pattern_error()` is its own function so `status` can check the row without printing the stderr warning.

## Touches

None of: data, money, auth, user email, migrations.
