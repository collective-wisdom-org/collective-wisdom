import json

import pytest

import cos_route
import project_config

ME = "me"


def tk(stage, **kw):
    return {"stage": stage, "parentThreadId": ME, **kw}


def run(tmp_path, capsys, monkeypatch, tickets, caller, setting="off", thread=None, chief=ME, ticket="ABC-1"):
    monkeypatch.setattr(project_config, "review_after_conflict", lambda: setting)
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"chiefThreadId": chief, "tickets": tickets}))
    args = [ticket, caller, "--file", str(f)] + (["--thread", thread] if thread else [])
    code = cos_route.main(args)
    return code, capsys.readouterr().out.splitlines()


FULL_BUILD = {"ABC-8": tk("build"), "ABC-9": tk("build")}
QUEUED_BUILD = {"ABC-8": tk("build-queued", pendingRelay="x")}
ONE_EACH = {"ABC-7": tk("spec"), "ABC-8": tk("build"), "ABC-9": tk("merge")}
OVER_CAP = {"ABC-5": tk("spec"), "ABC-6": tk("spec"), "ABC-7": tk("build"), "ABC-8": tk("build"), "ABC-9": tk("build")}  # adopt can pass the cap


@pytest.mark.parametrize(
    "caller, stage, others, setting, want",
    [
        # one row per caller and stage pair of the table, lanes empty
        ("approve-spec", "awaiting-build", {}, "off", "send build"),
        ("approve-merge", "awaiting-merge", {}, "off", "send merge"),
        ("changes", "awaiting-build", {}, "off", "send spec"),
        ("changes", "awaiting-review", {}, "off", "send build"),
        ("changes", "awaiting-merge", {}, "off", "send build"),
        ("reviewer-changes", "awaiting-review", {}, "off", "send build"),
        ("head-moved", "awaiting-review", {}, "off", "send build"),
        ("head-moved", "awaiting-merge", {}, "off", "send build"),
        ("head-moved", "merge-queued", {}, "off", "send build"),
        ("conflict-keep", "awaiting-merge", {}, "off", "send merge"),
        ("conflict-keep", "merge-queued", {}, "off", "send merge"),
        ("conflict-withdraw", "awaiting-review", {}, "on", "send build"),
        ("conflict-withdraw", "merge", {}, "on", "send build"),
        ("conflict-withdraw", "awaiting-merge", {}, "off", "send merge"),
        ("conflict-withdraw", "merge-queued", {}, "off", "send merge"),
        # a full lane, a waiting queue and the cap queue it; another lane's queue does not
        ("approve-spec", "awaiting-build", FULL_BUILD, "off", "queue build"),
        ("approve-spec", "awaiting-build", QUEUED_BUILD, "off", "queue build"),
        ("approve-merge", "awaiting-merge", QUEUED_BUILD, "off", "send merge"),
        ("approve-merge", "awaiting-merge", OVER_CAP, "off", "queue merge"),
        ("changes", "awaiting-build", ONE_EACH, "off", "send spec"),
        # a ticket that holds the merge slot does not block its own send; the queue it sits in is not "someone waiting"
        ("conflict-withdraw", "merge", {}, "off", "send merge"),
        ("conflict-keep", "merge-queued", {"ABC-8": tk("merge-queued", pendingRelay="x")}, "off", "queue merge"),
        # callers that do not apply from the stage
        ("approve-merge", "awaiting-build", {}, "off", "no"),
        ("changes", "build", {}, "off", "no"),
        ("conflict-keep", "awaiting-merge", {}, "on", "no"),
        ("resume", "awaiting-review", {}, "off", "no"),
    ],
)
def test_lane_and_send_or_queue(tmp_path, capsys, monkeypatch, caller, stage, others, setting, want):
    code, out = run(tmp_path, capsys, monkeypatch, {"ABC-1": tk(stage), **others}, caller, setting)
    assert out[-1].startswith(f"route: {want}")
    assert code == (1 if want == "no" else 0)
    ops = [json.loads(x[len("stage: "):]) for x in out if x.startswith("stage: ")]
    if want != "no":
        lane = want.split()[1]
        assert ops == [{"op": "stage", "ticket": "ABC-1", "stage": lane if want.startswith("send") else f"{lane}-queued", "status": "<status line>"}]


@pytest.mark.parametrize(
    "caller, resume, lane",
    [("answer", "spec", "spec"), ("resume", "build", "build"), ("rate-limit", "merge", "merge"), ("resume", None, None)],
)
def test_blocked_tickets_go_to_their_resume_stage(tmp_path, capsys, monkeypatch, caller, resume, lane):
    code, out = run(tmp_path, capsys, monkeypatch, {"ABC-1": tk("blocked", resumeStage=resume)}, caller)
    assert out[-1].startswith(f"route: send {lane}" if lane else "route: no ")


@pytest.mark.parametrize(
    "parent, chief, thread, last, moving",
    [
        (ME, ME, None, "route: send build", False),
        (None, ME, None, "route: send build", True),  # no parent known: nobody hears the run end
        ("old", ME, None, "route: continuation build", False),
        ("old", None, "old", "route: send build", False),  # --thread stands in for a missing chiefThreadId
        ("old", None, ME, "route: continuation build", False),
    ],
)
def test_parent_thread_decides_continuation_and_the_moving_line(tmp_path, capsys, monkeypatch, parent, chief, thread, last, moving):
    t = {"stage": "awaiting-review", "parentThreadId": parent}
    _, out = run(tmp_path, capsys, monkeypatch, {"ABC-1": t}, "reviewer-changes", thread=thread, chief=chief)
    assert out[-1] == last
    assert any(x.startswith("moving: ABC-1: I may not hear") for x in out) == moving
    assert any(x.startswith("fallback: ") for x in out) == (last.startswith("route: continuation"))


@pytest.mark.parametrize("ticket, caller", [("ABC-1", "nope"), ("bad", "resume"), ("ABC-5", "resume")])
def test_bad_arguments_and_unknown_tickets_exit_2(tmp_path, capsys, monkeypatch, ticket, caller):
    monkeypatch.setattr(project_config, "review_after_conflict", lambda: "off")
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"tickets": {"ABC-1": tk("blocked")}}))
    try:
        code = cos_route.main([ticket, caller, "--file", str(f)])
    except SystemExit as e:  # argparse rejects a bad caller
        code = e.code
    assert code == 2
    assert capsys.readouterr().out.startswith("route: cannot ")
    assert cos_route.main(["ABC-1", "resume", "--file", str(tmp_path / "missing.json")]) == 2
