#!/usr/bin/env python3
"""Post the owner's approving review on a PR after the user's own "approve N" in the Chief of Staff thread.

Usage:
    scripts/cos_approve_pr.py [--db PATH] [--file STATE] <PREFIX>-N

The only argument the caller picks is the ticket ID. The PR, its head, the thread, the cut-off time and the words
(`approve <N>`) come from the state file and T3's message store. Run it from the root checkout, with no AGENT_GH_ROLE
(it is removed from the environment), signed in to gh as the Owner login.

Gates, in order; the first failure stops with nothing posted: root checkout, state, the user's message
(scripts/cos_user_check.py latest), gh login, PR facts, head. If the owner already has an approving review on the head,
nothing is posted.

Exit 0: posted, or already approved. Last line:
  cos-approve: approved #N at <SHA>
  cos-approve: #N already approved by <owner> at <SHA>; nothing posted
Exit 1: a gate failed, nothing posted. Last line: cos-approve: stop <PREFIX>-N: <reason>
Exit 2: bad arguments, or state, the message store, gh or the POST failed. Last line: cos-approve: cannot <what>
"""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
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
cos_state = _load("cos_state")
cos_user_check = _load("cos_user_check")
ROOT, GH = merge_pr.ROOT, merge_pr.GH
PR_FIELDS = "state,isDraft,baseRefName,isCrossRepository,headRefOid,reviews"


class Stop(Exception):
    """A gate failed: exit 1, nothing posted."""


class Cannot(Exception):
    """A read or the POST failed: exit 2, nothing posted."""


def check_root(run):
    try:
        out = run(["git", "-C", str(ROOT), "worktree", "list", "--porcelain"])
    except merge_pr.CmdError as e:
        raise Cannot(f"list worktrees: {e}")
    first = out.strip().split("\n\n")[0].splitlines()[0].removeprefix("worktree ")
    if ROOT.resolve() != Path(first).resolve():
        raise Stop(f"not run from the root checkout; cd {first} first, its project.md is the one to trust")


def read_state(path, tid):
    try:
        state = cos_state.load(path)
    except SystemExit:
        raise Cannot("read the state file")
    t = state.get("tickets", {}).get(tid)
    if not isinstance(t, dict) or t.get("stage") != "awaiting-merge":
        raise Stop("ticket not in awaiting-merge")
    pr, sha, seen, thread = str(t.get("pr") or ""), t.get("headSha") or "", t.get("lastSeenAt"), state.get("chiefThreadId")
    if not re.fullmatch(r"[0-9]+", pr):
        raise Stop("ticket has no pr in the state file")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise Stop("ticket has no full headSha in the state file")
    if not thread or not isinstance(seen, str) or not cos_user_check.valid_after(seen):
        raise Stop("state file has no chiefThreadId or no usable lastSeenAt")
    return pr, sha, seen, thread


def user_said(db, thread, n, seen):
    """Return the snippet of the user's own `approve N` message newer than seen, else raise."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = cos_user_check.latest(db, thread, f"approve {n}", seen)
    except SystemExit:
        raise Cannot("read the message store")
    line = out.getvalue().strip()
    if code:
        raise Stop(f'no verified "approve {n}" from the user since {seen} ({line})')
    return line.split(" ", 3)[3] if line.count(" ") >= 3 else ""


def read_gh(run, pr):
    try:
        login = run([GH, "api", "user", "-q", ".login"]).strip()
        facts = json.loads(run([GH, "pr", "view", pr, "--json", PR_FIELDS]))
    except (merge_pr.CmdError, ValueError) as e:
        raise Cannot(f"read PR #{pr}: {e}")
    return login, facts


def approve(tid, args, run):
    n = str(int(tid.rsplit("-", 1)[1]))
    check_root(run)
    pr, sha, seen, thread = read_state(args.file, tid)
    snippet = user_said(args.db, thread, n, seen)
    try:
        owner = project_config.value("Owner login")
        agents = {l.lower() for r in project_config.ROLE_ROWS if (l := project_config.role_login(r))}
    except SystemExit as e:
        raise Cannot(f"read project.md: {e}")
    if not owner:
        raise Cannot("read the Owner login from project.md")
    login, f = read_gh(run, pr)
    if login.lower() in agents:
        raise Stop(f"gh is signed in as the agent user {login}, not the owner")
    if login.lower() != owner.lower():
        raise Stop(f"gh is signed in as {login}, not the owner")
    if f["state"] != "OPEN":
        raise Stop(f"PR is {'closed' if f['state'] == 'CLOSED' else f['state'].lower()}")
    if f["isDraft"]:
        raise Stop("PR is a draft")
    if f["isCrossRepository"]:
        raise Stop("PR is from a fork")
    if f["baseRefName"] != "main":
        raise Stop(f"base is {f['baseRefName']}, not main")
    if f["headRefOid"] != sha:
        raise Stop(f"head {f['headRefOid']} is not the approved head {sha}")
    if merge_pr.owner_approval({**f, "owner": owner}) is None:
        return f"cos-approve: #{pr} already approved by {owner} at {sha}; nothing posted"
    body = (
        f'Approved from the Chief of Staff thread on the user\'s message "{snippet}" '
        f"for {tid} at head {sha[:7]}. Posted by scripts/cos_approve_pr.py."
    )
    try:
        run([GH, "api", "-X", "POST", f"repos/{{owner}}/{{repo}}/pulls/{pr}/reviews",
             "-f", "event=APPROVE", "-f", f"commit_id={sha}", "-f", f"body={body}"])
    except merge_pr.CmdError as e:
        raise Cannot(f"post the review on #{pr}: {e}")
    return f"cos-approve: approved #{pr} at {sha}"


def main(argv, run=merge_pr.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=cos_user_check.DEFAULT_DB)
    ap.add_argument("--file", type=Path, default=cos_state.DEFAULT_FILE)
    ap.add_argument("ticket")
    try:
        args = ap.parse_args(argv)
        tid = args.ticket if project_config.ticket_re(anchored=True).match(args.ticket) else None
    except SystemExit as e:  # --help, bad arguments, or no usable prefix in project.md
        if e.code == 0:
            return 0
        tid = None
    if not tid:
        print("cos-approve: cannot read arguments; usage: scripts/cos_approve_pr.py [--db PATH] [--file STATE] <PREFIX>-N")
        return 2
    os.environ.pop("AGENT_GH_ROLE", None)  # the review is the owner's, never a role's
    try:
        print(approve(tid, args, run))
        return 0
    except Stop as e:
        print(f"cos-approve: stop {tid}: {e}")
        return 1
    except Cannot as e:
        print(f"cos-approve: cannot {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
