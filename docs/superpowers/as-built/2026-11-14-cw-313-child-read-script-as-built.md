# As-built: Read child threads through a script that prints a short result

**Shipped:** in PR #320
**Ticket:** CW-313
**Spec:** [2026-11-14-cw-313-child-read-script-design.md](../specs/2026-11-14-cw-313-child-read-script-design.md)

## Differs from the spec

- The spec saves T3's environment id to state as `t3EnvironmentId` when it isn't in T3's files. It is in `~/.t3/userdata/environment-id`, so `cos_idle_check.py --store` reads it from the directory beside `--db` and no state key exists. With the file missing, lines print the thread id in place of a link.
- The spec reads the newest finished assistant message from `orchestration_v2_projection_messages`. The script reads `assistant_message` turn items from `orchestration_v2_projection_turn_items` (the item ids are `turn-item:provider:…`, not `turn-item:message:<id>`); the text is the same.
- `next` is the item's rank among the thread's items, because store ordinals (`run number * 1,000,000 + item number`) are not read positions. A fallback `t3_thread_read afterPosition=<next>` never skips a message but may show a later one of another role.
- The delivered mark could not be shown to be unneeded: the `child-read` plan line keeps one `t3_thread_read` with `itemId: <item>` and `maxCharsPerItem: 1`, skipped when the script prints no `item=`.
- `cos_sweep.py` also keeps the merged check's `mismatch` and `unreadable` lines and the review check's `unreadable`, since `SKILL.md` has the Chief of Staff act on them. `--verbose` prints the rest.
- The `--wait --store` check takes the last 10 `dynamic_tool` items of the last run, not the last 10 items of any kind, so it is slightly more lenient than the activity read.
