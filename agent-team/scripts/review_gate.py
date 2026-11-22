#!/usr/bin/env python3
"""Say whether a PR's code review and security review stand at its current head, before `MERGE READY`.

Usage:
    ~/.collective-wisdom/scripts/review_gate.py <PR number> [--lines] [--next]

Run it from the worktree after wait-for-ci.sh passes. It reads the PR's comments, commits and head through gh, and applies merge_pr.py's own
review rules (merge_pr.review and merge_pr.stands), so this check and the merge gate cannot disagree. The head a review was posted on is the newest commit committed before the review
comment, the same rule merge_pr.py uses. It posts nothing.

Exit 0, last line:
  review-gate: pass head <SHA> code <url> security <url>   both reviews stand at the head; use the URLs in MERGE READY
  review-gate: note head <SHA> reviewed <SHA>               the head moved only by merging the merge target branch and the PR diff is
                                                            unchanged, or the PR diff changed only in docs files (the docs-file rule in
                                                            pr_diff_delta.py), or the docs check's one fix commit changed only living docs off
                                                            the hands path (pr_diff_delta.py's living rule); the line before it is the reviews-stand note. Post it with
                                                            gh.sh pr comment (as the builder), then run this again: it prints pass
  review-gate: rerun <code|security|both>: <why>            a review is missing, not PASS, stale, or the diff changed; run it on the head
  review-gate: ci                                           project.md's Review mode is ci; this check does not apply
Exit 2: bad arguments or a read failed. Last line: review-gate: cannot <what>. Run it once more, then stop as BLOCKED.

--lines adds two lines before the `pass` line (nothing is added to any other line; `ci` mode prints neither):
  reviews-needed: <logins and @org/team slugs, comma-separated, or none>   who GitHub still waits on (gh pr view --json reviewRequests); the MERGE READY
                                                                            `Reviews needed:` value. It does not say whether a teammate already approved
  docs-check: run                                                           no `## Docs check` comment by the gh user on the PR: run the docs check
  docs-check: done <url>                                                    the gh user's newest `## Docs check` comment; its `Docs checked:` line is the MERGE READY value
The docs check re-run after a conflict resolution with `Review after conflict resolution` `on` is not seen here: a script cannot tell that
resolution happened, so open-pr § Docs check keeps that rule.

--next (implies --lines) prints `next: <instruction>` after each line whose action is fixed, from the NEXT table below. The note text
(the line before `review-gate: note`) gets none: it is the comment to post. Without --next and --lines the output is unchanged.
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

# --next: the instruction after each output line, by line prefix (first match wins). Where ship-loop § Phases 4 used to hold this table.
NEXT = (
    ("reviews-needed: ", "put it after `Reviews needed:` in MERGE READY."),
    ("docs-check: run", "run the docs check once (open-pr § Docs check), then wait-for-ci.sh, then run review_gate.py again."),
    ("docs-check: done ", "copy the `Docs checked:` line of that comment into MERGE READY's `Docs checked:`."),
    ("review-gate: pass ", "go on to MERGE READY (ship-loop § Phases, 4) unless `docs-check: run` was printed: use the printed code and security URLs, set `Head:` to the printed head."),
    ("review-gate: note ", "post the line before this one with ~/.collective-wisdom/scripts/gh.sh pr comment as the builder, then run review_gate.py again: it prints pass."),
    ("review-gate: rerun ", "run the named review on the current head and post its result first (open-pr § Review scope), then run review_gate.py again."),
    ("review-gate: ci", "follow open-pr § CI review mode."),
    ("review-gate: cannot read arguments", "fix the call: review_gate.py <PR number> [--lines] [--next]."),
    ("review-gate: cannot ", "run it once more; if it exits 2 again, stop with BLOCKED: quoting its line."),
)
NO_NEXT = ("Head moved to ",)  # the note text: the comment to post, not an action


def next_for(line):
    """The --next instruction for an output line, or None for a line that has none."""
    return next((text for prefix, text in NEXT if line.startswith(prefix)), None)


def posted_on(f, c):
    """The commit that was the PR head when review comment c was posted: the newest commit committed before it, or None."""
    before = [x for x in f["commits"] if merge_pr.ts(x["committedDate"]) < merge_pr.ts(c["createdAt"])]
    return max(before, key=lambda x: merge_pr.ts(x["committedDate"]), default=None)


def read_facts(pr, run, lines=False):
    fields = "comments,commits,headRefOid" + (",reviewRequests" if lines else "")
    f = json.loads(run([merge_pr.GH, "pr", "view", pr, "--json", fields]))
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
    if kind not in ("same", "docs", "living"):
        return rerun(bad, all_why=f"diff changed since {reviewed[:7]}: {', '.join(repr(x) for x in files[:10])}"), None
    if kind == "docs":
        note = f"Head moved to {head}; PR diff changed only in docs files since {reviewed}: {merge_pr.pr_diff_delta.show(files)}. Reviews from {reviewed} stand."
        return f"review-gate: note head {head} reviewed {reviewed}", note
    if kind == "living":
        note = f"Head moved to {head} by the docs check fix commit; PR diff changed only in living docs since {reviewed}: {merge_pr.pr_diff_delta.show(files)}. Reviews from {reviewed} stand."
        return f"review-gate: note head {head} reviewed {reviewed}", note
    note = f"Head moved to {head} by merging {project_config.target_branch()}; PR diff unchanged since {reviewed}. Reviews from {reviewed} stand."
    return f"review-gate: note head {head} reviewed {reviewed}", note


def extra_lines(f):
    """The --lines text before a `pass` line: who the PR waits on, and whether the docs check ran."""
    docs = [c for c in f["comments"] if c["author"]["login"] == f["login"] and c["body"].startswith("## Docs check")]
    check = f"docs-check: done {max(docs, key=lambda c: merge_pr.ts(c['createdAt']))['url']}" if docs else "docs-check: run"
    return [f"reviews-needed: {', '.join(merge_pr.requested_names(f)) or 'none'}", check]


def rerun(bad, all_why=None):
    """The rerun line naming the bad reviews; all_why replaces their own reasons."""
    which = "both" if len(bad) == len(TITLES) else next(iter(bad))
    why = all_why or (next(iter(bad.values())) if len(bad) == 1 else "; ".join(f"{name}: {w}" for name, w in bad.items()))
    return f"review-gate: rerun {which}: {why}"


def main(argv, run=merge_pr.run, delta=merge_pr.real_delta):
    if argv in (['-h'], ['--help']):
        print(__doc__)
        return 0
    flags = [a for a in argv if a.startswith("--")]
    args = [a for a in argv if not a.startswith("--")]
    want_next = "--next" in flags
    with_lines = "--lines" in flags or want_next
    if len(args) != 1 or not re.fullmatch(r"[0-9]+", args[0]) or not set(flags) <= {"--lines", "--next"}:
        print("review-gate: cannot read arguments; usage: ~/.collective-wisdom/scripts/review_gate.py <PR number> [--lines] [--next]")
        if want_next:
            print(f"next: {next_for('review-gate: cannot read arguments')}")
        return 2
    pr = args[0]
    out = []
    try:
        if project_config.review_mode() == "ci":
            out = ["review-gate: ci"]
        else:
            facts = read_facts(pr, run, with_lines)
            last, note = verdict(facts, delta)
            out = ([note] if note else []) + (extra_lines(facts) if with_lines and last.startswith("review-gate: pass ") else []) + [last]
    except (Exception, SystemExit) as e:
        out = [f"review-gate: cannot read PR #{pr}: {type(e).__name__} {e}"]
        code = 2
    else:
        code = 0
    for line in out:
        print(line)
        if want_next and (text := next_for(line)):
            print(f"next: {text}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
