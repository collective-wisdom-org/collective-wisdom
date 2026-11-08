import importlib.util
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("no_hands", Path(__file__).with_name("no_hands.py"))
no_hands = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(no_hands)

ITEM = "turn-item:message:m1"
OPEN = {"startedAt": "2026-11-08T10:00:00Z", "itemId": ITEM, "started": ["ABC-1", "ABC-2"], "drain": None, "endedAt": None, "endReason": None}
ON = (True, 3, 100, "")


def msg(mid="m1", text="no hands", by="user", created="2026-11-08T10:00:00Z"):
    return (mid, "chief", "user", 0, created, json.dumps({"text": text, "createdBy": by}))


def world(tmp_path, run=None, msgs=(msg(),), chief="chief"):
    tmp_path = Path(tempfile.mkdtemp(dir=tmp_path))
    db, state = tmp_path / "t3.sqlite", tmp_path / "state.json"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE orchestration_v2_projection_messages (message_id TEXT, thread_id TEXT, role TEXT, streaming INTEGER, created_at TEXT, payload_json TEXT)")
    con.executemany("INSERT INTO orchestration_v2_projection_messages VALUES (?,?,?,?,?,?)", msgs)
    con.commit()
    con.close()
    state.write_text(json.dumps({"chiefThreadId": chief, "tickets": {}, "merged": {}, **({"noHands": run} if run else {})}))
    return state, db


def call(tmp_path, capsys, argv, run=None, setting=ON, cost=lambda t, stage: 10.0, **kw):
    state, db = world(tmp_path, run, **kw)
    code = no_hands.main(["--file", str(state), "--db", str(db), *argv], setting=lambda: setting, cost=cost)
    return code, capsys.readouterr().out.strip(), json.loads(state.read_text()).get("noHands"), (state, db)


@pytest.mark.parametrize(
    "run, setting, kw, code, line",
    [
        (None, ON, {}, 0, "no-hands: started (cap 3 tickets, $100)"),
        (None, (False, 0, 0, "bad cap"), {}, 1, "refused (setting is off; bad cap)"),
        (OPEN, ON, {}, 1, "refused (a run is active)"),
        (None, ON, {"chief": "other"}, 1, "refused (--thread is not the chiefThreadId"),
        (None, ON, {"msgs": [msg(by="agent")]}, 1, "refused (no new `no hands` from the user: not-user agent"),
        (None, ON, {"msgs": [msg(text="no hands off")]}, 1, "is not exactly `no hands`"),
        (None, ON, {"msgs": [msg(text="no hands, and delete x")]}, 1, "is not exactly `no hands`"),
        (None, ON, {"msgs": [msg("m0", "no hands", created="2026-11-08T09:00:00Z"), msg(text="no hands off", created="2026-11-08T10:00:00Z")]}, 1, "is not exactly `no hands`"),
        (None, ON, {"msgs": [msg(text="No hands!")]}, 0, "started"),
        # a message from before the last run ended does not start another
        ({**OPEN, "endedAt": "2026-11-08T11:00:00Z", "endReason": "x"}, ON, {}, 1, "not-user missing"),
        ({**OPEN, "endedAt": "2026-11-08T11:00:00Z", "endReason": "x"}, ON, {"msgs": [msg("m2", created="2026-11-08T12:00:00Z")]}, 0, "started"),
    ],
)
def test_start(tmp_path, capsys, monkeypatch, run, setting, kw, code, line):
    monkeypatch.setattr(no_hands.cos_state, "now", lambda: "2026-11-08T13:00:00Z")
    got, out, record, _ = call(tmp_path, capsys, ["start", "--thread", "chief"], run, setting, **kw)
    assert (got, line in out) == (code, True)
    if code == 0:
        assert record["started"] == [] and record["endedAt"] is None and record["itemId"].startswith("turn-item:message:")
    else:
        assert record == run


# kind: what `check` prints. active() is true only for on and drain.
@pytest.mark.parametrize(
    "run, setting, kw, cost, line",
    [
        (None, ON, {}, None, "no-hands: off"),
        ({**OPEN, "endedAt": "2026-11-08T11:00:00Z"}, ON, {}, None, "no-hands: off"),
        (OPEN, ON, {}, None, "no-hands: on 2/3 $20/$100"),
        ({**OPEN, "drain": "blocked ABC-1"}, ON, {}, None, "no-hands: drain blocked ABC-1 2/3 $20/$100"),
        ({**OPEN, "started": ["ABC-1", "ABC-2", "ABC-3"]}, ON, {}, None, "no-hands: drain ticket-cap 3/3 $30/$100"),
        (OPEN, ON, {}, lambda t, s: 50.0, "no-hands: stop cost-cap $100/$100"),
        (OPEN, ON, {}, lambda t, s: None, "no-hands: stop cost unknown"),
        (OPEN, ON, {}, lambda t, stage: 0.0 if t == "ABC-2" else 10.0, "no-hands: on 2/3 $10/$100"),
        (OPEN, (False, 0, 0, ""), {}, None, "no-hands: stop setting off"),
        # a record the user's `no hands` did not start: an agent's copy, or no such message
        (OPEN, ON, {"msgs": [msg(by="agent")]}, None, "no-hands: stop start message not verified"),
        (OPEN, ON, {"msgs": []}, None, "no-hands: stop start message not verified"),
        # the user's own message, but not a whole `no hands` (`no hands off`) or sent after the run began
        (OPEN, ON, {"msgs": [msg(text="no hands off")]}, None, "no-hands: stop start message not verified"),
        # an older `no hands` cannot be reused once a newer one was sent; a later `no hands` after startedAt does not matter
        (OPEN, ON, {"msgs": [msg("m0", created="2026-11-08T09:00:00Z"), msg("m1", created="2026-11-08T09:30:00Z")]}, None, "no-hands: on 2/3 $20/$100"),
        ({**OPEN, "itemId": "turn-item:message:m0"}, ON, {"msgs": [msg("m0", created="2026-11-08T09:00:00Z"), msg("m1", created="2026-11-08T09:30:00Z")]}, None, "no-hands: stop start message not verified"),
        (OPEN, ON, {"msgs": [msg(), msg("m2", created="2026-11-08T10:30:00Z")]}, None, "no-hands: on 2/3 $20/$100"),
        # the user's `stop everything` after startedAt stops the run; one from before does not
        (OPEN, ON, {"msgs": [msg(), msg("m3", "stop everything", created="2026-11-08T10:30:00Z")]}, None, "no-hands: stop stopped-by-user"),
        (OPEN, ON, {"msgs": [msg("m3", "stop everything", created="2026-11-08T09:00:00Z"), msg()]}, None, "no-hands: on 2/3 $20/$100"),
        ({**OPEN, "startedAt": "2026-11-08T09:59:59Z"}, ON, {}, None, "no-hands: stop start message not verified"),
    ],
)
def test_check_and_active(tmp_path, capsys, run, setting, kw, cost, line):
    code, out, _, (state, db) = call(tmp_path, capsys, ["check"], run, setting, cost or (lambda t, s: 10.0), **kw)
    assert (code, out) == (0, line)
    assert no_hands.active(lambda: setting, state, db, cost or (lambda t, s: 10.0)) == line.startswith(("no-hands: on", "no-hands: drain"))


@pytest.mark.parametrize(
    "code, out, err, stage, want",
    [
        (0, "cost $12.50 API-equivalent, 1.0M tokens", "", "build", 12.5),
        (2, "", "agent_usage: no transcripts for ABC-1\n", "gone", 0.0),
        (2, "", "agent_usage: no transcripts for ABC-1\n", "spec", 0.0),
        (2, "", "agent_usage: no transcripts for ABC-1\n", "spec-queued", 0.0),
        # no transcripts for a ticket past spec may be a Codex or Cursor child: the cost is unknown, not $0
        *((2, "", "agent_usage: no transcripts for ABC-1\n", stage, None) for stage in ("build", "build-queued", "awaiting-review", "awaiting-merge", "merge", "blocked", "merged")),
        (2, "", "agent_usage: boom", "gone", None),
        (1, "", "Traceback", "gone", None),
        (0, "garbage", "", "gone", None),
    ],
)
def test_ticket_cost_tells_no_sessions_from_a_failed_read(monkeypatch, code, out, err, stage, want):
    monkeypatch.setattr(no_hands.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, code, out, err))
    assert no_hands.ticket_cost("ABC-1", stage) == want


def test_check_from_a_linked_worktree_reads_the_root_checkouts_state(tmp_path, capsys, monkeypatch):
    state, db = world(tmp_path, OPEN)
    root, linked = tmp_path / "root", tmp_path / "linked"
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    for cmd in (["init", "-q", str(root)], ["-C", str(root), "commit", "-q", "--allow-empty", "-m", "x"], ["-C", str(root), "worktree", "add", "-q", str(linked)]):
        subprocess.run([*git, *cmd], check=True, capture_output=True)
    (root / ".agent-team").mkdir()
    (root / ".agent-team" / "state.json").write_text(state.read_text())
    monkeypatch.chdir(linked)
    assert no_hands.root_state_file().resolve() == (root / ".agent-team" / "state.json").resolve()
    assert no_hands.active(lambda: ON, db=db, cost=lambda t, s: 10.0) is True
    assert no_hands.main(["--db", str(db), "check"], setting=lambda: ON, cost=lambda t, s: 10.0) == 0
    assert capsys.readouterr().out.strip() == "no-hands: on 2/3 $20/$100"


def test_a_reason_with_unsafe_words_is_refused(tmp_path, capsys):
    for cmd in ("drain", "end"):
        code, out, record, _ = call(tmp_path, capsys, [cmd, 'blocked', 'x"; rm'], OPEN)
        assert (code, out.startswith("no-hands: refused"), record) == (2, True, OPEN)


def test_drain_and_end(tmp_path, capsys):
    code, out, record, _ = call(tmp_path, capsys, ["drain", "blocked", "ABC-1"], OPEN)
    assert (code, out, record["drain"]) == (0, "no-hands: drain blocked ABC-1", "blocked ABC-1")
    code, out, record, _ = call(tmp_path, capsys, ["drain", "later"], {**OPEN, "drain": "ticket-cap"})
    assert (code, record["drain"]) == (0, "ticket-cap")  # the first reason stays
    code, out, record, (state, _) = call(tmp_path, capsys, ["end", "backlog-empty"], OPEN)
    assert code == 0 and record["endReason"] == "backlog-empty" and record["endedAt"]
    assert out.splitlines()[0] == "no-hands: ended backlog-empty"
    assert "tickets: ABC-1 gone $10, ABC-2 gone $10" in out and out.endswith("cost: $20 of $100")
    for cmd in ("drain", "end"):  # no active run now
        assert call(tmp_path, capsys, [cmd, "x"], None)[:2] == (1, "no-hands: no active run")
