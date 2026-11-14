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
        ("infra/cw-57-cost", (0, "cost $1.00 API-equivalent\n"), "cost: cost $1.00 API-equivalent"),
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
    monkeypatch.setattr(cos_brief, "own_login", lambda: "me")
    cos_brief.cmd_pr(type("A", (), {"number": 5, "head": None})())
    assert want in capsys.readouterr().out.splitlines()
    assert calls == ([["--ticket", "CW-57"]] if branch.startswith(("feat/", "infra/")) else [])


SUCCESS = {"__typename": "CheckRun", "name": "t", "status": "COMPLETED", "conclusion": "SUCCESS"}
REVIEWS = [{"body": f"## {k} review (pass 1)\n\nVerdict: PASS", "url": "u", "author": {"login": "me"}} for k in ("Code", "Security")]
BOT_THREAD = {"id": "PRRT_1", "isResolved": False, "path": "a.py", "line": 3,
              "head": {"nodes": [{"author": {"login": "some-bot[bot]"}, "url": "https://github.com/o/r/pull/5#r1"}]}}


@pytest.mark.parametrize(
    "rows, rollup, threads, want, absent",
    [
        ("", [SUCCESS], [], ["code review: pass 1 PASS u ()", "security review: pass 1 PASS u ()"], ["ci:", "ci-review:"]),
        ("| Review mode | `ci` |\n| CI review bot login | `some-bot` |\n", [SUCCESS], [BOT_THREAD],
         [f"ci: green at {'a' * 40}", "ci-review: #5 some-bot: 0 fixed, 0 answered and resolved, 1 unresolved"], ["code review", "security review", "head moved"]),
        ("| Review mode | `ci` |\n| CI review bot login | `some-bot` |\n", [{**SUCCESS, "conclusion": "FAILURE"}], [],
         [f"ci: not green at {'a' * 40}", "ci-review: #5 some-bot: 0 fixed, 0 answered and resolved, 0 unresolved"], ["code review"]),
    ],
)
def test_pr_review_lines_by_mode(tmp_path, monkeypatch, capsys, rows, rollup, threads, want, absent):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n" + rows)
    monkeypatch.setenv("PROJECT_MD", str(md))
    pr = json.loads(fake_pr("feat/cw-57-cost"))
    pr.update(statusCheckRollup=rollup, comments=REVIEWS)
    gql = {"data": {"repository": {"pullRequest": {"reviewThreads": {"pageInfo": {"hasNextPage": False}, "nodes": threads}}}}}
    monkeypatch.setattr(cos_brief, "gh", lambda *a: json.dumps(gql if "graphql" in a else pr))
    monkeypatch.setattr(cos_brief, "own_login", lambda: "me")
    monkeypatch.setattr(cos_brief, "cost_line", lambda b: "cost: unknown")
    cos_brief.cmd_pr(type("A", (), {"number": 5, "head": None})())
    out = capsys.readouterr().out
    assert all(w in out.splitlines() for w in want) and not any(a in out for a in absent)
