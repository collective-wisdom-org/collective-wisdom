"""`--next` on cos_rank.py dry and pm_hygiene.py fill, drift and stale: one `next:` per kind of line, and none without the flag."""

import json

import pytest

from test_cos_rank import STATE, cos_rank
from test_pm_hygiene import run, ticket

AT = "2026-11-02T10:00:00Z"


@pytest.mark.parametrize("pm, has", [
    ({}, "ranking child now"),
    ({"rankedAt": AT}, "None means the Backlog is dry"),
])
def test_dry_next(tmp_path, monkeypatch, capsys, pm, has):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({**STATE, "pm": pm}))
    monkeypatch.setattr(cos_rank, "closed_prs_since", lambda at: False)
    assert cos_rank.main(["dry", "--file", str(path)]) == 0
    plain = capsys.readouterr().out.splitlines()
    assert cos_rank.main(["dry", "--file", str(path), "--next"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[:1] == plain and len(out) == 2 and out[1].startswith("next: ") and has in out[1]


def test_fill_next_is_one_line_per_kind_after_the_lines(tmp_path, monkeypatch, capsys):
    code, out = run(tmp_path, monkeypatch, capsys, "fill", [ticket(1), ticket(2)], extra=["--next"])
    assert code == 0 and out[:2] == ["ABC-1 fill: priority, type", "ABC-2 fill: priority, type"]
    assert len(out) == 3 and out[2].startswith("next: Fill only the fields") and "never Urgent" in out[2]


def test_stale_and_drift_next(tmp_path, monkeypatch, capsys):
    old = ticket(5, state="In Progress", updatedAt="2026-11-01T10:00:00Z")
    code, out = run(tmp_path, monkeypatch, capsys, "stale", [old], extra=["--next"], gh=lambda a: "[]")
    assert code == 0 and out[0].startswith("stale ABC-5") and out[1].startswith("next: Save each line's date")
    prs = {"prs": [{"number": 9, "state": "OPEN", "headRefName": "abc-6-x", "title": "t", "createdAt": "2026-11-07T10:00:00Z"}], "tickets": {}}
    code, out = run(tmp_path, monkeypatch, capsys, "drift", prs, extra=["--since", "2026-11-07T00:00:00Z", "--next"])
    assert out[0] == "get ABC-6 #9" and out[1].startswith("next: ") and "run drift again" in out[1]
    prs["tickets"] = {"ABC-6": {"state": "In Progress", "labels": []}}
    code, out = run(tmp_path, monkeypatch, capsys, "drift", prs, extra=["--since", "2026-11-07T00:00:00Z", "--next"])
    assert out[0] == "move ABC-6 In Review (PR #9 open)" and "set-state" in out[1]


def test_no_next_without_the_flag(tmp_path, monkeypatch, capsys):
    code, out = run(tmp_path, monkeypatch, capsys, "fill", [ticket(1)])
    assert code == 0 and out == ["ABC-1 fill: priority, type"]


@pytest.mark.parametrize("body, extra, code, has", [
    (json.dumps([{"id": "ABC-1", "title": "t", "reason": "r", "readiness": "needs: x", "priority": "High", "createdAt": AT}]), [], 0, "pm.needsReported"),
    ("[]", [], 3, "cos_rank.py count"),
    ("[]", ["--backlog-count", "2"], 2, "Backlog ranking rejected"),
    ("not json", [], 2, "Backlog ranking rejected"),
])
def test_ranking_next_per_result(tmp_path, monkeypatch, capsys, body, extra, code, has):
    from test_cos_rank import run
    got, _, _ = run(tmp_path, monkeypatch, body, started=AT, extra=[*extra, "--next"])
    out = capsys.readouterr().out.splitlines()
    assert got == code and out[-1].startswith("next: ") and has in out[-1]
    got, _, _ = run(tmp_path, monkeypatch, body, started=AT, extra=extra)
    assert got == code and "next:" not in capsys.readouterr().out
