#!/usr/bin/env python3
"""Say whether a PR's code review and security review stand at its current head, before `MERGE READY`.

Usage:
    ~/.collective-wisdom/scripts/review_gate.py <PR number>

Run it from the worktree after wait-for-ci.sh passes. It reads the PR's comments, commits and head through gh, and applies merge_pr.py's own
review rules (merge_pr.review and merge_pr.stands), so this check and the merge gate cannot disagree. The head a review was posted on is the newest commit committed before the review
comment, the same rule merge_pr.py uses. It posts nothing.

Exit 0, last line:
  review-gate: pass head <SHA> code <url> security <url>   both reviews stand at the head; use the URLs in MERGE READY
  review-gate: note head <SHA> reviewed <SHA>               the head moved only by merging the merge target branch and the PR diff is
                                                            unchanged; the line before it is the reviews-stand note. Post it with
                                                            gh.sh pr comment (as the builder), then run this again: it prints pass
  review-gate: rerun <code|security|both>: <why>            a review is missing, not PASS, stale, or the diff changed; run it on the head
  review-gate: ci                                           project.md's Review mode is ci; this check does not apply
Exit 2: bad arguments or a read failed. Last line: review-gate: cannot <what>. Run it once more, then stop as BLOCKED.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import merge_pr  # noqa: E402
import project_config  # noqa: E402

TITLES = {"code": "## Code review", "security": "## Security review"}
NO_NOTE = "no reviews-stand note for this head"


def posted_on(f, c):
    """The commit that was the PR head when review comment c was posted: the newest commit committed before it, or None."""
    before = [x for x in f["commits"] if merge_pr.ts(x["committedDate"]) < merge_pr.ts(c["createdAt"])]
    return max(before, key=lambda x: merge_pr.ts(x["committedDate"]), default=None)


def read_facts(pr, run):
    f = json.loads(run([merge_pr.GH, "pr", "view", pr, "--json", "comments,commits,headRefOid"]))
    f["pr"] = pr
    f["login"] = run([merge_pr.GH, "api", "user", "-q", ".login"]).strip()
    f["conflictReview"] = f["headParents"] = f["headNew"] = None
    if merge_pr.resolved_note(f):  # a conflict-resolved head is covered when merge_pr.resolved_head says so: give it the facts it reads
        f["conflictReview"] = project_config.review_after_conflict()
        try:
            merge_pr.pr_diff_delta.fetch(pr, run)
            f["headParents"] = run(["git", "rev-list", "--parents", "-n", "1", f["headRefOid"]]).split()[1:]
            if len(f["headParents"]) == 2:
                f["headNew"] = run(["git", "rev-list", f["headRefOid"], f"^{f['headParents'][0]}", f"^{project_config.target_ref()}"]).split()
        except merge_pr.CmdError:
            pass
    return f


def verdict(f, delta):
    """The last line to print, and the text before it (or None)."""
    results = {name: merge_pr.review(f, title, delta) for name, title in TITLES.items()}
    head = f["headRefOid"]
    bad = {name: why for name, (_, why) in results.items() if why}
    if not bad:
        urls = " ".join(f"{name} {results[name][0]['url']}" for name in TITLES)
        return f"review-gate: pass head {head} {urls}", None
    # Only a review that is PASS but older than the head, with no note yet, can be saved by one: the head may have moved by a merge.
    if not all(NO_NOTE in why and "older than head commit" in why for why in bad.values()):
        return rerun(bad), None
    heads = {name: posted_on(f, results[name][0]) for name in bad}
    if None in heads.values() or len({x["oid"] for x in heads.values()}) != 1:
        return rerun(bad, all_why="the reviews were posted on different heads"), None
    reviewed = next(iter(heads.values()))["oid"]
    try:
        kind, files = delta(f, reviewed)
    except merge_pr.CmdError as e:
        return rerun(bad, all_why=f"cannot compare diff since {reviewed[:7]}: {e}"), None
    if kind != "same":
        return rerun(bad, all_why=f"diff changed since {reviewed[:7]}: {', '.join(repr(x) for x in files[:10])}"), None
    note = f"Head moved to {head} by merging {project_config.target_branch()}; PR diff unchanged since {reviewed}. Reviews from {reviewed} stand."
    return f"review-gate: note head {head} reviewed {reviewed}", note


def rerun(bad, all_why=None):
    """The rerun line naming the bad reviews; all_why replaces their own reasons."""
    which = "both" if len(bad) == len(TITLES) else next(iter(bad))
    why = all_why or (next(iter(bad.values())) if len(bad) == 1 else "; ".join(f"{name}: {w}" for name, w in bad.items()))
    return f"review-gate: rerun {which}: {why}"


def main(argv, run=merge_pr.run, delta=merge_pr.real_delta):
    if argv in (['-h'], ['--help']):
        print(__doc__)
        return 0
    if len(argv) != 1 or not re.fullmatch(r"[0-9]+", argv[0]):
        print("review-gate: cannot read arguments; usage: ~/.collective-wisdom/scripts/review_gate.py <PR number>")
        return 2
    pr = argv[0]
    try:
        if project_config.review_mode() == "ci":
            print("review-gate: ci")
            return 0
        last, note = verdict(read_facts(pr, run), delta)
    except (Exception, SystemExit) as e:
        print(f"review-gate: cannot read PR #{pr}: {type(e).__name__} {e}")
        return 2
    if note:
        print(note)
    print(last)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
