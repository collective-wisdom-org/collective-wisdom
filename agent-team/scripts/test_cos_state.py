import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_state", Path(__file__).with_name("cos_state.py"))
cos_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_state)

OLD = "2020-01-01T00:00:00Z"
A, B = "a" * 40, "b" * 40
HELD = {"head": A, "itemId": "m1", "at": OLD}


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
        ("awaiting-review", HELD, set_(headSha=B), "new", None),
        ("awaiting-review", HELD, stage("awaiting-review", headSha=B), "new", None),
        ("awaiting-review", HELD, stage("awaiting-merge", headSha=A), "kept", None),
        ("awaiting-review", HELD, stage("build"), "kept", None),
        ("awaiting-review", HELD, set_(heldApproval=None), "new", None),
        ("awaiting-review", HELD, set_(note="n"), "kept", HELD),
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
    assert got.get("heldApproval") == want_held
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
