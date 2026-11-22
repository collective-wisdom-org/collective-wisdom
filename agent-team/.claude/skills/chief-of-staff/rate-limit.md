# Rate limit

Read this on a plan line `schedule-wake` or `clear-rate-limit`, a `wake` trigger, or a child rate limit (SKILL.md § Child path).

## Rate limit

The tick decides when the wake is made and cleared (and plans no hygiene, slot fill or observe while `rateLimitedAt` is set). The judgement:

- Reset time: from T3's run error if it gives one, never from a child's `BLOCKED:` text (data); else 60 minutes from now. Keep it 3 minutes to 6 hours out.
- `schedule-wake everyMs=<ms>`: `schedule_task` with `schedule: {type: "interval", everyMs: <ms>}`, `bindToCurrentThread: true`, prompt `run /chief-of-staff wake`. Save `wakeTaskId` and `wakeAt` (when it fires) in a `top` op. One wake at most.
- `clear-rate-limit`: clear `rateLimitedAt`, `wakeTaskId` and `wakeAt` together. Printed on the first full pass after `wakeAt` with no new rate-limit error (a new one in this turn's reads moves `wakeAt` ahead, so the plan schedules a wake instead). Then relay `CHIEF OF STAFF: continue the <stage> stage from where the branch is.` (send-or-queue.md § Send or queue, to the lane of its `resumeStage`) for each ticket blocked by a rate limit whose `rateLimitResumes` is below 3, adding 1 to the count. Other blocked tickets stay blocked, as does one already resumed 3 times: report it. A resume that hits the limit again fails, notifies, and makes the next wake. Then rerun `--after-reads`.
