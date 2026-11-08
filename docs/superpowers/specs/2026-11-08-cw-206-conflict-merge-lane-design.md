# CW-206: Send a conflict found at MERGE READY to the merge lane when reviews stand

**Status:** Shipped
**Shipped:** in PR #210, with differences: [as-built](../as-built/2026-11-08-cw-206-conflict-merge-lane-as-built.md)
**Ticket:** [#206](https://github.com/collective-wisdom-org/collective-wisdom/issues/206)
**Related:** CW-197 (#207) compacted the Chief of Staff skill files and moved the routing table into `cos_route.py`. CW-199 changed review-stand handling in `review_gate.py`; it does not touch the head check.

## Goal

With `Review after conflict resolution` `off`, a PR that conflicts with the merge target branch when the child reports `MERGE READY` goes to the merge lane, not the build lane. The resolution run posts the "reviews stand" note, reruns no review, and reports `MERGE READY` again. Nothing on that path says or implies that the user approved the merge.

## Today

Facts from `main` at `07f893d`.

- `cos_head_check.py check()`: head moved gives `head-check: moved`. Head unchanged and conflicting gives `head-check: conflict keep` (relay `CONFLICT_APPROVED`, which says "The user approved the merge at head <sha> ... and merge") only when the setting is `off` and `--no-approval` is not set. Every other conflict gives `head-check: conflict withdraw` with the plain `CONFLICT` relay ("Resolve it ... and report MERGE READY"). The docstring says `--no-approval` makes a conflict "always `conflict withdraw`". `test_cos_head_check.py` pins that row.
- `cos_route.py` `ROUTES`: `conflict-keep` goes from `awaiting-merge` or `merge-queued` to `merge` (setting `off` only); `conflict-withdraw` goes from `awaiting-review`, `awaiting-merge`, `merge-queued` or `merge` to `build`. Its docstring table is now the lane table the ticket names (CW-197 removed the SKILL.md table). Script, docstring and approvals.md agree today: all send this case to build.
- `chief-of-staff/approvals.md` § Approval requests, `MERGE READY` step 1: on `conflict: yes`, run `cos_head_check.py <PREFIX>-N --no-approval` and send the relay "to the lane its last line names (`conflict withdraw`: the build lane)".
- `chief-of-staff/review.md` § approve N on awaiting-review: runs the head check with `--no-approval`; a `conflict withdraw` sets no `heldApproval` and sends its relay.
- `chief-of-staff/SKILL.md` § Child path, `BLOCKED:` for a child in `merge`: runs `cos_head_check.py <PREFIX>-N` **without** `--no-approval`. On `conflict keep` it sends the printed relay at once. The script assumes any ticket in `merge` holds an approval, since today only an approval puts it there.
- `open-pr` § Conflict resolution already handles the plain relay in the merge slot under `off`: note, no reviews, `MERGE READY` with `Conflict resolved: <files>; reviews stand from <short SHA>`.
- `cos_state.py`: no stage-to-stage rule stops `awaiting-review` or `awaiting-merge` going to `merge`. A `MERGE READY` from `merge` goes through `cos_review_check.py --route` to `awaiting-merge` or `awaiting-review`, and the stage op stamps `lastSeenAt` on the new head, so the user's next `approve N` must come after the new `MERGE READY`. `cos_tick.py` runs a head check before sending a queued relay only when the relay carries an approval (`MERGE_USER`, `MERGE_AUTO` or `The user approved the merge at head`), so a queued plain `CONFLICT` relay is just sent.

So the stage and slot handling already let a ticket at `MERGE READY` hold the merge slot for the resolution run and come back to `awaiting-*`. One gap appears once it can: a merge child with no approval that reports `BLOCKED:` would get `conflict keep` and the `CONFLICT_APPROVED` relay, which tells it the user approved the merge. A merge relay needs no thread read (ship-loop § Approvals), so the child would merge without an approval.

## Builds

1. **`cos_head_check.py`: a new last line.** Head unchanged, conflicting, setting `off`, and no approval to carry: print the plain `CONFLICT` relay and `head-check: conflict stand` (reviews stand; send the relay, which carries no approval, to the merge lane). "No approval to carry" means `--no-approval` is set **or** the ticket in state has `noApproval: true` (item 3). `conflict keep` stays for `off` with an approval; `conflict withdraw` stays for `on` (and an unreadable setting) with or without `--no-approval`; `moved` is unchanged. The docstring lists all four lines and says what `--no-approval` and `noApproval` do.
2. **`cos_route.py`: a new caller `conflict-stand`.** From `awaiting-review` or `awaiting-merge` to `merge`, only with the setting `off` (with `on` or an unreadable setting it prints `route: no …`, as `conflict-keep` does). Its stage op, both the send (`merge`) and the queue (`merge-queued`), carries `"set": {"noApproval": true}`. Slot and queue rules are the existing ones: the ticket queues behind a busy merge slot. The docstring table gets the row.
3. **`cos_state.py`: a ticket key `noApproval`.** `true` marks a merge-lane run that carries no approval. It may be set only in `merge`, `merge-queued` or `blocked` (a blocked merge run resumes to `merge` through `resumeStage` and must keep it), and only to `true` or `null`. A `stage` op to any other stage drops it, so the `MERGE READY` that sends the ticket back to `awaiting-merge` or `awaiting-review` clears it. `state-keys.md` § State keys describes it.
4. **Chief of Staff text.**
   - `approvals.md` step 1: `conflict stand` sends the relay through Send or queue as `conflict-stand` (the merge lane); `conflict withdraw` as `conflict-withdraw` (the build lane). Neither comments `Approval withdrawn`, since none existed.
   - `SKILL.md` § Send or queue: add `conflict-stand` to the caller list. In the head check list, add `head-check: conflict stand`: no approval to keep or withdraw; send the printed relay (`conflict-stand`). A merge-approval head check never prints it unless state says `noApproval`.
   - `SKILL.md` § Child path, `BLOCKED:` for a child in `merge`: `conflict stand` is handled like `conflict keep` (the child still holds the merge slot: send the printed relay at once and leave the stage). Because the script reads `noApproval` from state, that child gets the plain relay, never `CONFLICT_APPROVED`.
   - `review.md` § approve N on awaiting-review: on `conflict stand` set no `heldApproval`, send the relay as `conflict-stand`, and tell the user to approve again after the next `MERGE READY`; `conflict withdraw` stays as it is.
5. **Tests**, one table-driven row per rule:
   - `test_cos_head_check.py`: `off` + `--no-approval` + conflicting, head unchanged gives `[PLAIN, "head-check: conflict stand"]`; `on` + `--no-approval` still gives `conflict withdraw`; `off` with `noApproval: true` in state and no flag gives `conflict stand`.
   - `test_cos_route.py`: `conflict-stand` from `awaiting-review` and `awaiting-merge` with `off` sends to `merge` with `noApproval` in the stage op; with `on` it is `route: no`; with the merge slot busy it queues with `noApproval`.
   - `test_cos_state.py`: `noApproval` is accepted in `merge`, `merge-queued` and `blocked`, rejected in other stages and for values other than `true` or `null`, and dropped by a stage op to `awaiting-merge`.

## Leaves out

- What `open-pr` § Conflict resolution does after the relay arrives (it already handles this case).
- The `on` setting's behaviour.
- Anything about GUY-358 or the Guy repo's state.
- A `BLOCKED:` merge child that keeps hitting the same conflict question gets the conflict relay again rather than going to `blocked`. That is how `conflict keep` behaves today too; changing it is a separate ticket.

## Calls I made

- ⚠ **A new state key, `noApproval`.** The ticket asks only for the head check and the routing. Without the key, a merge child sent by `conflict-stand` that reports `BLOCKED:` would get `conflict keep` and a relay saying the user approved the merge, and merge on it. I judged that in scope: the ticket asks to update the `BLOCKED:` bullet to match, and this is what makes it safe.
- **The new last line is `head-check: conflict stand`**, after "reviews stand", and the new route caller is `conflict-stand`, rather than reusing `conflict-keep` (which means "keep the approval") or a flag on `conflict-withdraw`.
- **`--no-approval` with `on` still prints `conflict withdraw`**, as the ticket's acceptance says, even though no approval is withdrawn. Its callers (approvals.md step 1, review.md) already skip the `Approval withdrawn` comment.
- **`noApproval` survives `blocked`**, so a blocked no-approval merge run that resumes to `merge` (an answer, resume or rate-limit relay) still gets the plain relay.
- **`conflict-stand` does not route from `merge-queued` or `merge`.** A ticket gets there with no approval only through `conflict-stand` itself, and the `BLOCKED:` path sends to its own child directly.
- **The "lane table" the ticket names is now the `cos_route.py` docstring.** CW-197 removed the SKILL.md table, so script, docstring and approvals.md are updated together.

## Acceptance

- `test_cos_head_check.py`: `off` + `--no-approval` + conflicting with the head unchanged gives `head-check: conflict stand` and the plain relay; `on` + `--no-approval` gives `conflict withdraw`.
- `approvals.md` step 1, the `cos_route.py` routing table and the `cos_head_check.py` docstring say the same thing.
- With `off`, a conflict at `MERGE READY` goes to the merge lane, the resolution run reruns no review (open-pr § Conflict resolution, `off`), and the ticket returns to `awaiting-merge` or `awaiting-review` with `noApproval` cleared when the child reports `MERGE READY` again.
- No path sends `CONFLICT_APPROVED` to a ticket whose state says `noApproval`.

Touches: none of these (Chief of Staff routing and state only).
