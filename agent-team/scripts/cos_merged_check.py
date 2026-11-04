#!/usr/bin/env python3
"""Which Chief of Staff tickets waiting on a merge have already merged on GitHub.

Usage:
    scripts/cos_merged_check.py [--file STATE] [--prs FILE] [--apply]

Reads .agent-team/state.json (under the repo root unless --file is given) and the
last 20 merged PRs from `./scripts/gh.sh pr list --state merged --limit 20 --json
number,headRefName,mergedAt` (--prs FILE reads that JSON from a file instead).
Candidates are tickets in merge, merge-queued or awaiting-merge, and blocked
tickets whose resumeStage is merge, that have an integer pr. Prints one line each:
    merged GORP-N #PR at <mergedAt>
    mismatch GORP-N #PR head <headRefName>   (PR merged, branch is not the ticket's)
    open GORP-N #PR                          (not in the merged list)
    unreadable GORP-N #PR                    (the PR's branch or time can't be trusted)
then "merged-check: <C> checked, <M> merged". --apply writes a merged op for each
merged line, in one cos_state.apply_file call. Exit 0 when nothing merged, 1 when
at least one ticket merged, 2 when the check did not run (gh failed or timed out,
bad JSON, state unreadable). On exit 2 nothing is written.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import cos_state  # noqa: E402
import project_config  # noqa: E402

ROOT = root()
WAITING = ("merge", "merge-queued", "awaiting-merge")
BRANCH = re.compile(r"[A-Za-z0-9._/-]{1,100}")
TICKET = project_config.ticket_re()


def fail(msg):
    print(f"cos_merged_check: {msg}")
    raise SystemExit(2)


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
    if path:
        try:
            raw = Path(path).read_text()
        except (OSError, UnicodeDecodeError):
            fail("unreadable PR list")
    else:
        cmd = [
            str(Path(__file__).absolute().parent / "gh.sh"), "pr", "list", "--state", "merged",
            "--limit", "20", "--json", "number,headRefName,mergedAt",
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=ROOT)
        except subprocess.TimeoutExpired:
            fail("gh timed out")
        except OSError:
            fail("gh did not run")
        if p.returncode != 0:
            fail("gh failed")
        raw = p.stdout
    try:
        prs = json.loads(raw)
    except ValueError:
        fail("bad PR list")
    if not isinstance(prs, list):
        fail("bad PR list")
    return {
        p["number"]: p
        for p in prs
        if isinstance(p, dict) and type(p.get("number")) is int
    }


def readable(pr):
    head, at = pr.get("headRefName"), pr.get("mergedAt")
    if not (isinstance(head, str) and BRANCH.fullmatch(head) and isinstance(at, str)):
        return False
    try:
        datetime.fromisoformat(at.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def candidates(state):
    for tid, info in sorted(state["tickets"].items()):
        if not TICKET.fullmatch(tid) or not isinstance(info, dict) or type(info.get("pr")) is not int:
            continue
        stage = info.get("stage")
        if stage in WAITING or (stage == "blocked" and info.get("resumeStage") == "merge"):
            yield tid, info


def same_branch(tid, info, head):
    branch = info.get("branch")
    if branch:
        return head == branch
    return head.startswith(f"{project_config.branch_head()}{tid.lower()}-")


def run(state_file, prs_file=None, apply=False):
    """(lines, merged): merged is [(ticket, pr)]. Calls fail() (exit 2) when the check can't run;
    nothing is written then."""
    state = load_state(state_file)
    prs = load_prs(prs_file)

    lines, ops = [], []
    for tid, info in candidates(state):
        n = info["pr"]
        pr = prs.get(n)
        if pr is None:
            lines.append(f"open {tid} #{n}")
        elif not readable(pr):
            lines.append(f"unreadable {tid} #{n}")
        elif not same_branch(tid, info, pr["headRefName"]):
            lines.append(f"mismatch {tid} #{n} head {pr['headRefName']}")
        else:
            lines.append(f"merged {tid} #{n} at {pr['mergedAt']}")
            ops.append({"op": "merged", "ticket": tid, "pr": n})
    # Lines are returned only once the write has happened, so a failed write never reads as success.
    try:
        failed = ops and apply and cos_state.apply_file(state_file, ops) != 0
    except Exception:  # a crash must exit 2, not 1 ("merged")
        failed = True
    if failed:
        fail("could not write state")
    lines.append(f"merged-check: {len(lines)} checked, {len(ops)} merged")
    return lines, [(op["ticket"], op["pr"]) for op in ops]


def main():
    ap = argparse.ArgumentParser(
        description="Which Chief of Staff tickets waiting on a merge have merged."
    )
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--prs", type=Path)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    lines, merged = run(args.file, args.prs, args.apply)
    print("\n".join(lines))
    raise SystemExit(1 if merged else 0)


if __name__ == "__main__":
    main()
