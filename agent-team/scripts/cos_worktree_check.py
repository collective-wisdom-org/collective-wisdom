#!/usr/bin/env python3
"""Would a new worktree on origin/<branch> have everything an old child's worktree has?

Usage:
    scripts/cos_worktree_check.py <PREFIX>-N [--file STATE] [--root DIR] -- <worktree path>

Reads the ticket's `branch` from .agent-team/state.json (under the repo root unless --file is
given) and checks the worktree, in this order: the branch matches <branch head><prefix>-<N>-<words>;
the path is one of `git -C <root> worktree list --porcelain` (compared resolved); HEAD is that
branch; `status --porcelain --untracked-files=all` is empty (ignored files don't count); and
`ls-remote --heads origin refs/heads/<branch>` lists the exact ref `refs/heads/<branch>` (decoys
like `refs/heads/a/refs/heads/<branch>` are skipped) at the same sha as the worktree's HEAD. Prints one line:
    safe <PREFIX>-N <branch> <full sha>
    unsafe <PREFIX>-N: <reason>
Exit 0 safe, 1 unsafe, 2 could not run (one "cos_worktree_check: <what>" line: bad ticket, no state
file, no such ticket, git failed). Read only: no fetch, and --no-optional-locks keeps `status`
from refreshing the index. Branch and sha print only after a pattern check.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_handoff  # noqa: E402
import project_config  # noqa: E402

ROOT = Path(__file__).absolute().parent.parent
SHA = re.compile(r"[0-9a-f]{40}")
# No fsmonitor daemon and no hooks from the worktree's own config.
HARDEN = ("-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null")


def fail(msg):
    print(f"cos_worktree_check: {msg}")
    raise SystemExit(2)


def git(*args, ok=(0,)):
    """(returncode, stdout) of a git command; exits 2 when it can't run or returns a code not in ok."""
    try:
        done = subprocess.run(["git", *HARDEN, *args], capture_output=True, text=True, timeout=30, errors="replace",
                              env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except (OSError, subprocess.SubprocessError):
        fail("git failed")
    if done.returncode not in ok:
        fail("git failed")
    return done.returncode, done.stdout


def check(branch, path, root):
    """(reason, sha): reason is None when safe."""
    _, listing = git("-C", str(root), "worktree", "list", "--porcelain")
    listed = {Path(line[len("worktree "):]).resolve() for line in listing.splitlines() if line.startswith("worktree ")}
    if Path(path).resolve() not in listed:
        return "not a worktree of this repo", None
    code, head = git("-C", path, "symbolic-ref", "--quiet", "--short", "HEAD", ok=(0, 1))
    if code == 1:
        return "detached HEAD", None
    if head.strip() != branch:
        return "on another branch", None
    _, status = git("--no-optional-locks", "-C", path, "status", "--porcelain", "--untracked-files=all")
    if status.strip():
        n = len(status.splitlines())
        return f"uncommitted changes ({n} file{'s' * (n != 1)})", None
    _, local = git("-C", path, "rev-parse", "HEAD")
    _, listed_refs = git("-C", str(root), "ls-remote", "--heads", "origin", f"refs/heads/{branch}")
    # The pattern also matches decoys like refs/heads/a/refs/heads/<branch>: keep the exact ref only.
    exact = [f.split("\t") for f in listed_refs.splitlines()]
    remote = next((f[0] for f in exact if len(f) == 2 and f[1] == f"refs/heads/{branch}"), "")
    local, remote = local.strip(), remote.strip()
    if not SHA.fullmatch(local) or (remote and not SHA.fullmatch(remote)):
        fail("unreadable sha")
    if local != remote:
        return f"not pushed (local {local[:7]}, remote {remote[:7] or 'none'})", None
    return None, local


def main(argv=None):
    ap = argparse.ArgumentParser(description="Is an old child's worktree safe to replace with a new one?")
    ap.add_argument("ticket")
    ap.add_argument("worktree")
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    tid = args.ticket
    if not project_config.ticket_re(anchored=True).fullmatch(tid):
        fail("bad ticket")
    try:
        info = json.loads(args.file.read_text())["tickets"][tid]
        if not isinstance(info, dict):
            raise TypeError
    except FileNotFoundError:
        fail("no state file")
    except KeyError:
        fail(f"no such ticket {tid}")
    except (OSError, UnicodeDecodeError, ValueError, TypeError):
        fail("unreadable state file")
    branch = info.get("branch")
    if not (isinstance(branch, str) and cos_handoff.branch_re(tid).fullmatch(branch)):
        print(f"unsafe {tid}: no branch in state")
        return 1
    reason, sha = check(branch, args.worktree, args.root)
    if reason:
        print(f"unsafe {tid}: {reason}")
        return 1
    print(f"safe {tid} {branch} {sha}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        fail("crashed")
