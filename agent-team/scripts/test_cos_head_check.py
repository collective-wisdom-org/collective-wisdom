import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_head_check", Path(__file__).with_name("cos_head_check.py"))
cos_head_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_head_check)

OLD, NEW = "a" * 40, "b" * 40
MOVED = (
    "CHIEF OF STAFF: the PR head moved from aaaaaaa to bbbbbbb after the user approved. Re-check the reviews per "
    "ship-loop § Phases, 4. Security review (~/.collective-wisdom/scripts/pr_diff_delta.py) and report MERGE READY again."
)
PLAIN = "CHIEF OF STAFF: the PR conflicts with main. Resolve it per open-pr § Conflict resolution and report MERGE READY."
KEPT = (
    "CHIEF OF STAFF: the PR conflicts with main. The user approved the merge at head aaaaaaa. "
    "Resolve it per open-pr § Conflict resolution and merge."
)


@pytest.mark.parametrize(
    "live, mergeable, rule, flags, want, code",
    [
        (OLD, "MERGEABLE", "off", [], ["head-check: ok"], 0),
        (OLD, "UNKNOWN", "on", [], ["head-check: ok"], 0),
        (NEW, "MERGEABLE", "off", [], [MOVED, "head-check: moved aaaaaaa bbbbbbb"], 0),
        (NEW, "CONFLICTING", "off", [], [MOVED, "head-check: moved aaaaaaa bbbbbbb"], 0),
        (OLD, "CONFLICTING", "off", [], [KEPT, "head-check: conflict keep"], 0),
        (OLD, "CONFLICTING", "on", [], [PLAIN, "head-check: conflict withdraw"], 0),
        (OLD, "CONFLICTING", "off", ["--no-approval"], [PLAIN, "head-check: conflict withdraw"], 0),
        (NEW, "MERGEABLE", "off", ["--no-approval"], [MOVED, "head-check: moved aaaaaaa bbbbbbb"], 0),
        ("junk", "MERGEABLE", "off", [], ["head-check: cannot read the PR"], 2),
        (OLD, None, "off", [], ["head-check: cannot read the PR"], 2),
    ],
)
def test_head_check(tmp_path, monkeypatch, capsys, live, mergeable, rule, flags, want, code):
    monkeypatch.setattr(cos_head_check.project_config, "review_after_conflict", lambda: rule)
    monkeypatch.setattr(cos_head_check.project_config, "target_branch", lambda: "main")
    (tmp_path / "state.json").write_text(json.dumps({"tickets": {"ABC-1": {"stage": "awaiting-merge", "pr": 5, "headSha": OLD}}}))
    (tmp_path / "prs.json").write_text(json.dumps({"5": {"headRefOid": live, "mergeable": mergeable}}))
    argv = ["ABC-1", "--file", str(tmp_path / "state.json"), "--prs", str(tmp_path / "prs.json"), *flags]
    assert cos_head_check.main(argv) == code
    assert capsys.readouterr().out.splitlines() == want


@pytest.mark.parametrize(
    "state, want",
    [
        (None, "head-check: cannot read the ticket in state"),
        ("not json", "head-check: cannot read the ticket in state"),
        ({"tickets": {}}, "head-check: cannot read the ticket in state"),
        ({"tickets": {"ABC-1": {"stage": "awaiting-merge", "pr": 5}}}, "head-check: cannot read the ticket in state"),
        ({"tickets": {"ABC-1": {"pr": 5, "headSha": "abc"}}}, "head-check: cannot read pr and headSha in state"),
    ],
)
def test_unreadable_state(tmp_path, capsys, state, want):
    path = tmp_path / "state.json"
    if state is not None:
        path.write_text(state if isinstance(state, str) else json.dumps(state))
    assert cos_head_check.main(["ABC-1", "--file", str(path)]) == 2
    assert capsys.readouterr().out.splitlines() == [want]


def test_setting_unreadable(tmp_path, monkeypatch, capsys):
    def boom():
        raise SystemExit("bad row")

    monkeypatch.setattr(cos_head_check.project_config, "review_after_conflict", boom)
    monkeypatch.setattr(cos_head_check.project_config, "target_branch", lambda: "main")
    (tmp_path / "state.json").write_text(json.dumps({"tickets": {"ABC-1": {"pr": 5, "headSha": OLD}}}))
    (tmp_path / "prs.json").write_text(json.dumps({"5": {"headRefOid": OLD, "mergeable": "CONFLICTING"}}))
    argv = ["ABC-1", "--file", str(tmp_path / "state.json"), "--prs", str(tmp_path / "prs.json")]
    assert cos_head_check.main(argv) == 2
    assert capsys.readouterr().out.splitlines() == ["head-check: cannot read the merge target branch or its settings"]
