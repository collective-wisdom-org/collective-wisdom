import json

import pytest

import cos_brief


def fake_pr(branch):
    return json.dumps({"url": "u", "title": "t", "headRefOid": "a" * 40, "headRefName": branch,
                       "files": [], "statusCheckRollup": [], "comments": []})


@pytest.mark.parametrize(
    "branch, usage, want",
    [
        ("feat/cw-57-cost", (0, "cost $1.00 API-equivalent\n"), "cost: cost $1.00 API-equivalent"),
        ("feat/cw-57-cost", (2, ""), "cost: unknown"),
        ("feat/cw-57-cost", "timeout", "cost: unknown"),
        ("fix/whatever", None, "cost: unknown"),  # not a ticket branch: the script is not run
    ],
)
def test_pr_prints_cost_line_and_never_fails_on_it(monkeypatch, capsys, branch, usage, want):
    calls = []

    def fake_run(cmd, **kw):
        if cmd[0] == cos_brief.GH:
            return type("P", (), {"returncode": 0, "stdout": fake_pr(branch), "stderr": ""})()
        calls.append(cmd[-2:])
        if usage == "timeout":
            raise cos_brief.subprocess.TimeoutExpired(cmd, kw["timeout"])
        return type("P", (), {"returncode": usage[0], "stdout": usage[1], "stderr": ""})()

    monkeypatch.setattr(cos_brief.subprocess, "run", fake_run)
    monkeypatch.setattr(cos_brief, "role_author", lambda role: "me")
    cos_brief.cmd_pr(type("A", (), {"number": 5, "head": None})())
    assert want in capsys.readouterr().out.splitlines()
    assert calls == ([["--ticket", "CW-57"]] if branch.startswith("feat/") else [])
