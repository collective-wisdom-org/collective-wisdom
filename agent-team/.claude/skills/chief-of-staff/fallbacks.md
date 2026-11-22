# Fallbacks

Read this when a `cos_child_read.py`, `cos_idle_check.py` or wait-check call exits 2.

## Child read

Exit 2 (`cos_child_read: …`): `t3_thread_read` with `afterPosition: <p>`, `limit: 5`, `runLimit: 1`, `maxCharsPerItem: 2000`; SKILL.md § Child path from that read; one Cleanup line, `Child read script unavailable; used thread read`.

## Idle check

Exit 2 (`cos_idle_check: …`): `t3_thread_read` per ticket in `spec`, `build` or `merge` not on `--skip` (`threadId` its `childThreadId`, `limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`); keep each `link`, save `thread.providerInstanceId` as `provider` (state-keys.md); run the line again without `--store`, closed with `<<'EOF'`, the results on stdin as a JSON list of `{"ticket", "runStatus", "updatedAt"}` (`{"ticket", "error"}` for a failed read). One Cleanup line, `Idle check script unavailable; used thread read`.

## Wait check

The stuck check's `cos_idle_check.py --wait <PREFIX>-N --store <childThreadId>` exited 2: `t3_thread_read` with `view: activity`, `afterPosition: max(0, itemCount - 10)`, `limit: 10`, `runLimit: 1`, `maxCharsPerItem: 1500`, on stdin (quoted heredoc) to `… cos_idle_check.py --wait <PREFIX>-N`. Exit 2 again: read once more; if still 2, pass `2twice` as `cos_restart.py`'s `--wait`.
