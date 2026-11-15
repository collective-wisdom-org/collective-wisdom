# CW-328: Reject a short skillCommit and report a mismatch on its own line

**Status:** Shipped
**Shipped:** in PR #337, as specified
**Ticket:** [#328](https://github.com/collective-wisdom-org/collective-wisdom/issues/328)

## Goal

A short `skillCommit` can't get into the state file, and an old state file that already holds one gets a rotation check line that says the value is invalid, instead of a "skill change waits" line that reads as a rotation about to happen.

## Today

Facts from `main` at `10f93a1`.

- `cos_state.py` `op_top()` (`agent-team/scripts/cos_state.py:326`) accepts any value for `skillCommit`: `keys_ok()` checks only that the key is allowed. It validates `reset` and `lastResetAt`, so there is a place for one more check.
- `cos_rotation_check.py` `skill_commit()` reads the commit with `git log -1 --format=%H`, which prints 40 lowercase hex characters.
- `decide()` (`agent-team/scripts/cos_rotation_check.py:153`) reads `old = state.get("skillCommit")`. On the merge target branch, `old` set and `commit != old` means a skill change: `rotate: skill changed ...` on a quiet turn, else `ok (skill change waits: <why>)`. A 7-character `old` never equals the 40-character commit, so the check reports a skill change forever, and on a busy turn the line is the waits line. A `null` `old` prints `ok; set skillCommit <sha>` and the Chief of Staff saves it (`rotation.md` § Thread rotation, `state-keys.md`).
- The 2026-11-14 compatibility run hit this with `8ddace1` (`docs/compatibility.md` G27).

## Design

1. **`cos_state.py` rejects it.** `op_top()` rejects a `skillCommit` that is not `null` and not a string of exactly 40 lowercase hex characters (`[0-9a-f]{40}`), with `Reject("skillCommit needs the full 40-character sha from cos_rotation_check.py --skill-commit, or null")`. The whole `apply` fails as it does for any other rejected op, so nothing is written. `null` stays valid: it is the "set it on the next check" value.
2. **`decide()` reports it.** When the stored `skillCommit` is set but is not 40 lowercase hex characters (a short sha, uppercase, or a non-string from an old or hand-edited file), `decide()` treats it as unset for the skill trigger, the same as `null` today, and prints its own line where the `null` line would be:

   `ok; skillCommit is not a full sha; set skillCommit <commit>`

   So it never prints `ok (skill change waits: ...)` or `rotate: skill changed ...` for that value. The holds (`paused`, a fresh `reset` marker) and the size trigger keep their order and win as they do for `null`, so a session over the size cap still rotates. On a provider with reset mode `none`, the line is the same one, where today the `null` case prints `ok; set skillCommit <commit>`. The line starts with `ok`, so the Stop hook does not block on it.
3. **Docs.** `rotation.md` § Thread rotation's Skill change row and `state-keys.md`'s `skillCommit` bullet each say that a `skillCommit` that is not a full sha prints `ok; skillCommit is not a full sha; set skillCommit <sha>`, handled like `null`: save the sha and don't reset. The script docstring of `cos_rotation_check.py` names the line.
4. **Test.** One table-driven test in `test_cos_state.py` over `top` ops: `8ddace1`, a 40-character uppercase sha, a 41-character value and a number are rejected; a 40-character lowercase sha and `null` are accepted. One table row set added to `test_decide` in `test_cos_rotation_check.py`: a short `skillCommit` on the merge target branch, on a quiet and a busy turn, prints the invalid line and never the waits line, and over the size cap it still prints `rotate: size ...`.

## Leaves out

- How the commit is read from git and when a rotation fires (ticket's Out of scope).
- Echoing the bad value in the line: the line names the fix, not the old value.
- Fixing the state file automatically: the Chief of Staff saves the sha, as it does for `null`.
- Updating `docs/compatibility.md` G27: it records what the run saw.

## Calls I made

- **Lowercase only.** The ticket says "40 hex characters". Git prints lowercase and the check compares strings, so an uppercase sha would never match either; it is rejected too.
- **The invalid value acts like `null`**, so the size trigger and the holds still work and the Chief of Staff's fix is the one it already knows (save the printed sha).
- **The line starts with `ok`**, so the Stop hook does not block the Chief of Staff's turn over it, as with `null`.
- **The line doesn't echo the stored value**, so a hand-edited state file can't put arbitrary text in the line the hook and the model read.
- **`null` stays accepted** by `cos_state.py`: it is the documented "not set yet" value.
