import importlib.util
import json
import re
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_tick", Path(__file__).with_name("cos_tick.py"))
cos_tick = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_tick)

NOW = "2026-11-08T12:00:00Z"
ME = "me"
S = "~/.collective-wisdom/scripts"
SWEEP = [f"run python3 {S}/cos_sweep.py --thread {ME}", "each full: read", "each sweep line", "tick --after-reads"]
IDLE = f"run python3 {S}/cos_idle_check.py"
ROTATION = f"run python3 {S}/cos_rotation_check.py"


def tk(stage, child=None, **kw):
    return {"stage": stage, "childThreadId": child, "parentThreadId": ME, **kw}


def run(tmp_path, capsys, state, trigger, *extra, thread=ME):
    f = tmp_path / "state.json"
    if state is not None:
        f.write_text(json.dumps({"chiefThreadId": ME, **state}))
    code = cos_tick.main(["--thread", thread, "--trigger", trigger, "--file", str(f), "--now", NOW, *extra])
    lines = [re.sub(r"^\d+\. ", "", x) for x in capsys.readouterr().out.splitlines()]
    assert code == 0
    return lines


BUILD, SPEC1 = tk("build", "c1"), tk("spec", "c2")
READ = lambda t, c, p=0: f"read {t} {c} afterPosition={p} limit=5 runLimit=1 maxCharsPerItem=2000"  # noqa: E731


@pytest.mark.parametrize(
    "state, trigger, thread, want",
    [
        ({"rotation": {"from": ME, "startedAt": "2026-11-08T11:49:00Z"}}, "user", ME, "stop failed-handoff"),
        ({"rotation": {"from": ME, "startedAt": "2026-11-08T11:55:00Z"}}, "user", ME, None),
        ({"chiefThreadId": "new"}, "user", ME, "stop retired"),
        ({"retiredThreads": [{"threadId": ME}]}, "notice:c1", ME, "stop retired"),
        ({"chiefThreadId": "new"}, "start", ME, "stop retired"),
        ({"chiefThreadId": None}, "start", ME, None),
        ({"chiefThreadId": "old", "rotation": {"from": "old", "to": ME, "startedAt": "2026-11-08T11:00:00Z"}}, "start", ME, None),
        # a dead handoff with a named successor stops even on `start`; resume mode would hide it
        ({"chiefThreadId": ME, "rotation": {"from": ME, "to": "new", "startedAt": "2026-11-08T11:00:00Z"}}, "start", ME, "stop failed-handoff"),
        ({"paused": True}, "user", ME, "stop paused"),
        ({"paused": True}, "status", ME, None),
    ],
)
def test_stops_print_only_their_line(tmp_path, capsys, state, trigger, thread, want):
    for after in ((), ("--after-reads",)):
        out = run(tmp_path, capsys, {"tickets": {}, **state}, trigger, *after, thread=thread)
        assert (out == [want]) if want else not out[0].startswith("stop")


@pytest.mark.parametrize(
    "tickets, extra, trigger, want",
    [
        # user turn: a read and pending per active child in state order, queued and awaiting skipped
        (
            {"ABC-1": {**BUILD, "lastPosition": 7}, "ABC-2": tk("awaiting-review", "c3"), "ABC-3": SPEC1},
            {}, "user",
            [READ("ABC-1", "c1", 7), "pending c1", READ("ABC-3", "c2"), "pending c2", *SWEEP],
        ),
        # notice for an active child: its own read, idle reads for the rest, idle check skipping it
        (
            {"ABC-1": BUILD, "ABC-3": SPEC1},
            {}, "notice:c1",
            [READ("ABC-1", "c1"), "pending c1", "idle-read ABC-3 c2", f"{IDLE} --skip ABC-1 <<'EOF'", *SWEEP],
        ),
        # notice for the only active child: no idle check
        ({"ABC-1": BUILD}, {}, "notice:c1", [READ("ABC-1", "c1"), "pending c1", *SWEEP]),
        # notice for a ticket in another stage: no own read, idle check without --skip
        (
            {"ABC-1": BUILD, "ABC-2": tk("awaiting-review", "c3")},
            {}, "notice:c3", ["idle-read ABC-1 c1", f"{IDLE} <<'EOF'", *SWEEP],
        ),
        # notice for a thread in no ticket
        ({"ABC-1": BUILD}, {}, "notice:zz", ["helper-test zz", "idle-read ABC-1 c1", f"{IDLE} <<'EOF'", *SWEEP]),
        # status: idle reads for every active child, no pending
        ({"ABC-1": BUILD, "ABC-3": SPEC1}, {}, "status", ["idle-read ABC-1 c1", "idle-read ABC-3 c2", f"{IDLE} <<'EOF'", *SWEEP]),
        # start-up: setup with empty state, resume mode with tickets
        (
            {}, {}, "start",
            ["follow startup.md § Setup", "follow startup.md § Start-up clean-up", *SWEEP],
        ),
        ({"ABC-1": BUILD}, {}, "start", ["follow rotation.md § Thread rotation: Resume mode"]),
        # wake: without a wake task only clean-up step 1; with one, delete it first
        ({"ABC-1": BUILD}, {}, "wake", ["follow startup.md § Start-up clean-up step 1"]),
        ({"ABC-1": BUILD}, {"wakeTaskId": "w1"}, "wake", ["delete-wake w1", READ("ABC-1", "c1"), "pending c1", *SWEEP]),
    ],
)
def test_look_plan(tmp_path, capsys, tickets, extra, trigger, want):
    assert run(tmp_path, capsys, {"tickets": tickets, **extra}, trigger) == want


def queued(stage, relay, at, **kw):
    return tk(stage, "q" + at[-1], pendingRelay=relay, queuedAt=f"2026-11-08T0{at}:00:00Z", **kw)


USER_SPEC = 'CHIEF OF STAFF: the user approved the spec: "ship it\nnow". Continue to the build stage.\nApproval in thread: th9'
AUTO_SPEC = "CHIEF OF STAFF: auto-approved the spec under `low` (Risk: Low (docs)). Continue to the build stage."
USER_MERGE = 'CHIEF OF STAFF: the user approved the merge of PR #5 at head abc1234: "go".'
AUTO_MERGE = "CHIEF OF STAFF: auto-approved the merge of PR #5 at head abc1234 under `low` (Risk: Low (docs))."
CHANGES = "CHIEF OF STAFF: changes: rename it."
CONFIGURE = "configure q1 claude-sonnet-5-5 effort=high"
TAIL = ["observe", "report (filling stopped: lanes full)", ROTATION]
TODO = ["observe", "report (filling stopped: spec slot free)", ROTATION]


@pytest.mark.parametrize(
    "tickets, want",
    [
        # merge before build before spec, oldest queuedAt first, one merge slot
        (
            {
                "ABC-1": queued("spec-queued", CHANGES, "1"),
                "ABC-2": queued("build-queued", CHANGES, "3"),
                "ABC-3": queued("build-queued", CHANGES, "2"),
                "ABC-4": queued("merge-queued", CHANGES, "5"),
                "ABC-5": queued("merge-queued", CHANGES, "4"),
                "ABC-6": SPEC1,
            },
            [
                f"send ABC-5 merge {json.dumps(CHANGES)}", f"send ABC-3 build {json.dumps(CHANGES)}",
                f"send ABC-2 build {json.dumps(CHANGES)}", f"send ABC-1 spec {json.dumps(CHANGES)}",
                *TAIL,
            ],
        ),
        # full lanes send nothing, however long the queues; a free spec slot goes to Todo
        (
            {"ABC-1": BUILD, "ABC-2": tk("build", "c2"), "ABC-3": SPEC1, "ABC-4": tk("spec", "c4"), "ABC-5": tk("merge", "c5"),
             "ABC-6": queued("build-queued", CHANGES, "1")},
            TAIL,
        ),
        ({"ABC-1": BUILD, "ABC-2": tk("build", "c2"), "ABC-4": tk("merge", "c4")}, ["start-todo", "start-todo", *TODO]),
        ({"ABC-1": BUILD, "ABC-2": tk("build", "c2"), "ABC-3": SPEC1, "ABC-4": tk("merge", "c4")}, ["start-todo", *TODO]),
        # a queued spec approval: user check, model switch, send
        (
            {"ABC-1": queued("build-queued", USER_SPEC, "1", approvalItemId="it1")},
            [
                'user-check ABC-1 th9 it1 words="ship it\\nnow"', CONFIGURE, f"send ABC-1 build {json.dumps(USER_SPEC)}",
                "start-todo", "start-todo", *TODO,
            ],
        ),
        # an auto spec approval: policy check, model switch, send
        (
            {"ABC-1": queued("build-queued", AUTO_SPEC, "1"), "ABC-2": BUILD, "ABC-3": SPEC1, "ABC-4": tk("spec", "c4")},
            [f"run python3 {S}/approval_policy.py auto ABC-1 spec", CONFIGURE, f"send ABC-1 build {json.dumps(AUTO_SPEC)}", *TAIL],
        ),
        # merge approvals: head check, and the auto one also checks the rule
        (
            {"ABC-1": queued("merge-queued", USER_MERGE, "1", pr=5, headSha="a" * 40)},
            ["head-check ABC-1 pr=5 head=" + "a" * 40, f"send ABC-1 merge {json.dumps(USER_MERGE)}", "start-todo", "start-todo", *TODO],
        ),
        (
            {"ABC-1": queued("merge-queued", AUTO_MERGE, "1", pr=5, headSha="b" * 40), "ABC-2": BUILD, "ABC-3": SPEC1, "ABC-4": tk("spec", "c4")},
            ["head-check ABC-1 pr=5 head=" + "b" * 40, f"run python3 {S}/cos_approve_pr.py ABC-1 --auto", f"send ABC-1 merge {json.dumps(AUTO_MERGE)}", *TAIL],
        ),
        # a ticket under an older thread continues in a new child; a queued ticket with no relay is rebuilt
        (
            {"ABC-1": queued("build-queued", USER_SPEC, "1", approvalItemId="it1", parentThreadId="old"), "ABC-2": BUILD, "ABC-3": SPEC1, "ABC-4": tk("spec", "c4")},
            ['user-check ABC-1 th9 it1 words="ship it\\nnow"', "continuation ABC-1 build", *TAIL],
        ),
        (
            {"ABC-1": {**tk("build-queued", "q1"), "queuedAt": "2026-11-08T01:00:00Z"}, "ABC-2": BUILD, "ABC-3": SPEC1, "ABC-4": tk("spec", "c4")},
            ["rebuild-relay ABC-1", *TAIL],
        ),
    ],
)
def test_act_plan_slot_fill(tmp_path, capsys, tickets, want):
    out = run(tmp_path, capsys, {"tickets": tickets}, "notice:zz", "--after-reads")
    assert out == want


FRESH = {"pm": {"lastDailyAt": "2026-11-08T03:00:00Z"}}
LIMITED = {"rateLimitedAt": NOW}
OPEN = ["start-todo", "start-todo", *TODO]
OFF = ["report", ROTATION]


@pytest.mark.parametrize(
    "state, trigger, want",
    [
        # hygiene: always on start; on user and wake when due or malformed; never on a notice; prune on full passes
        ({"pm": {"lastDailyAt": "2026-11-07T11:00:00Z"}}, "user", ["hygiene", "prune", *OPEN]),
        ({"pm": {"lastDailyAt": "2026-11-07T13:00:00Z"}}, "user", ["prune", *OPEN]),
        ({"pm": {"lastDailyAt": "yesterday"}}, "wake", ["hygiene", "prune", *OPEN]),
        ({"pm": None}, "user", ["hygiene", "prune", *OPEN]),
        (FRESH, "start", ["hygiene", "prune", *OPEN]),
        ({"pm": {}}, "notice:zz", OPEN),
        # rate limit with the wake task past: delete and clear, then tick again before anything else
        ({**LIMITED, "wakeTaskId": "w1", "wakeAt": "2026-11-08T11:00:00Z"}, "user", ["delete-wake w1", "clear-rate-limit", "tick --after-reads"]),
        ({**LIMITED, "wakeAt": None}, "wake", ["clear-rate-limit", "tick --after-reads"]),
        # future wake and no task: schedule it (ms until wakeAt plus 2 minutes, from 60000 to 6 hours); no hygiene, fill or observe
        ({**LIMITED, "wakeAt": "2026-11-08T12:30:00Z"}, "user", ["schedule-wake everyMs=1920000", "prune", *OFF]),
        ({**LIMITED, "wakeAt": "2026-11-09T12:30:00Z"}, "user", ["schedule-wake everyMs=21600000", "prune", *OFF]),
        ({**LIMITED, "wakeTaskId": "w1", "wakeAt": "2026-11-08T12:30:00Z"}, "user", ["prune", *OFF]),
        # a notice turn only schedules the wake, never clears the limit
        ({**LIMITED, "wakeAt": None}, "notice:zz", OFF),
        ({**LIMITED, "wakeAt": "2026-11-08T11:00:00Z"}, "notice:zz", OFF),
        ({**LIMITED, "wakeAt": "2026-11-08T12:00:20Z"}, "notice:zz", ["schedule-wake everyMs=140000", *OFF]),
        # rotation set: no observe; retired threads without archivedAt are archived before the rotation check
        (
            {"rotation": {"from": "x", "to": ME, "startedAt": NOW}, "retiredThreads": [{"threadId": "r1"}, {"threadId": "r2", "archivedAt": NOW}]},
            "notice:zz", ["start-todo", "start-todo", "report (filling stopped: spec slot free)", "archive r1", ROTATION],
        ),
    ],
)
def test_act_plan_pre_steps_and_gates(tmp_path, capsys, state, trigger, want):
    assert run(tmp_path, capsys, {"tickets": {}, **state}, trigger, "--after-reads") == want


def test_status_act_plan_is_archive_and_rotation_check(tmp_path, capsys):
    state = {"tickets": {"ABC-1": queued("build-queued", CHANGES, "1")}, "retiredThreads": [{"threadId": "r1"}], "paused": True}
    assert run(tmp_path, capsys, state, "status", "--after-reads") == ["archive r1", ROTATION]


@pytest.mark.parametrize(
    "content, args, out",
    [
        (None, ["--thread", ME, "--trigger", "start"], "tick --after-reads"),
        ("{not json", ["--thread", ME, "--trigger", "user"], "cos_tick: unreadable state file"),
        ('{"tickets": []}', ["--thread", ME, "--trigger", "user"], "cos_tick: unreadable state file"),
        ("{}", ["--thread", ME, "--trigger", "notice"], "cos_tick: argument --trigger: bad trigger 'notice'"),
        ("{}", ["--thread", ME, "--trigger", "user", "--now", "soon"], "cos_tick: argument --now: bad time 'soon'"),
        ("{}", ["--trigger", "user"], "cos_tick: the following arguments are required: --thread"),
    ],
)
def test_bad_input_exits_2_with_a_cos_tick_line(tmp_path, capsys, content, args, out):
    f = tmp_path / "state.json"
    if content:
        f.write_text(content)
    if content is None:  # a missing state file is empty state
        assert cos_tick.main([*args, "--file", str(f)]) == 0
        assert out in capsys.readouterr().out
        return
    with pytest.raises(SystemExit) as e:
        cos_tick.main([*args, "--file", str(f)])
    assert e.value.code == 2
    assert capsys.readouterr().out.strip() == out
