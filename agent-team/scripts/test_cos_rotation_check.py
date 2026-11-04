import importlib.util
import io
import json
import os
import subprocess
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
    monkeypatch.setattr(crc, "ROOT", tmp_path)
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
    monkeypatch.setattr(crc, "ROOT", tmp_path)
    assert crc.skill_paths() == crc.SKILL_PATHS


def test_skill_commit_works_when_root_is_a_subfolder(tmp_path, monkeypatch):
    run = _repo(tmp_path)
    run("add", "-A")
    run("commit", "-qm", "one")
    sub = tmp_path / "agent-team"
    (sub / ".claude").mkdir(exist_ok=True)
    (sub / "docs" / "agents").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(crc, "ROOT", sub)
    assert crc.skill_commit() == run("rev-parse", "HEAD")


@pytest.mark.parametrize("argv, want_project_dir", [(["--hook"], True), ([], False)])
def test_hook_roots_at_claude_project_dir(tmp_path, argv, want_project_dir):
    # The Stop hook's cwd can drift; only --hook trusts CLAUDE_PROJECT_DIR.
    app, elsewhere = tmp_path / "app", tmp_path / "elsewhere"
    app.mkdir()
    elsewhere.mkdir()
    code = (
        "import runpy, sys; f = sys.argv[1]; sys.argv = ['x'] + sys.argv[2:]; "
        "print(runpy.run_path(f, run_name='linked')['ROOT'])"
    )
    out = subprocess.run(
        [sys.executable, "-c", code, str(Path(__file__).with_name("cos_rotation_check.py")), *argv],
        capture_output=True, text=True, cwd=elsewhere, check=True,
        env={"PATH": os.environ["PATH"], "CLAUDE_PROJECT_DIR": str(app)},
    ).stdout.strip()
    assert (out == str(app)) == want_project_dir


def test_context_lookup_uses_the_rotation_root_not_the_cwd(monkeypatch):
    seen = {}

    class FakeUsage:
        PROJECT = "cwd-repo"
        project_name = staticmethod(lambda root: Path(root).name)

        @classmethod
        def context_line(cls, projects):
            seen["project"] = cls.PROJECT
            return "context=1 started=2026-01-01T00:00:00Z"

    monkeypatch.setattr(crc, "load_module", lambda name: FakeUsage)
    crc.read_context()
    assert seen["project"] == crc.ROOT.name
