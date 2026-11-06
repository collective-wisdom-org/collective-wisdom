import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cos_untracked_check", Path(__file__).with_name("cos_untracked_check.py")
)
cos_untracked_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_untracked_check)

FIXTURE = Path(os.environ["PROJECT_MD"]).read_text()  # conftest's; its Owner login is `me`


def issue(n, labels=("agent", "status:in-review"), author="bot"):
    return {"number": n, "labels": [{"name": x} for x in labels], "author": {"login": author}}


def pr(n, branch, author="bot"):
    return {"number": n, "headRefName": branch, "author": {"login": author}}


def run(monkeypatch, capsys, tmp_path, tracker, state, issues, prs, login="bot"):
    md = tmp_path / "project.md"
    md.write_text(FIXTURE + f"| Tracker | `{tracker}` |\n")
    monkeypatch.setenv("PROJECT_MD", str(md))
    argv = ["cos_untracked_check", "--file", str(tmp_path / "state.json"), "--open-prs", str(tmp_path / "prs.json"),
            "--issues", str(tmp_path / "issues.json")]
    for name, data in (("state.json", state), ("issues.json", issues), ("prs.json", prs)):
        (tmp_path / name).write_text(data if isinstance(data, str) else json.dumps(data))
    if login is not None:
        argv += ["--login", login]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as e:
        cos_untracked_check.main()
    return e.value.code, capsys.readouterr().out.splitlines()


EMPTY = {"tickets": {}, "merged": {}}
PR5 = pr(5, "feat/abc-1-a")


@pytest.mark.parametrize(
    "tracker, state, issues, prs, want, code",
    [
        ("github", EMPTY, [issue(1)], [PR5], ["untracked ABC-1 in-review #5", "untracked-check: 1 not in state"], 1),
        ("github", {"tickets": {"ABC-1": {}}, "merged": {}}, [issue(1)], [PR5], ["untracked-check: 0 not in state"], 0),
        ("github", {"tickets": {}, "merged": {"ABC-1": {"pr": 5}}}, [issue(1)], [PR5], ["untracked-check: 0 not in state"], 0),
        ("github", EMPTY, [issue(1, ("agent", "agent-skip", "status:in-review"))], [PR5], ["untracked-check: 0 not in state"], 0),
        ("github", EMPTY, [], [PR5], ["untracked-check: 0 not in state"], 0),  # issue closed or not `agent`
        ("github", EMPTY, [issue(2, ("agent", "status:in-progress"))], [], ["untracked ABC-2 in-progress", "untracked-check: 1 not in state"], 1),
        ("github", EMPTY, [issue(2, ("agent",))], [], ["untracked-check: 0 not in state"], 0),  # no status, no PR
        ("github", EMPTY, [issue(1, author="ME")], [PR5], ["untracked ABC-1 in-review #5", "untracked-check: 1 not in state"], 1),  # Owner login
        ("github", EMPTY, [issue(1, author="stranger")], [PR5], ["untracked-check: 0 not in state"], 0),
        ("github", EMPTY, [issue(1, author="stranger")], [pr(5, "feat/abc-1-a", "bot")], ["untracked-check: 0 not in state"], 0),
        ("github", EMPTY, [issue(1)], [pr(5, "feat/abc-11-a"), pr(6, "feat/abc-1-b"), pr(7, "feat/abc-1-a")], ["untracked ABC-1 in-review #6", "untracked-check: 1 not in state"], 1),
        ("linear", EMPTY, [], [pr(5, "feat/abc-1-a", "BOT")], ["untracked ABC-1 #5", "untracked-check: 1 not in state"], 1),
        ("linear", EMPTY, [], [pr(5, "feat/abc-1-a", "stranger")], ["untracked-check: 0 not in state"], 0),
        ("linear", EMPTY, "not json", [PR5], ["untracked ABC-1 #5", "untracked-check: 1 not in state"], 1),  # linear never reads the issue list
        # cannot run: only the error line, exit 2
        ("github", EMPTY, "not json", [PR5], ["cos_untracked_check: bad issue list"], 2),
        ("github", EMPTY, [issue(1)], "not json", ["cos_untracked_check: bad PR list"], 2),
        ("github", "not json", [issue(1)], [PR5], ["cos_untracked_check: unreadable state file"], 2),
        ("gitlab", EMPTY, [], [PR5], ["cos_untracked_check: bad project.md"], 2),
    ],
)
def test_untracked_tickets(monkeypatch, capsys, tmp_path, tracker, state, issues, prs, want, code):
    got_code, out = run(monkeypatch, capsys, tmp_path, tracker, state, issues, prs)
    assert got_code == code
    assert out == want


def test_unreadable_own_login_stops_the_check(monkeypatch, capsys, tmp_path):
    def boom():
        raise cos_untracked_check.cos_brief.ReadError("gh failed")

    monkeypatch.setattr(cos_untracked_check.cos_brief, "own_login", boom)
    code, out = run(monkeypatch, capsys, tmp_path, "github", EMPTY, [issue(1)], [PR5], login=None)
    assert (code, out) == (2, ["cos_untracked_check: could not read own login"])
