# As-built: cos_tick.py plans a Chief of Staff turn

**Shipped:** in PR #196
**Ticket:** CW-60
**Spec:** [2026-11-04-cw-60-cos-tick-design.md](../specs/2026-11-04-cw-60-cos-tick-design.md)

## Differs from the spec

- `run` lines carry no `AGENT_GH_ROLE=chief-of-staff` prefix: that variable no longer exists in the scripts. Script paths are `~/.collective-wisdom/scripts/...`.
- Notice turns also print `schedule-wake` (never the clearing), so a rate limit a notice turn finds still gets its wake. The spec's notice act plan left it out.
- `clear-rate-limit` (and `delete-wake` before it on a full pass) ends the plan with `tick --after-reads`, because resuming rate-limited tickets changes state the rest of the plan depends on. The child path writes `rateLimitedAt` and `wakeAt` and never `wakeTaskId`.
- Extra plan lines the spec did not name: `run ... approval_policy.py auto <T> spec` for a queued auto-approved spec, `run ... cos_approve_pr.py <T> --auto` for a queued auto-approved merge, and `words="..."` on `user-check`. `configure` is skipped when `continuation` replaces `send`.
- `report` carries the stop reason in parentheses (`filling stopped: spec slot free` or `lanes full`); a rate limited turn prints a plain `report`.
- The `status` act plan is only the `archive` lines and the rotation check. After a `status` read that changed a stage, the model runs `--trigger notice:<own thread id> --after-reads` for the slot fill.
- `start` skips the retired and failed-handoff stops when `rotation.to` is this thread, or `rotation.to` is null and `chiefThreadId` is absent or this thread. A missing state file is empty state, not an error.
- A user question that is not a command runs the `status` trigger, not the `user` one: it gets an answer and no slot fill unless a read changed a stage, and then `--trigger notice:<own thread id> --after-reads` fills the slot with no hygiene and no rate-limit clearing. The old text split on this (a full pass on every user message, but no slot fill on a question).
- `rotation.md` take over step 4.4 runs `cos_tick.py --thread <id> --trigger user --after-reads` and follows its lines up to, but not including, `observe`, skipping `hygiene`, `report` and the final rotation check. `startup.md` Setup no longer repeats the start-up clean-up that the `start` plan prints.
- SKILL.md shrank by about 0.5 KB, not much: § Tick, § Child path and § Rate limit carry every rule the replaced sections held.
- The script checks every state value and argument it prints into a plan line (`[A-Za-z0-9._:%@-]+`) and stops with `cos_tick: unsafe <field> in state or arguments` (exit 2) otherwise, so text from a child's report or an agent notice cannot add a plan line. SKILL.md runs a `run` line only when it starts with `python3 ~/.collective-wisdom/scripts/`, and uses a notice thread id only when it matches that pattern. JSON in `send` and `user-check` lines is ASCII-escaped.
