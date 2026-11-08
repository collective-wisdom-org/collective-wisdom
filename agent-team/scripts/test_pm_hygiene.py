import importlib.util
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("pm_hygiene", Path(__file__).with_name("pm_hygiene.py"))
pm_hygiene = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pm_hygiene)

FIXTURE = Path(os.environ["PROJECT_MD"]).read_text()  # conftest's: prefix ABC, repo example/app
NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
SINCE = "2026-11-07T00:00:00Z"


def run(tmp_path, monkeypatch, capsys, cmd, stdin, state=None, areas="none", extra=(), gh=None):
    md = tmp_path / "project.md"
    md.write_text(FIXTURE + f"\n## Areas and labels\n\n- Area labels: {areas}. Type labels: `Feature`, `Improvement`, `Bug`.\n")
    monkeypatch.setenv("PROJECT_MD", str(md))
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state if state is not None else {"tickets": {}, "merged": {}, "pm": {}}))
    before = path.read_bytes()
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin if isinstance(stdin, str) else json.dumps(stdin)))
    monkeypatch.setattr(pm_hygiene, "now", lambda: NOW)
    if gh:
        monkeypatch.setattr(pm_hygiene, "gh", gh)
    code = pm_hygiene.main([cmd, "--file", str(path), *extra])
    assert path.read_bytes() == before  # never writes
    return code, capsys.readouterr().out.splitlines()


def ticket(n, state="Backlog", labels=(), priority="No priority", **kw):
    return {"id": f"ABC-{n}", "title": "t", "state": state, "labels": list(labels), "priority": priority, **kw}


S = {"tickets": {"ABC-9": {}}, "merged": {}, "pm": {"filled": {"ABC-3": ["priority"]}}}


@pytest.mark.parametrize("areas,tickets,state,want", [
    # nothing set: all of priority, type; area only when the project names area labels
    ("none", [ticket(1)], None, ["ABC-1 fill: priority, type"]),
    ("`web`, `api`", [ticket(1)], None, ["ABC-1 fill: priority, area, type"]),
    ("`web`, `api`", [ticket(1, labels=["Web", "Bug"], priority="High")], None, []),
    ("`web`, `api`", [ticket(1, labels=["Bug"], priority="Medium")], None, ["ABC-1 fill: area"]),
    ("none", [ticket(1, labels=[{"name": "type:bug"}], priority={"name": "No priority", "value": 0})], None, ["ABC-1 fill: priority"]),
    # pm.filled blocks a refill of that field only
    ("`web`", [ticket(3, labels=["Bug"], priority="Low", state="Todo")], S, ["ABC-3 fill: area"]),
    ("none", [ticket(3)], S, ["ABC-3 fill: type"]),
    # Chief of Staff tickets, finished states and other labels are left alone
    ("none", [ticket(9)], S, []),
    ("none", [ticket(1, state="Done"), ticket(2, state="Canceled")], None, []),
    ("none", [ticket(4, state="In Review", labels=["agent"])], None, ["ABC-4 fill: priority, type"]),
    ("none", [{"id": "XYZ-1", "state": "Backlog"}], None, []),
])
def test_fill(tmp_path, monkeypatch, capsys, areas, tickets, state, want):
    assert run(tmp_path, monkeypatch, capsys, "fill", tickets, state, areas) == (0, want)


def test_fill_reads_two_pasted_lists_and_rejects_junk(tmp_path, monkeypatch, capsys):
    both = json.dumps([ticket(1)]) + "\n" + json.dumps({"issues": [ticket(2)]})
    assert run(tmp_path, monkeypatch, capsys, "fill", both)[1] == ["ABC-1 fill: priority, type", "ABC-2 fill: priority, type"]
    assert run(tmp_path, monkeypatch, capsys, "fill", "not json") == (2, ["pm_hygiene: stdin is not JSON"])


def pr(n, branch="feat/abc-1-x", state="OPEN", created="2026-11-07T10:00:00Z", merged=None, title="x"):
    return {"number": n, "state": state, "headRefName": branch, "title": title, "createdAt": created, "mergedAt": merged}


def tk(state, *labels):
    return {"state": state, "labels": list(labels)}


MERGED = pr(5, state="MERGED", created="2026-11-01T10:00:00Z", merged="2026-11-07T10:00:00Z")
OLD_MERGE = pr(5, state="MERGED", created="2026-11-01T10:00:00Z", merged="2026-11-06T10:00:00Z")
OLD_OPEN = pr(6, created="2026-11-06T10:00:00Z")
AGENT_STATE = {"tickets": {}, "merged": {"ABC-1": {"pr": 5, "at": "2026-11-07T11:00:00Z"}}, "pm": {}}


@pytest.mark.parametrize("prs,tickets,state,want", [
    # first run: which PRs could move a ticket
    ([MERGED], {}, None, ["get ABC-1 #5"]),
    ([pr(6)], {}, None, ["get ABC-1 #6"]),
    ([pr(7, branch="feat/other", title="Do it (ABC-2)")], {}, None, ["get ABC-2 #7"]),
    ([OLD_MERGE, OLD_OPEN, pr(8, state="CLOSED")], {}, None, []),
    ([pr(7, branch="feat/abc-12-x")], {}, None, ["get ABC-12 #7"]),
    ([pr(7, branch="feat/abc-1-x")], {}, {"tickets": {"ABC-1": {}}, "merged": {}}, []),
    ([pr(7, branch="main", title="no ticket")], {}, None, []),
    # second run: the moves
    ([MERGED], {"ABC-1": tk("In Progress")}, None, ["move ABC-1 Done (PR #5 merged)"]),
    ([MERGED], {"ABC-1": tk("In Review")}, None, ["move ABC-1 Done (PR #5 merged)"]),
    ([MERGED], {"ABC-1": tk("Done")}, None, []),
    ([MERGED], {"ABC-1": tk("Canceled")}, None, []),
    ([MERGED], {"ABC-1": tk("Duplicate")}, None, []),
    ([OLD_MERGE], {"ABC-1": tk("In Progress")}, None, []),
    ([pr(6)], {"ABC-1": tk("Backlog")}, None, ["move ABC-1 In Review (PR #6 open)"]),
    ([pr(6)], {"ABC-1": tk("Todo")}, None, ["move ABC-1 In Review (PR #6 open)"]),
    ([pr(6)], {"ABC-1": tk("In Progress")}, None, ["move ABC-1 In Review (PR #6 open)"]),
    ([pr(6)], {"ABC-1": tk("In Review")}, None, []),
    ([pr(6)], {"ABC-1": tk("Done")}, None, []),
    ([OLD_OPEN], {"ABC-1": tk("In Progress")}, None, []),
    ([pr(6, state="CLOSED")], {"ABC-1": tk("In Progress")}, None, []),
    # a merged and an open PR for one ticket move it once, to Done
    ([pr(6), MERGED], {"ABC-1": tk("In Progress")}, None, ["move ABC-1 Done (PR #5 merged)"]),
    # the agent label: skipped unless the ticket is in merged, and then only Done
    ([MERGED], {"ABC-1": tk("In Progress", "agent")}, None, []),
    ([MERGED], {"ABC-1": tk("In Progress", {"name": "agent"})}, None, []),
    ([MERGED], {"ABC-1": tk("In Progress", "agent")}, AGENT_STATE, ["move ABC-1 Done (PR #5 merged)"]),
    ([pr(6)], {"ABC-1": tk("In Progress", "agent")}, AGENT_STATE, []),
    ([pr(6)], {"ABC-1": tk("In Progress", "agent")}, None, []),
    # a ticket the get-ticket read did not return is left alone
    ([MERGED], {"ABC-2": tk("In Progress")}, None, []),
])
def test_drift(tmp_path, monkeypatch, capsys, prs, tickets, state, want):
    got = run(tmp_path, monkeypatch, capsys, "drift", {"prs": prs, "tickets": tickets}, state, extra=["--since", SINCE])
    assert got == (0, want)


def test_drift_bad_input(tmp_path, monkeypatch, capsys):
    assert run(tmp_path, monkeypatch, capsys, "drift", {"prs": []}, extra=["--since", "yesterday"]) == (2, ["pm_hygiene: bad --since"])
    assert run(tmp_path, monkeypatch, capsys, "drift", [], extra=["--since", SINCE])[0] == 2


def stub(prs, commit_date=None, calls=None):
    """gh reads: one PR search answer, one commit date for every branch."""
    def gh(args):
        if calls is not None:
            calls.append(args)
        if args[0] == "pr":
            return json.dumps(prs)
        if commit_date is None:
            raise OSError("exit 1")
        return json.dumps([{"commit": {"committer": {"date": commit_date}, "author": {"date": "2000-01-01T00:00:00Z"}}}])
    return gh


OLD = "2026-11-01T10:00:00Z"  # 7 days before NOW
FRESH = "2026-11-07T10:00:00Z"
STALE_STATE = {"tickets": {"ABC-9": {}}, "merged": {}, "pm": {"flaggedStale": {"ABC-2": "2026-11-01T10:00:00Z"}}}


@pytest.mark.parametrize("tickets,prs,commit,state,want", [
    ([ticket(1, "In Progress", updatedAt=OLD)], [], None, None, ["stale ABC-1 In Progress since 2026-11-01"]),
    ([ticket(1, "In Review", updatedAt=FRESH)], [], None, None, []),
    # a recent PR update or branch commit counts as activity
    ([ticket(1, "In Progress", updatedAt=OLD)], [{"number": 3, "updatedAt": FRESH, "headRefName": "feat/abc-1-x"}], None, None, []),
    ([ticket(1, "In Progress", updatedAt=OLD)], [{"number": 3, "updatedAt": OLD, "headRefName": "feat/abc-1-x"}], FRESH, None, []),
    # the newest of the three times is the one reported
    ([ticket(1, "In Progress", updatedAt=OLD)], [{"number": 3, "updatedAt": "2026-11-02T10:00:00Z", "headRefName": "feat/abc-1-x"}], "2026-11-03T10:00:00Z", None,
     ["stale ABC-1 In Progress since 2026-11-03"]),
    # already flagged for that time; a newer stale time flags again
    ([ticket(2, "In Progress", updatedAt=OLD)], [], None, STALE_STATE, []),
    ([ticket(2, "In Progress", updatedAt="2026-11-04T10:00:00Z")], [], None, STALE_STATE, ["stale ABC-2 In Progress since 2026-11-04"]),
    # Chief of Staff tickets are skipped
    ([ticket(9, "In Progress", updatedAt=OLD)], [], None, STALE_STATE, []),
    # a deleted branch (commit read fails) falls back to the other two times
    ([ticket(1, "In Progress", updatedAt=OLD)], [{"number": 3, "updatedAt": "2026-11-02T10:00:00Z", "headRefName": "gone"}], None, None,
     ["stale ABC-1 In Progress since 2026-11-02"]),
])
def test_stale(tmp_path, monkeypatch, capsys, tickets, prs, commit, state, want):
    assert run(tmp_path, monkeypatch, capsys, "stale", tickets, state, gh=stub(prs, commit)) == (0, want)


@pytest.mark.parametrize("branch,queried", [
    ("feat/abc-1_x.y", True),
    ("feat/abc-1; rm -rf", False),
    ("$(touch x)", False),
    ("-fbad", True),  # matches the pattern; gh.sh passes it as a -f value, never as a flag
    ("", False),
])
def test_stale_only_reads_safe_branch_names(tmp_path, monkeypatch, capsys, branch, queried):
    calls = []
    prs = [{"number": 3, "updatedAt": OLD, "headRefName": branch}]
    run(tmp_path, monkeypatch, capsys, "stale", [ticket(1, "In Progress", updatedAt=OLD)], gh=stub(prs, None, calls))
    assert [c for c in calls if c[0] == "api"] == ([["api", "-X", "GET", "repos/example/app/commits", "-f", f"sha={branch}", "-f", "per_page=1"]] if queried else [])
    assert calls[0] == ["pr", "list", "--state", "all", "--search", "ABC-1", "--json", "number,updatedAt,headRefName"]


def test_stale_skips_a_ticket_when_the_pr_read_fails(tmp_path, monkeypatch, capsys):
    def boom(args):
        raise OSError("exit 1")

    got = run(tmp_path, monkeypatch, capsys, "stale", [ticket(1, "In Progress", updatedAt=OLD)], gh=boom)
    assert got == (0, ["pm_hygiene: could not read PRs for ABC-1, not checked"])


def test_unreadable_state(tmp_path, monkeypatch, capsys):
    for bad in ({"tickets": []}, {"tickets": {}, "merged": []}):
        assert run(tmp_path, monkeypatch, capsys, "fill", [], bad) == (2, ["pm_hygiene: unreadable state file"])
