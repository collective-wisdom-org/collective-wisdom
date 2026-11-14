# CW-310: Configurable active-agent cap and lane limits, merge lane outside the cap

**Status:** Shipped
**Shipped:** in PR #318, as specified
**Ticket:** [#310](https://github.com/collective-wisdom-org/collective-wisdom/issues/310)

## Goal

The overall cap on active children, the spec lane limit and the build lane limit are settings in the machine's `~/.config/collective-wisdom/user.md`. The merge lane is fixed at 1 and no longer counts toward the cap, so a merge can always take its slot.

## Today

Facts from `main` at `82f27a1`.

- `agent-team/scripts/cos_tick.py:36` has `LIMITS = {"spec": 2, "build": 2, "merge": 1}` and `CAP = sum(LIMITS.values())` (5). `slot_fill` (`:244`) loops `while sum(counts.values()) < CAP` over the lanes in order merge, build, spec, and the Todo count (`:262`) is `min(LIMITS["spec"] - spec, CAP - sum(counts))`. The merge count is in both sums.
- `agent-team/scripts/cos_route.py:121` decides send or queue with `count(lane) < cos_tick.LIMITS[lane] and count(*cos_state.ACTIVE) < cos_tick.CAP`. A merge approval with four spec and build children active and one more over the cap (an adopt can pass the cap) queues the merge today (`test_cos_route.py:54`, `OVER_CAP`).
- `no_hands.py` imports `cos_tick` for `SAFE` only; it does not read the limits.
- The tick's report line is `report (filling stopped: lanes full|spec slot free|No Hands <reason>)`. The model fills `Moving (<active count> of <overall cap> active)` and `Spec <count> of <spec limit>` from SKILL.md § Lanes, where the numbers are written in a table (`SKILL.md:165`). `SKILL.md:176` says the table and `cos_tick.py` must agree.
- `agent-team/scripts/user_config.py` reads `user.md` tables. `subscription_usage` finds its row by the key's prefix and reads the first backticked token of the value cell, returning None for anything it cannot use. `_rows` raises `UserConfigError` when the file exists but cannot be read.
- `agent-team/templates/user.md` § Settings has one row (the Claude subscription figure). `agent-team/docs/agents/github-auth.md:89` says the file holds "GitHub logins and one dollar figure".
- `agent-team/docs/agents/org-chart.md:22` and `:103` say "up to 5 active".
- `cos_tick.py`, `cos_route.py`, `user_config.py`, the `chief-of-staff` skill and `github-auth.md` are on the hands path, and the scripts and role docs on the approval path (`approval_policy.py`), so this ticket never auto-approves.

## Design

### Settings rows

Three rows go in the Settings table of `agent-team/templates/user.md`, with `none` as the value:

| Key | Value |
|---|---|
| Active children cap (spec and build together) | `none` |
| Spec lane limit | `none` |
| Build lane limit | `none` |

The template's lead line changes from "It holds GitHub logins, never tokens." to say it holds GitHub logins and team settings, never tokens. No merge row is added. A row whose key starts with `Merge lane limit` (or any other key) is not read.

### Reader

`user_config.py` gets one reader, `lane_limits()`, returning `{"cap": int, "spec": int, "build": int}`. Each row is found by key prefix, like `subscription_usage`. A value is used only when its first backticked token is a whole number of 1 or more written as plain digits (`3`, not `3.0` or `+3`; see below). Anything else (no file, no row, `none`, `0`, `-1`, `2.5`, text, an unreadable file) reads as the default for that key. The reader never raises: a `UserConfigError` from `_rows` gives all defaults.

- Defaults: spec 2, build 2.
- The cap's default is the spec limit plus the build limit in effect, so with no rows it is 4. A user who raises only the build limit to 3 gets a cap of 5, not a silent 4.
- A cap set above spec + build changes nothing (the lane limits bind). A cap set below lets fewer run than the lanes allow, which is the point of the row.
- Accepted digits: `[1-9][0-9]*`, at most 3 digits. `03` and anything over 999 read as the default, so a typo cannot start a thousand children.

### Lanes in the tick and the route

`cos_tick.py` replaces the `LIMITS` and `CAP` constants with `MERGE_LIMIT = 1` and a function `limits()` that returns `({"spec": s, "build": b, "merge": 1}, cap)` from `user_config.lane_limits()`. The merge limit is never read from the config.

- `slot_fill` reads `limits()` once per call. The overall count is `spec` + `build`. The merge lane fills first while its count is under 1 and its queue has a ticket, whatever the overall count. Then build and spec fill, in that order, while each lane is under its limit and the overall count is under the cap. The Todo count is `min(spec limit - spec, cap - (spec + build))`, floored at 0.
- `cos_route.py` reads `cos_tick.limits()` once per call. For `merge`, room is `count("merge") < 1` and no merge waiting ahead. For `spec` and `build`, room is the lane under its limit, `count("spec", "build") < cap`, and none waiting ahead. Its module docstring changes to match.
- The report line carries the numbers in effect, so the model never prints a stale cap: `report cap=<N> spec=<S> build=<B> merge=1 (filling stopped: …)`. A rate-limited turn prints `report cap=<N> spec=<S> build=<B> merge=1` with no parenthetical.

### Skill and docs

- `chief-of-staff/SKILL.md` § Lanes: the Limit column says "`user.md` (default 2)" for spec and build, "1, fixed" for merge; the Overall row is `spec` + `build`, default the two lane limits added, set in `user.md`. The text says the merge lane is outside the cap, so a merge can always take its one slot, and that `cos_tick.py` reads the values (`limits()`) and `cos_route.py` uses the same function. The sentence that the table and the script must agree goes; the numbers live in one place now.
- SKILL.md § Tick row for `report (...)` and § Report format: the cap and limits printed come from the `report` line's `cap=`, `spec=`, `build=`, `merge=` values. The Moving header's active count is spec + build; the merge line keeps `Merge <count> of 1`. `Filling stopped: lanes full.` says the cap is reached or every lane with work queued is at its limit.
- `startup.md:52` (count over the cap after a rebuild) stays; it means the spec and build count now.
- `github-auth.md:89`: the file holds GitHub logins, the Claude subscription figure and the lane settings, never tokens.
- `org-chart.md:22`, `:103`: "up to the cap (4 by default) plus one merging".
- `README.md:95`: the per-machine settings list adds the cap and lane limits.

### Tests

Two table-driven tests, per `AGENTS.md` § Testing:

- `test_user_config.py`: one table over `user.md` contents for `lane_limits()`: no file, empty rows, each valid value, `none`, `0`, `-1`, `2.5`, `03`, `1000`, text, a cap row only, lane rows only (cap follows the sum), a `Merge lane limit` row (ignored), an unreadable file (all defaults).
- `test_cos_tick.py`: one table for the slot plan under configured limits: defaults (cap 4), a raised cap, a lowered spec limit, cap full of spec and build with a queued merge (merge still sent), a second queued merge (never sent while one is in `merge`). Existing tick expectations change for the new report line (`TAIL`, `TODO`) and for cases where the merge ticket used to count toward the cap.
- `test_cos_route.py`: the `OVER_CAP` approve-merge row flips from `queue merge` to `send merge`; add rows for a configured cap and spec limit through the same table.

Tests set `HOME` to a temp dir and write `user.md` there, so the reader runs for real.

## Acceptance

- With no `user.md` rows, spec and build limits are 2 and 2, merge is 1, the cap is 4.
- Setting the cap, spec or build row changes what `cos_tick.py` starts and what `cos_route.py` sends or queues.
- With the cap full of spec and build tickets, a queued merge is sent. A second ticket never enters `merge`, whatever `user.md` says.
- An invalid, missing or unreadable value falls back to the default and never stops a pass.
- `python3 -I -m pytest -q agent-team/scripts` passes.

## Leaves out

- A configurable merge limit, per-repo values, and any change to the default lane limits.
- A setting in `project.md`; the config stays machine-wide.
- Writing the new rows from `setup_repo.py user` or the startup user settings check: the rows are optional, and an existing `user.md` without them keeps the defaults.

## Calls I made

- **The cap's default is the spec and build limits added, not a fixed 4.** The ticket says a missing cap reads as "the current default". With default lanes that is 4 either way; with a raised lane limit and no cap row, the sum avoids a cap that silently undoes the raise.
- **Values over 999 and with a leading zero read as the default.** The ticket asks for "a whole number of 1 or more"; I added the upper bound so a typo can't start hundreds of children.
- **The tick prints the numbers in its `report` line** (`report cap=4 spec=2 build=2 merge=1 (…)`), so the model reads the cap from the plan rather than from a table that no longer holds the number. This changes the line format the skill documents.
- **The merge lane fills before the cap is checked, but build and spec still fill in the old order** (merge, build, spec).
- **An unreadable `user.md` gives all defaults silently**, with no report line, matching how `subscription_usage` treats a bad value.
- **No change to `setup_repo.py` or the startup check**: new and old `user.md` files work without the rows; only the template shows them.
- **The row keys** are `Active children cap (spec and build together)`, `Spec lane limit` and `Build lane limit`.
