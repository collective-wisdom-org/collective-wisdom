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


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def retired(*minutes):
    return {"retiredThreads": [{"threadId": f"R{m}", "retiredAt": ago(m)} for m in minutes]}


QUEUED = {"tickets": {"CW-10": {"stage": "spec-queued"}, "CW-9": {"stage": "build-queued"}, "CW-8": {"stage": "build"}}}
WAITS = "ok (skill change waits: "


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
        ({"paused": True}, 40_000, NEW, "main", "ok (held: paused)"),
        ({"rotation": {"from": "T0"}}, 40_000, NEW, "main", "ok (held: rotation)"),
        ({"rotationHeldUntil": "2026-11-02T13:00:00Z"}, 40_000, OLD, "main", "ok (held"),
        ({"rotationHeldUntil": "2026-11-02T11:00:00Z"}, 40_000, OLD, "main", "rotate: size"),
        ({"tk": ("T0", 10_000)}, 10_000, OLD, "main", "rotate: size"),
        ({"tk": ("T1", -20_000)}, 10_000, OLD, "main", "rotate: size"),
        ({"tk": ("T1", 10_000)}, 10_000, OLD, "main", "ok (size trigger off"),
        # a skill change waits for a quiet turn: queued first, then relay, then rotation
        (QUEUED, -50_000, NEW, "main", WAITS + "queued CW-9)"),
        ({"lastRelayAt": ago(5)}, -50_000, NEW, "main", WAITS + "relay 5m ago)"),
        ({"lastRelayAt": ago(11)}, -50_000, NEW, "main", "rotate: skill changed"),
        (retired(600, 30), -50_000, NEW, "main", WAITS + "rotated 30m ago)"),
        (retired(600, 61), -50_000, NEW, "main", "rotate: skill changed"),
        ({**QUEUED, "lastRelayAt": ago(1), **retired(5)}, -50_000, NEW, "main", WAITS + "queued"),
        # junk timestamps are not a wait
        ({"lastRelayAt": "soon", "retiredThreads": [{"retiredAt": None}, {}, "x"]}, -50_000, NEW, "main", "rotate: skill changed"),
        # size ignores quiet; the size-off note comes ahead of the waits line
        ({"lastRelayAt": ago(1), **QUEUED}, 0, NEW, "main", "rotate: size"),
        ({"lastRelayAt": ago(1), "tk": ("T1", 10_000)}, 10_000, NEW, "main", "ok (size trigger off"),
    ],
)
def test_decide(cap, state, context_over_cap_by, commit, branch, want):
    state = {"skillCommit": OLD, "chiefThreadId": "T1", **state}
    if "tk" in state:  # takeoverContext as (thread, tokens over the cap)
        thread, over = state.pop("tk")
        state["takeoverContext"] = {"threadId": thread, "tokens": cap + over}
    line = crc.decide(state, cap + context_over_cap_by, NOW, commit, branch, cap)
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
    (230_000, True, "ok (size trigger off: take-over ended at 230k); take-over context=230k", {"threadId": "T1", "tokens": 230_000}),
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
    for f in ("cos_rotation_check.py", "app_root.py", "project_config.py"):
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


def test_hook_blocks_from_a_drifted_cwd(tmp_path):
    # The Stop hook's cwd can drift out of the app. It must still read the app's project.md, state and transcript.
    sid = "0123abcd-0123-0123-0123-0123456789ab"
    app, elsewhere, projects = tmp_path / "app", tmp_path / "elsewhere", tmp_path / "projects"
    (app / "docs" / "agents").mkdir(parents=True)
    (app / "docs" / "agents" / "project.md").write_text("| Issue identifier prefix | `ZZ` |\n| Repo | `acme/app` |\n")
    (app / ".agent-team").mkdir()
    state = app / ".agent-team" / "state.json"
    state.write_text(json.dumps({"chiefSessionId": sid, "chiefThreadId": "T1", "skillCommit": None}))
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
