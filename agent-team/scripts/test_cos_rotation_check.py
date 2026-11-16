import importlib.util
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from test_agent_usage import context_store
from test_cos_idle_check import make_store

SPEC = importlib.util.spec_from_file_location(
    "cos_rotation_check", Path(__file__).with_name("cos_rotation_check.py")
)
crc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(crc)

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
OLD, NEW = "a" * 40, "b" * 40


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


CLAUDE = {"threadId": "T1", "provider": "claudeAgent"}
QUEUED = {"tickets": {"CW-10": {"stage": "spec-queued"}, "CW-9": {"stage": "build-queued"}, "CW-8": {"stage": "build"}}}
WAITS = "ok (skill change waits: "
INVALID = "ok; skillCommit is not a full sha; set skillCommit"
GANTT = {"ganttPluginVersion": "0.1.12", "plugin": "0.1.13"}  # state's version, and the clone's (plugin) passed to decide
PLUGIN_WAITS = "ok (plugin change waits: "


@pytest.mark.parametrize("cap", [220_000, 250_000])
@pytest.mark.parametrize(
    "state, context_over_cap_by, commit, branch, want",
    [
        ({}, -1_000, OLD, "main", "ok context="),
        ({}, 0, OLD, "main", "rotate: size"),
        ({}, 40_000, OLD, "main", "rotate: size"),
        ({}, -50_000, NEW, "main", "rotate: skill changed aaaaaaa..bbbbbbb"),
        ({}, -50_000, NEW, "feat/x", "ok context="),
        ({"skillCommit": None}, -50_000, NEW, "main", f"ok; set skillCommit {NEW}"),
        # a stored skillCommit that is not a full sha reads like null, never as a skill change; size still wins
        ({"skillCommit": "8ddace1"}, -50_000, NEW, "main", INVALID),
        ({"skillCommit": "8ddace1", **QUEUED}, -50_000, NEW, "main", INVALID),
        ({"skillCommit": "8ddace1"}, 0, NEW, "main", "rotate: size"),
        ({"paused": True}, 40_000, NEW, "main", "ok (held: paused)"),
        # an unfinished take over comes after paused and ahead of the reset hold and every trigger; null is today's line
        ({"takeover": {"startedAt": ago(7), "mode": "take-over"}}, -1_000, OLD, "main", "finish: take over unfinished since 7m; mode take-over"),
        ({"takeover": {"startedAt": ago(2), "mode": "resume"}, "reset": {"id": "0a1b2c3d", "startedAt": ago(1)}}, 40_000, NEW, "main", "finish: take over unfinished since 2m; mode resume"),
        ({"takeover": {"startedAt": ago(2), "mode": "bogus"}}, 40_000, NEW, "main", "finish: take over unfinished since 2m; mode ?"),
        ({"takeover": {"startedAt": ago(2), "mode": "take-over"}, "paused": True}, 40_000, NEW, "main", "ok (held: paused)"),
        ({"takeover": None, "reset": {"id": "0a1b2c3d", "startedAt": ago(1)}}, 40_000, NEW, "main", "ok (held: reset)"),
        # a reset marker holds for 10 minutes; an older one does not and the trigger fires again
        ({"reset": {"id": "0a1b2c3d", "startedAt": ago(9)}}, 40_000, NEW, "main", "ok (held: reset)"),
        ({"reset": {"id": "0a1b2c3d", "startedAt": ago(10)}}, 40_000, OLD, "main", "rotate: size"),
        ({"reset": {"id": "0a1b2c3d", "startedAt": "soon"}}, 40_000, OLD, "main", "rotate: size"),
        ({"tk": ("T0", 10_000)}, 10_000, OLD, "main", "rotate: size"),
        ({"tk": ("T1", -20_000)}, 10_000, OLD, "main", "rotate: size"),
        ({"tk": ("T1", 10_000)}, 10_000, OLD, "main", "ok (size trigger off"),
        # a skill change waits for a quiet turn: queued first, then relay, then a reset
        (QUEUED, -50_000, NEW, "main", WAITS + "queued CW-9)"),
        ({"lastRelayAt": ago(5)}, -50_000, NEW, "main", WAITS + "relay 5m ago)"),
        ({"lastRelayAt": ago(11)}, -50_000, NEW, "main", "rotate: skill changed"),
        ({"lastResetAt": ago(30)}, -50_000, NEW, "main", WAITS + "reset 30m ago)"),
        ({"lastResetAt": ago(61)}, -50_000, NEW, "main", "rotate: skill changed"),
        ({**QUEUED, "lastRelayAt": ago(1), "lastResetAt": ago(5)}, -50_000, NEW, "main", WAITS + "queued"),
        # junk timestamps are not a wait
        ({"lastRelayAt": "soon", "lastResetAt": "x"}, -50_000, NEW, "main", "rotate: skill changed"),
        # size ignores quiet; the size-off note comes ahead of the waits line
        ({"lastRelayAt": ago(1), **QUEUED}, 0, NEW, "main", "rotate: size"),
        ({"lastRelayAt": ago(1), "tk": ("T1", 10_000)}, 10_000, NEW, "main", "ok (size trigger off"),
        # the clone's agent-gantt version differs from state's: the skill-change rules, on the merge target branch only
        (GANTT, -50_000, OLD, "main", "rotate: agent-gantt plugin 0.1.12 -> 0.1.13; mode reset"),
        (GANTT, -50_000, OLD, "feat/x", "ok context="),
        ({**GANTT, **QUEUED}, 0, OLD, "main", "rotate: size"),  # a waiting plugin change does not hold back the size trigger
        ({**GANTT, **QUEUED}, -50_000, OLD, "main", PLUGIN_WAITS + "queued CW-9)"),
        ({**GANTT, "lastRelayAt": ago(5)}, -50_000, OLD, "main", PLUGIN_WAITS + "relay 5m ago)"),
        ({**GANTT, "lastResetAt": ago(61)}, -50_000, OLD, "main", "rotate: agent-gantt plugin"),
        # a skill change on the same turn wins the line, quiet or not
        (GANTT, -50_000, NEW, "main", "rotate: skill changed"),
        ({**GANTT, **QUEUED}, -50_000, NEW, "main", WAITS + "queued CW-9)"),
        # off: same version, null or unreadable stored version, clone version unreadable
        ({**GANTT, "plugin": "0.1.12"}, -50_000, OLD, "main", "ok context="),
        ({**GANTT, "ganttPluginVersion": None}, -50_000, OLD, "main", "ok context="),
        ({**GANTT, "ganttPluginVersion": "v1"}, -50_000, OLD, "main", "ok context="),
        ({**GANTT, "plugin": None}, -50_000, OLD, "main", "ok context="),
        ({"plugin": "0.1.13"}, -50_000, OLD, "main", "ok context="),
        # the stored version is newer than the clone's (a pull behind, a rollback): no rotation; an older stored one rotates
        ({**GANTT, "ganttPluginVersion": "0.1.14"}, -50_000, OLD, "main", "ok context="),
        ({**GANTT, "ganttPluginVersion": "0.1.9"}, -50_000, OLD, "main", "rotate: agent-gantt plugin 0.1.9 -> 0.1.13; mode reset"),
        ({**GANTT, "ganttPluginVersion": "0.2"}, -50_000, OLD, "main", "ok context="),  # compared as numbers, not text
    ],
)
def test_decide(cap, state, context_over_cap_by, commit, branch, want):
    state = {"skillCommit": OLD, "chiefThreadId": "T1", "chiefProvider": CLAUDE, **state}
    plugin = state.pop("plugin", None)
    if "tk" in state:  # takeoverContext as (thread, tokens over the cap)
        thread, over = state.pop("tk")
        state["takeoverContext"] = {"threadId": thread, "tokens": cap + over}
    line = crc.decide(state, cap + context_over_cap_by, NOW, commit, branch, cap, plugin)
    assert line.startswith(want)


@pytest.mark.parametrize(
    "provider, state, context, commit, want",
    [
        ("claudeAgent", {}, 231_000, OLD, "rotate: size 231k >= 220k; mode reset"),
        ("claudeAgent", {}, 40_000, NEW, "rotate: skill changed aaaaaaa..bbbbbbb; mode reset"),
        ("cursor", {}, 231_000, OLD, "rotate: size 231k >= 220k; mode reset"),
        ("cursor", {}, 40_000, NEW, "rotate: skill changed aaaaaaa..bbbbbbb; mode reset"),
        ("p-scheduled", {}, 231_000, OLD, "rotate: size 231k >= 220k; mode reset-scheduled"),
        ("p-compact", {}, 40_000, NEW, "rotate: skill changed aaaaaaa..bbbbbbb; mode compact"),
        ("claudeAgent", {"reset": {"startedAt": ago(11)}}, 231_000, OLD, "rotate: size 231k >= 220k; mode reset; reset never confirmed"),
        # no reset on this provider: never rotate:, even over the cap or with a new skill commit
        ("codex", {}, 231_000, NEW, "ok (no reset on codex; context=231k)"),
        ("codex", {}, None, NEW, "ok (no reset on codex; size unknown)"),
        ("codex", {"skillCommit": None}, 231_000, NEW, f"ok; set skillCommit {NEW}"),
        ("codex", {"skillCommit": "8ddace1"}, 231_000, NEW, f"ok; skillCommit is not a full sha; set skillCommit {NEW}"),
        (None, {}, 231_000, OLD, "ok (no reset on unknown; context=231k)"),
        ("bad\nname", {}, 231_000, OLD, "ok (no reset on unknown; context=231k)"),
        ("claudeAgent", {}, None, OLD, "ok (size unknown on Cursor)"),
        # the plugin change rotates in every reset mode but none
        ("p-compact", GANTT, 40_000, OLD, "rotate: agent-gantt plugin 0.1.12 -> 0.1.13; mode compact"),
        ("codex", GANTT, 40_000, OLD, "ok (no reset on codex; context=40k)"),
    ],
)
def test_line_by_reset_mode(monkeypatch, provider, state, context, commit, want):
    monkeypatch.setitem(crc.RESET_MODES, "p-scheduled", "reset-scheduled")
    monkeypatch.setitem(crc.RESET_MODES, "p-compact", "compact")
    cp = {"chiefProvider": {"threadId": "T1", "provider": provider}} if provider else {}
    state = {"skillCommit": OLD, **cp, **state}
    plugin = state.pop("plugin", None)
    assert crc.decide(state, context, NOW, commit, "main", plugin=plugin) == want


@pytest.mark.parametrize("text, want", [
    ('{"version": "0.1.13"}', "0.1.13"),
    ('{"version": "1.0"}', "1.0"),
    ('{"version": "0.2.0-beta"}', None),
    ('{"version": 3}', None),
    ('{"name": "agent-gantt"}', None),
    ("[]", None),
    ("not json", None),
    (None, None),  # no file
])
def test_plugin_version_is_a_file_read_of_the_clones_mod(monkeypatch, tmp_path, text, want):
    monkeypatch.setattr(crc, "TEAM", tmp_path / "agent-team")
    if text is not None:
        manifest = tmp_path / crc.PLUGIN_JSON
        manifest.parent.mkdir(parents=True)
        manifest.write_text(text)
    monkeypatch.setattr(crc.subprocess, "run", lambda *a, **k: pytest.fail("the rotation check never runs claude or git here"))
    assert crc.plugin_version() == want


def run_hook(monkeypatch, capsys, tmp_path, hook_in, state, context=230_000, readable=True, commit=OLD, real_store=False):
    path = tmp_path / "state.json"
    if state is not None:
        path.write_text(json.dumps(state))
    monkeypatch.setenv("COS_STATE_FILE", str(path))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))  # no machine copy unless a test adds one
    monkeypatch.setattr(sys, "stdin", io.StringIO(hook_in if isinstance(hook_in, str) else json.dumps(hook_in)))

    def read_context(sid=None, cursor=False):
        if not readable:
            raise crc.Unreadable("context")
        return context, datetime.now(timezone.utc) - timedelta(hours=1)

    if not real_store:
        monkeypatch.setattr(crc, "read_context", read_context)
    monkeypatch.setattr(crc, "skill_commit", lambda: commit)
    monkeypatch.setattr(crc, "branch", lambda: "main")
    assert crc.main(["--hook"]) == 0
    return capsys.readouterr().out


STATE = {"chiefSessionId": "S1", "chiefThreadId": "T1", "skillCommit": OLD, "chiefProvider": CLAUDE}


@pytest.mark.parametrize(
    "hook_in, state, kw, blocks",
    [
        ({"session_id": "S1", "stop_hook_active": False}, STATE, {}, "rotate: size 230k"),
        ({"session_id": "S1"}, STATE, {"readable": False}, "cannot read context"),
        ({"session_id": "S1"}, {**STATE, "takeover": {"startedAt": "2020-01-01T00:00:00Z", "mode": "take-over"}}, {"context": 90_000}, "finish: take over unfinished"),
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


SEEN = "2026-11-02T04:30:00Z"
LATE_STATE = {**STATE, "tickets": {"WISE-1": {"stage": "build", "childThreadId": "c1", "lastSeenAt": SEEN}}}
WAIT = [("mcp__t3-code__t3_background_wait", {"content": json.dumps({"matched": ["bg1"]})})]
JUST_NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.parametrize(
    "runs, asks, tools, extra, hook_in, kw, want",
    [
        ([("completed", "2026-11-02T18:12:00Z")], [], [], {}, {}, {}, "late-child: WISE-1 completed 6:12 pm UTC; read each per chief-of-staff SKILL.md § Child path"),
        ([("failed", "2026-11-02T18:12:00Z")], [], [], {}, {}, {}, "WISE-1 failed 6:12 pm UTC"),
        ([("running", None)], [("pending", "2026-11-02T18:20:00Z")], [], {}, {}, {}, "WISE-1 question 6:20 pm UTC"),
        ([("running", None)], [("resolved", "2026-11-02T18:20:00Z")], [], {}, {}, {}, None),
        ([("completed", "2026-11-02T04:20:00Z")], [("pending", "2026-11-02T04:25:00Z")], [], {}, {}, {}, None),  # already read
        ([("completed", JUST_NOW)], [], WAIT, {}, {}, {}, None),  # waiting on its own command
        ([("completed", "2026-11-02T18:12:00Z")], [], [], {"paused": True}, {}, {}, None),
        ([("completed", "2026-11-02T18:12:00Z")], [], [], {}, {"stop_hook_active": True}, {}, None),
        ([("completed", "2026-11-02T18:12:00Z")], [], [], {}, {}, {"db": "missing"}, None),
        ([("completed", "2026-11-02T18:12:00Z")], [], [], {}, {}, {"db": "no_requests_table"}, None),
        ([("completed", "2026-11-02T18:12:00Z")], [], [], {}, {}, {"context": 230_000}, "rotate: size 230k"),  # rotation first, then the late line
    ],
)
def test_hook_sends_the_chief_back_to_read_a_late_child(monkeypatch, capsys, tmp_path, runs, asks, tools, extra, hook_in, kw, want):
    db = tmp_path / "statev2.sqlite"
    make_store(db, [], runs, tools)
    con = sqlite3.connect(db)
    if kw.get("db") != "no_requests_table":
        con.execute("CREATE TABLE orchestration_v2_projection_runtime_requests (thread_id, status, created_at)")
        con.executemany("INSERT INTO orchestration_v2_projection_runtime_requests VALUES ('c1', ?, ?)", asks)
    con.commit()
    con.close()
    monkeypatch.setenv("COS_T3_DB", str(tmp_path / "none.sqlite" if kw.get("db") == "missing" else db))
    out = run_hook(monkeypatch, capsys, tmp_path, {"session_id": "S1", **hook_in}, {**LATE_STATE, **extra}, context=kw.get("context", 90_000))
    if want is None:
        assert out == ""
    else:
        reason = json.loads(out)["reason"]
        assert want in reason and (not kw.get("context") or reason.index(want) < reason.index("late-child:"))


CURSOR = {"conversation_id": "C1", "hook_event_name": "stop", "status": "completed", "loop_count": 0}


@pytest.mark.parametrize(
    "hook_in, kw, want, provider",
    [
        (CURSOR, {"commit": NEW}, "rotate: skill changed", CLAUDE),  # a provider with a reset mode
        (CURSOR, {"commit": NEW}, "rotate: skill changed", {"provider": "cursor"}),
        (CURSOR, {"readable": False}, "rotation-check: cannot read context", {"provider": "cursor"}),
        (CURSOR, {"commit": NEW}, None, {"provider": "codex"}),  # no reset on this provider: silent
        (CURSOR, {"readable": False}, None, {"provider": "codex"}),  # ... even over a store it cannot read
        ({**CURSOR, "conversation_id": "C2"}, {"commit": NEW}, None, CLAUDE),
        ({**CURSOR, "conversation_id": "agent-C1"}, {"commit": NEW}, "rotate: skill changed", CLAUDE),  # T3 Code names the folder agent-<id>
        ({**CURSOR, "loop_count": 1}, {"commit": NEW}, None, CLAUDE),
        ({**CURSOR, "status": "aborted"}, {"commit": NEW}, None, CLAUDE),
        ({"conversation_id": "C1"}, {"commit": NEW}, None, CLAUDE),  # not Cursor's payload, and no session_id
    ],
)
def test_hook_on_cursor_answers_with_a_followup_only_for_the_chief_once(monkeypatch, capsys, tmp_path, hook_in, kw, want, provider):
    out = run_hook(monkeypatch, capsys, tmp_path, hook_in, {**STATE, "chiefSessionId": "C1", "chiefProvider": provider}, **kw)
    assert (list(json.loads(out)) == ["followup_message"] and want in out) if want else out == ""


def test_hook_on_cursor_reads_the_size_from_the_run_store(monkeypatch, capsys, tmp_path):
    context_store(tmp_path / "cur" / "proj", "agent-C1", [(1, {"inputTokens": 230_000}, [])])
    monkeypatch.setenv("COS_CURSOR_PROJECTS_DIR", str(tmp_path / "cur"))
    out = run_hook(monkeypatch, capsys, tmp_path, CURSOR, {**STATE, "chiefSessionId": "C1", "chiefProvider": {"provider": "cursor"}}, real_store=True)
    assert "rotate: size 230k >= 220k; mode reset" in json.loads(out)["followup_message"]


def test_hook_on_cursor_leaves_a_pending_takeover_over_the_cap_alone_and_unsaved(monkeypatch, capsys, tmp_path):
    context_store(tmp_path / "cur" / "proj", "agent-C1", [(1, {"inputTokens": 250_000}, [])])
    monkeypatch.setenv("COS_CURSOR_PROJECTS_DIR", str(tmp_path / "cur"))
    pending = {"threadId": "T1", "tokens": None, "turn": 1}
    state = {**STATE, "chiefSessionId": "C1", "chiefProvider": {"provider": "cursor"}, "takeoverContext": pending}
    assert run_hook(monkeypatch, capsys, tmp_path, CURSOR, state, real_store=True) == ""  # no rotate: the take-over itself landed above the cap
    assert json.loads((tmp_path / "state.json").read_text())["takeoverContext"] == pending


USAGE = [(1, {"inputTokens": 230_000}, [])]
SIZE_RESET = "rotate: size 230k >= 220k; mode reset"


@pytest.mark.parametrize("ages, turns, provider, want_id, want_line", [
    ({"C1": 1, "C2": 0.5, "C3": 10}, USAGE, "cursor", "C2", SIZE_RESET),  # the newest fresh one is the Chief's
    ({"C2": 1}, USAGE, "p-reset", "C2", SIZE_RESET),
    ({"C2": 1}, [(1, None, [])], "p-reset", "C2", "ok (size unknown on Cursor)"),  # no usage yet
    ({"C2": 1}, None, "p-reset", "C2", "rotation-check: cannot read context"),  # no store has the conversation
    ({"C1": 10}, USAGE, "p-reset", None, "rotation-check: cannot read context"),  # only stale ones: not Cursor
])
def test_plain_on_cursor_saves_the_conversation_id_and_reads_the_size(monkeypatch, capsys, tmp_path, ages, turns, provider, want_id, want_line):
    app, cursor, path = tmp_path / "my_app.x", tmp_path / "cursor", tmp_path / "state.json"
    slug = str(app).replace("/", "-").replace("_", "-").replace(".", "-").strip("-")
    if turns:
        context_store(cursor / slug, "agent-C2", turns)
    monkeypatch.setitem(crc.RESET_MODES, "p-reset", "reset")
    for cid, minutes in ages.items():
        f = cursor / slug / "agent-transcripts" / cid / f"{cid}.jsonl"
        f.parent.mkdir(parents=True)
        f.write_text("{}\n")
        os.utime(f, (time.time() - minutes * 60,) * 2)
    path.write_text(json.dumps({"chiefThreadId": "T1", "skillCommit": OLD, "chiefProvider": {"provider": provider}}))
    monkeypatch.setattr(crc, "ROOT", app)
    monkeypatch.setenv("COS_STATE_FILE", str(path))
    monkeypatch.setenv("COS_CURSOR_PROJECTS_DIR", str(cursor))
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.setattr(crc, "skill_commit", lambda: OLD)
    monkeypatch.setattr(crc, "branch", lambda: "main")
    assert crc.main([]) == (2 if "cannot read" in want_line else 0)
    assert capsys.readouterr().out.strip() == want_line
    assert json.loads(path.read_text()).get("chiefSessionId") == want_id


@pytest.mark.parametrize("context, record, want_line, want_tk", [
    (230_000, True, "ok (size trigger off: take-over ended at 230k); take-over context=230k", {"threadId": "T1", "tokens": 230_000}),
    (230_000, False, "rotate: size 230k >= 220k; mode reset", None),
])
def test_plain_saves_session_and_takeover(monkeypatch, capsys, tmp_path, context, record, want_line, want_tk):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"chiefThreadId": "T1", "chiefSessionId": "old", "skillCommit": OLD, "tickets": {}, "chiefProvider": CLAUDE}))
    monkeypatch.setenv("COS_STATE_FILE", str(path))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "S9")
    monkeypatch.setattr(crc, "read_context", lambda sid=None, cursor=False: (context, datetime.now(timezone.utc) - timedelta(hours=1)))
    monkeypatch.setattr(crc, "skill_commit", lambda: OLD)
    monkeypatch.setattr(crc, "branch", lambda: "main")
    assert crc.main(["--record-takeover"] if record else []) == 0
    assert capsys.readouterr().out.strip() == want_line
    saved = json.loads(path.read_text())
    assert saved["chiefSessionId"] == "S9" and saved.get("takeoverContext") == want_tk
    monkeypatch.setattr(crc, "read_context", lambda sid=None, cursor=False: (_ for _ in ()).throw(crc.Unreadable("context")))
    assert crc.main([]) == 2
    assert capsys.readouterr().out.strip() == "rotation-check: cannot read context"


def _repo(tmp_path):
    def run(*a):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
            cwd=tmp_path, capture_output=True, text=True, check=True,
        ).stdout.strip()

    run("init", "-q")
    for rel in (
        "agent-team/.claude/skills/chief-of-staff/SKILL.md",
        "agent-team/.claude/skills/project-manager/SKILL.md",
        "agent-team/docs/agents/chief-of-staff.md",
    ):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("one\n")
    return run


def test_skill_paths_follow_symlinks(tmp_path, monkeypatch):
    run = _repo(tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "skills").symlink_to("../agent-team/.claude/skills")
    (tmp_path / "docs" / "agents").mkdir(parents=True)
    (tmp_path / "docs" / "agents" / "chief-of-staff.md").symlink_to(
        "../../agent-team/docs/agents/chief-of-staff.md"
    )
    monkeypatch.setattr(crc, "TEAM", tmp_path)
    assert crc.skill_paths() == [
        "agent-team/.claude/skills/chief-of-staff",
        "agent-team/.claude/skills/project-manager",
        "agent-team/docs/agents/chief-of-staff.md",
    ]
    run("add", "-A")
    run("commit", "-qm", "one")
    (tmp_path / "agent-team/.claude/skills/chief-of-staff/SKILL.md").write_text("two\n")
    run("add", "-A")
    run("commit", "-qm", "two")
    assert crc.skill_commit() == run("rev-parse", "HEAD")


def test_skill_paths_unchanged_without_links(tmp_path, monkeypatch):
    run = _repo(tmp_path)
    for rel in crc.SKILL_PATHS:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".md"):
            p.write_text("x\n")
        else:
            p.mkdir(exist_ok=True)
    monkeypatch.setattr(crc, "TEAM", tmp_path)
    assert crc.skill_paths() == crc.SKILL_PATHS


def test_skill_commit_works_when_root_is_a_subfolder(tmp_path, monkeypatch):
    run = _repo(tmp_path)
    run("add", "-A")
    run("commit", "-qm", "one")
    sub = tmp_path / "agent-team"
    (sub / ".claude").mkdir(exist_ok=True)
    (sub / "docs" / "agents").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(crc, "TEAM", sub)
    assert crc.skill_commit() == run("rev-parse", "HEAD")


def test_skill_commit_follows_the_clone_not_the_app(tmp_path):
    # The clone sits outside the app repo and is reached through a ~/.collective-wisdom style link.
    clone, app, home = tmp_path / "clone", tmp_path / "app", tmp_path / "home"
    for d in (clone, app, home):
        d.mkdir()
    run = _repo(clone)
    scripts = clone / "agent-team" / "scripts"
    scripts.mkdir()
    for f in ("cos_rotation_check.py", "app_root.py", "project_config.py", "gantt_plugin.py"):
        (scripts / f).write_text((Path(__file__).with_name(f)).read_text())
    run("add", "-A")
    run("commit", "-qm", "one")
    (home / ".collective-wisdom").symlink_to(clone / "agent-team")
    for cmd in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "app"]):
        subprocess.run(["git", *cmd], cwd=app, check=True)

    def commit():
        return subprocess.run(
            [sys.executable, str(home / ".collective-wisdom" / "scripts" / "cos_rotation_check.py"), "--skill-commit"],
            cwd=app, capture_output=True, text=True, check=True, env={"PATH": os.environ["PATH"], "HOME": str(home)},
        ).stdout.strip()

    first = run("rev-parse", "HEAD")
    assert commit() == first
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "app2"], cwd=app, check=True)
    assert commit() == first  # the app's history does not move it
    (clone / "agent-team/docs/agents/chief-of-staff.md").write_text("two\n")
    run("add", "-A")
    run("commit", "-qm", "two")
    assert commit() == run("rev-parse", "HEAD") != first  # the clone's history does


@pytest.mark.parametrize("has_project_md, blocks", [(False, False), (True, True)])
def test_hook_is_silent_in_a_repo_without_project_md(monkeypatch, capsys, tmp_path, has_project_md, blocks):
    app = tmp_path / "app"
    (app / "docs" / "agents").mkdir(parents=True)
    if has_project_md:
        (app / "docs" / "agents" / "project.md").write_text("| Key | Value |\n")
    monkeypatch.setattr(crc, "ROOT", app)
    out = run_hook(monkeypatch, capsys, tmp_path, {"session_id": "S1"}, STATE)  # would block: context over the cap
    assert ("rotate: size" in out) == blocks and (out == "") == (not blocks)


@pytest.mark.parametrize("machine_copy, blocks", [(None, True), ("other", False), ("link", True)])
def test_hook_defers_to_the_machine_copy(monkeypatch, capsys, tmp_path, machine_copy, blocks):
    # An app's older-style copy of this script must not disagree with the machine install's copy.
    app = tmp_path / "app"
    (app / "docs" / "agents").mkdir(parents=True)
    (app / "docs" / "agents" / "project.md").write_text("| Key | Value |\n")
    monkeypatch.setattr(crc, "ROOT", app)
    scripts = tmp_path / "home" / ".collective-wisdom" / "scripts"
    scripts.mkdir(parents=True)
    if machine_copy == "other":
        (scripts / "cos_rotation_check.py").write_text("# another file\n")
    elif machine_copy == "link":
        (scripts / "cos_rotation_check.py").symlink_to(crc.__file__)
    out = run_hook(monkeypatch, capsys, tmp_path, {"session_id": "S1"}, STATE)
    assert ("rotate: size" in out) == blocks and (out == "") == (not blocks)


def test_hook_blocks_from_a_drifted_cwd(tmp_path):
    # The Stop hook's cwd can drift out of the app. It must still read the app's project.md, state and transcript.
    sid = "0123abcd-0123-0123-0123-0123456789ab"
    app, elsewhere, projects = tmp_path / "app", tmp_path / "elsewhere", tmp_path / "projects"
    (app / "docs" / "agents").mkdir(parents=True)
    (app / "docs" / "agents" / "project.md").write_text("| Issue identifier prefix | `ZZ` |\n| Repo | `acme/app` |\n")
    (app / ".agent-team").mkdir()
    state = app / ".agent-team" / "state.json"
    state.write_text(json.dumps({"chiefSessionId": sid, "chiefThreadId": "T1", "skillCommit": None, "chiefProvider": CLAUDE}))
    (projects / "-x-app").mkdir(parents=True)
    usage = {"input_tokens": 230_000, "output_tokens": 1}
    (projects / "-x-app" / f"{sid}.jsonl").write_text(json.dumps(
        {"type": "assistant", "requestId": "r1", "timestamp": "2026-11-01T10:00:00Z",
         "message": {"model": "claude-opus-5-5", "usage": usage}}))
    elsewhere.mkdir()
    (app / ".claude" / "skills" / "chief-of-staff").mkdir(parents=True)
    (app / ".claude" / "skills" / "chief-of-staff" / "SKILL.md").write_text("x")
    for cmd in (["init", "-q"], ["add", "."], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"]):
        subprocess.run(["git", *cmd], cwd=app, check=True)
    out = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("cos_rotation_check.py")), "--hook"],
        input=json.dumps({"session_id": sid, "stop_hook_active": False}),
        capture_output=True, text=True, cwd=elsewhere, check=True,
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "CLAUDE_PROJECT_DIR": str(app),
             "COS_PROJECTS_DIR": str(projects), "COS_STATE_FILE": str(state)},
    ).stdout
    # "rotate: size", not "cannot read ...": a wrong project.md, transcript or git root also blocks, with another reason.
    assert json.loads(out)["reason"].startswith("rotate: size")


PENDING = {"threadId": "T1", "tokens": None, "turn": 1}
ENDED, RUNNING = [(1, {"inputTokens": 180_000}, [])], [(1, None, [])]


@pytest.mark.parametrize("args, turns, tk_in, want_suffix, want_tk", [
    (["--record-takeover"], RUNNING, None, "; take-over context pending (turn 1)", PENDING),  # the take-over turn has no usage yet
    ([], RUNNING, PENDING, "", PENDING),  # still running: nothing changes
    ([], ENDED, PENDING, "; take-over context=180k (turn 1)", {"threadId": "T1", "tokens": 180_000}),  # turn is dropped
    (["--record-takeover"], ENDED, None, "; take-over context=180k", {"threadId": "T1", "tokens": 180_000}),
])
def test_cursor_takeover_context_is_recorded_pending_then_filled(monkeypatch, capsys, tmp_path, args, turns, tk_in, want_suffix, want_tk):
    app, cursor, path = tmp_path / "app", tmp_path / "cursor", tmp_path / "state.json"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(app)).strip("-")
    context_store(cursor / slug, "agent-C2", turns)
    f = cursor / slug / "agent-transcripts" / "C2" / "C2.jsonl"
    f.parent.mkdir(parents=True)
    f.write_text("{}\n")
    state = {"chiefThreadId": "T1", "skillCommit": OLD, "chiefProvider": {"provider": "cursor"}}
    path.write_text(json.dumps({**state, **({"takeoverContext": tk_in} if tk_in else {})}))
    monkeypatch.setattr(crc, "ROOT", app)
    monkeypatch.setenv("COS_STATE_FILE", str(path))
    monkeypatch.setenv("COS_CURSOR_PROJECTS_DIR", str(cursor))
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    monkeypatch.setattr(crc, "skill_commit", lambda: OLD)
    monkeypatch.setattr(crc, "branch", lambda: "main")
    assert crc.main(args) == 0
    out = capsys.readouterr().out.strip()
    assert out.endswith(want_suffix) and ("take-over context" in out) == bool(want_suffix)
    assert json.loads(path.read_text()).get("takeoverContext") == want_tk
