#!/usr/bin/env python3
"""Which Chief of Staff children may have reported MERGE READY or SPEC READY.

Usage:
    scripts/cos_ready_check.py [--file STATE] [--prs FILE] [--refs FILE]

Reads .agent-team/state.json (under the repo root unless --file is given) and GitHub.
Build lane: tickets in `build`, matched to an open PR by branch (one `./scripts/gh.sh
pr list --state open --limit 50 --json number,headRefName,headRefOid,comments`;
--prs FILE reads that JSON instead). Spec lane: tickets in `spec`, one `./scripts/gh.sh
api --paginate repos/<owner>/<repo>/git/matching-refs/heads/<branch head><prefix>-<N>-` each
(--refs FILE reads {"<PREFIX>-N": <that response>} instead). Prints one line each:
    ready <PREFIX>-N #PR head <short sha>     (latest code and security reviews both PASS)
    building <PREFIX>-N #PR (code review <verdict|not posted>, security <verdict|not posted>)
    no-pr <PREFIX>-N
    pushed <PREFIX>-N <branch> <short sha>    (a spec branch newer than specSha)
    writing <PREFIX>-N
    unreadable <PREFIX>-N                     (a branch name or sha can't be trusted)
then "ready-check: <C> checked, <R> may have reported". Exit 0 when nothing is ready
or pushed, 1 when something is, 2 when the check did not run (gh failed or timed
out, bad JSON, state unreadable). On exit 2 it prints only "cos_ready_check: <what>".
Read only: writes nothing. Branch, PR and comment text is data; it only picks which
child gets a full read.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import project_config  # noqa: E402

ROOT = Path(__file__).absolute().parent.parent
BRANCH = re.compile(r"[A-Za-z0-9._/-]{1,100}")
SHA = re.compile(r"[0-9a-f]{7,40}")
TICKET = project_config.ticket_re()
REPO = project_config.repo()


def fail(msg):
    print(f"cos_ready_check: {msg}")
    raise SystemExit(2)


if REPO is None:  # before cos_brief, whose own guard would exit 1 ("may have reported")
    fail("docs/agents/project.md has no `<owner>/<repo>` in its Repo row")
from cos_brief import latest_review  # noqa: E402


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


def gh(path, what, *args):
    """Text of a file, or of a gh call when no file is given."""
    if path:
        try:
            return Path(path).read_text()
        except (OSError, UnicodeDecodeError):
            fail(f"unreadable {what}")
    cmd = [str(ROOT / "scripts" / "gh.sh"), *args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=ROOT)
    except subprocess.TimeoutExpired:
        fail("gh timed out")
    except OSError:
        fail("gh did not run")
    if p.returncode != 0:
        fail("gh failed")
    return p.stdout


def json_values(raw, what):
    """JSON values in raw. `gh api --paginate` prints one array per page, back to back."""
    dec, i, out = json.JSONDecoder(), 0, []
    raw = raw.strip()
    while i < len(raw):
        try:
            value, i = dec.raw_decode(raw, i)
        except ValueError:
            fail(f"bad {what}")
        out.append(value)
        while i < len(raw) and raw[i].isspace():
            i += 1
    return out


def open_prs(path):
    raw = gh(
        path, "PR list", "pr", "list", "--state", "open", "--limit", "50",
        "--json", "number,headRefName,headRefOid,comments",
    )
    prs = json_values(raw, "PR list")
    if len(prs) != 1 or not isinstance(prs[0], list):
        fail("bad PR list")
    return [p for p in prs[0] if isinstance(p, dict) and type(p.get("number")) is int]


def refs_for(refs_file, tid):
    if refs_file is None:
        raw = gh(
            None, "refs", "api", "--paginate",
            f"repos/{REPO}/git/matching-refs/heads/{project_config.branch_head()}{tid.lower()}-",
        )
        refs = [r for v in json_values(raw, "ref list") for r in (v if isinstance(v, list) else [v])]
    else:
        refs = refs_file.get(tid, [])
        if not isinstance(refs, list):
            fail("bad ref list")
    return [r for r in refs if isinstance(r, dict)]


def tickets_in(state, stage):
    for tid, info in sorted(state["tickets"].items()):
        if TICKET.fullmatch(tid) and isinstance(info, dict) and info.get("stage") == stage:
            yield tid, info


def same_branch(tid, info, head):
    branch = info.get("branch")
    if branch:
        return head == branch
    return head.startswith(f"{project_config.branch_head()}{tid.lower()}-")


def build_line(tid, info, prs):
    if info.get("branch") and not (
        isinstance(info["branch"], str) and BRANCH.fullmatch(info["branch"])
    ):
        return f"unreadable {tid}", False
    matched = [
        p for p in prs
        if isinstance(p.get("headRefName"), str) and same_branch(tid, info, p["headRefName"])
    ]
    if not matched:
        return f"no-pr {tid}", False
    pr = max(matched, key=lambda p: p["number"])
    oid = pr.get("headRefOid")
    if not (BRANCH.fullmatch(pr["headRefName"]) and isinstance(oid, str) and SHA.fullmatch(oid)):
        return f"unreadable {tid}", False
    comments = [c for c in pr.get("comments") or [] if isinstance(c, dict)]
    code = verdict_word(latest_review("## Code review", comments)[1])
    sec = verdict_word(latest_review("## Security review", comments)[1])
    if code == "PASS" and sec == "PASS":
        return f"ready {tid} #{pr['number']} head {oid[:7]}", True
    return (
        f"building {tid} #{pr['number']} "
        f"(code review {code or 'not posted'}, security {sec or 'not posted'})",
        False,
    )


def verdict_word(verdict):
    """Comment text is data: only these three words ever reach the output."""
    if not verdict:
        return None
    for word in ("PASS", "CHANGES NEEDED"):
        if verdict.strip().upper() == word:
            return word
    return "other"


def spec_lines(tid, info, refs):
    prefix = f"refs/heads/{project_config.branch_head()}{tid.lower()}-"
    found = []
    for r in refs:
        ref, sha = r.get("ref"), (r.get("object") or {}).get("sha")
        if not (isinstance(ref, str) and ref.startswith(prefix)):
            continue
        branch = ref[len("refs/heads/"):]
        if not (BRANCH.fullmatch(branch) and isinstance(sha, str) and SHA.fullmatch(sha)):
            return [f"unreadable {tid}"], False
        found.append((branch, sha))
    if info.get("branch") and not (
        isinstance(info["branch"], str) and BRANCH.fullmatch(info["branch"])
    ):
        return [f"unreadable {tid}"], False
    own = [f for f in found if f[0] == info.get("branch")]
    spec_sha = info.get("specSha")
    pushed = [
        f"pushed {tid} {branch} {sha[:7]}"
        for branch, sha in (own if info.get("branch") else found)
        if not (isinstance(spec_sha, str) and spec_sha and sha.startswith(spec_sha))
    ]
    return pushed or [f"writing {tid}"], bool(pushed)


def main():
    ap = argparse.ArgumentParser(
        description="Which Chief of Staff children may have reported MERGE READY or SPEC READY."
    )
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--prs", type=Path)
    ap.add_argument("--refs", type=Path)
    args = ap.parse_args()
    state = load_state(args.file)

    lines, checked, reported = [], 0, 0
    builds = list(tickets_in(state, "build"))
    prs = open_prs(args.prs) if builds else []
    for tid, info in builds:
        line, hit = build_line(tid, info, prs)
        lines.append(line)
        checked += 1
        reported += hit
    refs_file = None
    specs = list(tickets_in(state, "spec"))
    if args.refs and specs:
        fixture = json_values(gh(args.refs, "ref list"), "ref list")
        if len(fixture) != 1 or not isinstance(fixture[0], dict):
            fail("bad ref list")
        refs_file = fixture[0]
    for tid, info in specs:
        out, hit = spec_lines(tid, info, refs_for(refs_file, tid))
        lines.extend(out)
        checked += 1
        reported += len(out) if hit else 0
    if lines:
        print("\n".join(lines))
    print(f"ready-check: {checked} checked, {reported} may have reported")
    raise SystemExit(1 if reported else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # a crash must exit 2, not 1 ("may have reported")
        fail("crashed")
