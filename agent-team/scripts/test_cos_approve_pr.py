import importlib.util
import json
import os
import sqlite3
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_approve_pr", Path(__file__).with_name("cos_approve_pr.py"))
cap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cap)

HEAD = "a" * 40
SEEN = "2026-11-02T01:00:00Z"
OWNER_REVIEW = {"author": {"login": "Owner"}, "state": "APPROVED", "commit": {"oid": HEAD}, "submittedAt": "2026-11-02T03:00:00Z"}


def msg(mid="m1", by="user", text="approve 87", created="2026-11-02T02:00:00Z"):
    return (mid, "chief", "user", 0, created, json.dumps({"text": text, "createdBy": by}))


# Each row changes one thing from the happy path: (id, changes, exit code, posts, last-line part).
ROWS = [
    ("happy", {}, 0, 1, "approved #7 at " + HEAD),
    ("already approved", {"reviews": [OWNER_REVIEW]}, 0, 0, "already approved by owner"),
    ("already approved, agent message only", {"reviews": [OWNER_REVIEW], "msgs": [msg(by="agent")]}, 1, 0, "no verified"),
    ("agent message", {"msgs": [msg(by="agent")]}, 1, 0, "no verified"),
    ("message before lastSeenAt", {"msgs": [msg(created="2026-11-02T00:30:00Z")]}, 1, 0, "no verified"),
    ("wrong number", {"msgs": [msg(text="approve 870")]}, 1, 0, "no verified"),
    ("not awaiting-merge", {"stage": "merge"}, 1, 0, "not in awaiting-merge"),
    ("agent login", {"login": "builder-bot"}, 1, 0, "agent user builder-bot"),
    ("not the owner", {"login": "someone"}, 1, 0, "not the owner"),
    ("draft", {"pr": {"isDraft": True}}, 1, 0, "draft"),
    ("closed", {"pr": {"state": "CLOSED"}}, 1, 0, "closed"),
    ("head moved", {"pr": {"headRefOid": "b" * 40}}, 1, 0, "not the approved head"),
    ("not root checkout", {"root": "/elsewhere"}, 1, 0, "root checkout"),
    ("pr read fails", {"fail": "view"}, 2, 0, "cannot read PR #7"),
    ("post fails", {"fail": "POST"}, 2, 1, "cannot post the review"),
    ("state tickets is a list", {"tickets": []}, 2, 0, "cannot read the state file or PR facts: AttributeError"),
    ("pr facts miss a key", {"dropkey": "isDraft"}, 2, 0, "cannot read the state file or PR facts: KeyError"),
    ("no message store", {"nodb": True}, 2, 0, "cannot read the message store"),
]


@pytest.mark.parametrize("changes, code, posts, line", [r[1:] for r in ROWS], ids=[r[0] for r in ROWS])
def test_cos_approve(tmp_path, monkeypatch, capsys, changes, code, posts, line):
    real = cap.project_config.value
    monkeypatch.setattr(cap.project_config, "value", lambda k: "owner" if k == "Owner login" else real(k))
    monkeypatch.setattr(cap.project_config, "role_login", lambda r: "builder-bot" if r == "builder" else None)
    monkeypatch.setenv("AGENT_GH_ROLE", "chief-of-staff")
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
          "reviews": changes.get("reviews", []), **changes.get("pr", {})}
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
    reviews = [c for c in calls if "POST" in c]
    assert len(reviews) == posts
    assert "AGENT_GH_ROLE" not in os.environ
    if code == 0 and posts:
        assert "event=APPROVE" in reviews[0] and f"commit_id={HEAD}" in reviews[0]
        assert any('"approve 87"' in a for a in reviews[0])
