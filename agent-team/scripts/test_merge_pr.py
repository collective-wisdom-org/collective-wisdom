import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "merge_pr", Path(__file__).with_name("merge_pr.py")
)
merge_pr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge_pr)

HEAD = "a" * 40
ASBUILT = "docs/superpowers/as-built/x.md"
SPECMD = "docs/superpowers/specs/x-design.md"
INDEX = "docs/superpowers/index/x.md"


def review(title, verdict="PASS", at="2026-11-02T10:00:00Z", who="me"):
    return {
        "author": {"login": who},
        "body": f"{title}\n\nbody\n\n**Verdict:** {verdict}\n\n",
        "createdAt": at,
    }


def green():
    return {
        "state": "OPEN", "isDraft": False, "baseRefName": "main",
        "headRefOid": HEAD, "headRefName": "feat/x", "approved": HEAD[:7], "isCrossRepository": False,
        "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
        "statusCheckRollup": [
            {"__typename": "CheckRun", "name": "build", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"__typename": "StatusContext", "context": "ext", "state": "SUCCESS"},
        ],
        "login": "me",
        "comments": [review("## Code review (pass 2)"), review("## Security review (pass 1)")],
        "commits": [{"oid": HEAD, "committedDate": "2026-11-02T09:00:00Z"}],
        "files": [
            {"path": ASBUILT, "changeType": "ADDED"},
            {"path": SPECMD, "changeType": "ADDED"},
            {"path": INDEX, "changeType": "ADDED"},
        ],
        "docs": {SPECMD: "**Status:** Shipped\n", INDEX: "| [x](../as-built/x.md) |\n"},
        "mergeCommit": None, "root": "/root", "root_branch": "main", "root_dirty": False, "root_ahead": 0,
    }


def reviews(**kw):
    return lambda f: f.update(comments=[review("## Code review"), review("## Security review", **kw)])


@pytest.mark.parametrize(
    "change, cause",
    [
        (lambda f: None, None),
        (lambda f: f.update(approved="bbbbbbb"), "is not approved head"),
        (lambda f: f.update(state="CLOSED"), "closed"),
        (lambda f: f.update(mergeStateStatus="UNKNOWN"), "not mergeable"),
        (lambda f: f["statusCheckRollup"][0].update(conclusion="FAILURE"), "check build failed"),
        (lambda f: f["statusCheckRollup"][0].update(status="IN_PROGRESS", conclusion=None), "check build not finished"),
        (lambda f: f["statusCheckRollup"][1].update(state="PENDING"), "check ext"),
        (lambda f: f.update(comments=[review("## Code review")]), "no Security review"),
        (reviews(verdict="FAIL"), "Security review does not end in"),
        (reviews(at="2026-11-02T08:00:00Z"), "Security review is older than head"),
        (reviews(who="other"), "no Security review"),
        (lambda f: [c.update(body=c["body"].replace("**Verdict:**", "Verdict:")) for c in f["comments"]], None),
        (lambda f: f.update(isCrossRepository=True), "from a fork"),
        (lambda f: f.update(commits=[{"oid": HEAD, "committedDate": "2026-11-02T10:30:00Z"}, {"oid": "c" * 40, "committedDate": "2026-11-02T08:00:00Z"}]), "older than head"),
        (lambda f: f.update(commits=[{"oid": "c" * 40, "committedDate": "2026-11-02T08:00:00Z"}]), "head commit not in"),
        (lambda f: f.update(root_ahead=1), "local commits"),
        (lambda f: f.update(root_ahead=None), "no upstream"),
        (lambda f: f["files"].pop(0), "no added docs/superpowers/as-built"),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Draft\n"}), "Shipped"),
        (lambda f: (f["files"].pop(2), f["docs"].pop(INDEX)), "no docs/superpowers/index"),
        (lambda f: f["docs"].update({INDEX: "no row"}), "no index entry"),
        (lambda f: f.update(root_branch="feat/y"), "root checkout is on feat/y"),
        (lambda f: f.update(state="MERGED", approved="bbbbbbb"), None),
    ],
)
def test_gate(change, cause):
    f = green()
    change(f)
    reason = merge_pr.gate(f)
    if cause is None:
        assert reason is None
    else:
        assert cause in reason


def fake(f):
    """A runner that serves reads from facts f and records every call."""
    calls = []

    def runner(cmd):
        calls.append(cmd)
        text = " ".join(cmd)
        if "pr view" in text:
            return json.dumps({k: v for k, v in f.items() if k not in ("docs", "login", "approved", "root", "root_branch", "root_dirty", "root_ahead")})
        if "api user" in text:
            return f["login"]
        if "/contents/" in text:
            return f["docs"][next(p for p in f["docs"] if p in text)]
        if "worktree list" in text:
            return f"worktree {f['root']}\nbranch refs/heads/{f['root_branch']}\n\nworktree /w\n"
        if "status --porcelain" in text:
            return " M a.py" if f["root_dirty"] else ""
        if "rev-list" in text:
            return str(f["root_ahead"])
        if "git/ref/heads" in text:
            return f["headRefOid"] + "\n"
        if "-X PUT" in text:
            return json.dumps({"sha": "m" * 40})
        return ""

    return runner, calls


def writes(calls):
    return [c for c in calls if "PUT" in c or "DELETE" in c or "pull" in c]


@pytest.mark.parametrize(
    "change, code, wrote",
    [
        (lambda f: f.update(approved="bbbbbbb"), 1, 0),
        (lambda f: f["statusCheckRollup"][0].update(conclusion="FAILURE"), 1, 0),
        (lambda f: f.update(state="MERGED", mergeCommit={"oid": "m" * 40}), 0, 2),
        (lambda f: None, 0, 3),
    ],
)
def test_main_writes(change, code, wrote, capsys):
    f = green()
    change(f)
    runner, calls = fake(copy.deepcopy(f))
    assert merge_pr.main(["7", f["approved"]], runner) == code
    out = capsys.readouterr().out.splitlines()[-1]
    assert out.startswith("merge-pr: ")
    assert len(writes(calls)) == wrote
    assert any("PUT" in c for c in calls) == (f["state"] == "OPEN" and code == 0)


@pytest.mark.parametrize(
    "tip, cross, deleted",
    [("b" * 40, False, False), (HEAD, True, False), (HEAD, False, True), (None, False, False)],
)
def test_cleanup_deletes_only_our_unmoved_branch(tip, cross, deleted):
    calls = []

    def runner(cmd):
        calls.append(cmd)
        if "git/ref/heads" in " ".join(cmd):
            if tip is None:  # branch already gone: a rerun must still pull and exit clean
                raise merge_pr.CmdError("gh: Not Found (HTTP 404)")
            return tip
        return ""

    f = {"isCrossRepository": cross, "headRefName": "feat/x", "headRefOid": HEAD, "root": "/root", "root_branch": "main"}
    merge_pr.cleanup(f, runner)
    assert any("DELETE" in c for c in calls) == deleted
    assert any("pull" in c for c in calls)


OLD = "c" * 40


def moved(f, note="Head moved to {h} by merging main; PR diff unchanged since {o}. Reviews from {o} stand.", who="me", head=HEAD):
    """Head committed after the reviews, plus a reviews-stand note."""
    f["commits"] = [{"oid": HEAD, "committedDate": "2026-11-02T10:30:00Z"}, {"oid": OLD, "committedDate": "2026-11-02T08:00:00Z"}]
    f["comments"].append({"author": {"login": who}, "body": note.format(h=head, o=OLD), "createdAt": "2026-11-02T10:40:00Z"})


@pytest.mark.parametrize(
    "change, delta, cause",
    [
        (moved, ("same", []), None),
        (lambda f: moved(f, who="other"), ("same", []), "no reviews-stand note"),
        (lambda f: moved(f, head="d" * 40), ("same", []), "no reviews-stand note"),
        (lambda f: (moved(f), f["commits"].append({"oid": "e" * 40, "committedDate": "2026-11-02T09:30:00Z"})), ("same", []), "not the head the review was posted on"),
        (lambda f: moved(f), ("changed", ["a.py"]), "diff changed since ccccccc: 'a.py'"),
        (lambda f: moved(f), "boom", "cannot compare diff: boom"),
    ],
)
def test_review_older_than_head(change, delta, cause):
    f = green()
    change(f)

    def fake_delta(f, reviewed):
        assert reviewed == OLD
        if delta == "boom":
            raise merge_pr.CmdError("boom")
        return delta

    reason = merge_pr.gate(f, fake_delta)
    if cause is None:
        assert reason is None
    else:
        assert "older than head commit" in reason and cause in reason
