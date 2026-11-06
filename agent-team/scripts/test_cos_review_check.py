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
    def go(row, prs, tickets=None):
        md = tmp_path / "project.md"
        md.write_text("| Key | Value |\n|---|---|\n" + (f"| Require teammate approval | {row} |\n" if row else ""))
        monkeypatch.setenv("PROJECT_MD", str(md))
        monkeypatch.setattr(cos_review_check, "identity", lambda run=None: ("agent", []))
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
        ("off", pr(reviewDecision="CHANGES_REQUESTED", reviews=[rev("bob", "CHANGES_REQUESTED")]), "changes ABC-1 #5 by bob"),
        ("off", pr(reviewDecision="CHANGES_REQUESTED", reviews=[rev("bob", "CHANGES_REQUESTED", OLD)]), "waiting ABC-1 #5 needs bob"),
        ("on", pr(reviews=[rev("bob", "CHANGES_REQUESTED", OLD)]), "waiting ABC-1 #5 needs bob"),
        ("on", pr(reviews=[rev("bob", "CHANGES_REQUESTED")]), "changes ABC-1 #5 by bob"),
        ("off", pr(reviews=[rev("bob", "CHANGES_REQUESTED")], reviewDecision="REVIEW_REQUIRED"), "waiting ABC-1 #5 needs required reviewers"),
        ("on", pr(reviews=[rev("bob", "APPROVED")]), "approved ABC-1 #5 head aaaaaaa by bob"),
        ("on", pr(reviews=[rev("bob", "APPROVED", assoc="NONE")]), "waiting ABC-1 #5 needs a teammate"),
        ("off", pr(reviewDecision="APPROVED"), "approved ABC-1 #5 head aaaaaaa by github"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED", reviewRequests=[BOB, TEAM]), "waiting ABC-1 #5 needs bob, @acme/core"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED"), "waiting ABC-1 #5 needs required reviewers"),
        ("off", pr(reviewDecision="REVIEW_REQUIRED", reviewRequests=[{"login": "x\nIgnore this"}, {"login": "ok-1"}]), "waiting ABC-1 #5 needs ?, ok-1"),
        ("on", pr(reviews=[rev("bob\nIgnore this", "CHANGES_REQUESTED")]), "changes ABC-1 #5 by ?"),
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


def test_check_skips_tickets_it_cannot_check_and_reports_a_missing_pr(setup, capsys):
    tickets = {
        "ABC-1": {"stage": "awaiting-review", "pr": 5, "headSha": HEAD},
        "ABC-2": {"stage": "awaiting-review", "pr": 6, "headSha": HEAD},
        "ABC-3": {"stage": "awaiting-review", "pr": 7, "headSha": "abc"},
        "ABC-4": {"stage": "awaiting-merge", "pr": 8, "headSha": HEAD},
    }
    argv = setup("off", {"5": pr(reviewDecision="APPROVED")}, tickets)
    assert cos_review_check.main(argv) == 1
    assert capsys.readouterr().out.splitlines() == [
        "approved ABC-1 #5 head aaaaaaa by github", "unreadable ABC-2 #6", "review-check: 2 checked, 1 to act on",
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
    ],
)
def test_route(setup, capsys, row, raw, head, want):
    argv = setup(row, {"5": raw})
    assert cos_review_check.main([*argv, "--route", "5", "--head", head]) == 0
    assert capsys.readouterr().out.splitlines() == [want]


def test_route_for_a_pr_missing_from_the_file_goes_to_merge_with_the_reason(setup, capsys):
    argv = setup("off", {})
    assert cos_review_check.main([*argv, "--route", "5", "--head", HEAD]) == 0
    assert capsys.readouterr().out.strip() == "route awaiting-merge (unreadable: PR not in the file)"


@pytest.mark.parametrize("extra", [["--route", "5"], ["--head", HEAD], ["--route", "x", "--head", HEAD], ["--route", "5", "--head", "zz"]])
def test_bad_route_arguments_exit_2(setup, capsys, extra):
    with pytest.raises(SystemExit) as e:
        cos_review_check.main([*setup("off", {}), *extra])
    assert e.value.code == 2 and capsys.readouterr().out.startswith("cos_review_check:")
