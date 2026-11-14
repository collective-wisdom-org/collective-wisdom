import importlib.util
import json
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cos_merged_check", Path(__file__).with_name("cos_merged_check.py")
)
cos_merged_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_merged_check)

AT = "2026-11-03T02:40:00Z"


def run(monkeypatch, capsys, tmp_path, *extra):
    state_file, prs_file = tmp_path / "state.json", tmp_path / "prs.json"
    monkeypatch.setattr(
        sys, "argv", ["cos_merged_check", "--file", str(state_file), "--prs", str(prs_file), *extra]
    )
    with pytest.raises(SystemExit) as e:
        cos_merged_check.main()
    return e.value.code, capsys.readouterr().out


@pytest.mark.parametrize(
    "ticket, prs, want_line, want_code",
    [
        ({"stage": "merge", "branch": "feat/abc-9-a"}, [(7, "feat/abc-9-a")], "merged ABC-9 #7", 1),
        ({"stage": "awaiting-merge", "branch": "feat/abc-9-a"}, [(7, "feat/abc-9-a")], "merged ABC-9 #7", 1),
        ({"stage": "merge-queued", "branch": "feat/abc-9-a"}, [(7, "feat/abc-9-a")], "merged ABC-9 #7", 1),
        ({"stage": "awaiting-review", "branch": "feat/abc-9-a"}, [(7, "feat/abc-9-a")], "merged ABC-9 #7", 1),
        (
            {"stage": "blocked", "resumeStage": "merge", "branch": "feat/abc-9-a"},
            [(7, "feat/abc-9-a")],
            "merged ABC-9 #7",
            1,
        ),
        (
            {"stage": "blocked", "resumeStage": "build", "branch": "feat/abc-9-a"},
            [(7, "feat/abc-9-a")],
            "merged-check: 0 checked",
            0,
        ),
        ({"stage": "build", "branch": "feat/abc-9-a"}, [(7, "feat/abc-9-a")], "merged-check: 0 checked", 0),
        ({"stage": "merge", "branch": "feat/abc-9-a"}, [(7, "feat/abc-4-z")], "mismatch ABC-9 #7 head feat/abc-4-z", 0),
        ({"stage": "merge", "branch": None}, [(7, "feat/abc-9-x")], "merged ABC-9 #7", 1),
        ({"stage": "merge", "branch": None}, [(7, "feat/abc-4-x")], "mismatch ABC-9 #7", 0),
        ({"stage": "merge", "branch": None}, [(7, "feat/abc-90-x")], "mismatch ABC-9 #7", 0),
        ({"stage": "merge", "branch": None}, [(7, "infra/abc-9-x")], "merged ABC-9 #7", 1),
        ({"stage": "merge", "branch": None}, [(7, "infra/abc-90-x")], "mismatch ABC-9 #7", 0),
        ({"stage": "merge", "branch": None}, [(7, "fix/abc-9-x")], "mismatch ABC-9 #7", 0),
        ({"stage": "merge", "branch": "feat/abc-9-a"}, [(8, "feat/abc-9-a")], "open ABC-9 #7", 0),
        ({"stage": "merge", "branch": "feat/abc-9-a"}, [(7, "bad branch\nname")], "unreadable ABC-9 #7", 0),
    ],
)
def test_ticket_leaves_only_when_its_own_branch_merged(
    tmp_path, capsys, monkeypatch, ticket, prs, want_line, want_code
):
    state = {
        "tickets": {"ABC-9": {"pr": 7, **ticket}, "ABC-3": {"stage": "build", "pr": 7}},
        "merged": {},
    }
    (tmp_path / "state.json").write_text(json.dumps(state))
    (tmp_path / "prs.json").write_text(
        json.dumps([{"number": n, "headRefName": h, "mergedAt": AT} for n, h in prs])
    )
    code, out = run(monkeypatch, capsys, tmp_path, "--apply")
    after = json.loads((tmp_path / "state.json").read_text())
    assert code == want_code
    assert want_line in out
    if want_code == 1:
        assert "ABC-9" not in after["tickets"] and after["merged"]["ABC-9"]["pr"] == 7
    else:
        assert after["tickets"]["ABC-9"] == state["tickets"]["ABC-9"] and not after["merged"]
    assert "ABC-3" in after["tickets"]


def test_malformed_ticket_key_does_not_block_the_others(tmp_path, capsys, monkeypatch):
    state = {
        "tickets": {
            "ABC-9": {"stage": "merge", "pr": 7, "branch": "feat/abc-9-a"},
            "ABC-9 ": {"stage": "merge", "pr": 8, "branch": "feat/abc-9-b"},
        },
        "merged": {},
    }
    (tmp_path / "state.json").write_text(json.dumps(state))
    (tmp_path / "prs.json").write_text(
        json.dumps([{"number": n, "headRefName": h, "mergedAt": AT} for n, h in [(7, "feat/abc-9-a"), (8, "feat/abc-9-b")]])
    )
    code, out = run(monkeypatch, capsys, tmp_path, "--apply")
    after = json.loads((tmp_path / "state.json").read_text())
    assert code == 1 and "merged-check: 1 checked, 1 merged" in out
    assert "ABC-9" not in after["tickets"] and "ABC-9 " in after["tickets"]


@pytest.mark.parametrize("prs_text", ["not json", '{"number": 7}', None])
def test_check_that_cannot_run_exits_2_and_writes_nothing(tmp_path, capsys, monkeypatch, prs_text):
    state = {"tickets": {"ABC-9": {"stage": "merge", "pr": 7, "branch": "feat/abc-9-a"}}, "merged": {}}
    (tmp_path / "state.json").write_text(json.dumps(state))
    before = (tmp_path / "state.json").read_text()
    if prs_text is not None:  # None: no PR file at all
        (tmp_path / "prs.json").write_text(prs_text)
    code, out = run(monkeypatch, capsys, tmp_path, "--apply")
    assert code == 2
    assert out.startswith("cos_merged_check:")
    assert (tmp_path / "state.json").read_text() == before


def test_write_that_crashes_exits_2_not_1(tmp_path, capsys, monkeypatch):
    state = {"tickets": {"ABC-9": {"stage": "merge", "pr": 7, "branch": "feat/abc-9-a"}}, "merged": []}
    (tmp_path / "state.json").write_text(json.dumps(state))
    (tmp_path / "prs.json").write_text(
        json.dumps([{"number": 7, "headRefName": "feat/abc-9-a", "mergedAt": AT}])
    )
    code, out = run(monkeypatch, capsys, tmp_path, "--apply")
    assert code == 2 and out.startswith("cos_merged_check:") and "merged ABC-9" not in out
