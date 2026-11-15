import contextlib
import importlib.util
import re
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_state", Path(__file__).with_name("cos_state.py"))
cos_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_state)

OLD = "2020-01-01T00:00:00Z"
A, B = "a" * 40, "b" * 40
HELD = {"head": A, "itemId": "m1"}  # what an op sends; the script adds at
HELD_AT = {**HELD, "at": OLD}  # what the state file holds


def stage(to, **sets):
    return {"op": "stage", "ticket": "ABC-1", "stage": to, "status": "s", **({"set": sets} if sets else {})}


def set_(**sets):
    return {"op": "set", "ticket": "ABC-1", "set": sets}


@pytest.mark.parametrize(
    "stage_now, held, op, stamp, want_held",
    [
        # the stamp: awaiting-review to awaiting-merge on the same head keeps lastSeenAt, any other move restamps
        ("awaiting-review", None, stage("awaiting-merge", headSha=A), "kept", None),
        ("awaiting-review", None, stage("awaiting-merge", headSha=B), "new", None),
        ("build", None, stage("awaiting-review", headSha=A), "new", None),
        ("awaiting-review", None, stage("blocked"), "new", None),
        ("awaiting-merge", None, stage("awaiting-merge", headSha=A), "kept", None),
        # heldApproval: set only in awaiting-review on the ticket's head
        ("awaiting-review", None, set_(heldApproval=HELD), "kept", HELD),
        ("awaiting-review", None, set_(heldApproval={**HELD, "head": B}), "reject: head must equal", None),
        ("awaiting-review", None, set_(heldApproval={k: v for k, v in HELD.items() if k != "itemId"}), "reject: needs an object", None),
        ("awaiting-review", None, set_(heldApproval="yes"), "reject: needs an object", None),
        ("build", None, stage("awaiting-review", headSha="abc", heldApproval={**HELD, "head": "abc"}), "reject: needs an object", None),
        ("awaiting-merge", None, set_(heldApproval=HELD), "reject: only belongs to awaiting-review", None),
        ("awaiting-merge", None, stage("awaiting-merge", heldApproval=HELD), "reject: only belongs to awaiting-review", None),
        # cleared by a head change, by a stage op to any other stage, and by the user's hold
        ("awaiting-review", HELD_AT, set_(headSha=B), "new", None),
        ("awaiting-review", HELD_AT, stage("awaiting-review", headSha=B), "new", None),
        ("awaiting-review", HELD_AT, stage("awaiting-merge", headSha=A), "kept", None),
        ("awaiting-review", HELD_AT, stage("build"), "kept", None),
        ("awaiting-review", HELD_AT, set_(heldApproval=None), "new", None),
        ("awaiting-review", HELD_AT, set_(note="n"), "kept", HELD),
    ],
)
def test_awaiting_review_stamp_and_held_approval(stage_now, held, op, stamp, want_held):
    t = {"stage": stage_now, "headSha": A, "lastSeenAt": OLD, "status": "s", "pendingRelay": None, "queuedAt": None}
    if held:
        t["heldApproval"] = held
    state = {"tickets": {"ABC-1": t}}
    if stamp.startswith("reject"):
        with pytest.raises(cos_state.Reject, match=stamp.removeprefix("reject: ")):
            cos_state.apply_ops(state, [op])
        return
    new, _, _ = cos_state.apply_ops(state, [op])
    got = new["tickets"]["ABC-1"]
    assert (got["lastSeenAt"] == OLD) == (stamp == "kept")
    assert {k: v for k, v in (got.get("heldApproval") or {}).items() if k != "at"} == (want_held or {})
    shown = cos_state.show(new).splitlines()
    assert f"awaiting-review={int(got['stage'] == 'awaiting-review')}" in shown[1]
    if got["stage"] == "awaiting-review":
        assert any(l.startswith(f"ABC-1 awaiting-review seen={got['lastSeenAt']}") for l in shown)


RELAYED = {"head": A, "at": OLD}


@pytest.mark.parametrize(
    "op, want",
    [
        (set_(changesRelayed={**RELAYED, "at": "2026-11-02T10:00:00Z"}), {**RELAYED, "at": "2026-11-02T10:00:00Z"}),
        (set_(changesRelayed=None), None),
        (stage("build", headSha=B), RELAYED),  # nothing but a set clears it
        (set_(changesRelayed={**RELAYED, "head": "abc"}), "reject"),
        (set_(changesRelayed={"head": A}), "reject"),
        (set_(changesRelayed={**RELAYED, "at": ""}), "reject"),
        (set_(changesRelayed={**RELAYED, "at": "2026-11-02T10:00:00"}), "reject"),  # no zone: the review check could not compare it
        (set_(changesRelayed="x"), "reject"),
    ],
)
def test_changes_relayed_is_a_validated_record_the_script_never_clears(op, want):
    state = {"tickets": {"ABC-1": {"stage": "awaiting-review", "headSha": A, "lastSeenAt": OLD, "status": "s", "changesRelayed": RELAYED}}}
    if want == "reject":
        with pytest.raises(cos_state.Reject, match="changesRelayed needs"):
            cos_state.apply_ops(state, [op])
    else:
        assert cos_state.apply_ops(state, [op])[0]["tickets"]["ABC-1"]["changesRelayed"] == want


@pytest.mark.parametrize(
    "stage_now, op, want",
    [
        ("build", set_(conflictHead=A), A),
        ("awaiting-review", set_(conflictHead=None), None),
        ("build", stage("awaiting-review", headSha=B), A),  # nothing but a set clears it
        ("build", set_(conflictHead="abc"), "reject"),
        ("build", set_(conflictHead=A.upper()), "reject"),  # not lower-case hex
        ("build", set_(conflictHead={"head": A}), "reject"),
    ],
)
def test_conflict_head_is_a_full_sha_the_script_never_clears(stage_now, op, want):
    state = {"tickets": {"ABC-1": {"stage": stage_now, "headSha": A, "lastSeenAt": OLD, "status": "s", "conflictHead": A}}}
    if want == "reject":
        with pytest.raises(cos_state.Reject, match="conflictHead needs"):
            cos_state.apply_ops(state, [op])
    else:
        assert cos_state.apply_ops(state, [op])[0]["tickets"]["ABC-1"]["conflictHead"] == want


@pytest.mark.parametrize(
    "stage_now, op, want",
    [
        ("merge", set_(noApproval=True), True),
        ("blocked", set_(noApproval=True), True),
        ("awaiting-merge", set_(noApproval=True), "reject"),
        ("merge", set_(noApproval=False), "reject"),
        ("merge", set_(noApproval=None), "reject"),
        ("merge", stage("blocked"), True),  # kept so the resumed run still carries no approval
        ("merge", stage("awaiting-merge"), None),
    ],
)
def test_no_approval_belongs_to_the_merge_lane(stage_now, op, want):
    t = {"stage": stage_now, "headSha": A, "lastSeenAt": OLD, "status": "s", "noApproval": True}
    state = {"tickets": {"ABC-1": {k: v for k, v in t.items() if k != "noApproval"} if op["op"] == "set" else t}}
    if want == "reject":
        with pytest.raises(cos_state.Reject):
            cos_state.apply_ops(state, [op])
        return
    new, _, _ = cos_state.apply_ops(state, [op])
    assert new["tickets"]["ABC-1"].get("noApproval") == want


RUN = {"startedAt": OLD, "itemId": "turn-item:message:m1", "started": [], "drain": None, "endedAt": None, "endReason": None}
START = {"op": "start", "ticket": "ABC-2", "firstTaskId": "t", "childThreadId": "c", "parentThreadId": "p", "status": "s", "title": "x"}


# stageAt is stamped by start and by a stage change, kept by a same-stage op, never set by hand
@pytest.mark.parametrize(
    "op, key, want",
    [(START, "ABC-2", True), (stage("build"), "ABC-1", True), (stage("awaiting-merge"), "ABC-1", False), (set_(stageAt=OLD), "ABC-1", None), (stage("build", stageAt=OLD), "ABC-1", None)],
)
def test_stage_at_is_stamped_on_a_stage_change_only(op, key, want):
    state = {"tickets": {"ABC-1": {"stage": "awaiting-merge", "status": "s", "stageAt": OLD}}}
    if want is None:
        with pytest.raises(cos_state.Reject, match="stageAt is stamped"):
            cos_state.apply_ops(state, [op])
        return
    assert (cos_state.apply_ops(state, [op])[0]["tickets"][key]["stageAt"] != OLD) == want


# The noHands run record: only the no-hands op writes it, and only the moves no_hands.py makes; the start op appends to it while the run has not ended.
ENDED = {**RUN, "endedAt": OLD, "endReason": "x"}


@pytest.mark.parametrize(
    "state, ops, err, started",
    [
        ({}, [{"op": "no-hands", "set": RUN}], None, []),
        ({"noHands": ENDED}, [{"op": "no-hands", "set": {**RUN, "startedAt": "2020-01-02T00:00:00Z", "itemId": "turn-item:message:m2"}}], None, []),
        ({"noHands": RUN}, [{"op": "no-hands", "set": {"drain": "ticket-cap"}}], None, []),
        ({"noHands": RUN}, [{"op": "no-hands", "set": {"endedAt": OLD, "endReason": "x"}}], None, []),
        ({"noHands": RUN}, [START, START], None, ["ABC-2"]),
        ({"noHands": ENDED}, [START], None, []),
        ({}, [START], None, None),
        ({}, [{"op": "no-hands", "set": {"drain": "x"}}], "drain is set once", None),
        ({}, [{"op": "no-hands", "set": {**RUN, "startedAt": "2026-11-08"}}], "time zone", None),
        ({}, [{"op": "no-hands", "set": {**RUN, "cap": 99}}], "unknown noHands key", None),
        ({}, [{"op": "top", "set": {"noHands": RUN}}], "unknown top-level key noHands", None),
        # a new run cannot replay the last run's message, or start no later than the last run ended
        ({"noHands": ENDED}, [{"op": "no-hands", "set": {**RUN, "startedAt": "2020-01-02T00:00:00Z"}}], "new itemId", None),
        ({"noHands": ENDED}, [{"op": "no-hands", "set": {**RUN, "itemId": "turn-item:message:m2"}}], "new itemId", None),
        # a state edit cannot reopen an ended run, empty started, change itemId, or replace a run that is active
        ({"noHands": ENDED}, [{"op": "no-hands", "set": {"endedAt": None, "endReason": None}}], "ends with an endedAt", None),
        ({"noHands": ENDED}, [{"op": "no-hands", "set": {"drain": "x"}}], "drain is set once", None),
        ({"noHands": ENDED}, [{"op": "no-hands", "set": {**RUN, "started": ["ABC-1"]}}], "starts with started", None),
        ({"noHands": {**RUN, "started": ["ABC-1"]}}, [{"op": "no-hands", "set": {"started": []}}], "set a whole new record", None),
        ({"noHands": RUN}, [{"op": "no-hands", "set": {"itemId": "turn-item:message:m9"}}], "set a whole new record", None),
        ({"noHands": RUN}, [{"op": "no-hands", "set": {**RUN, "startedAt": "2026-11-09T10:00:00Z"}}], "a run is active", None),
        ({"noHands": {**RUN, "drain": "a"}}, [{"op": "no-hands", "set": {"drain": "b"}}], "drain is set once", None),
    ],
)
def test_no_hands_record(state, ops, err, started):
    if err:
        with pytest.raises(cos_state.Reject, match=err):
            cos_state.apply_ops(state, ops)
        return
    new = cos_state.apply_ops(state, ops)[0]
    assert new.get("noHands", {}).get("started") == started


# skillCommit is the full lowercase sha from cos_rotation_check.py --skill-commit, or null
@pytest.mark.parametrize("value, ok", [("8ddace1", 0), (A.upper(), 0), ("a" * 41, 0), (123, 0), (A, 1), (None, 1)])
def test_top_skill_commit_must_be_a_full_sha(value, ok):
    ops = [{"op": "top", "set": {"skillCommit": value}}]
    with pytest.raises(cos_state.Reject, match="full 40-character sha") if not ok else contextlib.nullcontext():
        assert cos_state.apply_ops({}, ops)[0]["skillCommit"] == value


START_ABC1 = {"op": "start", "ticket": "ABC-1", "firstTaskId": "t", "childThreadId": "c", "parentThreadId": "p", "status": "s", "title": "T"}
HAS_ABC1 = {"tickets": {"ABC-1": {"stage": "build", "status": "s"}}, "merged": {}}


@pytest.mark.parametrize(
    "state, op, lists, gone_and_kept",
    [
        # start, merged and drop take the ticket out of both saved lists and leave each list's `at` alone
        ({"tickets": {}, "merged": {}}, START_ABC1, "file", True),
        (HAS_ABC1, {"op": "merged", "ticket": "ABC-1", "pr": 5}, "file", True),
        (HAS_ABC1, {"op": "drop", "ticket": "ABC-1"}, "file", True),
        # a repeat merged prints unchanged and still clears a stale entry
        ({"tickets": {}, "merged": {"ABC-1": {"pr": 5, "at": "2999-01-01T00:00:00Z"}}}, {"op": "merged", "ticket": "ABC-1", "pr": 5}, "file", True),
        # a missing lists file or a link in its place never changes the result
        (HAS_ABC1, {"op": "drop", "ticket": "ABC-1"}, "missing", False),
        (HAS_ABC1, {"op": "drop", "ticket": "ABC-1"}, "link", False),
    ],
)
def test_state_ops_remove_the_ticket_from_the_saved_lists(tmp_path, capsys, state, op, lists, gone_and_kept):
    import json

    def block(*ids):
        return {"at": OLD, "list": [{"identifier": i} for i in ids]}

    held = {"todo": block("ABC-1", "ABC-2"), "backlog": block("ABC-3", "ABC-1")}
    (tmp_path / "state.json").write_text(json.dumps(state))
    target = tmp_path / ("target.json" if lists == "link" else "tracker-lists.json")
    if lists != "missing":
        target.write_text(json.dumps(held))
    if lists == "link":
        (tmp_path / "tracker-lists.json").symlink_to(target)
    code = cos_state.apply_file(tmp_path / "state.json", [op])
    assert code == 0
    assert capsys.readouterr().out.split("\n")[0] in ("saved", "unchanged")
    if lists == "missing":
        assert not target.exists()
    elif gone_and_kept:
        got = json.loads(target.read_text())
        assert got == {"todo": block("ABC-2"), "backlog": block("ABC-3")}
    else:
        assert json.loads(target.read_text()) == held


# takeover is null, or {startedAt with a zone, not in the future; mode take-over|resume} and nothing else
@pytest.mark.parametrize(
    "value, ok",
    [
        (None, 1),
        ({"startedAt": OLD, "mode": "take-over"}, 1),
        ({"startedAt": OLD, "mode": "resume"}, 1),
        ({"startedAt": OLD, "mode": "reset"}, 0),
        ({"mode": "resume"}, 0),
        ({"startedAt": OLD, "mode": "resume", "x": 1}, 0),
        ("take-over", 0),
    ],
)
def test_top_takeover_is_null_or_a_marker(value, ok):
    ops = [{"op": "top", "set": {"takeover": value}}]
    with pytest.raises(cos_state.Reject, match="takeover needs") if not ok else contextlib.nullcontext():
        new = cos_state.apply_ops({}, ops)[0]
        assert new["takeover"] == value


# ganttPluginVersion is dot-separated integers, or null
@pytest.mark.parametrize("value, ok", [("v1", 0), ("1.x", 0), ("1.", 0), ("", 0), (1, 0), ("0.1.12", 1), ("1", 1), (None, 1)])
def test_top_gantt_plugin_version_must_be_dotted_integers(value, ok):
    ops = [{"op": "top", "set": {"ganttPluginVersion": value}}]
    with pytest.raises(cos_state.Reject, match="ganttPluginVersion needs") if not ok else contextlib.nullcontext():
        assert cos_state.apply_ops({}, ops)[0]["ganttPluginVersion"] == value


# the since time in a status is the ticket's stageAt, filled from {since}; a hand-typed one is rejected
@pytest.mark.parametrize(
    "op, ok",
    [
        ({**START, "status": "spec since {since}: x"}, True),
        ({**stage("build"), "status": "build since {since}: x"}, True),
        ({**stage("awaiting-merge"), "status": "awaiting-merge since {since}: x"}, True),  # same stage: the current stageAt
        (set_(status="awaiting-merge since {since}: x"), True),
        (set_(status='blocked: "stuck since 5 days"'), True),  # quoted words are left alone
        (set_(status="awaiting-merge since {since}: x. Risk: Low (unchanged since 2024)."), True),  # a Risk: reason is left alone
        ({**stage("build"), "status": "build since 5:20am: x"}, False),
        (set_(status="awaiting-merge since 14:05: x"), False),
    ],
)
def test_status_since_time_is_the_stage_at_stamp(op, ok):
    state = {"tickets": {"ABC-1": {"stage": "awaiting-merge", "status": "s", "stageAt": OLD}}}
    if not ok:
        with pytest.raises(cos_state.Reject, match="write since {since}"):
            cos_state.apply_ops(state, [op])
        return
    got = cos_state.apply_ops(state, [op])[0]["tickets"][op.get("ticket")]
    assert got["status"] == (op.get("set") or op)["status"].replace("{since}", cos_state.stamp_text(got["stageAt"]))


@pytest.mark.parametrize("given", [{}, {"at": OLD}])
def test_held_approval_at_is_stamped_and_never_given(given):
    state = {"tickets": {"ABC-1": {"stage": "awaiting-review", "headSha": A, "lastSeenAt": OLD, "status": "s"}}}
    if given:
        with pytest.raises(cos_state.Reject, match="at is stamped"):
            cos_state.apply_ops(state, [set_(heldApproval={**HELD, **given})])
    else:
        assert cos_state.apply_ops(state, [set_(heldApproval=HELD)])[0]["tickets"]["ABC-1"]["heldApproval"]["at"] != OLD


def test_now_prints_the_stamp_text_and_the_iso_form(capsys):
    assert cos_state.main(["now"]) == 0 and re.fullmatch(r"\d{4}-\d\d-\d\d (1[0-2]|[1-9]):\d\d (am|pm) UTC", capsys.readouterr().out.strip())
    assert cos_state.main(["now", "--iso"]) == 0 and cos_state.parse(capsys.readouterr().out.strip())
    assert cos_state.stamp_text("2026-11-15T17:05:00Z") == "2026-11-15 5:05 pm UTC"


def test_show_time_today_is_12_hour_without_a_space_and_other_days_stay_iso():
    now = cos_state.datetime.now(cos_state.timezone.utc).replace(hour=14, minute=5, second=0, microsecond=0)
    assert cos_state.t(now.strftime("%Y-%m-%dT%H:%M:%SZ")) == "2:05pm"
    assert cos_state.t(OLD) == OLD
    assert cos_state.t(None) == "-"
