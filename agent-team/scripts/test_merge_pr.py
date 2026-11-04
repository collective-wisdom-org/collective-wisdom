import copy
import importlib.util
import json
import os
import subprocess
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
NOTEMD = "docs/superpowers/release-notes/x.md"
SHIPPED = "**Status:** Shipped\n**Shipped:** in PR #7, as specified\n"


def old_shape(f, note="\n# 2026-11-03 X-1: a title\n\nbody\n"):
    """As-built and release note as files, no body section."""
    f["body"] = ""
    f["docs"] = {SPECMD: "**Status:** Shipped\n", NOTEMD: note}
    f["files"] += [{"path": ASBUILT, "changeType": "ADDED"}, {"path": NOTEMD, "changeType": "ADDED"}]


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
        "pr": "7",
        "body": "## Summary\n\nx\n\n## Release note\n\nA note.\n\n## Test plan\n\ny\n",
        "files": [{"path": SPECMD, "changeType": "ADDED"}],
        "docs": {SPECMD: SHIPPED},
        "mergeCommit": None, "root": str(merge_pr.ROOT), "root_branch": "main", "root_dirty": False, "root_ahead": 0,
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
        (lambda f: f.update(login="cw-builder", agentLogins=["cw-chief", "cw-builder"]), "agent user cw-builder"),
        (lambda f: f.update(commits=[{"oid": HEAD, "committedDate": "2026-11-02T10:30:00Z"}, {"oid": "c" * 40, "committedDate": "2026-11-02T08:00:00Z"}]), "older than head"),
        (lambda f: f.update(commits=[{"oid": "c" * 40, "committedDate": "2026-11-02T08:00:00Z"}]), "head commit not in"),
        (lambda f: f.update(root_ahead=1), "local commits"),
        (lambda f: f.update(root_ahead=None), "no upstream"),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Draft\n"}), "Shipped"),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Shipped\n"}), 'no spec says "**Shipped:** in PR #7, as specified"'),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Shipped\n**Shipped:** in PR #70, as specified\n"}), "no spec says"),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Shipped\n**Shipped:** in PR #7, with differences\n"}), "no spec says"),
        (lambda f: (f["docs"].update({SPECMD: "**Status:** Shipped\n"}), f["files"].append({"path": ASBUILT, "changeType": "ADDED"})), None),
        (lambda f: f.update(body="## Summary\n\nx\n"), 'no "## Release note" section'),
        (lambda f: f.update(body="## Release note\n\n## Test plan\n\ny\n"), 'no "## Release note" section'),
        (lambda f: f.update(body="## Release note\r\n\r\nA note.\r\n"), None),
        (old_shape, None),
        (lambda f: old_shape(f, "# A title\n"), f"release note {NOTEMD} has no '# YYYY-MM-DD"),
        (lambda f: (old_shape(f), f["files"].pop()), 'no "## Release note" section'),
        (lambda f: (old_shape(f, "# A title\n"), f.update(body="## Release note\n\nx\n")), f"release note {NOTEMD} has no '# YYYY-MM-DD"),
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
        (lambda f: f.update(root="/elsewhere"), 1, 0),  # run from a worktree: read_facts flags it, gate refuses
        (lambda f: f.update(root="/elsewhere", state="MERGED", mergeCommit={"oid": "m" * 40}), 1, 0),
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


ROLES = {"code-reviewer": "cw-reviewer", "security-reviewer": "cw-sentinel", "builder": "cw-builder"}


def posted(code="cw-reviewer", security="cw-sentinel", note="cw-builder"):
    """Reviews older than the head, so a reviews-stand note from `note` has to cover them."""
    def change(f):
        moved(f, who=note)
        f["comments"][:0] = [
            review("## Code review", who=code, at="2026-11-02T09:30:00Z"),
            review("## Security review", who=security, at="2026-11-02T09:30:00Z"),
        ]
    return change


@pytest.mark.parametrize(
    "change, roles, code, cause",
    [
        (posted(), ROLES, 0, None),
        (posted(code="me"), ROLES, 1, "no Code review comment by cw-reviewer"),
        (posted(security="me"), ROLES, 1, "no Security review comment by cw-sentinel"),
        (posted(code="cw-sentinel"), ROLES, 1, "no Code review comment by cw-reviewer"),
        (posted(note="me"), ROLES, 1, "no reviews-stand note"),
        (posted(code="me", security="me", note="me"), {}, 0, None),
    ],
)
def test_main_trusts_the_role_login_once_set(monkeypatch, capsys, change, roles, code, cause):
    monkeypatch.setattr(merge_pr.project_config, "role_login", roles.get)
    monkeypatch.setattr(merge_pr, "gate", lambda f, g=merge_pr.gate: g(f, lambda f, reviewed: ("same", [])))
    f = green()
    change(f)
    runner, _ = fake(copy.deepcopy(f))
    assert merge_pr.main(["7", f["approved"]], runner) == code
    assert cause is None or cause in capsys.readouterr().out


def test_main_runs_without_a_gh_role(monkeypatch):
    """The merge stays on the owner's login even when the caller set a role."""
    monkeypatch.setenv("AGENT_GH_ROLE", "builder")
    f = green()
    runner, _ = fake(f)
    merge_pr.main(["7", f["approved"]], runner)
    assert "AGENT_GH_ROLE" not in os.environ


TIP = "t" * 40
NOTE_TEXT = "# 2026-11-04 CW-2: file note\n\nbody\n"
PRS = [{"number": 5, "title": "feat: new", "body": "## Release note\n\nA note.\n", "mergedAt": "2026-11-04T10:00:00Z"}]


def publisher(state):
    """A runner for publish: serves the PR list, the git reads and the API; records each write as (command, body)."""
    writes = []
    want = merge_pr.release_notes.render([("cw-2.md", NOTE_TEXT)], PRS) + "\n"

    def runner(cmd, input=None):
        text = " ".join(cmd)
        if "pr list" in text:
            if state == "prfail":
                raise merge_pr.CmdError("gh: not logged in")
            return json.dumps(PRS)
        if "ls-tree" in text:
            return "100644 blob " + "n" * 40 + "\tdocs/superpowers/release-notes/cw-2.md\0"
        if "cat-file" in text:
            return NOTE_TEXT
        if "git/ref/heads" in text:
            if state == "missing":
                raise merge_pr.CmdError("gh: Not Found (HTTP 404)")
            return TIP + "\n"
        if f"commits/{TIP}" in text:
            return "r" * 40
        if "git/trees/" in text:
            blob = {"path": "RELEASE_NOTES.md", "type": "blob", "sha": merge_pr.blob_sha(want.encode()) if state == "same" else "0" * 40}
            return json.dumps({"tree": [blob] + ([dict(blob, path="other.md")] if state == "other" else [])})
        if "-X" in cmd:
            writes.append((cmd[cmd.index("-X") + 1] + " " + cmd[-3].split("/git/")[1], json.loads(input)))
            if state == "422" and "PATCH" in text:
                raise merge_pr.CmdError("gh: Update is not a fast forward (HTTP 422)")
            return json.dumps({"sha": "s" * 40})
        return ""  # git merge-base

    return runner, writes


@pytest.mark.parametrize(
    "state, kinds, parents, warn",
    [
        ("missing", ["POST trees", "POST commits", "POST refs"], [], ""),
        ("changed", ["POST trees", "POST commits", "PATCH refs/heads/release-notes"], [TIP], ""),
        ("same", [], None, ""),
        ("other", [], None, "holds other files"),
        ("422", ["POST trees", "POST commits", "PATCH refs/heads/release-notes"], [TIP], "update rejected"),
        ("prfail", [], None, "cannot read merged PRs"),
    ],
)
def test_publish(capsys, state, kinds, parents, warn):
    runner, writes = publisher(state)
    merge_pr.publish("7", "m" * 40, runner)
    out = capsys.readouterr().out
    assert [w[0] for w in writes] == kinds
    assert (out.startswith("merge-pr: warn ") and warn in out) if warn else out == ""
    if parents is not None:
        assert writes[1][1]["parents"] == parents and writes[1][1]["message"] == "docs: release notes after #7"
        assert writes[0][1]["tree"][0]["content"].startswith("# Release notes\n") and "(#5)" in writes[0][1]["tree"][0]["content"]
        assert writes[-1][1].get("force", False) is False


def test_publish_reads_git_objects_only(tmp_path):
    """A symlinked note and an untracked draft in the working tree never reach the published text."""
    secret = tmp_path / "secret.md"
    secret.write_text("# 2026-11-04 LEAK: outside the repo\n")
    remote, repo = tmp_path / "remote.git", tmp_path / "repo"
    notes = repo / "docs" / "superpowers" / "release-notes"
    git = lambda *a, cwd=repo: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    git("init", "-q", "-b", "main", str(repo), cwd=tmp_path)
    notes.mkdir(parents=True)
    (notes / "cw-2.md").write_text(NOTE_TEXT)
    (notes / "link.md").symlink_to(secret)
    git("add", "-A")
    git("commit", "-qm", "notes")
    git("remote", "add", "origin", str(remote))
    git("push", "-q", "-u", "origin", "main")
    (notes / "draft.md").write_text("# 2026-11-04 DRAFT: untracked\n")
    sent = []

    def runner(cmd, input=None):
        if cmd[0] == "git":
            return git(*cmd[1:])
        if "pr list" in " ".join(cmd):
            return "[]"
        if "git/ref/heads" in " ".join(cmd):
            raise merge_pr.CmdError("HTTP 404")
        sent.append(input)
        return json.dumps({"sha": "s" * 40})

    merge_pr.publish("7", git("rev-parse", "HEAD").strip(), runner)
    content = json.loads(sent[0])["tree"][0]["content"]
    assert "CW-2: file note" in content and "LEAK" not in content and "DRAFT" not in content


def test_failed_publish_keeps_the_merge_result(capsys):
    f = green()
    runner, _ = fake(f)  # its PR list answers nothing, so publish warns
    assert merge_pr.main(["7", f["approved"]], runner) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-2].startswith("merge-pr: warn ") and out[-1].startswith("merge-pr: merged #7")
