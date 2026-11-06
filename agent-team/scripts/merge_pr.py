#!/usr/bin/env python3
"""Squash-merge an approved PR, delete its branch (if it still points at the PR head and the PR is not from a fork) and fast-forward root main.

Usage:
    scripts/merge_pr.py <PR number> <approved head SHA>

Run it from the root checkout (`cd <root checkout> && python3 scripts/merge_pr.py ...`): it finds the repo from the current directory. The approved head is at least 7 hex characters. Every gate in
the checks list of the merge-pr skill (gh signed in as project.md's Owner login among them) must pass first; if one fails nothing changes. The merge goes through the REST API with sha=<head>,
so no local branch is switched and GitHub refuses it if the head moved.

When project.md's `Publish release notes` row is not `off`, the gate asks for a release note and, after the fast-forward, the script publishes the full release notes as RELEASE_NOTES.md on the release-notes branch through the API. With `off` it does neither. A failed publish prints
`merge-pr: warn <reason>` before the last line and changes neither the exit code nor the last line.

Exit 0: merged, or already merged (cleanup is repeated). Last line:
  merge-pr: merged #N as <SHA>; head <SHA> matches approved <SHA>
  merge-pr: #N already merged as <SHA>; nothing to do; head <SHA> matches|differs from approved <SHA>
Exit 1: a gate failed, nothing changed. Last line: merge-pr: stop #N: <reason>
Exit 2: bad arguments, a gh or git call failed. Last line: merge-pr: cannot <what>
"""

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import ci_review  # noqa: E402
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
    "statusCheckRollup,comments,commits,files,mergeCommit,isCrossRepository,body,"
    "author,reviews,reviewDecision,reviewRequests"
)
VERDICTS = ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")
TEAM_ASSOCIATIONS = ("OWNER", "MEMBER", "COLLABORATOR")  # a review from anyone else is ignored
AS_BUILT = r"docs/superpowers/as-built/[^/]+\.md"
SPECS = r"docs/superpowers/specs/[^/]+\.md"
RELEASE = r"docs/superpowers/release-notes/[^/]+\.md"
NOTES_DIR = "docs/superpowers/release-notes/"
NOTES_BRANCH = "release-notes"
NOTES_FILE = "RELEASE_NOTES.md"
API = "repos/{owner}/{repo}/git"
OK_CONCLUSIONS = ("SUCCESS", "SKIPPED", "NEUTRAL")
NOTE = re.compile(r"Head moved to ([0-9a-f]{40})\b.*?unchanged since ([0-9a-f]{40})", re.I | re.S)


def run(cmd, input=None):
    """Run a command in the repo and return its stdout; raise CmdError on failure. `input` goes to stdin."""
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, input=input)
    if p.returncode:
        raise CmdError((p.stderr or p.stdout).strip() or f"exit {p.returncode}")
    return p.stdout


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def codeowners(run):
    """Lower-cased user logins on the `*` line of .github/CODEOWNERS on origin/main (the repo's trusted copy), or [] when there is none."""
    try:
        text = run(["git", "-C", str(ROOT), "show", "refs/remotes/origin/main:.github/CODEOWNERS"])
    except CmdError:
        return []
    owners = []
    for line in text.splitlines():
        parts = line.split("#", 1)[0].split()
        if parts[:1] == ["*"]:
            owners += [o[1:].lower() for o in parts[1:] if o.startswith("@") and "/" not in o]
    return owners


def read_facts(pr, approved, run):
    """Everything the gate needs, from gh and git reads only."""
    f = json.loads(run([GH, "pr", "view", pr, "--json", FIELDS]))
    f["approved"] = approved
    f["pr"] = pr
    f["login"] = run([GH, "api", "user", "-q", ".login"]).strip()
    f["owner"] = project_config.value("Owner login")
    f["codeowners"] = codeowners(run)
    teammate = project_config.setting("Require teammate approval")
    f["teammate"] = teammate.lower() if teammate else None
    f["noCi"] = project_config.no_ci()
    f["notesOn"] = project_config.release_notes_enabled()
    try:
        f["reviewMode"] = project_config.review_mode()
    except SystemExit as e:  # a bad value is a failed read (exit 2), never `agents`
        raise CmdError(str(e))
    if f["reviewMode"] == "ci":
        f["ciBot"] = project_config.ci_bot()
        if f["ciBot"] and f["state"] == "OPEN":
            try:
                threads = ci_review.fetch(pr, lambda *a: run([GH, *a]), repo=None)
            except ci_review.CiError as e:
                raise CmdError(f"read CI review threads: {e}")
            f["ciThreads"] = ci_review.classify(threads, f["ciBot"])["unresolved"]
    f["docs"] = {}
    if f["state"] == "OPEN":
        want = [
            x["path"]
            for x in f["files"]
            if (re.fullmatch(SPECS, x["path"]) and x["changeType"] != "DELETED")
            or (f["notesOn"] and re.fullmatch(RELEASE, x["path"]) and x["changeType"] == "ADDED")
        ]
        for path in want:
            url = f"repos/{{owner}}/{{repo}}/contents/{quote(path)}?ref={f['headRefOid']}"
            f["docs"][path] = run([GH, "api", url, "-H", "Accept: application/vnd.github.raw+json"])
    wt = run(["git", "-C", str(ROOT), "worktree", "list", "--porcelain"])
    block = wt.strip().split("\n\n")[0].splitlines()
    f["root"] = block[0].removeprefix("worktree ")
    # The gate reads project.md from the current directory, so a feature worktree would let its PR change the rules.
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


def stands(f, c, delta):
    """Return None when a reviews-stand note covers review c at the current head, else why not."""
    notes = [
        n
        for n in f["comments"]
        if n["author"]["login"] == f["login"] and n["body"].startswith("Head moved to ")
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
    who = f["login"]
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


def requested_names(f):
    """Who GitHub still waits on: logins, and @org/team for a team."""
    names = []
    for r in f.get("reviewRequests") or []:
        names.append(f"@{r['slug']}" if r.get("__typename") == "Team" else r["login"])  # slug is "org/team"
    return names


def required_reviews(f):
    """Return why GitHub's required reviews still block the PR, or None.

    A codeowner may merge past a missing review (the ruleset's bypass is for repo admins, who are the codeowners): the PR is then
    allowed to be BLOCKED, and only for that reason, since every other gate still runs.
    """
    if f.get("reviewDecision") != "REVIEW_REQUIRED":
        return None
    if f["login"].lower() in f.get("codeowners", []):
        f["bypass"] = True
        return None
    return f"required reviews missing: waiting on {', '.join(requested_names(f)) or 'required reviewers'}"


def latest_verdicts(f):
    """{lower-cased reviewer: (login, their newest verdict review)} over team members' reviews, the author's own left out."""
    author = f["author"]["login"]
    latest = {}
    others = [
        r
        for r in f.get("reviews") or []
        if r["author"]["login"].lower() != author.lower() and r.get("authorAssociation") in TEAM_ASSOCIATIONS
    ]
    for r in sorted((r for r in others if r["state"] in VERDICTS), key=lambda r: ts(r["submittedAt"])):
        latest[r["author"]["login"].lower()] = (r["author"]["login"], r)
    return latest


def teammate_approval(f):
    """Return why the teammate rule stops the merge, or None when it passes or is off."""
    rule = f.get("teammate")
    if rule in (None, "off"):
        return None
    if rule != "on":
        return f"project.md's Require teammate approval is {rule}; use on or off"
    author = f["author"]["login"]
    head = f["headRefOid"]
    latest = latest_verdicts(f)
    stuck = [who for who, r in latest.values() if r["state"] == "CHANGES_REQUESTED"]
    if stuck:
        return f"changes requested by {', '.join(stuck)} on PR #{f['pr']}"
    approved = [r for _, r in latest.values() if r["state"] == "APPROVED"]
    if any((r.get("commit") or {}).get("oid") == head for r in approved):
        return None
    if approved:
        old = (approved[0].get("commit") or {}).get("oid") or ""
        return f"no approving review on head {head[:7]}; approved {old[:7]}, head moved"
    base = f"no approving review by a user other than {author} on head {head[:7]}"
    if latest:
        seen = ", ".join(who + " " + r["state"] for who, r in latest.values())
        return f"{base}; latest reviews are {seen}"
    own = any(
        r["state"] == "APPROVED" and r["author"]["login"].lower() == author.lower()
        for r in f.get("reviews") or []
    )
    return base + ("; the author's own approval does not count" if own else "")


def review_stop(f):
    """Return the first reason the review rules stop the merge (required reviews, then the teammate rule), or None."""
    for check in (required_reviews, teammate_approval):
        problem = check(f)
        if problem:
            return problem
    return None


def gate(f, delta=real_delta):
    """Return the reason to stop, or None when the PR may merge (or is merged)."""
    if f.get("not_root_checkout"):
        return f"run it from the root checkout: cd {f['root']} && python3 scripts/merge_pr.py ...; this directory's project.md is not the gate's"
    if not f.get("owner"):
        return "project.md has no Owner login; cannot tell whose gh login this is"
    if f["login"].lower() not in [f["owner"].lower(), *f.get("codeowners", [])]:
        return f"gh is signed in as {f['login']}, not the owner {f['owner']}"
    if f["state"] == "MERGED":
        return None
    if f["state"] == "CLOSED":
        return "PR is closed, not merged"
    if f["state"] != "OPEN":
        return f"PR state is {f['state']}"
    if f["isDraft"]:
        return "PR is a draft"
    if f["isCrossRepository"]:
        return "PR is from a fork"
    if f["baseRefName"] != "main":
        return f"base is {f['baseRefName']}, not main"
    if not f["headRefOid"].startswith(f["approved"]):
        return f"head {f['headRefOid']} is not approved head {f['approved']}"
    problem = review_stop(f)
    if problem:
        return problem
    if f["mergeable"] != "MERGEABLE" or f["mergeStateStatus"] != ("BLOCKED" if f.get("bypass") else "CLEAN"):
        return f"not mergeable: mergeable {f['mergeable']}, state {f['mergeStateStatus']}"
    if not f["statusCheckRollup"] and not f.get("noCi"):
        return "no checks (a repo with no CI says so in project.md's Required CI checks row)"
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
    if f.get("reviewMode") == "ci":
        if not f.get("ciBot"):
            return "project.md Review mode is ci but has no CI review bot login"
        if "ciThreads" not in f:
            return "CI review threads not read"
        if f["ciThreads"]:
            t = f["ciThreads"][0]
            return f"unresolved CI review thread by {f['ciBot']}: {t['path']}:{t['line']} {t['url']}"
    else:
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
    if f.get("notesOn", True):
        notes = [x["path"] for x in paths if x["changeType"] == "ADDED" and re.fullmatch(RELEASE, x["path"])]
        if not notes and not release_notes.section(f["body"]):
            return 'closeout missing: no "## Release note" section in the PR body and no added release note file'
        for p in notes:
            first = next((l for l in f["docs"][p].splitlines() if l.strip()), "")
            if not re.match(r"# \d{4}-\d{2}-\d{2} \S", first):
                return f"closeout missing: release note {p} has no '# YYYY-MM-DD <title>' heading"
    proof = release_notes.section(f["body"], "Proof")
    if not proof:
        return 'proof missing: no "## Proof" section in the PR body'
    if not re.search(r"^Not proven", proof, re.M):
        return 'proof missing: the "## Proof" section has no "Not proven" line'
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


class Skip(Exception):
    """A publish step that stops the publish quietly or with a reason."""


def blob_sha(data):
    """The git blob SHA of data (bytes)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def note_files(run):
    """(file name, text) for each regular `.md` blob directly in the release notes folder of origin/main."""
    out = run(["git", "ls-tree", "-z", "refs/remotes/origin/main", "--", NOTES_DIR])
    files = []
    for entry in out.split("\0"):
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        name = path.removeprefix(NOTES_DIR)
        if len(parts) == 3 and parts[:2] in (["100644", "blob"], ["100755", "blob"]) and path.startswith(NOTES_DIR) and "/" not in name and name.endswith(".md"):
            files.append((name, run(["git", "cat-file", "blob", parts[2]])))
    return files


def post(run, kind, body, method="POST"):
    """Send a JSON body to the git data API on stdin and return the parsed answer."""
    return json.loads(run([GH, "api", "-X", method, f"{API}/{kind}", "--input", "-"], input=json.dumps(body)))


def publish_notes(pr, sha, run):
    try:
        prs = json.loads(run([GH, "pr", "list", "--state", "merged", "--base", "main",
                              "--json", "number,title,body,mergedAt", "--limit", "500"]))
    except Exception:
        raise Skip("cannot read merged PRs; release notes not published")
    try:
        run(["git", "merge-base", "--is-ancestor", sha, "refs/remotes/origin/main"])
        text = release_notes.render(note_files(run), prs, release_notes.file_merge_times()) + "\n"
    except Exception as e:
        raise Skip(f"cannot build the release notes: {type(e).__name__} {e}")
    data = text.encode()
    tip = None
    try:
        tip = run([GH, "api", f"{API}/ref/heads/{NOTES_BRANCH}", "-q", ".object.sha"]).strip()
    except CmdError as e:
        if "HTTP 404" not in str(e):
            raise Skip(f"cannot read the {NOTES_BRANCH} branch: {e}")
    if tip:
        try:
            tree = run([GH, "api", f"{API}/commits/{tip}", "-q", ".tree.sha"]).strip()
            entries = json.loads(run([GH, "api", f"{API}/trees/{tree}"]))["tree"]
        except Exception as e:
            raise Skip(f"cannot read the {NOTES_BRANCH} branch: {e}")
        if len(entries) != 1 or entries[0]["type"] != "blob" or entries[0]["path"] != NOTES_FILE or entries[0]["mode"] != "100644":
            raise Skip(f"{NOTES_BRANCH} branch holds other files; not published")
        if entries[0]["sha"] == blob_sha(data):
            return
    try:
        tree = post(run, "trees", {"tree": [{"path": NOTES_FILE, "mode": "100644", "type": "blob", "content": text}]})["sha"]
        commit = post(run, "commits", {"message": f"docs: release notes after #{pr}", "tree": tree, "parents": [tip] if tip else []})["sha"]
        if tip:
            post(run, f"refs/heads/{NOTES_BRANCH}", {"sha": commit, "force": False}, "PATCH")
        else:
            post(run, "refs", {"ref": f"refs/heads/{NOTES_BRANCH}", "sha": commit})
    except CmdError as e:
        if "HTTP 422" in str(e):
            raise Skip(f"{NOTES_BRANCH} update rejected; the next merge repairs it")
        raise


def publish(pr, sha, run):
    """Write RELEASE_NOTES.md on the release-notes branch through the API. Never raises: a problem prints one warn line."""
    try:
        publish_notes(pr, sha, run)
    except Exception as e:
        reason = e if isinstance(e, Skip) else f"cannot publish release notes: {e}"
        print(f"merge-pr: warn {' '.join(str(reason).split())}")


def main(argv, run=run):
    if len(argv) != 2 or not re.fullmatch(r"[0-9]+", argv[0]) or not re.fullmatch(r"[0-9a-fA-F]{7,40}", argv[1]):
        print("merge-pr: cannot read arguments; usage: scripts/merge_pr.py <PR number> <approved head SHA, 7+ hex>")
        return 2
    pr, approved = argv[0], argv[1].lower()
    try:
        f = read_facts(pr, approved, run)
        reason = gate(f)
    except Exception as e:
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
    if f.get("notesOn", True):
        publish(pr, sha, run)
    print(tail)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
