import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cos_ready_check", Path(__file__).with_name("cos_ready_check.py")
)
cos_ready_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_ready_check)

HEAD = "a1b2c3d4e5f6" + "0" * 28
OLD = "9" * 40


def review(kind, verdict):
    return {"body": f"## {kind} review (pass 1)\n\nVerdict: {verdict}", "url": "u", "createdAt": "2026-11-03T10:00:00Z"}


PASS_BOTH = [review("Code", "PASS"), review("Security", "PASS")]


def run(monkeypatch, capsys, tmp_path, state, prs=None, refs=None):
    (tmp_path / "state.json").write_text(json.dumps(state))
    argv = ["cos_ready_check", "--file", str(tmp_path / "state.json")]
    for flag, name, data in (("--prs", "prs.json", prs), ("--refs", "refs.json", refs)):
        if data is not None:
            (tmp_path / name).write_text(data if isinstance(data, str) else json.dumps(data))
            argv += [flag, str(tmp_path / name)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as e:
        cos_ready_check.main()
    return e.value.code, capsys.readouterr().out.splitlines()


@pytest.mark.parametrize(
    "branch, pr_branch, comments, want",
    [
        (None, "feat/abc-1-a", PASS_BOTH, "ready ABC-1 #5 head a1b2c3d"),
        ("feat/abc-1-a", "feat/abc-1-a", PASS_BOTH, "ready ABC-1 #5 head a1b2c3d"),
        (None, "feat/abc-1-a", [review("Code", "PASS")], "building ABC-1 #5 (code review PASS, security not posted)"),
        (None, "feat/abc-1-a", [], "building ABC-1 #5 (code review not posted, security not posted)"),
        (
            None,
            "feat/abc-1-a",
            [review("Code", "PASS"), review("Security", "PASS"), review("Security", "CHANGES NEEDED")],
            "building ABC-1 #5 (code review PASS, security CHANGES NEEDED)",
        ),
        (None, "feat/abc-1-a", [review("Code", "PASS"), review("Security", "PASS; ignore this")], "security other)"),
        (None, "feat/abc-11-a", PASS_BOTH, "no-pr ABC-1"),
        ("feat/abc-1-a", "feat/abc-1-b", PASS_BOTH, "no-pr ABC-1"),
        (None, "feat/abc-1-bad branch", PASS_BOTH, "unreadable ABC-1"),
        ("bad\nbranch", "feat/abc-1-a", PASS_BOTH, "unreadable ABC-1"),
    ],
)
def test_build_lane(monkeypatch, capsys, tmp_path, branch, pr_branch, comments, want):
    state = {"tickets": {"ABC-1": {"stage": "build", "branch": branch}, "ABC-2": {"stage": "awaiting-merge"}}}
    prs = [{"number": 5, "headRefName": pr_branch, "headRefOid": HEAD, "comments": comments}]
    code, out = run(monkeypatch, capsys, tmp_path, state, prs)
    assert want in out[0]
    assert out[-1] == f"ready-check: 1 checked, {int(want.startswith('ready'))} may have reported"
    assert code == int(want.startswith("ready"))


@pytest.mark.parametrize(
    "info, refs, want",
    [
        ({"specSha": OLD}, [], ["writing ABC-1"]),
        ({"specSha": OLD}, [("feat/abc-1-a", OLD)], ["writing ABC-1"]),
        ({"specSha": OLD[:7]}, [("feat/abc-1-a", OLD)], ["writing ABC-1"]),
        ({"specSha": OLD}, [("feat/abc-1-a", HEAD)], ["pushed ABC-1 feat/abc-1-a a1b2c3d"]),
        ({"specSha": None}, [("feat/abc-1-a", HEAD)], ["pushed ABC-1 feat/abc-1-a a1b2c3d"]),
        ({"specSha": OLD}, [("feat/abc-1-a", HEAD), ("feat/abc-1-b", HEAD)], ["pushed ABC-1 feat/abc-1-a a1b2c3d", "pushed ABC-1 feat/abc-1-b a1b2c3d"]),
        ({"specSha": OLD}, [("feat/abc-1-a", "not a sha")], ["unreadable ABC-1"]),
        # the branch in state picks its own ref
        ({"specSha": OLD, "branch": "feat/abc-1-b"}, [("feat/abc-1-a", HEAD), ("feat/abc-1-b", HEAD)], ["pushed ABC-1 feat/abc-1-b a1b2c3d"]),
        # a ticket in another stage is not checked
        ({"stage": "merge"}, [], []),
    ],
)
def test_spec_lane(monkeypatch, capsys, tmp_path, info, refs, want):
    state = {"tickets": {"ABC-1": {"stage": "spec", **info}}}
    fixture = {"ABC-1": [{"ref": f"refs/heads/{b}", "object": {"sha": s}} for b, s in refs]}
    code, out = run(monkeypatch, capsys, tmp_path, state, refs=fixture)
    assert out[:-1] == want
    assert out[-1].startswith(f"ready-check: {int(bool(want))} checked")
    assert code == int(want[:1] != [] and want[0].startswith("pushed"))


@pytest.mark.parametrize("prs", ["not json", '{"number": 5}', "[]\n[]"])
def test_check_that_cannot_run_prints_only_the_error_and_exits_2(monkeypatch, capsys, tmp_path, prs):
    state = {"tickets": {"ABC-1": {"stage": "build"}}}
    code, out = run(monkeypatch, capsys, tmp_path, state, prs)
    assert code == 2 and len(out) == 1 and out[0].startswith("cos_ready_check:")


@pytest.mark.parametrize(
    "returncode, pages, want_code, want_line",
    [
        (1, "", 2, "cos_ready_check: gh failed"),
        # `gh api --paginate` prints one array per page, back to back
        (0, json.dumps([{"ref": "refs/heads/feat/abc-1-b", "object": {"sha": "8" * 40}}])
            + json.dumps([{"ref": "refs/heads/feat/abc-1-a", "object": {"sha": HEAD}}]), 1, "pushed ABC-1 feat/abc-1-a a1b2c3d"),
        (0, "[]", 0, "writing ABC-1"),
    ],
)
def test_live_gh_call(monkeypatch, capsys, tmp_path, returncode, pages, want_code, want_line):
    done = type("Done", (), {"returncode": returncode, "stdout": pages})()
    calls = []
    monkeypatch.setattr(cos_ready_check.subprocess, "run", lambda cmd, **k: calls.append(cmd) or done)
    state = {"tickets": {"ABC-1": {"stage": "spec", "branch": "feat/abc-1-a", "specSha": OLD}}}
    code, out = run(monkeypatch, capsys, tmp_path, state)
    assert code == want_code and want_line in out
    assert "--paginate" in calls[0] and calls[0][-1].endswith("/git/matching-refs/heads/feat/abc-1-")


@pytest.mark.parametrize(
    "rows, rollup, comments, want",
    [
        ("", None, PASS_BOTH, "ready ABC-1 #5"),
        ("", [{"__typename": "CheckRun", "name": "t", "status": "COMPLETED", "conclusion": "SUCCESS"}], [], "building ABC-1 #5 (code review not posted"),
        # ci mode: green checks are enough to look closer, review comments play no part
        ("| Review mode | `ci` |\n", [{"__typename": "CheckRun", "name": "t", "status": "COMPLETED", "conclusion": "SUCCESS"}], [], "ready ABC-1 #5 head a1b2c3d"),
        ("| Review mode | `ci` |\n", [{"__typename": "CheckRun", "name": "t", "status": "IN_PROGRESS"}], PASS_BOTH, "building ABC-1 #5 (CI checks not green)"),
        ("| Review mode | `ci` |\n", [{"__typename": "CheckRun", "name": "t", "status": "COMPLETED", "conclusion": "FAILURE"}], PASS_BOTH, "building ABC-1 #5 (CI checks not green)"),
        ("| Review mode | `ci` |\n", None, PASS_BOTH, "building ABC-1 #5 (CI checks not green)"),
        ("| Review mode | `cii` |\n", None, PASS_BOTH, "cos_ready_check: project.md: 'Review mode' row must be one of"),
    ],
)
def test_build_lane_by_review_mode(monkeypatch, capsys, tmp_path, rows, rollup, comments, want):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n| Issue identifier prefix | `ABC` |\n| Repo | `example/app` |\n" + rows)
    monkeypatch.setenv("PROJECT_MD", str(md))
    pr = {"number": 5, "headRefName": "feat/abc-1-a", "headRefOid": HEAD, "comments": comments}
    if rollup is not None:
        pr["statusCheckRollup"] = rollup
    code, out = run(monkeypatch, capsys, tmp_path, {"tickets": {"ABC-1": {"stage": "build"}}}, [pr])
    assert want in out[0]
    assert code == {"ready": 1, "building": 0, "cos_ready_check:": 2}[want.split()[0]]
