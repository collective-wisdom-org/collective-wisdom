# NH-29: Keep the merge approval human-only after CW-110

**Ticket:** [NH-29 (noahstotland/nohands#29)](https://github.com/noahstotland/nohands/issues/29)
**Status:** Shipped
**Shipped:** in PR #PRNUM, as specified

## Goal

CW-110 removed the owner's GitHub approving review. The merge approval is now only the user's own `approve N`, verified by `scripts/cos_approve_pr.py`, and the relay the Chief of Staff sends after it. A security review of an app install (noahstotland/nohands PR #30) found places where the old review was the only backstop. This PR closes the small ones and keeps the human gate: only the user's own verified `approve N` starts a merge.

## Change

1. **A push after approval ends the merge.** `merge-pr` § Team mode used to tell the merge child to merge a head pushed after the approval ("Don't ask again") once reviews were re-run. The owner's review used to void that; nothing does now. Now any head other than the relayed `at head <SHA>` stops with `BLOCKED: head moved after approval`; the child reports `MERGE READY` again and the user replies `approve N` again. `ship-loop` and `github-auth.md` say the same. The pre-approval flow (the `Head moved to` note before `MERGE READY`) is unchanged.
2. **`merge_pr.py` checks the gh login.** It stops unless gh is signed in as `project.md`'s `Owner login` (case-insensitive), instead of trusting whoever runs it for review comments and the `Head moved to` note.
3. **No merge approval from a rebuilt or queued relay.** A rebuild or a `pendingRelay`-less merge approval sets the ticket to `awaiting-merge` (which restamps `lastSeenAt`), and the user replies `approve N` again. The merge relay is built only after `cos_approve_pr.py` exits 0 in that run.
4. **A new head voids the cut-off.** `cos_state.py` restamps `lastSeenAt` when `headSha` changes while a ticket stays in `awaiting-spec`, `awaiting-merge` or `blocked`, so an `approve N` written for the old head no longer counts.
5. **`cos_approve_pr.py` shows what it verified.** The success line ends with `(user wrote: "<first 80 characters>")`.
6. **Stale doc.** `chief-of-staff/continuation.md` no longer says the owner's GitHub review proves a merge approval.

## Left out (follow-up tickets)

- `merge_pr.py` checking an approval record itself (for example the approved head from the state file). It is a larger design, and the script is still a guard against mistakes and relay confusion, not a boundary against a role that runs it with the owner's login.
- `cos_user_check.has_words` accepts a message such as "do not approve 30 yet". Needs a matching rule that also fits spec approvals.

## Calls I made

- Strict stop on any moved head after approval, with no "same diff" exception. A new `approve N` is cheap; a quiet merge of an unapproved head is not.
- The owner gate is in `merge_pr.py`, not only in `cos_approve_pr.py`, because the merge reads reviews and notes by login.
- The rebuilt-relay fix removes the shortcut rather than adding a check, so there is one way to a merge relay.
