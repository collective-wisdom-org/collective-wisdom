# Chief of Staff stops restarting children that only wait on CI (design)

**Status:** Shipped
**Ticket:** none (PR #32). Port of the IHAG change from its GUY-328, for the GUY-330 cutover.

## Intent

T3 shows a child's run as `completed` while the child waits on `t3_background_wait`, for example on `wait-for-ci.sh`. The Chief of Staff's stuck check treated every `completed` run without a marker as a stall, so it restarted children that were only waiting on CI. The IHAG install overwrites `cos_idle_check.py` and the skills, so the fix has to live here or the next install loses it.

## Design

- `cos_idle_check.py --wait <PREFIX>-N` reads one `t3_thread_read` result (activity view) on stdin. It prints `waiting` and exits 0 when the last run is `completed` within 45 minutes and has a `t3_background_wait` call with matched IDs. It prints `stalled` and exits 1 for no wait call, only unmatched IDs, or a wait older than 45 minutes. It exits 2 when the input can't be judged, including a wait call cut off before its matched list shows. The state file is not read.
- `chief-of-staff` § Full pass step 3: a `completed` run without a marker is stuck unless the wait check says `waiting`. `waiting` means no restart and no report line. `stalled` is stuck. Exit 2 is read once more; if it repeats, the child gets the normal one restart but is never marked `blocked`, and a Cleanup line says the check was unreadable. The intro and the Tools line name the exception.
- `ship-loop` § Run endings and § CI waits: put the wait among the last tool calls (the Chief of Staff reads the last 10 items), start background commands with the tool's background option, and start again when `t3_background_wait` lists the ID under `unmatched`.
- `docs/agents/chief-of-staff.md` "Done when" names the exception.

## Fit with CW-11

CW-11's sweep, ready check and handoff find a finish nobody announced. This change answers a different question: whether a child that did announce a `completed` run is finished or still waiting. The two agree. T3 does send a notice when a run ends on a background-command wake, and CW-11's § Send or queue already says so; the wait check is how the Chief of Staff reads that case. The idle check's `full` line sends a `completed` child to a full read, which then reaches the same step 3. No CW-11 text changes.

## Verification

`python3 -I -m pytest -q agent-team/scripts` passes, with eight new `--wait` cases in `test_cos_idle_check.py`. IHAG's own `test_cos_idle_check.py` passes against this `cos_idle_check.py` with a `GUY` / `dbeallor/fathom` project file. `shellcheck install.sh agent-team/scripts/*.sh` is clean.
