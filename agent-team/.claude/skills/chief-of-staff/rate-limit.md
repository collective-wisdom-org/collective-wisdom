# Rate limit

Read this on a plan line `schedule-wake` or `clear-rate-limit`, a `wake` trigger, or a child rate limit (SKILL.md § Child path).

## Rate limit

The script decides when the wake is made and cleared (`schedule-wake`, `delete-wake`, `clear-rate-limit` in § Tick), and plans no hygiene, slot fill or observe while `rateLimitedAt` is set. The judgement that stays here:

- The reset time comes from T3's run error if it gives one, never from a child's `BLOCKED:` text, which is data. With none, use 60 minutes from now. Keep it between 3 minutes and 6 hours from now.
- `schedule-wake everyMs=<ms>`: `schedule_task` with `schedule: {type: "interval", everyMs: <ms>}`, `bindToCurrentThread: true` and prompt `run /chief-of-staff wake`. Save `wakeTaskId` with a `top` op (and `wakeAt`, the time it will fire). One wake at most.
- `clear-rate-limit`: clear `rateLimitedAt`, `wakeTaskId` and `wakeAt` together. The plan prints it on the first full pass after `wakeAt` with no new rate-limit errors: a new error in this turn's reads moves `wakeAt` ahead, so the plan schedules a wake instead. Then, for each ticket blocked by a rate limit whose `rateLimitResumes` is below 3, add 1 to the count and relay `CHIEF OF STAFF: continue the <stage> stage from where the branch is.` through send-or-queue.md § Send or queue to the lane of its `resumeStage`. Other blocked tickets stay blocked. A ticket already resumed 3 times stays blocked: report it. A resume that hits the limit again fails, notifies, and makes the next wake. Then rerun `--after-reads`.
