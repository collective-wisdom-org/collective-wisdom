import pytest

import cos_brief

OID = "a" * 40
OLD = "c" * 40
RESOLVED = f"Head moved to {OID} by resolving conflicts with main; reviews from {OLD} stand."
MAIN_MERGE = f"Head moved to {OID} by merging main; PR diff unchanged since {OLD}. Reviews from {OLD} stand."


@pytest.mark.parametrize(
    "body, who, oid, flagged",
    [
        (RESOLVED, "bot", OID, True),
        (RESOLVED, "other", OID, False),
        (RESOLVED, "bot", "b" * 40, False),
        (MAIN_MERGE, "bot", OID, False),
    ],
)
def test_resolved_flag_needs_the_conflict_note_by_our_login_on_this_head(body, who, oid, flagged):
    comments = [{"body": body, "author": {"login": who}}]
    assert bool(cos_brief.resolved_flag(oid, comments, "bot")) == flagged


@pytest.mark.parametrize("mergeable, shown", [("CONFLICTING", True), ("MERGEABLE", False), ("UNKNOWN", False)])
def test_pr_prints_conflict_line(monkeypatch, capsys, mergeable, shown):
    pr = {"url": "u", "title": "t", "headRefOid": OID, "headRefName": "x", "files": [], "statusCheckRollup": [],
          "comments": [], "mergeable": mergeable}
    monkeypatch.setattr(cos_brief, "gh_json", lambda *a: pr)
    monkeypatch.setattr(cos_brief, "own_login", lambda: "bot")
    monkeypatch.setattr(cos_brief, "cost_line", lambda b: "cost: unknown")
    cos_brief.cmd_pr(type("A", (), {"number": 7, "head": None})())
    assert ("conflict: yes" in capsys.readouterr().out.splitlines()) == shown
