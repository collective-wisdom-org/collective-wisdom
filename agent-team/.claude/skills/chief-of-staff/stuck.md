# Chief of Staff: stuck check

Read this when SKILL.md § Child path, Stuck check fires.

**Stuck check.** Only for a child in `spec`, `build` or `merge` (not queued or `awaiting-*`), after its read. It is stuck only if `recentRuns[0].status` is `failed` or `interrupted`; it is `completed` with no marker and the wait check does not say `waiting`; or it is `running` and the thread's `updatedAt` is more than 45 minutes old. For a `completed` run with no marker, first run the wait check: `python3 ~/.collective-wisdom/scripts/cos_idle_check.py --wait <PREFIX>-N --store <childThreadId>`; its exit code is `--wait` below. On exit 2: fallbacks.md § Wait check. Then run

```
python3 ~/.collective-wisdom/scripts/cos_restart.py <PREFIX>-N --run <recentRuns[0].status> --updated-at <updatedAt> [--marker] [--wait <0|1|2|2twice>] --step "<text>" --missing "<text>" [--spec <path>] --thread <this thread's id> --next
```

`--marker` means the child read reported a marker. Write the two judgement lines yourself, one line each: `--step`, the last step the child finished (from its last assistant message), and `--missing`, the next step (e.g. "run the security review on head <sha>, post it on the PR, then MERGE READY"; in `spec`, the rest of commit, push, `BUILD READY`; in `build` with no PR, the rest of the plan). In `spec`, pass `--spec` when the child's last message gave a spec path. A first stall restarts the child once per stage; a second blocks it.

Do what each `next:` line says. Exit 2 (`restart: cannot <what>`) has no `next:`: fix the call, or tell the user under Needs you.
