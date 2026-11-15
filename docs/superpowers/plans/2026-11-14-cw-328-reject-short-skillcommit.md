# CW-328 plan: reject a short skillCommit

Spec: `docs/superpowers/specs/2026-11-14-cw-328-reject-short-skillcommit-design.md`. Test command: `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: cos_state.py rejects it

- In `op_top()` (`agent-team/scripts/cos_state.py`), after the `lastResetAt` check: if `skillCommit` is in `op["set"]` and is neither `None` nor a `str` matching `[0-9a-f]{40}` (`re.fullmatch`), `raise Reject("skillCommit needs the full 40-character sha from cos_rotation_check.py --skill-commit, or null")`.

## Task 2: decide() reports it (`agent-team/scripts/cos_rotation_check.py`)

- Add `FULL_SHA = re.compile(r"[0-9a-f]{40}")`. In `decide()`, after `old = state.get("skillCommit")`: `bad = bool(old) and not (isinstance(old, str) and FULL_SHA.fullmatch(old))`; if `bad`, set `old = None`.
- Everywhere `decide()` prints `ok; set skillCommit {commit}` (the mode-none branch and the final `if not old` return), print `ok; skillCommit is not a full sha; set skillCommit {commit}` instead when `bad`. Holds and the size trigger keep their order. Never print the stored value.
- Add one sentence about the line to the module docstring.

## Task 3: docs

- `agent-team/.claude/skills/chief-of-staff/rotation.md` Skill change row (line ~20) and `state-keys.md` `skillCommit` bullet (line ~53): a `skillCommit` that is not a full sha prints `ok; skillCommit is not a full sha; set skillCommit <sha>`; handle like `null` (save the sha, no reset). Keep it to one short clause each.

## Task 4: tests (table-driven, short)

- `test_cos_state.py`: one parametrized test over `top` ops: `8ddace1`, a 40-char uppercase sha, a 41-char value and `123` are rejected (state file unchanged); a 40-char lowercase sha and `None` are accepted. Follow the file's existing helpers.
- `test_cos_rotation_check.py`: add rows to `test_decide`'s table: short `skillCommit` on main, quiet turn and busy turn (`QUEUED`), want `ok; skillCommit is not a full sha; set skillCommit`; and over the cap still `rotate: size`. Add a `test_line_by_reset_mode` row for a short value on a `none` provider.
