import importlib.util
import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cos_state = load("cos_state")
cos_user_check = load("cos_user_check")


def ticket(stage="build", **kw):
    return {"stage": stage, "childThreadId": "c1", "status": "s", "pendingRelay": None,
            "approvalItemId": None, "queuedAt": None, "resumeStage": None, **kw}


STATE = {
    "paused": False,
    "tickets": {"ABC-1": ticket(), "ABC-2": ticket("awaiting-build"), "ABC-4": ticket("awaiting-build")},
    "merged": {"ABC-8": 7, "ABC-9": {"pr": 9, "at": "2020-01-01T00:00:00Z"}},
    "retiredThreads": [{"threadId": "t1", "retiredAt": "2026-11-01T00:00:00Z", "archivedAt": None}],
    "pm": {},
    "staleKey": "x",
}
START = {"op": "start", "ticket": "ABC-3", "firstTaskId": "f", "childThreadId": "c3", "parentThreadId": "t9",
         "status": "s", "title": "Add X"}
QUEUE = {"op": "stage", "ticket": "ABC-2", "stage": "build-queued", "status": "q",
         "set": {"pendingRelay": "go"}}


@pytest.mark.parametrize("ops", [
    [START],
    [QUEUE],
    [{"op": "stage", "ticket": "ABC-1", "stage": "blocked", "status": "b", "set": {"note": "n"}}],
    [{"op": "stage", "ticket": "ABC-1", "stage": "awaiting-build", "status": "w"}],
    [{"op": "set", "ticket": "ABC-1", "set": {"headSha": "abc", "lastPosition": 4}}],
    [{"op": "merged", "ticket": "ABC-1", "pr": 5}],
    [{"op": "drop", "ticket": "ABC-1"}],
    [{"op": "top", "set": {"paused": True, "rotation": {"from": "a", "to": None}}}],
    [{"op": "pm", "set": {"rankedAt": "x"}}],
    [{"op": "retire", "threadId": "t2"}],
    [{"op": "archive", "threadId": "t1", "archivedAt": "2026-11-02T00:00:00Z"}],
    [{"op": "unretire", "threadId": "t1"}],
    [{"op": "prune"}],
])
def test_apply_twice_is_idempotent(tmp_path, capsys, ops):
    path = tmp_path / "state.json"
    path.write_text(json.dumps(STATE))
    assert cos_state.apply_file(path, ops) == 0
    assert capsys.readouterr().out.startswith("saved")
    first = path.read_bytes()
    for op in ops:
        if op["op"] == "stage" and op["stage"] in ("awaiting-build", "blocked"):
            assert json.loads(first)["tickets"][op["ticket"]]["lastSeenAt"]
    assert cos_state.apply_file(path, ops) == 0
    assert capsys.readouterr().out.startswith("unchanged")
    assert path.read_bytes() == first


@pytest.mark.parametrize("old", ["awaiting-spec", "awaiting-build"])
def test_old_stage_name_loads_as_awaiting_build(tmp_path, capsys, old):
    path = tmp_path / "state.json"
    seen = "2026-11-01T00:00:00Z"
    state = {**STATE, "tickets": {"ABC-2": ticket(old, lastSeenAt=seen)}}
    path.write_text(json.dumps(state))
    assert cos_state.load(path)["tickets"]["ABC-2"]["stage"] == "awaiting-build"
    assert cos_state.main(["--file", str(path), "show"]) == 0
    assert "ABC-2 awaiting-build" in capsys.readouterr().out
    ops = [{"op": "set", "ticket": "ABC-2", "set": {"lastPosition": 4}}]
    assert cos_state.apply_file(path, ops) == 0
    saved = json.loads(path.read_text())["tickets"]["ABC-2"]
    assert (saved["stage"], saved["lastSeenAt"]) == ("awaiting-build", seen)


@pytest.mark.parametrize("ops, stamped", [
    ([START], True),
    ([{"op": "stage", "ticket": "ABC-1", "stage": "merge", "status": "m"}], True),
    ([{"op": "stage", "ticket": "ABC-1", "stage": "build", "status": "again"}], False),
    ([{"op": "stage", "ticket": "ABC-1", "stage": "build", "status": "again", "set": {"childThreadId": "c9"}}], True),
    ([{"op": "set", "ticket": "ABC-1", "set": {"childThreadId": "c9"}}], True),
    ([{"op": "set", "ticket": "ABC-1", "set": {"note": "x"}}], False),
    ([{"op": "stage", "ticket": "ABC-1", "stage": "awaiting-build", "status": "w"}], False),
])
def test_relay_and_child_start_stamp_lastRelayAt(ops, stamped):
    new, _, _ = cos_state.apply_ops(STATE, ops)
    assert ("lastRelayAt" in new) == stamped


OLD_SEEN = "2020-01-01T00:00:00Z"


@pytest.mark.parametrize("stage, op, restamped", [
    ("awaiting-merge", {"op": "set", "set": {"headSha": "b" * 40}}, True),
    ("awaiting-merge", {"op": "stage", "stage": "awaiting-merge", "status": "s", "set": {"headSha": "b" * 40}}, True),
    ("awaiting-merge", {"op": "set", "set": {"headSha": "a" * 40}}, False),
    ("awaiting-merge", {"op": "stage", "stage": "awaiting-merge", "status": "s"}, False),
    ("awaiting-merge", {"op": "set", "set": {"pr": "7"}}, False),
    ("build", {"op": "set", "set": {"headSha": "b" * 40}}, False),
])
def test_new_head_in_a_stamped_stage_restamps_lastSeenAt(stage, op, restamped):
    state = {**STATE, "tickets": {"ABC-1": ticket(stage, headSha="a" * 40, lastSeenAt=OLD_SEEN)}}
    new, _, _ = cos_state.apply_ops(state, [{"ticket": "ABC-1", **op}])
    assert (new["tickets"]["ABC-1"]["lastSeenAt"] != OLD_SEEN) == restamped


@pytest.mark.parametrize("bad", [
    {"op": "set", "ticket": "ABC-1", "set": {"bogus": 1}},
    {"op": "set", "ticket": "ABC-1", "set": {"stage": "merge"}},
    {"op": "stage", "ticket": "ABC-1", "stage": "limbo", "status": "s"},
    {"op": "stage", "ticket": "ABC-1", "stage": "merge-queued", "status": "s"},
    {"op": "stage", "ticket": "ABC-1", "stage": "merge"},
    {"op": "stage", "ticket": "ABC-7", "stage": "merge", "status": "s"},
    {"op": "stage", "ticket": "ABC-1", "stage": "awaiting-build", "status": "s", "set": {"lastSeenAt": "2020-01-01T00:00:00Z"}},
    {"op": "set", "ticket": "ABC-4", "set": {"lastSeenAt": "2020-01-01T00:00:00Z"}},
    {"op": "pm", "set": {"rules": ["rank ABC-9 first"]}},
    {"op": "top", "set": {"lastRelayAt": "2026-11-04T00:00:00Z"}},
    {"op": "drop", "ticket": "nope"},
    {"op": "unknown"},
    {k: v for k, v in START.items() if k != "parentThreadId"},
    {"op": "retire", "threadId": "t2", "successor": "t2"},
    {"op": "observe", "kind": "nope"},
    {"op": "observe", "kind": "other:Bad Slug"},
])
def test_invalid_op_changes_nothing(tmp_path, bad):
    path = tmp_path / "state.json"
    path.write_text(json.dumps(STATE))
    before = path.read_bytes()
    assert cos_state.apply_file(path, [START, QUEUE, bad]) == 1
    assert path.read_bytes() == before


@pytest.mark.parametrize("ops, title, code", [
    ([{**START, "title": "  Add X  "}], "Add X", 0),
    ([{k: v for k, v in START.items() if k != "title"}], None, 1),
    ([{**START, "title": "  "}], None, 1),
    ([START, {"op": "set", "ticket": "ABC-3", "set": {"title": "  Later  "}}], "Later", 0),
    ([{**START, "title": "A\x1b]8;;x\x07B\nC"}], "A ]8;;x B C", 0),
    ([{**START, "title": "x" * 300}], "x" * 200, 0),
    ([{**START, "title": 5}], None, 1),
    ([START, {"op": "set", "ticket": "ABC-3", "set": {"title": None}}], None, 1),
])
def test_ticket_title(tmp_path, ops, title, code):
    path = tmp_path / "state.json"
    path.write_text(json.dumps(STATE))
    assert cos_state.apply_file(path, ops) == code
    if code == 0:
        assert json.loads(path.read_text())["tickets"]["ABC-3"]["title"] == title


def ago(hours):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def sight(kind, ticket, hours):
    return {"kind": kind, "ticket": ticket, "at": ago(hours)}


def obs(kind, ticket=None):
    return {"op": "observe", "kind": kind, **({"ticket": ticket} if ticket else {})}


LOST = sight("lost-notice", "ABC-1", 24)
FILED_TODAY = [{"kind": k, "at": ago(2)} for k in ("stall", "rotation-failed", "helper-no-report")]


@pytest.mark.parametrize("seen, filed, ops, notes, sightings, filed_kinds", [
    ([], [], [obs("lost-notice", "ABC-1")], ["hold (1 of 2 sightings)"], 1, []),
    ([LOST], [], [obs("lost-notice", "ABC-2")], ["file (ABC-1 "], 2, ["lost-notice"]),
    ([LOST], [], [obs("lost-notice", "ABC-1")], ["hold (1 of 2 sightings)"], 1, []),
    ([sight("rotation-failed", None, 24)], [], [obs("rotation-failed")], ["file (- "], 2, ["rotation-failed"]),
    ([], [], [obs("other:slow-handoff")], ["file (-"], 1, ["other:slow-handoff"]),
    ([LOST, sight("lost-notice", "ABC-2", 1)], [{"kind": "lost-notice", "at": ago(72)}],
     [obs("lost-notice", "ABC-3")], ["hold (filed "], 3, ["lost-notice"]),
    ([], FILED_TODAY, [obs("other:slow-handoff")], ["hold (3 filed today)"], 1, [f["kind"] for f in FILED_TODAY]),
    ([], [], [obs("other:a"), obs("other:b")], ["file (", "hold (one per turn)"], 2, ["other:a"]),
    (None, None, [obs("lost-notice", "ABC-1")], ["hold (1 of 2 sightings)"], 1, []),
    ([LOST, sight("lost-notice", "ABC-2", 1)], [{"kind": "lost-notice", "at": ago(24 * 8)}],
     [obs("lost-notice", "ABC-3")], ["file ("], 3, ["lost-notice", "lost-notice"]),
    ([], [], [obs("stall"), obs("stall")], ["hold (1 of 2 sightings)", "hold (1 of 2 sightings)"], 1, []),
])
def test_observe_files_on_repeat_within_caps(seen, filed, ops, notes, sightings, filed_kinds):
    state = dict(STATE) if seen is None else {**STATE, "observed": {"sightings": seen, "filed": filed}}  # None: key absent
    new, _, got = cos_state.apply_ops(state, ops)
    assert len(got) == len(notes)
    assert all(n.split(": ", 1)[1].startswith(w) for n, w in zip(got, notes))
    assert len(new["observed"]["sightings"]) == sightings
    assert [f["kind"] for f in new["observed"]["filed"]] == filed_kinds


def test_prune_drops_observed_older_than_a_week():
    old, fresh = ago(24 * 8), ago(1)
    state = {**STATE, "observed": {
        "sightings": [sight("stall", "ABC-1", 24 * 8), sight("stall", "ABC-2", 1)],
        "filed": [{"kind": "stall", "at": old}, {"kind": "lost-notice", "at": fresh}],
    }}
    new, _, _ = cos_state.apply_ops(state, [{"op": "prune"}])
    assert new["observed"] == {
        "sightings": [sight("stall", "ABC-2", 1)], "filed": [{"kind": "lost-notice", "at": fresh}],
    }


@pytest.mark.parametrize("ops, retired, shown", [
    ([{"op": "retire", "threadId": "t2", "successor": "t3"}], ["t1", "t2"], "t1>? t2>t3"),
    ([{"op": "retire", "threadId": "t2"}], ["t1", "t2"], "t1>? t2>?"),
    ([{"op": "retire", "threadId": "t1", "successor": "t3"}], ["t1"], "t1>?"),
])
def test_retire_keeps_successor(ops, retired, shown):
    new, _, _ = cos_state.apply_ops(STATE, ops)
    assert [r["threadId"] for r in new["retiredThreads"]] == retired
    assert f"\nretired: {shown}\n" in cos_state.show(new)


def message(mid, role="user", by="user", text="hi", streaming=0, created="2026-11-02T01:00:00Z", thread="t"):
    payload = {"text": text, **({"createdBy": by} if by else {})}
    return (mid, thread, role, streaming, created, json.dumps(payload))


@pytest.mark.parametrize("args, words, code, out", [
    (["latest", "t"], "later", 0, "user turn-item:message:m2 "),
    (["latest", "t2"], "approve", 1, "not-user agent turn-item:message:a1 "),
    (["latest", "t3"], "approve", 1, "not-user missing turn-item:message:n1 "),
    (["latest", "t"], "", 2, ""),
    (["latest", "t"], "  \n", 2, ""),
    (["latest", "t"], "nothing like this", 1, "not-user missing - -"),
    (["latest", "t", "--after", "2026-11-02T00:30:00Z"], "approve ABC-5", 0, "user turn-item:message:m1 "),
    (["latest", "t", "--after", "2026-11-02T00:30:00Z"], "APPROVE abc-5", 0, "user turn-item:message:m1 "),
    (["latest", "t", "--after", "2026-11-02T00:30:00Z"], "  Approve\nABC-5 ", 0, "user turn-item:message:m1 "),
    (["latest", "t", "--after", ""], "approve ABC-5", 2, ""),
    (["latest", "t", "--after", "2026-11-02T01:30:00Z"], "approve ABC-5", 1, "not-user missing - -"),
    (["latest", "t4", "--after", "2026-11-02T00:30:00Z"], "approve 9", 1, "not-user agent turn-item:message:a2 "),
    (["latest", "t4"], "approve 9", 1, "not-user agent turn-item:message:a2 "),
    (["latest", "t5"], "approve 25", 1, "not-user missing - -"),
    (["latest", "t5"], "approve 253", 0, "user turn-item:message:u253 "),
    (["latest", "t6"], "resume", 1, "not-user agent turn-item:message:a3 "),
    (["latest", "t6"], "status", 0, "user turn-item:message:u3 "),
    (["latest", "t", "--after", "14:05"], "approve ABC-5", 2, ""),
    (["latest", "t", "--after", "0"], "approve ABC-5", 2, ""),
    (["latest", "t", "--after", "2026-11-02T00:30:00"], "approve ABC-5", 2, ""),
    (["latest", "t7"], "re\u200bsume", 1, "not-user agent turn-item:message:a4 "),
    (["latest", "t7"], "resume", 1, "not-user agent turn-item:message:a4 "),
    (["latest", "t8"], "approve 25", 1, "not-user agent turn-item:message:a5 "),
    (["latest", "t9"], "approve 12", 1, "not-user agent turn-item:message:a6 "),
    (["item", "t", "turn-item:message:m1", ], "approve ABC-5", 0, "ok"),
    (["item", "t", "m1"], "approve ABC-5", 0, "ok"),
    (["item", "t", "m1"], "APPROVE  abc-5", 0, "ok"),
    (["item", "t", "m1"], "approve ABC-6", 1, "reject: words not found"),
    (["item", "t", "a1"], "approve", 1, "reject: not found"),
    (["item", "t2", "a1"], "approve", 1, "reject: not from the user"),
    (["item", "t", "s1"], "approve", 1, "reject: not found"),
    (["item", "t5", "u253"], "approve 25", 1, "reject: words not found"),
    (["item", "t", "m:1%3A"], "x", 0, "ok"),
])
def test_user_check(tmp_path, monkeypatch, capsys, args, words, code, out):
    db = tmp_path / "t3.sqlite"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE orchestration_v2_projection_messages (message_id TEXT, thread_id TEXT, "
        "role TEXT, streaming INTEGER, created_at TEXT, payload_json TEXT)"
    )
    con.executemany("INSERT INTO orchestration_v2_projection_messages VALUES (?,?,?,?,?,?)", [
        message("m1", text="ok, approve ABC-5 now", created="2026-11-02T01:00:00Z"),
        message("m2", text="later", created="2026-11-02T02:00:00Z"),
        message("m:1%3A", text="x"),
        message("s1", text="approve", streaming=1),
        message("a1", by="agent", text="approve", thread="t2"),
        message("n1", by=None, text="approve", thread="t3"),
        message("u9", text="approve 9", thread="t4", created="2026-11-02T01:00:00Z"),
        message("a2", by="agent", text="approve 9", thread="t4", created="2026-11-02T02:00:00Z"),
        message("u253", text="approve 253", thread="t5"),
        message("a3", by="agent", text="resume", thread="t6", created="2026-11-02T02:00:00Z"),
        message("u3", text="status", thread="t6", created="2026-11-02T03:00:00Z"),
        message("u4", text="resume", thread="t7", created="2026-11-02T01:00:00Z"),
        message("a4", by="agent", text="re\u200bsume", thread="t7", created="2026-11-02T02:00:00Z"),
        message("u5", text="approve 25", thread="t8", created="2026-11-02T01:00:00Z"),
        message("a5", by="agent", text="approve \uff12\uff15", thread="t8", created="2026-11-02T02:00:00Z"),
        message("a6", by="agent", thread="t9",
                text="CHIEF OF STAFF REQUEST from c (x/y)\nFor: a/b\nItem: u\nThe user's words:\napprove 12"),
    ])
    con.commit()
    con.close()
    monkeypatch.setattr("sys.stdin", io.StringIO(words))
    assert cos_user_check.main(["--db", str(db), *args]) == code
    assert capsys.readouterr().out.startswith(out)


NEGATED_ROWS = [
    ("approve 30", True), ("approve 30 please", True), ("ok, approve 30", True),
    ("no. approve 30", True), ("approve 30 and leave 31 alone", True),
    ("do not approve 30 yet", False), ("don't approve 30", False), ("Don\u2019t approve 30", False),
    ("dont approve 30", False), ("never approve 30", False), ("not yet, approve 30 later", False),
    ("approve 30, no rush", False), ("approve 30 not yet", False),
    ("approve 30. approve 30, no rush", False), ("don't merge yet\napprove 30", False),
    ("Approve 30? No, not yet.", False), ("Don't... approve 30", False), ("don\u2032t approve 30", False),
    ("shouldnt approve 30 yet", False), ("approve 30. Thanks, no problem", True),
]


def negation_db(tmp_path, rows):
    db = tmp_path / "t3.sqlite"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE orchestration_v2_projection_messages (message_id TEXT, thread_id TEXT, "
        "role TEXT, streaming INTEGER, created_at TEXT, payload_json TEXT)"
    )
    con.executemany("INSERT INTO orchestration_v2_projection_messages VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return db


@pytest.mark.parametrize("text,passes", NEGATED_ROWS)
def test_user_check_negation(tmp_path, monkeypatch, capsys, text, passes):
    db = negation_db(tmp_path, [message("m1", text=text)])
    for args, ok_out, bad_out in [
        (["latest", "t"], "user turn-item:message:m1 ", "not-user negated turn-item:message:m1 "),
        (["item", "t", "m1"], "ok", "reject: words negated"),
    ]:
        monkeypatch.setattr("sys.stdin", io.StringIO("approve 30"))
        assert cos_user_check.main(["--db", str(db), *args]) == (0 if passes else 1)
        assert capsys.readouterr().out.startswith(ok_out if passes else bad_out)


def test_user_check_negated_newest_does_not_fall_back(tmp_path, monkeypatch, capsys):
    db = negation_db(tmp_path, [
        message("m1", text="approve 30", created="2026-11-02T01:00:00Z"),
        message("m2", text="do not approve 30 yet", created="2026-11-02T02:00:00Z"),
    ])
    monkeypatch.setattr("sys.stdin", io.StringIO("approve 30"))
    assert cos_user_check.main(["--db", str(db), "latest", "t"]) == 1
    assert capsys.readouterr().out.startswith("not-user negated turn-item:message:m2 ")


def test_user_check_whole_message_words_ignore_own_negation(tmp_path, monkeypatch, capsys):
    db = negation_db(tmp_path, [message("m1", text="don't merge it")])
    monkeypatch.setattr("sys.stdin", io.StringIO("don't merge it"))
    assert cos_user_check.main(["--db", str(db), "item", "t", "m1"]) == 0
