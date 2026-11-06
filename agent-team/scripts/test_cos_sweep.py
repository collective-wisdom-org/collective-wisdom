import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_sweep", Path(__file__).with_name("cos_sweep.py"))
cos_sweep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_sweep)

PASS = [
    {"body": f"## {k} review (pass 1)\n\nVerdict: PASS", "url": "u", "createdAt": "2026-11-03T10:00:00Z"}
    for k in ("Code", "Security")
]
BUILD = {"stage": "build", "branch": "feat/abc-1-a"}
OPEN_READY = [{"number": 5, "headRefName": "feat/abc-1-a", "headRefOid": "a" * 40, "comments": PASS}]
MERGED_7 = [{"number": 7, "headRefName": "feat/abc-2-a", "mergedAt": "2026-11-03T02:40:00Z"}]
MERGE = {"stage": "merge", "branch": "feat/abc-2-a", "pr": 7}

UNTRACKED_PR = {"number": 9, "headRefName": "feat/abc-3-x", "author": {"login": "Bot"}}


@pytest.mark.parametrize(
    "tickets, open_prs, want_last, want_in_out, code",
    [
        # ready and under an old parent: listed once, both reasons
        ({"ABC-1": {**BUILD, "parentThreadId": "OLD"}}, OPEN_READY, "read in full: ABC-1 (ready, old-parent); merged: none", [], 1),
        # ready under this thread: the ready check alone lists it
        ({"ABC-1": {**BUILD, "parentThreadId": "ME"}}, OPEN_READY, "read in full: ABC-1 (ready); merged: none", ["ready ABC-1 #5"], 1),
        # just merged: written to state first, so no longer a child to read
        ({"ABC-2": {**MERGE, "parentThreadId": "OLD"}}, [], "read in full: none; merged: ABC-2 #7", ["merged ABC-2 #7"], 1),
        # nothing found
        ({"ABC-1": {**BUILD, "parentThreadId": "ME"}}, [], "read in full: none; merged: none", ["no-pr ABC-1"], 0),
        # ready part cannot run: the other parts still print, exit 2
        ({"ABC-1": {**BUILD, "parentThreadId": "OLD"}}, "not json", "read in full: ABC-1 (old-parent); merged: none; didn't run: ready, untracked",
         ["cos_ready_check:", "merged-check:", "parent-check:", "cos_untracked_check:"], 2),
        # a ticket in flight that state doesn't know (linear: an open PR by our own login): listed on the last line
        ({"ABC-1": {**BUILD, "parentThreadId": "ME"}}, OPEN_READY + [UNTRACKED_PR], "read in full: ABC-1 (ready); merged: none; untracked: ABC-3 #9",
         ["untracked ABC-3 #9"], 1),
    ],
)
def test_sweep_lists_each_child_once_and_runs_every_part(tmp_path, capsys, tickets, open_prs, want_last, want_in_out, code):
    (tmp_path / "state.json").write_text(json.dumps({"tickets": tickets, "merged": {}}))
    (tmp_path / "merged.json").write_text(json.dumps(MERGED_7))
    (tmp_path / "open.json").write_text(open_prs if isinstance(open_prs, str) else json.dumps(open_prs))
    argv = ["--thread", "ME", "--file", str(tmp_path / "state.json"),
            "--merged-prs", str(tmp_path / "merged.json"), "--open-prs", str(tmp_path / "open.json"), "--login", "bot"]
    assert cos_sweep.main(argv) == code
    out = capsys.readouterr().out
    assert out.splitlines()[-1] == "sweep: " + want_last
    for text in want_in_out:
        assert text in out
    if "merged ABC-2" in out:
        assert "ABC-2" not in json.loads((tmp_path / "state.json").read_text())["tickets"]


def test_project_md_without_a_repo_row_only_stops_the_github_parts(tmp_path):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n| Issue identifier prefix (`<PREFIX>`) | `ABC` |\n")
    (tmp_path / "state.json").write_text(json.dumps({"tickets": {"ABC-1": {**BUILD, "parentThreadId": "ME"}}, "merged": {}}))
    (tmp_path / "merged.json").write_text("[]")
    (tmp_path / "open.json").write_text("[]")
    r = subprocess.run(
        [sys.executable, "-I", str(Path(__file__).with_name("cos_sweep.py")), "--thread", "ME",
         "--file", str(tmp_path / "state.json"), "--merged-prs", str(tmp_path / "merged.json"),
         "--open-prs", str(tmp_path / "open.json"), "--login", "bot"],
        capture_output=True, text=True, env={**os.environ, "PROJECT_MD": str(md)},
    )
    lines = r.stdout.splitlines()
    assert r.returncode == 2
    assert any(line.startswith("merged-check:") for line in lines)
    assert lines[-1] == "sweep: read in full: none; merged: none; didn't run: ready, untracked"


@pytest.mark.parametrize(
    "review_prs, want_last, code",
    [
        ({"5": {"state": "OPEN", "author": {"login": "me"}, "headRefOid": "a" * 40, "reviews": [], "reviewDecision": "APPROVED", "reviewRequests": []}},
         "read in full: none; merged: none; review: ABC-1 approved", 1),
        ("not json", "read in full: none; merged: none; didn't run: review", 2),
    ],
)
def test_sweep_runs_the_review_check_last_and_grows_the_last_line(tmp_path, capsys, monkeypatch, review_prs, want_last, code):
    monkeypatch.setattr(cos_sweep.cos_review_check, "identity", lambda run=None: ("agent", []))
    state = {"tickets": {"ABC-1": {"stage": "awaiting-review", "pr": 5, "headSha": "a" * 40, "parentThreadId": "ME"}}, "merged": {}}
    (tmp_path / "state.json").write_text(json.dumps(state))
    (tmp_path / "none.json").write_text("[]")
    (tmp_path / "review.json").write_text(review_prs if isinstance(review_prs, str) else json.dumps(review_prs))
    argv = ["--thread", "ME", "--file", str(tmp_path / "state.json"), "--merged-prs", str(tmp_path / "none.json"),
            "--open-prs", str(tmp_path / "none.json"), "--review-prs", str(tmp_path / "review.json"), "--login", "bot"]
    assert cos_sweep.main(argv) == code
    assert capsys.readouterr().out.splitlines()[-1] == "sweep: " + want_last


def test_unreadable_issue_list_only_stops_the_untracked_part(tmp_path, capsys, monkeypatch):
    md = tmp_path / "project.md"
    md.write_text(Path(os.environ["PROJECT_MD"]).read_text() + "| Tracker | `github` |\n")
    monkeypatch.setenv("PROJECT_MD", str(md))
    for name, text in (("state.json", '{"tickets": {}, "merged": {}}'), ("merged.json", "[]"), ("open.json", "[]"), ("issues.json", "not json")):
        (tmp_path / name).write_text(text)
    argv = ["--thread", "ME", "--file", str(tmp_path / "state.json"), "--merged-prs", str(tmp_path / "merged.json"),
            "--open-prs", str(tmp_path / "open.json"), "--issues", str(tmp_path / "issues.json"), "--login", "bot"]
    assert cos_sweep.main(argv) == 2
    lines = capsys.readouterr().out.splitlines()
    assert "cos_untracked_check: bad issue list" in lines
    assert any(line.startswith("merged-check:") for line in lines)
    assert lines[-1] == "sweep: read in full: none; merged: none; didn't run: untracked"
