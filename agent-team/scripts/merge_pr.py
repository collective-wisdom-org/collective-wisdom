#!/usr/bin/env python3
"""Squash-merge an approved PR, delete its branch (if it still points at the PR head and the PR is not from a fork) and fast-forward root main.

Usage:
    scripts/merge_pr.py <PR number> <approved head SHA>

Run it from the root checkout (`cd <root checkout> && python3 scripts/merge_pr.py ...`): it finds the repo from the current directory. The approved head is at least 7 hex characters. Every gate in
the checks list of the merge-pr skill must pass first; if one fails nothing changes. The merge goes through the REST API with sha=<head>,
so no local branch is switched and GitHub refuses it if the head moved.

Exit 0: merged, or already merged (cleanup is repeated). Last line:
  merge-pr: merged #N as <SHA>; head <SHA> matches approved <SHA>
  merge-pr: #N already merged as <SHA>; nothing to do; head <SHA> matches|differs from approved <SHA>
Exit 1: a gate failed, nothing changed. Last line: merge-pr: stop #N: <reason>
Exit 2: bad arguments, a gh or git call failed. Last line: merge-pr: cannot <what>
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import project_config  # noqa: E402
import release_notes  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "pr_diff_delta", Path(__file__).with_name("pr_diff_delta.py")
)
pr_diff_delta = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr_diff_delta)
CmdError = pr_diff_delta.CmdError

ROOT = root()
GH = str(Path(__file__).absolute().parent / "gh.sh")
FIELDS = (
    "state,isDraft,mergeable,mergeStateStatus,headRefOid,headRefName,baseRefName,"
    "statusCheckRollup,comments,commits,files,mergeCommit,isCrossRepository,body,reviews"
)
AS_BUILT = r"docs/superpowers/as-built/[^/]+\.md"
SPECS = r"docs/superpowers/specs/[^/]+\.md"
RELEASE = r"docs/superpowers/release-notes/[^/]+\.md"
OK_CONCLUSIONS = ("SUCCESS", "SKIPPED", "NEUTRAL")
NOTE = re.compile(r"Head moved to ([0-9a-f]{40})\b.*?unchanged since ([0-9a-f]{40})", re.I | re.S)


def run(cmd):
    """Run a command in the repo and return its stdout; raise CmdError on failure."""
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        raise CmdError((p.stderr or p.stdout).strip() or f"exit {p.returncode}")
    return p.stdout


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def read_protection(run):
    """Approving reviews branch protection on main requires (0 when it requires none), or None when main has no protection."""
    try:
        out = run([GH, "api", "repos/{owner}/{repo}/branches/main/protection"])
    except CmdError as e:
        if re.search(r"HTTP 404", str(e)):
            return None
        raise
    return json.loads(out).get("required_pull_request_reviews", {}).get("required_approving_review_count", 0)


def owner_approval(f):
    """Return None when the owner's latest verdict review is an approval on the current head, else why not."""
    mine = [
        r for r in f["reviews"]
        if r["author"]["login"] == f["owner"] and r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")
    ]
    short = f["headRefOid"][:7]
    if not mine:
        return f"no approving review by {f['owner']} on head {short}"
    last = max(mine, key=lambda r: ts(r["submittedAt"]))
    if last["state"] != "APPROVED":
        return f"no approving review by {f['owner']} on head {short}; their latest review is {last['state']}"
    if last["commit"]["oid"] != f["headRefOid"]:
        return f"no approving review by {f['owner']} on head {short}; approved {last['commit']['oid'][:7]}, head moved"
    return None


def read_facts(pr, approved, run):
    """Everything the gate needs, from gh and git reads only."""
    f = json.loads(run([GH, "pr", "view", pr, "--json", FIELDS]))
    f["approved"] = approved
    f["pr"] = pr
    f["login"] = run([GH, "api", "user", "-q", ".login"]).strip()
    roles = {"code": "code-reviewer", "security": "security-reviewer", "builder": "builder"}
    f["authors"] = {k: project_config.role_login(r) or f["login"] for k, r in roles.items()}
    f["owner"] = project_config.value("Owner login") or f["login"]
    f["protection"] = read_protection(run)
    f["agentLogins"] = sorted({l for r in project_config.ROLE_ROWS if (l := project_config.role_login(r))})
    f["docs"] = {}
    if f["state"] == "OPEN":
        want = [
            x["path"]
            for x in f["files"]
            if (re.fullmatch(SPECS, x["path"]) and x["changeType"] != "DELETED")
            or (re.fullmatch(RELEASE, x["path"]) and x["changeType"] == "ADDED")
        ]
        for path in want:
            url = f"repos/{{owner}}/{{repo}}/contents/{quote(path)}?ref={f['headRefOid']}"
            f["docs"][path] = run([GH, "api", url, "-H", "Accept: application/vnd.github.raw+json"])
    wt = run(["git", "-C", str(ROOT), "worktree", "list", "--porcelain"])
    block = wt.strip().split("\n\n")[0].splitlines()
    f["root"] = block[0].removeprefix("worktree ")
    # Reviewer logins come from project.md in the current directory, so a feature worktree would let its PR pick them.
    f["not_root_checkout"] = ROOT.resolve() != Path(f["root"]).resolve()
    f["root_branch"] = next(
        (l.removeprefix("branch refs/heads/") for l in block if l.startswith("branch ")),
        None,
    )
    f["root_dirty"] = bool(
        run(["git", "-C", f["root"], "status", "--porcelain", "--untracked-files=no"]).strip()
    )
    try:
        f["root_ahead"] = int(run(["git", "-C", f["root"], "rev-list", "--count", "@{u}..HEAD"]))
    except (CmdError, ValueError):
        f["root_ahead"] = None
    return f


def real_delta(f, reviewed):
    """Fetch main and the PR head into the root checkout, then compare the PR's diff at both heads."""
    pr_diff_delta.fetch(f["pr"], pr_diff_delta.run)
    return pr_diff_delta.delta(reviewed, f["headRefOid"], pr_diff_delta.run)


def author(f, kind):
    """Login whose comments count for kind (code, security, builder): the role login, else the running one."""
    return f.get("authors", {}).get(kind, f["login"])


def stands(f, c, delta):
    """Return None when a reviews-stand note covers review c at the current head, else why not."""
    notes = [
        n
        for n in f["comments"]
        if n["author"]["login"] == author(f, "builder") and n["body"].startswith("Head moved to ")
    ]
    m = NOTE.match(max(notes, key=lambda n: ts(n["createdAt"]))["body"]) if notes else None
    if not m or not f["headRefOid"].startswith(m[1].lower()):
        return "no reviews-stand note for this head"
    reviewed = next((x for x in f["commits"] if x["oid"].startswith(m[2].lower())), None)
    if reviewed is None or ts(c["createdAt"]) <= ts(reviewed["committedDate"]):
        return "no reviews-stand note for this head"
    between = [
        x for x in f["commits"]
        if ts(reviewed["committedDate"]) < ts(x["committedDate"]) < ts(c["createdAt"])
    ]
    if between:
        return f"reviewed commit {reviewed['oid'][:7]} is not the head the review was posted on"
    try:
        kind, files = delta(f, reviewed["oid"])
    except CmdError as e:
        return f"cannot compare diff: {e}"
    if kind != "same":
        return f"diff changed since {reviewed['oid'][:7]}: {', '.join(repr(x) for x in files[:10])}"
    return None


def review(f, title, delta=real_delta):
    """Return (latest comment or None, problem or None) for a review heading."""
    who = author(f, "security" if title.startswith("## Security") else "code")
    mine = [
        c
        for c in f["comments"]
        if c["author"]["login"] == who and c["body"].startswith(title)
    ]
    if not mine:
        return None, f"no {title[3:]} comment by {who}"
    c = max(mine, key=lambda c: ts(c["createdAt"]))
    last = [l for l in c["body"].splitlines() if l.strip()][-1].strip()
    if not re.fullmatch(r"\**Verdict:\** PASS\**", last):
        return c, f"latest {title[3:]} does not end in Verdict: PASS"
    head = next((x for x in f["commits"] if x["oid"] == f["headRefOid"]), None)
    if head is None:
        return c, "head commit not in the PR's commit list"
    if ts(c["createdAt"]) <= ts(head["committedDate"]):
        why = stands(f, c, delta)
        if why:
            return c, f"latest {title[3:]} is older than head commit {f['headRefOid'][:7]}; {why}"
    return c, None


def gate(f, delta=real_delta):
    """Return the reason to stop, or None when the PR may merge (or is merged)."""
    if f.get("not_root_checkout"):
        return f"run it from the root checkout: cd {f['root']} && python3 scripts/merge_pr.py ...; this directory's project.md is not the gate's"
    if f["state"] == "MERGED":
        return None
    if f["state"] == "CLOSED":
        return "PR is closed, not merged"
    if f["state"] != "OPEN":
        return f"PR state is {f['state']}"
    if f["login"] in f.get("agentLogins", ()):
        return f"gh is signed in as the agent user {f['login']}, not the owner; run gh auth switch -u <owner login>"
    if f["isDraft"]:
        return "PR is a draft"
    if f["isCrossRepository"]:
        return "PR is from a fork"
    if f["baseRefName"] != "main":
        return f"base is {f['baseRefName']}, not main"
    if not f["headRefOid"].startswith(f["approved"]):
        return f"head {f['headRefOid']} is not approved head {f['approved']}"
    if f["mergeable"] != "MERGEABLE" or f["mergeStateStatus"] != "CLEAN":
        return f"not mergeable: mergeable {f['mergeable']}, state {f['mergeStateStatus']}"
    if not f["statusCheckRollup"]:
        return "no checks"
    for c in f["statusCheckRollup"]:
        name = c.get("name") or c.get("context")
        if c["__typename"] == "StatusContext":
            done, result = c["state"] not in ("PENDING", "EXPECTED"), c["state"]
            ok = result == "SUCCESS"
        else:
            done, result = c["status"] == "COMPLETED", c["conclusion"] or c["status"]
            ok = done and result in OK_CONCLUSIONS
        if not ok:
            kind = "failed" if done and result else "not finished"
            return f"check {name} {kind} ({result})"
    if not f["protection"]:
        return "main has no branch protection requiring an approving review; set it up per docs/agents/github-auth.md § Merge gate"
    problem = owner_approval(f)
    if problem:
        return problem
    for title in ("## Code review", "## Security review"):
        problem = review(f, title, delta)[1]
        if problem:
            return problem
    paths = f["files"]
    specs = [p for p in f["docs"] if re.fullmatch(SPECS, p)]
    if not any(re.search(r"^\*\*Status:\*\*\s*Shipped\b", f["docs"][p], re.M) for p in specs):
        return "closeout missing: no spec in the PR has **Status:** Shipped"
    pr = re.escape(str(f["pr"]))
    as_specified = any(re.search(rf"^\*\*Shipped:\*\*\s*in PR #{pr}, as specified\s*$", f["docs"][p], re.M) for p in specs)
    if not as_specified and not any(x["changeType"] == "ADDED" and re.fullmatch(AS_BUILT, x["path"]) for x in paths):
        return f'closeout missing: no spec says "**Shipped:** in PR #{f["pr"]}, as specified" and no added docs/superpowers/as-built/*.md'
    notes = [x["path"] for x in paths if x["changeType"] == "ADDED" and re.fullmatch(RELEASE, x["path"])]
    if not notes and not release_notes.section(f["body"]):
        return 'closeout missing: no "## Release note" section in the PR body and no added release note file'
    for p in notes:
        first = next((l for l in f["docs"][p].splitlines() if l.strip()), "")
        if not re.match(r"# \d{4}-\d{2}-\d{2} \S", first):
            return f"closeout missing: release note {p} has no '# YYYY-MM-DD <title>' heading"
    if f["root_branch"] != "main":
        return f"root checkout is on {f['root_branch']}, not main; cannot fast-forward"
    if f["root_dirty"]:
        return "root checkout has tracked changes; cannot fast-forward"
    if f["root_ahead"] is None or f["root_ahead"] > 0:
        return "root main has local commits / no upstream; cannot fast-forward"
    return None


def cleanup(f, run):
    """Delete the remote branch if it is still the PR head, then fast-forward root main.

    Raises CmdError(what). A fork PR's branch is not ours to delete.
    """
    if not f["isCrossRepository"]:
        ref = quote(f["headRefName"], safe="/")
        try:
            tip = run([GH, "api", f"repos/{{owner}}/{{repo}}/git/ref/heads/{ref}", "-q", ".object.sha"]).strip()
        except CmdError as e:
            if not re.search(r"HTTP 404", str(e)):
                raise CmdError(f"read branch: {e}")
            tip = None
        if tip == f["headRefOid"]:
            try:
                run([GH, "api", "-X", "DELETE", f"repos/{{owner}}/{{repo}}/git/refs/heads/{ref}"])
            except CmdError as e:
                if not re.search(r"HTTP 4(04|22)", str(e)):
                    raise CmdError(f"delete branch: {e}")
    if f["root_branch"] != "main":
        raise CmdError(f"fast-forward root main: root checkout is on {f['root_branch']}")
    try:
        run(["git", "-C", f["root"], "pull", "--ff-only"])
    except CmdError as e:
        raise CmdError(f"fast-forward root main: {e}")


def main(argv, run=run):
    if len(argv) != 2 or not re.fullmatch(r"[0-9]+", argv[0]) or not re.fullmatch(r"[0-9a-fA-F]{7,40}", argv[1]):
        print("merge-pr: cannot read arguments; usage: scripts/merge_pr.py <PR number> <approved head SHA, 7+ hex>")
        return 2
    pr, approved = argv[0], argv[1].lower()
    os.environ.pop("AGENT_GH_ROLE", None)  # the merge and the branch delete run as the owner, never a role
    try:
        f = read_facts(pr, approved, run)
        reason = gate(f)
    except (Exception, SystemExit) as e:  # SystemExit: a bad login row in project.md
        print(f"merge-pr: cannot read PR #{pr}: {type(e).__name__} {e}")
        return 2
    if reason:
        print(f"merge-pr: stop #{pr}: {reason}")
        return 1
    if f["state"] == "MERGED":
        sha = (f.get("mergeCommit") or {}).get("oid")
        if not sha:
            print(f"merge-pr: cannot read merge commit of merged PR #{pr}")
            return 2
        verb = "matches" if f["headRefOid"].startswith(approved) else "differs from"
        tail = (
            f"merge-pr: #{pr} already merged as {sha}; nothing to do; "
            f"head {f['headRefOid']} {verb} approved {approved}"
        )
    else:
        try:
            out = run(
                [GH, "api", "-X", "PUT", f"repos/{{owner}}/{{repo}}/pulls/{pr}/merge",
                 "-f", "merge_method=squash", "-f", f"sha={f['headRefOid']}"]
            )
            sha = json.loads(out)["sha"]
        except Exception as e:
            print(f"merge-pr: cannot merge #{pr}: {e}")
            return 2
        tail = f"merge-pr: merged #{pr} as {sha}; head {f['headRefOid']} matches approved {approved}"
    try:
        cleanup(f, run)
    except Exception as e:
        print(f"merge-pr: merged #{pr} as {sha}; cannot {e}")
        return 2
    print(tail)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
