#!/usr/bin/env python3
"""Where a PR waits for a teammate's GitHub review, and which tickets in awaiting-review can move on.

Usage:
    scripts/cos_review_check.py [--file STATE] [--prs FILE]
    scripts/cos_review_check.py --route PR --head SHA [--prs FILE]

Read only: writes nothing. Reads GitHub through `./scripts/gh.sh pr view <N> --json
state,author,headRefOid,reviews,reviewDecision,reviewRequests`, the signed-in login (`gh api user`) and
project.md's `Require teammate approval` row. --prs FILE reads {"<N>": <that JSON>} instead of gh pr view
(tests do). The review rule is merge_pr.review_stop(), the same code the merge gate runs, so the two cannot
drift apart. Because of it, when the signed-in login is a codeowner, REVIEW_REQUIRED alone does not hold a
ticket (the merge gate lets that login past it); the teammate rule with the row `on` still does.

A changes request only fires `changes` on the head it was made on, so a child that pushed a fix is not sent
back to build again while the reviewer has yet to re-review.

--route decides where a fresh MERGE READY goes. Prints one line, exit 0:
    route awaiting-merge
    route awaiting-review needs <names>    (review_stop() blocks, or GitHub's decision is CHANGES_REQUESTED)
    route moved head <short>               (the PR head is not --head)
    route awaiting-merge (unreadable: <what>)   (merge_pr.py still gates at merge)

With no --route it checks every ticket in awaiting-review. One line each,
in state order; the first rule that fits wins:
    closed CW-N #PR                        (the PR was closed, not merged)
    moved CW-N #PR head <short>            (the PR head is not the ticket's headSha)
    changes CW-N #PR by <logins>           (a reviewer's newest verdict is CHANGES_REQUESTED on the ticket's head,
                                           and the row is on or GitHub's decision is CHANGES_REQUESTED)
    approved CW-N #PR head <short> by <logins>   (review_stop() passes; the non-author approvers on the head, else
                                           `github` when its decision is APPROVED, `codeowner` when merge_pr's
                                           codeowner bypass let a missing review pass, else `none`)
    waiting CW-N #PR needs <names>         (a changes request on an older head waits here, naming who must
                                           re-review; so does a bare GitHub decision with no such review)
    unreadable CW-N #PR                    (`#?` when the ticket has no pr; also a missing or short headSha)
A merged PR prints no line (the merged check owns it) but counts as checked.
then "review-check: <C> checked, <A> to act on" (closed, moved, changes and approved count). Logins and team
names print only in GitHub's shape, else as `?`; review text never reaches the output.
Exit 0 when nothing is to act on, 1 when something is, 2 when the check did not run (state or --prs unreadable,
bad arguments). On exit 2 it prints only "cos_review_check: <what>".
"""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import project_config  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


merge_pr = _load("merge_pr")
ROOT, GH = merge_pr.ROOT, merge_pr.GH
PR_FIELDS = "state,author,headRefOid,reviews,reviewDecision,reviewRequests"
LOGIN = r"[A-Za-z0-9][A-Za-z0-9-]{0,38}"
SHAPE = re.compile(rf"{LOGIN}|@{LOGIN}/{LOGIN}")
FULL_SHA = re.compile(r"[0-9a-f]{40}")
TICKET = project_config.ticket_re()
ACT = ("closed", "moved", "changes", "approved")


class Unreadable(Exception):
    """A read failed. The message is a fixed phrase, never text from GitHub."""


def fail(msg):
    print(f"cos_review_check: {msg}")
    raise SystemExit(2)


def run_gh(cmd):
    """stdout of a command in the repo; raises merge_pr.CmdError when it fails or times out."""
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        raise merge_pr.CmdError(type(e).__name__)
    if p.returncode:
        raise merge_pr.CmdError((p.stderr or p.stdout).strip() or f"exit {p.returncode}")
    return p.stdout


def safe(name):
    """A login or @org/team prints as is only when it has GitHub's shape."""
    return name if isinstance(name, str) and SHAPE.fullmatch(name) else "?"


def names(items):
    return ", ".join(safe(x) for x in items)


def rule_row():
    rule = project_config.setting("Require teammate approval")
    rule = rule.lower() if rule else None
    if rule not in (None, "off", "on"):
        raise Unreadable("bad Require teammate approval row")
    return rule


def identity(run=run_gh):
    """(login, codeowners) for the merge rule's REVIEW_REQUIRED bypass."""
    try:
        return run([GH, "api", "user", "-q", ".login"]).strip(), merge_pr.codeowners(run)
    except merge_pr.CmdError:
        raise Unreadable("gh failed")


def read_pr(n, prs, run=run_gh):
    if prs is not None:
        if str(n) not in prs:
            raise Unreadable("PR not in the file")
        return prs[str(n)]
    try:
        return json.loads(run([GH, "pr", "view", str(n), "--json", PR_FIELDS]))
    except (merge_pr.CmdError, ValueError):
        raise Unreadable("gh failed")


def facts(n, raw, rule, who):
    """The facts dict merge_pr's review rules read, checked for shape."""
    try:
        f = {
            "login": who[0], "codeowners": who[1], "teammate": rule, "pr": str(n), "state": raw["state"],
            "author": {"login": raw["author"]["login"]}, "reviews": raw["reviews"], "reviewDecision": raw["reviewDecision"],
            "reviewRequests": raw["reviewRequests"], "headRefOid": raw["headRefOid"],
        }
        ok = (
            f["state"] in ("OPEN", "CLOSED", "MERGED") and FULL_SHA.fullmatch(f["headRefOid"])
            and isinstance(f["author"]["login"], str) and isinstance(f["reviews"], list)
            and isinstance(f["reviewRequests"], list) and f["reviewDecision"] in ("", None, "APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED")
        )
    except (KeyError, TypeError):
        ok = False
    if not ok:
        raise Unreadable("bad PR data")
    return f


def changers(f):
    """(logins, logins on the PR head) of reviewers whose newest verdict is CHANGES_REQUESTED, when that stops the PR."""
    if f["teammate"] != "on" and f["reviewDecision"] != "CHANGES_REQUESTED":
        return [], []
    got = [(login, (r.get("commit") or {}).get("oid")) for login, r in merge_pr.latest_verdicts(f).values() if r["state"] == "CHANGES_REQUESTED"]
    return [login for login, _ in got], [login for login, oid in got if oid == f["headRefOid"]]


def needs(f):
    """Who the PR waits on: reviewers with a standing changes request, else GitHub's requested reviewers, else the reason there is no name."""
    return names(changers(f)[0]) or names(merge_pr.requested_names(f)) or ("required reviewers" if f["reviewDecision"] == "REVIEW_REQUIRED" else "a teammate")


def verdict(f, head):
    """(word, text after the PR number) for a ticket at head; the first rule that fits wins. May raise on bad review data."""
    if f["state"] == "CLOSED":
        return "closed", ""
    if f["state"] == "MERGED":
        return "merged", ""
    if f["headRefOid"] != head:
        return "moved", f" head {f['headRefOid'][:7]}"
    on_head = changers(f)[1]
    if on_head:
        return "changes", f" by {names(on_head)}"
    if f["reviewDecision"] != "CHANGES_REQUESTED" and merge_pr.review_stop(f) is None:
        ok = [login for login, r in merge_pr.latest_verdicts(f).values() if r["state"] == "APPROVED" and (r.get("commit") or {}).get("oid") == head]
        who = names(ok) if ok else "github" if f["reviewDecision"] == "APPROVED" else "codeowner" if f.get("bypass") else "none"
        return "approved", f" head {head[:7]} by {who}"
    return "waiting", f" needs {needs(f)}"


def route(n, head, prs, run=run_gh):
    """The one line that says where a MERGE READY at head goes."""
    try:
        rule = rule_row()
        f = facts(n, read_pr(n, prs, run), rule, identity(run))
        if not f["headRefOid"].startswith(head):
            return f"route moved head {f['headRefOid'][:7]}"
        if merge_pr.review_stop(f) is None and f["reviewDecision"] != "CHANGES_REQUESTED":
            return "route awaiting-merge"
        return f"route awaiting-review needs {needs(f)}"
    except Unreadable as e:
        return f"route awaiting-merge (unreadable: {e})"
    except (KeyError, TypeError, ValueError, AttributeError):  # a review row of an unexpected shape
        return "route awaiting-merge (unreadable: bad PR data)"


def load_state(path):
    try:
        state = json.loads(Path(path).read_text())
    except FileNotFoundError:
        fail("no state file")
    except (OSError, UnicodeDecodeError, ValueError):
        fail("unreadable state file")
    if not isinstance(state, dict) or not isinstance(state.get("tickets"), dict):
        fail("unreadable state file")
    return state


def load_prs(path):
    try:
        prs = json.loads(Path(path).read_text())
    except (OSError, UnicodeDecodeError, ValueError):
        fail("unreadable PR file")
    if not isinstance(prs, dict):
        fail("bad PR file")
    return prs


def tickets(state):
    """(ticket, pr number or None, headSha or None) for each awaiting-review ticket; None marks a field that can't be used."""
    for tid, info in sorted(state["tickets"].items()):
        if not (isinstance(info, dict) and TICKET.fullmatch(tid) and info.get("stage") == "awaiting-review"):
            continue
        pr, head = info.get("pr"), info.get("headSha")
        pr = int(pr) if isinstance(pr, str) and pr.isdigit() else pr
        yield tid, pr if type(pr) is int else None, head if isinstance(head, str) and FULL_SHA.fullmatch(head) else None


def check(state, prs=None, run=run_gh):
    """(lines, flagged): flagged is [(ticket, word)] for each line to act on."""
    items = list(tickets(state))
    lines, flagged, shared = [], [], None
    if items:
        try:
            shared = rule_row(), identity(run)
        except Unreadable:
            pass
    for tid, n, head in items:
        try:
            if shared is None or n is None or head is None:
                raise Unreadable("nothing to check")
            word, rest = verdict(facts(n, read_pr(n, prs, run), *shared), head)
        except (Unreadable, KeyError, TypeError, ValueError, AttributeError):
            lines.append(f"unreadable {tid} #{'?' if n is None else n}")
            continue
        if word == "merged":
            continue
        lines.append(f"{word} {tid} #{n}{rest}")
        if word in ACT:
            flagged.append((tid, word))
    lines.append(f"review-check: {len(items)} checked, {len(flagged)} to act on")
    return lines, flagged


def main(argv=None):
    ap = argparse.ArgumentParser(description="Which awaiting-review tickets a teammate's review lets move on.")
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--prs", type=Path)
    ap.add_argument("--route")
    ap.add_argument("--head")
    args = ap.parse_args(argv)
    prs = load_prs(args.prs) if args.prs else None
    if args.route is not None or args.head is not None:
        if not (args.route and re.fullmatch(r"[0-9]+", args.route) and args.head and re.fullmatch(r"[0-9a-fA-F]{7,40}", args.head)):
            fail("usage: --route <PR number> --head <sha, 7+ hex>")
        print(route(int(args.route), args.head.lower(), prs))
        return 0
    lines, flagged = check(load_state(args.file), prs)
    print("\n".join(lines))
    return 1 if flagged else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:  # a crash must exit 2, not 1 ("something to act on")
        fail("crashed")
