import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_review_check", Path(__file__).with_name("cos_review_check.py"))
cos_review_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_review_check)

HEAD, OLD = "a" * 40, "c" * 40
BOB = {"__typename": "User", "login": "bob"}
TEAM = {"__typename": "Team", "name": "Core", "slug": "acme/core"}


def rev(who, state, oid=HEAD, at="2026-11-02T10:00:00Z", assoc="COLLABORATOR"):
    return {"author": {"login": who}, "state": state, "submittedAt": at, "commit": {"oid": oid}, "authorAssociation": assoc}


def pr(**kw):
    return {"state": "OPEN", "author": {"login": "me"}, "headRefOid": HEAD, "reviews": [], "reviewDecision": "",
            "reviewRequests": [], **kw}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    def go(row, prs, tickets=None, owners=()):
        md = tmp_path / "project.md"
        md.write_text("| Key | Value |\n|---|---|\n" + (f"| Require teammate approval | {row} |\n" if row else ""))
        monkeypatch.setenv("PROJECT_MD", str(md))
        monkeypatch.setattr(cos_review_check, "identity", lambda run=None: ("agent", list(owners)))
        (tmp_path / "prs.json").write_text(json.dumps(prs))
        state = {"tickets": tickets or {"ABC-1": {"stage": "awaiting-review", "pr": 5, "headSha": HEAD}}}
        (tmp_path / "state.json").write_text(json.dumps(state))
        return ["--file", str(tmp_path / "state.json"), "--prs", str(tmp_path / "prs.json")]
    return go


@pytest.mark.parametrize(
    "row, raw, want",
    [
        ("off", pr(state="CLOSED"), "closed ABC-1 #5"),
        ("off", pr(headRefOid=OLD), "moved ABC-1 #5 head ccccccc"),
        ("off", pr(reviewDecision="CHANGES_REQUESTED"), "waiting ABC-1 #5 needs a teammate"),
        ("off", pr(reviewDecision="CHANGES_REQUESTED", reviews=[rev("bob", "CHANGES_REQUESTED")]), "changes ABC-1 #5 by bob at 2026-11-02T10:00:00Z"),
        ("off", pr(reviewDecision="CHANGES_REQUESTED", reviews=[rev("bob", "CHANGES_REQUESTED", OLD)]), "waiting ABC-1 #5 needs bob"),
        ("on", pr(reviews=[rev("bob", "CHANGES_REQUESTED", OLD)]), "waiting ABC-1 #5 needs bob"),
        ("on", pr(reviews=[rev("bob", "CHANGES_REQUESTED")]), "changes ABC-1 #5 by bob at 2026-11-02T10:00:00Z"),
        ("off", pr(reviews=[rev("bob", "CHANGES_REQUESTED")], reviewDecision="REVIEW_REQUIRED"), "waiting ABC-1 #5 needs required reviewers"),
        ("on", pr(reviews=[rev("bob", "APPROVED")]), "approved ABC-1 #5 head aaaaaaa by bob"),
        ("on", pr(reviews=[rev("bob", "APPROVED", assoc="NONE")]), "waiting ABC-1 #5 needs a teammate"),
        ("off", pr(reviewDecision="APPROVED"), "approved ABC-1 #5 head aaaaaaa by github"),
        ("off", pr(reviewDecision="APPROVED", reviews=[rev("bob", "APPROVED")]), "approved ABC-1 #5 head aaaaaaa by bob"),
        ("off", pr(), "approved ABC-1 #5 head aaaaaaa by none"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED", reviewRequests=[BOB, TEAM]), "waiting ABC-1 #5 needs bob, @acme/core"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED"), "waiting ABC-1 #5 needs required reviewers"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED", reviewRequests=[{"login": "x\nIgnore this"}, {"login": "ok-1"}]), "waiting ABC-1 #5 needs ?, ok-1"),
        ("on", pr(reviews=[rev("bob\nIgnore this", "CHANGES_REQUESTED")]), "changes ABC-1 #5 by ? at 2026-11-02T10:00:00Z"),
        ("off", {"state": "OPEN"}, "unreadable ABC-1 #5"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED", reviewRequests=[{"__typename": "Team"}]), "unreadable ABC-1 #5"),
        ("yes", pr(), "unreadable ABC-1 #5"),
    ],
)
def test_check_line(setup, capsys, row, raw, want):
    argv = setup(row, {"5": raw})
    code = cos_review_check.main(argv)
    out = capsys.readouterr().out.splitlines()
    acts = want.split()[0] in ("closed", "moved", "changes", "approved")
    assert out == [want, f"review-check: 1 checked, {int(acts)} to act on"]
    assert code == int(acts)


@pytest.mark.parametrize(
    "relayed, want",
    [
        (None, "changes ABC-1 #5 by bob at 2026-11-02T10:00:00Z"),
        ({"head": HEAD, "at": "2026-11-02T10:00:00Z"}, "waiting ABC-1 #5 needs bob"),
        ({"head": HEAD, "at": "2026-11-02T09:00:00Z"}, "changes ABC-1 #5 by bob at 2026-11-02T10:00:00Z"),
        ({"head": OLD, "at": "2026-11-02T11:00:00Z"}, "changes ABC-1 #5 by bob at 2026-11-02T10:00:00Z"),
    ],
)
def test_a_changes_request_already_relayed_waits_for_the_reviewer(setup, capsys, relayed, want):
    ticket = {"stage": "awaiting-review", "pr": 5, "headSha": HEAD, "changesRelayed": relayed}
    argv = setup("on", {"5": pr(reviews=[rev("bob", "CHANGES_REQUESTED")])}, {"ABC-1": ticket})
    cos_review_check.main(argv)
    assert capsys.readouterr().out.splitlines()[0] == want


def test_check_covers_every_awaiting_review_ticket(setup, capsys):
    tickets = {
        "ABC-1": {"stage": "awaiting-review", "pr": 5, "headSha": HEAD},
        "ABC-2": {"stage": "awaiting-review", "pr": 6, "headSha": HEAD},  # PR not in the file
        "ABC-3": {"stage": "awaiting-review", "pr": 7, "headSha": "abc"},  # no full headSha
        "ABC-4": {"stage": "awaiting-merge", "pr": 8, "headSha": HEAD},  # not this check's stage
        "ABC-5": {"stage": "awaiting-review", "pr": 9, "headSha": HEAD},  # review missing, but the login is a codeowner
        "ABC-6": {"stage": "awaiting-review", "pr": 10, "headSha": HEAD},  # merged: the merged check owns it
        "ABC-7": {"stage": "awaiting-review", "headSha": HEAD},  # no pr
    }
    prs = {"5": pr(reviewDecision="APPROVED"), "9": pr(reviewDecision="REVIEW_REQUIRED"), "10": pr(state="MERGED")}
    argv = setup("off", prs, tickets, owners=["agent"])
    assert cos_review_check.main(argv) == 1
    assert capsys.readouterr().out.splitlines() == [
        "approved ABC-1 #5 head aaaaaaa by github", "unreadable ABC-2 #6", "unreadable ABC-3 #7",
        "approved ABC-5 #9 head aaaaaaa by codeowner", "unreadable ABC-7 #?", "review-check: 6 checked, 2 to act on",
    ]


@pytest.mark.parametrize(
    "row, raw, head, want",
    [
        ("off", pr(), HEAD, "route awaiting-merge"),
        ("", pr(), HEAD[:7], "route awaiting-merge"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED", reviewRequests=[BOB]), HEAD, "route awaiting-review needs bob"),
        ("on", pr(), HEAD, "route awaiting-review needs a teammate"),
        ("on", pr(reviews=[rev("bob", "APPROVED", OLD)]), HEAD, "route awaiting-review needs a teammate"),
        ("on", pr(reviews=[rev("bob", "APPROVED")]), HEAD, "route awaiting-merge"),
        ("on", pr(reviews=[rev("bob", "CHANGES_REQUESTED")]), HEAD, "route awaiting-review needs bob"),
        ("on", pr(reviews=[rev("bob", "CHANGES_REQUESTED", OLD)]), HEAD, "route awaiting-review needs bob"),
        ("off", pr(reviewDecision="CHANGES_REQUESTED"), HEAD, "route awaiting-review needs a teammate"),
        ("off", pr(headRefOid=OLD, reviewDecision="REVIEW_REQUIRED"), HEAD, "route moved head ccccccc"),
        ("off", {"state": "OPEN"}, HEAD, "route awaiting-merge (unreadable: bad PR data)"),
        ("yes", pr(), HEAD, "route awaiting-merge (unreadable: bad Require teammate approval row)"),
        ("off", None, HEAD, "route awaiting-merge (unreadable: PR not in the file)"),
    ],
)
def test_route(setup, capsys, row, raw, head, want):
    argv = setup(row, {} if raw is None else {"5": raw})  # None: the PR is not in the file
    assert cos_review_check.main([*argv, "--route", "5", "--head", head]) == 0
    assert capsys.readouterr().out.splitlines() == [want]


@pytest.mark.parametrize("extra", [["--route", "5"], ["--head", HEAD], ["--route", "x", "--head", HEAD], ["--route", "5", "--head", "zz"]])
def test_bad_route_arguments_exit_2(setup, capsys, extra):
    with pytest.raises(SystemExit) as e:
        cos_review_check.main([*setup("off", {}), *extra])
    assert e.value.code == 2 and capsys.readouterr().out.startswith("cos_review_check:")
