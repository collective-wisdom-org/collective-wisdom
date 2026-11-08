import copy
import importlib.util
import json
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
        "login": "me", "owner": "me", "repoKey": "github.com/example/app",
        "author": {"login": "me"}, "reviews": [], "reviewDecision": "", "reviewRequests": [], "teammate": None,
        "comments": [review("## Code review (pass 2)"), review("## Security review (pass 1)")],
        "commits": [{"oid": HEAD, "committedDate": "2026-11-02T09:00:00Z"}],
        "pr": "7",
        "body": "## Summary\n\nx\n\n## Release note\n\nA note.\n\n## Proof\n\nNot proven: nothing\n\n## Test plan\n\ny\n",
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
        (lambda f: f.update(owner="ME"), None),
        (lambda f: f.update(login="agent"), "gh is signed in as agent, not me, the login user.md maps to github.com/example/app"),
        (lambda f: f.update(login="agent", state="MERGED"), "the login user.md maps to"),
        (lambda f: f.update(owner=None), "user.md has no GitHub login for github.com/example/app"),
        (lambda f: f.update(state="CLOSED"), "closed"),
        (lambda f: f.update(statusCheckRollup=[]), "no checks"),
        (lambda f: f.update(statusCheckRollup=[], noCi=True), None),
        (lambda f: (f.update(noCi=True), f["statusCheckRollup"][0].update(conclusion="FAILURE")), "check build failed"),
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
        (lambda f: f["docs"].update({SPECMD: "**Status:** Draft\n"}), "Shipped"),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Shipped\n"}), 'no spec says "**Shipped:** in PR #7, as specified"'),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Shipped\n**Shipped:** in PR #70, as specified\n"}), "no spec says"),
        (lambda f: f["docs"].update({SPECMD: "**Status:** Shipped\n**Shipped:** in PR #7, with differences\n"}), "no spec says"),
        (lambda f: (f["docs"].update({SPECMD: "**Status:** Shipped\n"}), f["files"].append({"path": ASBUILT, "changeType": "ADDED"})), None),
        (lambda f: f.update(body="## Summary\n\nx\n"), 'no "## Release note" section'),
        (lambda f: f.update(body="## Release note\n\n## Test plan\n\ny\n"), 'no "## Release note" section'),
        (lambda f: f.update(body="## Release note\r\n\r\nA note.\r\n\r\n## Proof\r\n\r\nNot proven: nothing\r\n"), None),
        (lambda f: f.update(body="## Release note\n\nA note.\n"), 'no "## Proof" section'),
        (lambda f: f.update(body="## Release note\n\nA note.\n\n## Proof\n\n## Test plan\n\ny\n"), 'no "## Proof" section'),
        (lambda f: f.update(body="## Release note\n\nA note.\n\n## Proof\n\nran it\n"), 'has no "Not proven" line'),
        (lambda f: f.update(body="## Proof\n\nNot proven: nothing\n", files=f["files"] + [{"path": NOTEMD, "changeType": "ADDED"}]), 'no "## Release note" section'),
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


@pytest.mark.parametrize(
    "row, base, root_branch, cause",
    [
        ("| Merge target branch | `dev` |\n", "dev", "dev", None),
        ("| Merge target branch | `dev` |\n", "main", "dev", "base is main, not dev"),
        ("| Merge target branch | `dev` |\n", "dev", "main", "root checkout is on main, not dev"),
        ("", "main", "main", None),
        ("", "dev", "main", "base is dev, not main"),
        ("", "main", "dev", "root checkout is on dev, not main"),
        ("| Merge target branch | `-x` |\n", "main", "main", "'Merge target branch' row has no usable branch name"),
    ],
)
def test_gate_uses_the_merge_target_branch(tmp_path, monkeypatch, row, base, root_branch, cause):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n" + row)
    monkeypatch.setenv("PROJECT_MD", str(md))
    f = {**green(), "baseRefName": base, "root_branch": root_branch}
    reason = merge_pr.gate(f)
    assert reason is None if cause is None else cause in reason


BOT_THREAD = {"path": "a.py", "line": 3, "url": "https://github.com/o/r/pull/7#discussion_r1", "id": "PRRT_1"}


@pytest.mark.parametrize(
    "facts, cause",
    [
        ({}, "no Code review"),  # no Review mode row: the agent reviews are still required
        ({"reviewMode": "agents", "ciBot": "bot", "ciThreads": []}, "no Code review"),
        ({"reviewMode": "ci", "ciBot": "bot", "ciThreads": []}, None),  # no review comments needed
        ({"reviewMode": "ci", "ciBot": "bot", "ciThreads": [BOT_THREAD]}, "unresolved CI review thread by bot: a.py:3 https://github.com/o/r/pull/7#discussion_r1"),
        ({"reviewMode": "ci", "ciBot": None, "ciThreads": []}, "Review mode is ci but has no CI review bot login"),
        ({"reviewMode": "ci", "ciBot": "bot", "ciThreads": [], "statusCheckRollup": []}, "no checks"),  # the other gates stay
        ({"reviewMode": "ci", "ciBot": "bot"}, "CI review threads not read"),  # a missing read never passes
    ],
)
def test_gate_review_mode(facts, cause):
    f = green()
    f["comments"] = []
    f.update(facts)
    reason = merge_pr.gate(f)
    assert (reason is None) if cause is None else (cause in reason)


@pytest.mark.parametrize(
    "rows, threads, code, want",
    [
        ("", [], 1, "no Code review"),
        ("| Review mode | `ci` |\n| CI review bot login | `Bot[bot]` |\n", [], 0, "merged #7"),
        ("| Review mode | `ci` |\n| CI review bot login | `Bot[bot]` |\n", [{"id": "PRRT_1", "isResolved": False, "path": "a.py", "line": 3,
          "head": {"nodes": [{"author": {"login": "bot"}, "url": BOT_THREAD["url"]}]}}], 1, "unresolved CI review thread by bot: a.py:3"),
        ("| Review mode | `ci` |\n", [], 1, "has no CI review bot login"),
        ("| Review mode | `cii` |\n", [], 2, "'Review mode' row must be one of"),
    ],
)
def test_main_review_mode(tmp_path, monkeypatch, capsys, rows, threads, code, want):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n| Repo | `other/repo` |\n" + rows)
    monkeypatch.setenv("PROJECT_MD", str(md))
    f = green()
    f["comments"] = []
    runner, calls = fake(copy.deepcopy(f))
    gql = json.dumps({"data": {"repository": {"pullRequest": {"reviewThreads": {"pageInfo": {"hasNextPage": False}, "nodes": threads}}}}})
    monkeypatch.setattr(merge_pr, "publish", lambda *a: None)
    graphql = []

    def run(cmd, input=None):
        if "graphql" in cmd:
            graphql.append(cmd)
            return gql
        return runner(cmd)

    assert merge_pr.main(["7", f["approved"]], run) == code
    # The gate reads threads from gh's own repo (the checkout's remote), never the project.md Repo row.
    assert all("owner=:owner" in c and "name=:repo" in c for c in graphql)
    assert bool(graphql) == ("`ci`" in rows and "bot login" in rows)
    assert want in capsys.readouterr().out
    assert any("PUT" in c for c in calls) == (code == 0)


def fake(f):
    """A runner that serves reads from facts f and records every call."""
    calls = []

    def runner(cmd):
        calls.append(cmd)
        text = " ".join(cmd)
        if "pr view" in text:
            return json.dumps({k: v for k, v in f.items() if k not in ("docs", "login", "owner", "repoKey", "approved", "root", "root_branch", "root_dirty", "root_ahead")})
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
        (lambda f: f.update(login="agent"), 1, 0),
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


def test_main_stops_with_a_merge_line_on_an_invalid_target_row(tmp_path, monkeypatch, capsys):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n| Merge target branch | `-x` |\n")
    monkeypatch.setenv("PROJECT_MD", str(md))
    f = green()
    runner, calls = fake(copy.deepcopy(f))
    assert merge_pr.main(["7", f["approved"]], runner) == 1
    assert capsys.readouterr().out.splitlines()[-1].startswith("merge-pr: stop #7: project.md: 'Merge target branch' row has no usable branch name")
    assert not writes(calls)


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


@pytest.mark.parametrize(
    "row, root_branch, pulled",
    [
        ("| Merge target branch | `dev` |\n", "dev", True),
        ("| Merge target branch | `dev` |\n", "main", False),
        ("", "main", True),
        ("", "dev", False),
    ],
)
def test_cleanup_fast_forwards_only_a_root_on_the_merge_target_branch(tmp_path, monkeypatch, row, root_branch, pulled):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n" + row)
    monkeypatch.setenv("PROJECT_MD", str(md))
    calls = []

    def runner(cmd):
        calls.append(cmd)
        return ""

    f = {"isCrossRepository": True, "headRefName": "feat/x", "headRefOid": HEAD, "root": "/root", "root_branch": root_branch}
    if pulled:
        merge_pr.cleanup(f, runner)
    else:
        with pytest.raises(merge_pr.CmdError, match="fast-forward root"):
            merge_pr.cleanup(f, runner)
    assert [c for c in calls if "pull" in c] == ([["git", "-C", "/root", "pull", "--ff-only"]] if pulled else [])


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


RES_NOTE = "Head moved to {h} by resolving conflicts with main; reviews from {o} stand."
STALE = "2026-11-02T08:00:00Z"


def resolved(f, note=RES_NOTE, who="me", head=HEAD, setting="off", parents=(OLD, "d" * 40), extra=False, approved=OLD, new=None, old_date=STALE):
    """Head HEAD is a merge commit on the approved head OLD; reviews were posted on OLD."""
    f["approved"] = approved[:7]
    f["conflictReview"], f["headParents"], f["headNew"] = setting, list(parents), [HEAD] if new is None else new
    f["commits"] = [{"oid": OLD, "committedDate": old_date}, {"oid": HEAD, "committedDate": "2026-11-02T10:30:00Z"}]
    if extra:
        f["commits"].insert(1, {"oid": "e" * 40, "committedDate": "2026-11-02T09:00:00Z"})
    f["comments"].append({"author": {"login": who}, "body": note.format(h=head, o=OLD), "createdAt": "2026-11-02T10:40:00Z"})


@pytest.mark.parametrize(
    "change, cause",
    [
        (resolved, None),
        (lambda f: resolved(f, setting="on"), "is not approved head"),
        (lambda f: resolved(f, setting=None), "is not approved head"),
        (lambda f: resolved(f, who="other"), "is not approved head"),
        (lambda f: resolved(f, head="d" * 40), "is not approved head"),
        (lambda f: resolved(f, extra=True), "is not approved head"),
        (lambda f: resolved(f, new=[HEAD, "f" * 40]), "is not approved head"),  # second parent brings commits not on main
        (lambda f: resolved(f, old_date="2026-11-03T00:00:00Z"), "is older than head commit"),  # review predates the approved head
        (lambda f: resolved(f, parents=(OLD,)), "is not approved head"),
        (lambda f: resolved(f, parents=("d" * 40, OLD)), "is not approved head"),
        (lambda f: resolved(f, note="Head moved to {h} by merging main; PR diff unchanged since {o}."), "is not approved head"),
        (lambda f: resolved(f, approved="b" * 40), "is not approved head"),
        (lambda f: resolved(f, approved=HEAD), None),  # the user approved the resolved head itself after MERGE READY
    ],
)
def test_resolved_head_is_covered_by_the_approval_of_its_first_parent(change, cause):
    f = green()
    change(f)
    reason = merge_pr.gate(f, lambda f, r: ("changed", ["a.py"]))  # reviews must stand without a diff comparison
    assert reason is None if cause is None else cause in reason


TIP = "t" * 40
NOTE_TEXT = "# 2026-11-04 CW-2: file note\n\nbody\n"
PRS = [{"number": 5, "title": "feat: new", "body": "## Release note\n\nA note.\n", "mergedAt": "2026-11-04T10:00:00Z"}]


@pytest.fixture(autouse=True)
def no_git_times(monkeypatch):
    """Publish asks git when each note file merged; the tests don't read this repo's history."""
    monkeypatch.setattr(merge_pr.release_notes, "file_merge_times", lambda: {})


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
            blob = {"path": "RELEASE_NOTES.md", "type": "blob", "mode": "100644", "sha": merge_pr.blob_sha(want.encode()) if state == "same" else "0" * 40}
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
    assert "CW-2: file note" in content and "LEAK" not in content and "secret.md" not in content and "DRAFT" not in content


def test_failed_publish_keeps_the_merge_result(capsys):
    f = green()
    runner, _ = fake(f)  # its PR list answers nothing, so publish warns
    assert merge_pr.main(["7", f["approved"]], runner) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-2].startswith("merge-pr: warn ") and out[-1].startswith("merge-pr: merged #7")


@pytest.mark.parametrize("row, notes_on", [("", True), ("on", True), ("off", False), ("OFF", False), ("maybe", True)])
def test_release_notes_setting(tmp_path, monkeypatch, row, notes_on):
    """Only an `off` row drops the release note gate and the publish step."""
    md = tmp_path / "project.md"
    md.write_text(f"| Publish release notes | `{row}`. text |\n" if row else "")
    monkeypatch.setenv("PROJECT_MD", str(md))
    bare = dict(green(), body="## Proof\n\nNot proven: nothing\n", notesOn=merge_pr.project_config.release_notes_enabled())
    assert ("Release note" in merge_pr.gate(bare)) if notes_on else merge_pr.gate(bare) is None
    published = []
    monkeypatch.setattr(merge_pr, "publish", lambda *a: published.append(a))
    f = green()
    assert merge_pr.main(["7", f["approved"]], fake(f)[0]) == 0 and bool(published) == notes_on


def verdict(who, state, at, oid=HEAD, assoc="COLLABORATOR"):
    return {"author": {"login": who}, "state": state, "submittedAt": at, "commit": {"oid": oid}, "authorAssociation": assoc}


def with_reviews(*reviews, teammate="on"):
    return lambda f: f.update(teammate=teammate, reviews=list(reviews))


@pytest.mark.parametrize(
    "change, cause",
    [
        (with_reviews(), "no approving review by a user other than me on head aaaaaaa"),
        (with_reviews(teammate=None), None),
        (with_reviews(teammate="off"), None),
        (with_reviews(teammate="yes"), "Require teammate approval is yes; use on or off"),
        (with_reviews(verdict("bob", "APPROVED", "2026-11-02T10:00:00Z", assoc="NONE")), "no approving review by a user other than me on head aaaaaaa"),
        (with_reviews(verdict("bob", "CHANGES_REQUESTED", "2026-11-02T10:00:00Z", assoc="NONE"), verdict("amy", "APPROVED", "2026-11-02T10:00:00Z", assoc="MEMBER")), None),
        (with_reviews(verdict("ME", "APPROVED", "2026-11-02T10:00:00Z")), "; the author's own approval does not count"),
        (with_reviews(verdict("bob", "APPROVED", "2026-11-02T10:00:00Z", OLD)), "approved ccccccc, head moved"),
        (
            with_reviews(verdict("bob", "APPROVED", "2026-11-02T10:00:00Z"), verdict("bob", "CHANGES_REQUESTED", "2026-11-02T11:00:00Z")),
            "changes requested by bob on PR #7",
        ),
        (
            with_reviews(verdict("bob", "CHANGES_REQUESTED", "2026-11-02T10:00:00Z"), verdict("bob", "APPROVED", "2026-11-02T11:00:00Z")),
            None,
        ),
        (
            with_reviews(verdict("bob", "APPROVED", "2026-11-02T10:00:00Z"), verdict("amy", "CHANGES_REQUESTED", "2026-11-02T11:00:00Z")),
            "changes requested by amy",
        ),
        (with_reviews(verdict("bob", "APPROVED", "2026-11-02T10:00:00Z"), verdict("bob", "COMMENTED", "2026-11-02T11:00:00Z", OLD)), None),
        (with_reviews(verdict("bob", "APPROVED", "2026-11-02T10:00:00Z", OLD), verdict("bob", "APPROVED", "2026-11-02T11:00:00Z")), None),
        (with_reviews(verdict("bob", "DISMISSED", "2026-11-02T10:00:00Z")), "latest reviews are bob DISMISSED"),
        (with_reviews(verdict("bob", "APPROVED", "2026-11-02T10:00:00Z")), None),
        (with_reviews(verdict("Bob", "APPROVED", "2026-11-02T10:00:00Z")), None),
    ],
)
def test_teammate_approval(change, cause):
    f = green()
    change(f)
    reason = merge_pr.gate(f)
    if cause is None:
        assert reason is None
    else:
        assert cause in reason


USER = {"__typename": "User", "login": "bob"}
TEAM = {"__typename": "Team", "name": "Core", "slug": "acme/core"}


@pytest.mark.parametrize(
    "decision, requests, expect",
    [
        ("REVIEW_REQUIRED", [USER, TEAM], "required reviews missing: waiting on bob, @acme/core"),
        ("REVIEW_REQUIRED", [], "required reviews missing: waiting on required reviewers"),
        ("APPROVED", [USER], None),
        ("", [USER], None),
    ],
)
def test_required_reviews(decision, requests, expect):
    f = green()
    f.update(reviewDecision=decision, reviewRequests=requests, mergeStateStatus="BLOCKED" if expect else "CLEAN")
    assert merge_pr.gate(f) == expect


@pytest.mark.parametrize(
    "login, owners, state, decision, expect",
    [
        ("noah", ["david", "noah"], "BLOCKED", "REVIEW_REQUIRED", None),
        ("noah", ["david", "noah"], "BLOCKED", "", "state BLOCKED"),
        ("me", [], "BLOCKED", "REVIEW_REQUIRED", "required reviews missing"),
        ("eve", ["david", "noah"], "BLOCKED", "REVIEW_REQUIRED", "not me, the login user.md maps to"),
    ],
)
def test_codeowner_bypasses_missing_review_only(login, owners, state, decision, expect):
    f = green()
    f.update(login=login, codeowners=owners, mergeStateStatus=state, reviewDecision=decision)
    f["comments"] = [review("## Code review", who=login), review("## Security review", who=login)]
    reason = merge_pr.gate(f)
    assert reason is None if expect is None else expect in reason


@pytest.mark.parametrize(
    "text, expect",
    [
        ("* @David @noah\n", ["david", "noah"]),
        ("# c\n*  @a  @org/team # x\n/docs @b\n", ["a"]),
        (None, []),
    ],
)
def test_codeowners(text, expect):
    def run(cmd, input=None):
        if text is None:
            raise merge_pr.CmdError("missing")
        return text

    assert merge_pr.codeowners(run) == expect


@pytest.mark.parametrize("row, ref", [("", "main"), ("| Merge target branch | `dev` |\n", "dev")])
def test_codeowners_are_read_from_the_merge_target_branch(tmp_path, monkeypatch, row, ref):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n" + row)
    monkeypatch.setenv("PROJECT_MD", str(md))
    seen = []

    def run(cmd, input=None):
        seen.append(cmd[-1])
        return "* @a\n"

    merge_pr.codeowners(run)
    assert seen == [f"refs/remotes/origin/{ref}:.github/CODEOWNERS"]


@pytest.mark.parametrize(
    "cell, cause",
    [
        ("`on`", "no approving review by a user other than me"),
        ("on", "no approving review by a user other than me"),
        ("ON", "no approving review by a user other than me"),
        ("yes", "Require teammate approval is yes; use on or off"),
        ("`off`", None),
        ("off", None),
        ("", None),
    ],
)
def test_teammate_row_as_written(tmp_path, monkeypatch, cell, cause):
    md = tmp_path / "project.md"
    md.write_text(f"| Key | Value |\n|---|---|\n| Require teammate approval | {cell} |\n")
    monkeypatch.setenv("PROJECT_MD", str(md))
    runner, _ = fake(green())
    f = merge_pr.read_facts("7", HEAD[:7], runner)
    reason = merge_pr.gate(f)
    assert reason is None if cause is None else cause in reason
