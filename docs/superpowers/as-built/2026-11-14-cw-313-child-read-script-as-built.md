# As-built: Read child threads through a script that prints a short result

**Shipped:** in PR #320
**Ticket:** CW-313
**Spec:** [2026-11-14-cw-313-child-read-script-design.md](../specs/2026-11-14-cw-313-child-read-script-design.md)

## Differs from the spec

- The spec saves T3's environment id to state as `t3EnvironmentId` when it isn't in T3's files. It is in `~/.t3/userdata/environment-id`, so `cos_idle_check.py --store` reads it from the directory beside `--db` and no state key exists. With the file missing, lines print the thread id in place of a link.
- The spec reads the newest finished assistant message from `orchestration_v2_projection_messages`. The script reads `assistant_message` turn items from `orchestration_v2_projection_turn_items` (the item ids are `turn-item:provider:…`, not `turn-item:message:<id>`); the text is the same.
- `next` is the item's rank among the thread's stored position rows, because store ordinals (`run number * 1,000,000 + item number`) are not read positions. The rank counts every stored row, so in a thread with rolled_back runs or cancelled queued messages (items T3's read leaves out) `next` can be higher than a read's position and a fallback `afterPosition=<next>` could skip such items (rare for children). After a fallback read, `lastPosition` comes from the read's lower `nextPosition`, so the next script run can report an already-seen message as new: a repeat notice, harmless.
- T3 acknowledges a child's final result only when a read returns the whole message, so the 1-character read the spec considered would do nothing and none is kept; results of messages longer than the old 2,000-character read were not acknowledged before either.
- Marker turns still add the marker block (about 1.9k characters typical with the 1,500-character block cap; before: up to 10k), which the spec's `## Calls I made` chose for the approval request; the ticket's "few hundred characters" holds for turns without a block.
- `cos_sweep.py` also keeps the merged check's `mismatch` and `unreadable` lines and the review check's `unreadable`, since `SKILL.md` has the Chief of Staff act on them. `--verbose` prints the rest.
- The `--wait --store` check takes the last 10 `dynamic_tool` items of the last run, not the last 10 items of any kind, so it is slightly more lenient than the activity read.
