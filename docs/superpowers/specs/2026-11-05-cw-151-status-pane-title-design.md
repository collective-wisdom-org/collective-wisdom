# CW-151: ticket title in the status pane rows

**Status:** Shipped
**Shipped:** in PR #152, as specified
**Ticket:** [#151](https://github.com/collective-wisdom-org/collective-wisdom/issues/151)

## Goal

A status pane row reads `CW-N title`, then risk, then next step. Today it shows the ID, risk and next step, because state has no title.

## Today

- `agent-team/.claude/mods/status-pane/hooks/groups.ts` (`row`) already reads `t.title` from state, and `register.tsx` prints it after the ID. State never holds one.
- `agent-team/scripts/cos_state.py`: `TICKET` has no `title` key, and `op_start` takes none. `keys_ok` rejects unknown keys in `set`.
- The pane polls a file; it has no tracker access. `status.md` gets titles from the tracker, so the status answer in chat already shows them.
- `register.tsx` builds `t3-thread://` links from an `environmentId` option. Those links are not clickable in the terminal pane.

## Builds

- `cos_state.py`: `title` joins the ticket keys. `start` accepts an optional `title` (a string; control characters become spaces, it is trimmed and capped at 200 characters, `""` when absent). `set` can fill or change it for a ticket already in state.
- The chief-of-staff skill passes the ticket title in the `start` op. It already has the ticket from the readiness check. `state-keys.md` documents the key.
- The pane row: ID, title, `| risk | next`. A ticket with no title shows the ID alone, as now.
- The mod drops the thread link, the `environmentId` option and the `childThreadId` field it carried for the link. `autoOpen` stays.
- `status-pane.md`: remove the environment ID section and the "ticket titles" line in "What it leaves out".
- Tests: one table-driven test for the title rule in `test_cos.py` (start with title, start without, set later, wrong type rejected), and `groups.test.ts` rows with and without a title.

## Leaves out

- Backfilling titles for tickets already in state, apart from the Chief of Staff using `set` on them.
- Cost in the pane, and acting on tickets from it.
- Any change to the `status` answer in chat; it keeps reading titles from the tracker.

## Calls I made

- **The title is stored in state, not read from the tracker by the pane.** The pane polls every 5 seconds and has no tracker access. The cost is a title that can go stale if someone renames the ticket; the Chief of Staff only writes it at `start`.
- **Removing the thread link and `environmentId` in this ticket**, because you said to drop the thread links. Anyone who set `environmentId` keeps a stored value that the mod now ignores.
- **Existing tickets get a title only through a `set` op.** No script backfills them, so they show the ID alone until the Chief of Staff next touches them or you ask it to set one.
- **A missing `title` on `start` is allowed**, so older callers keep working.

## Touches

none of: data, money, auth, user email, migrations.
