import importlib.util
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cos_rotation_check", Path(__file__).with_name("cos_rotation_check.py")
)
crc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(crc)

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
OLD, NEW = "a" * 40, "b" * 40


def hours_ago(h):
    return NOW - timedelta(hours=h)


@pytest.mark.parametrize("cap", [220_000, 250_000])
@pytest.mark.parametrize(
    "state, context_over_cap_by, hours, commit, branch, want",
    [
        ({}, -1_000, 1, OLD, "main", "ok context="),
        ({}, 0, 1, OLD, "main", "rotate: size"),
        ({}, 40_000, 1, OLD, "main", "rotate: size"),
        ({}, -50_000, 1, NEW, "main", "rotate: skill changed aaaaaaa..bbbbbbb"),
        ({}, -50_000, 1, NEW, "feat/x", "ok context="),
        ({"skillCommit": None}, -50_000, 1, NEW, "main", f"ok; set skillCommit {NEW}"),
        ({"paused": True}, 40_000, 1, NEW, "main", "ok (held: paused)"),
        ({"rotation": {"from": "T0"}}, 40_000, 1, NEW, "main", "ok (held: rotation)"),
        ({"rotationHeldUntil": "2026-11-02T13:00:00Z"}, 40_000, 1, OLD, "main", "ok (held"),
        ({"rotationHeldUntil": "2026-11-02T11:00:00Z"}, 40_000, 1, OLD, "main", "rotate: size"),
        ({}, -35_000, 4, OLD, "main", "rotate: age 4h"),
        ({}, -35_000, 3.9, OLD, "main", "ok context="),
        ({"tk": ("T0", 10_000)}, 10_000, 1, OLD, "main", "rotate: size"),
        ({"tk": ("T1", -20_000)}, 10_000, 1, OLD, "main", "rotate: size"),
        ({"tk": ("T1", 10_000)}, 10_000, 1, OLD, "main", "ok (size trigger off"),
        ({"tk": ("T1", 10_000)}, 10_000, 5, OLD, "main", "rotate: age 5h"),
    ],
)
def test_decide(cap, state, context_over_cap_by, hours, commit, branch, want):
    state = {"skillCommit": OLD, "chiefThreadId": "T1", **state}
    if "tk" in state:  # takeoverContext as (thread, tokens over the cap)
        thread, over = state.pop("tk")
        state["takeoverContext"] = {"threadId": thread, "tokens": cap + over}
    line = crc.decide(state, cap + context_over_cap_by, hours_ago(hours), NOW, commit, branch, cap)
    assert line.startswith(want)


def run_hook(monkeypatch, capsys, tmp_path, hook_in, state, context=230_000, readable=True):
    path = tmp_path / "state.json"
    if state is not None:
        path.write_text(json.dumps(state))
    monkeypatch.setenv("COS_STATE_FILE", str(path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(hook_in if isinstance(hook_in, str) else json.dumps(hook_in)))

    def read_context(sid=None):
        if not readable:
            raise crc.Unreadable("context")
        return context, datetime.now(timezone.utc) - timedelta(hours=1)

    monkeypatch.setattr(crc, "read_context", read_context)
    monkeypatch.setattr(crc, "skill_commit", lambda: OLD)
    monkeypatch.setattr(crc, "branch", lambda: "main")
    assert crc.main(["--hook"]) == 0
    return capsys.readouterr().out


STATE = {"chiefSessionId": "S1", "chiefThreadId": "T1", "skillCommit": OLD}


@pytest.mark.parametrize(
    "hook_in, state, kw, blocks",
    [
        ({"session_id": "S1", "stop_hook_active": False}, STATE, {}, "rotate: size 230k"),
        ({"session_id": "S1"}, STATE, {"readable": False}, "cannot read context"),
        ({"session_id": "S1"}, STATE, {"context": 90_000}, None),
        ({"session_id": "S2"}, STATE, {}, None),
        ({"session_id": "S1", "stop_hook_active": True}, STATE, {}, None),
        ({"session_id": "S1"}, None, {}, None),
        ({"session_id": "S1"}, {"tickets": {}}, {}, None),
        ("not json", STATE, {}, None),
    ],
)
def test_hook_blocks_only_the_chief_once(monkeypatch, capsys, tmp_path, hook_in, state, kw, blocks):
    out = run_hook(monkeypatch, capsys, tmp_path, hook_in, state, **kw)
    if blocks is None:
        assert out == ""
    else:
        d = json.loads(out)
        assert d["decision"] == "block" and blocks in d["reason"]
        assert d["reason"].endswith("Thread rotation")


@pytest.mark.parametrize("context, record, want_line, want_tk", [
    (230_000, True, "ok (size trigger off: take-over ended at 230k)", {"threadId": "T1", "tokens": 230_000}),
    (230_000, False, "rotate: size 230k >= 220k", None),
])
def test_plain_saves_session_and_takeover(monkeypatch, capsys, tmp_path, context, record, want_line, want_tk):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"chiefThreadId": "T1", "chiefSessionId": "old", "skillCommit": OLD, "tickets": {}}))
    monkeypatch.setenv("COS_STATE_FILE", str(path))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "S9")
    monkeypatch.setattr(crc, "read_context", lambda sid=None: (context, datetime.now(timezone.utc) - timedelta(hours=1)))
    monkeypatch.setattr(crc, "skill_commit", lambda: OLD)
    monkeypatch.setattr(crc, "branch", lambda: "main")
    assert crc.main(["--record-takeover"] if record else []) == 0
    assert capsys.readouterr().out.strip() == want_line
    saved = json.loads(path.read_text())
    assert saved["chiefSessionId"] == "S9" and saved.get("takeoverContext") == want_tk
    monkeypatch.setattr(crc, "read_context", lambda sid=None: (_ for _ in ()).throw(crc.Unreadable("context")))
    assert crc.main([]) == 2
    assert capsys.readouterr().out.strip() == "rotation-check: cannot read context"
