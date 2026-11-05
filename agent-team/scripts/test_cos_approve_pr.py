import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_approve_pr", Path(__file__).with_name("cos_approve_pr.py"))
cap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cap)

HEAD = "a" * 40
SEEN = "2026-11-02T01:00:00Z"


def msg(mid="m1", by="user", text="approve 87", created="2026-11-02T02:00:00Z"):
    return (mid, "chief", "user", 0, created, json.dumps({"text": text, "createdBy": by}))


# Each row changes one thing from the happy path: (id, changes, exit code, last-line part).
ROWS = [
    ("happy", {}, 0, f'verified approve 87 for #7 at {HEAD} (user wrote: "approve 87")'),
    ("snippet is one line, cut at 80", {"msgs": [msg(text="approve 87\n" + "x" * 90)]}, 0, f'at {HEAD} (user wrote: "approve 87 {"x" * 69}")'),
    ("agent message", {"msgs": [msg(by="agent")]}, 1, "no verified"),
    ("message before lastSeenAt", {"msgs": [msg(created="2026-11-02T00:30:00Z")]}, 1, "no verified"),
    ("wrong number", {"msgs": [msg(text="approve 870")]}, 1, "no verified"),
    ("not awaiting-merge", {"stage": "merge"}, 1, "not in awaiting-merge"),
    ("not the owner", {"login": "someone"}, 1, "not the owner"),
    ("draft", {"pr": {"isDraft": True}}, 1, "draft"),
    ("closed", {"pr": {"state": "CLOSED"}}, 1, "closed"),
    ("head moved", {"pr": {"headRefOid": "b" * 40}}, 1, "not the approved head"),
    ("not root checkout", {"root": "/elsewhere"}, 1, "root checkout"),
    ("pr read fails", {"fail": "view"}, 2, "cannot read PR #7"),
    ("state tickets is a list", {"tickets": []}, 2, "cannot read the state file or PR facts: AttributeError"),
    ("pr facts miss a key", {"dropkey": "isDraft"}, 2, "cannot read the state file or PR facts: KeyError"),
    ("no message store", {"nodb": True}, 2, "cannot read the message store"),
]


@pytest.mark.parametrize("changes, code, line", [r[1:] for r in ROWS], ids=[r[0] for r in ROWS])
def test_cos_approve(tmp_path, monkeypatch, capsys, changes, code, line):
    real = cap.project_config.value
    monkeypatch.setattr(cap.project_config, "value", lambda k: "owner" if k == "Owner login" else real(k))
    db = tmp_path / "t3.sqlite"
    if not changes.get("nodb"):
        con = sqlite3.connect(db)
        con.execute(
            "CREATE TABLE orchestration_v2_projection_messages (message_id TEXT, thread_id TEXT, "
            "role TEXT, streaming INTEGER, created_at TEXT, payload_json TEXT)"
        )
        con.executemany("INSERT INTO orchestration_v2_projection_messages VALUES (?,?,?,?,?,?)", changes.get("msgs", [msg()]))
        con.commit()
        con.close()
    state = tmp_path / "state.json"
    ticket = {"stage": changes.get("stage", "awaiting-merge"), "pr": 7, "headSha": HEAD, "lastSeenAt": SEEN}
    state.write_text(json.dumps({"chiefThreadId": "chief", "tickets": changes.get("tickets", {"ABC-87": ticket})}))
    monkeypatch.setattr(cap.cos_user_check, "DEFAULT_DB", db)
    monkeypatch.setattr(cap.cos_state, "DEFAULT_FILE", state)
    pr = {"state": "OPEN", "isDraft": False, "baseRefName": "main", "isCrossRepository": False, "headRefOid": HEAD,
          **changes.get("pr", {})}
    pr.pop(changes.get("dropkey"), None)
    calls = []

    def run(cmd):
        calls.append(cmd)
        if cmd[0] == "git":
            return f"worktree {changes.get('root', cap.ROOT)}\nHEAD x\n\n"
        if changes.get("fail") in cmd:
            raise cap.merge_pr.CmdError("boom")
        return changes.get("login", "owner") if "user" in cmd else json.dumps(pr)

    assert cap.main(["ABC-87"], run) == code
    assert capsys.readouterr().out.strip().splitlines()[-1].count(line) == 1
    assert not [c for c in calls if "-X" in c], "the script writes nothing to GitHub"


F = lambda *paths: [{"path": p} for p in paths]  # noqa: E731
STATUS = "PR #7 ready. Risk: Medium (changes how the team works)."

# --auto: each row changes one thing from the happy path (Medium under permissive, no user message in the store).
AUTO_ROWS = [
    ("medium under permissive", {}, 0, f"auto-approved #7 at {HEAD} under permissive (Risk: Medium)"),
    ("low under balanced", {"tol": "balanced", "status": "Risk: Low (x)."}, 0, "under balanced (Risk: Low)"),
    ("no thread or lastSeenAt needed", {"seen": None}, 0, "auto-approved"),
    ("medium under balanced", {"tol": "balanced"}, 1, "the user decides: Medium"),
    ("strict", {"tol": "strict"}, 1, "the user decides: strict"),
    ("setting unreadable", {"tol": "strict", "note": "could not read project.md"}, 1, "could not read project.md"),
    ("high", {"status": "Risk: High (x)."}, 1, "the user decides: High"),
    ("not rated", {"status": "PR #7 ready."}, 1, "the user decides: not rated"),
    ("approval path file", {"files": F("README.md", "agent-team/scripts/merge_pr.py")}, 1, "approval path (agent-team/scripts/merge_pr.py)"),
    ("project.md", {"files": F("docs/agents/project.md")}, 1, "approval path"),
    ("renamed file", {"files": [{"path": "docs/x.md", "changeType": "RENAMED"}]}, 1, "renames a file (docs/x.md)"),
    ("merge-queued auto relay", {"stage": "merge-queued", "relay": "CHIEF OF STAFF: auto-approved the merge of PR #7"}, 0, "auto-approved"),
    ("merge-queued user relay", {"stage": "merge-queued", "relay": "CHIEF OF STAFF: the user approved the merge"}, 1, "not in awaiting-merge"),
    ("flag path", {"files": F("src/auth/login.py")}, 1, "flag: src/auth/login.py"),
    ("too many files", {"files": F(*[f"f{i}.md" for i in range(100)])}, 1, "too many to check"),
    ("not the owner", {"login": "someone"}, 1, "not the owner"),
    ("draft", {"pr": {"isDraft": True}}, 1, "draft"),
    ("head moved", {"pr": {"headRefOid": "b" * 40}}, 1, "not the approved head"),
    ("not awaiting-merge", {"stage": "merge"}, 1, "not in awaiting-merge"),
    ("pr read fails", {"fail": "view"}, 2, "cannot read PR #7"),
]


@pytest.mark.parametrize("changes, code, line", [r[1:] for r in AUTO_ROWS], ids=[r[0] for r in AUTO_ROWS])
def test_cos_approve_auto(tmp_path, monkeypatch, capsys, changes, code, line):
    real = cap.project_config.value
    monkeypatch.setattr(cap.project_config, "value", lambda k: "owner" if k == "Owner login" else real(k))
    setting = (changes.get("tol", "permissive"), changes.get("note", ""))
    monkeypatch.setattr(cap.project_config, "approval_setting", lambda: setting)
    state = tmp_path / "state.json"
    ticket = {"stage": changes.get("stage", "awaiting-merge"), "pr": 7, "headSha": HEAD, "lastSeenAt": changes.get("seen", SEEN),
              "status": changes.get("status", STATUS), "pendingRelay": changes.get("relay")}
    state.write_text(json.dumps({"tickets": {"ABC-87": ticket}}))
    monkeypatch.setattr(cap.cos_state, "DEFAULT_FILE", state)
    monkeypatch.setattr(cap.cos_user_check, "DEFAULT_DB", tmp_path / "no-such.sqlite")  # --auto must not open it
    pr = {"state": "OPEN", "isDraft": False, "baseRefName": "main", "isCrossRepository": False, "headRefOid": HEAD,
          "files": changes.get("files", F("agent-team/docs/superpowers/specs/x.md")), **changes.get("pr", {})}
    calls = []

    def run(cmd):
        calls.append(cmd)
        if cmd[0] == "git":
            return f"worktree {cap.ROOT}\nHEAD x\n\n"
        if changes.get("fail") in cmd:
            raise cap.merge_pr.CmdError("boom")
        return changes.get("login", "owner") if "user" in cmd else json.dumps(pr)

    assert cap.main(["ABC-87", "--auto"], run) == code
    assert line in capsys.readouterr().out.strip().splitlines()[-1]
    assert not [c for c in calls if "-X" in c], "the script writes nothing to GitHub"
    assert not (tmp_path / "no-such.sqlite").exists()
