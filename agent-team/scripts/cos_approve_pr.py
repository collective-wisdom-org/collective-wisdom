#!/usr/bin/env python3
"""Verify the user's own "approve N" in the Chief of Staff thread before a merge approval is relayed.

Usage:
    scripts/cos_approve_pr.py <PREFIX>-N

The only argument is the ticket ID: the caller cannot pick the message store or the state file. The PR, its head, the thread, the cut-off time and the words
(`approve <N>`) come from the state file and T3's message store. Run it from the root checkout, signed in to gh as the
Owner login. It writes nothing: exit 0 is the proof the Chief of Staff needs before it relays the merge approval.

Gates, in order; the first failure stops: root checkout, state, the user's message (scripts/cos_user_check.py latest),
gh login, PR facts, head.

Exit 0: verified. Last line: cos-approve: verified approve N for #N at <SHA> (user wrote: "<snippet>")
  The snippet is the start of the user's message on one line (80 characters at most), so the Chief of Staff can show the user what was verified.
Exit 1: a gate failed. Last line: cos-approve: stop <PREFIX>-N: <reason>
Exit 2: bad arguments, or state, the message store or gh failed, or one of them had an unexpected shape.
Last line: cos-approve: cannot <what>
"""

import argparse
import contextlib
import importlib.util
import io
import json
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
PR_FIELDS = "state,isDraft,baseRefName,isCrossRepository,headRefOid"


class Stop(Exception):
    """A gate failed: exit 1."""


class Cannot(Exception):
    """A read failed: exit 2."""


def check_root(run):
    try:
        out = run(["git", "-C", str(ROOT), "worktree", "list", "--porcelain"])
    except merge_pr.CmdError as e:
        raise Cannot(f"list worktrees: {e}")
    first = out.strip().split("\n\n")[0].splitlines()[0].removeprefix("worktree ")
    if ROOT.resolve() != Path(first).resolve():
        raise Stop(f"not run from the root checkout; cd {first} first, its project.md is the one to trust")


def read_state(tid):
    try:
        state = cos_state.load(cos_state.DEFAULT_FILE)
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


def approve(tid, run):
    n = str(int(tid.rsplit("-", 1)[1]))
    check_root(run)
    pr, sha, seen, thread = read_state(tid)
    snippet = user_said(cos_user_check.DEFAULT_DB, thread, n, seen)
    owner = project_config.value("Owner login")
    if not owner:
        raise Cannot("read the Owner login from project.md")
    login, f = read_gh(run, pr)
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
    return f'cos-approve: verified approve {n} for #{pr} at {sha} (user wrote: "{snippet}")'


def main(argv, run=merge_pr.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticket")
    try:
        args = ap.parse_args(argv)
        tid = args.ticket if project_config.ticket_re(anchored=True).match(args.ticket) else None
    except SystemExit as e:  # --help, bad arguments, or no usable prefix in project.md
        if e.code == 0:
            return 0
        tid = None
    if not tid:
        print("cos-approve: cannot read arguments; usage: scripts/cos_approve_pr.py <PREFIX>-N")
        return 2
    try:
        print(approve(tid, run))
        return 0
    except Stop as e:
        print(f"cos-approve: stop {tid}: {e}")
        return 1
    except Cannot as e:
        print(f"cos-approve: cannot {e}")
        return 2
    except (KeyError, TypeError, AttributeError, ValueError) as e:  # an unexpected shape in state or gh output
        print(f"cos-approve: cannot read the state file or PR facts: {type(e).__name__}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
