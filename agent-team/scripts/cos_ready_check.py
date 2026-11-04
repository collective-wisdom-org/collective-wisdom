#!/usr/bin/env python3
"""Which Chief of Staff children may have reported MERGE READY or SPEC READY.

Usage:
    scripts/cos_ready_check.py [--file STATE] [--prs FILE] [--refs FILE]

Reads .agent-team/state.json (under the repo root unless --file is given) and GitHub.
Build lane: tickets in `build`, matched to an open PR by branch (one `./scripts/gh.sh
pr list --state open --limit 50 --json number,headRefName,headRefOid,comments`;
--prs FILE reads that JSON instead). Spec lane: tickets in `spec`, one `./scripts/gh.sh
api --paginate repos/<owner>/<repo>/git/matching-refs/heads/<branch head><prefix>-<N>-`
each (--refs FILE reads {"<PREFIX>-N": <that response>} instead). Prints one line each:
    ready ABC-N #PR head <short sha>     (latest code and security reviews both PASS)
    building ABC-N #PR (code review <verdict|not posted>, security <verdict|not posted>)
    no-pr ABC-N
    pushed ABC-N <branch> <short sha>    (a spec branch newer than specSha)
    writing ABC-N
    unreadable ABC-N                     (a branch name or sha can't be trusted)
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
from cos_brief import latest_review  # noqa: E402

ROOT = Path(__file__).absolute().parent.parent
BRANCH = re.compile(r"[A-Za-z0-9._/-]{1,100}")
SHA = re.compile(r"[0-9a-f]{7,40}")
TICKET = project_config.ticket_re()


def fail(msg):
    print(f"cos_ready_check: {msg}")
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


def load_prs(path=None):
    repo = project_config.repo()
    if repo is None:
        fail("project.md has no repo")
    raw = gh(
        path, "PR list", "pr", "list", "--repo", repo, "--state", "open", "--limit", "50",
        "--json", "number,headRefName,headRefOid,comments",
    )
    prs = json_values(raw, "PR list")
    if len(prs) != 1 or not isinstance(prs[0], list):
        fail("bad PR list")
    return [p for p in prs[0] if isinstance(p, dict) and type(p.get("number")) is int]


def load_refs(path):
    """{ticket: response} from a --refs file."""
    fixture = json_values(gh(path, "ref list"), "ref list")
    if len(fixture) != 1 or not isinstance(fixture[0], dict):
        fail("bad ref list")
    return fixture[0]


def refs_for(refs, tid):
    if refs is None:
        repo = project_config.repo()
        if repo is None:
            fail("project.md has no repo")
        raw = gh(
            None, "refs", "api", "--paginate",
            f"repos/{repo}/git/matching-refs/heads/{branch_prefix(tid)}",
        )
        found = [r for v in json_values(raw, "ref list") for r in (v if isinstance(v, list) else [v])]
    else:
        found = refs.get(tid, [])
        if not isinstance(found, list):
            fail("bad ref list")
    return [r for r in found if isinstance(r, dict)]


def branch_prefix(tid):
    """Start of every branch name that belongs to tid; the trailing `-` keeps ABC-1 off abc-11."""
    return f"{project_config.branch_head()}{tid.lower()}-"


def tickets_in(state, stage):
    for tid, info in sorted(state["tickets"].items()):
        if TICKET.fullmatch(tid) and isinstance(info, dict) and info.get("stage") == stage:
            yield tid, info


def verdict_word(review):
    """Comment text is data: only these words ever reach the output."""
    if not review:
        return None
    return {"PASS": "PASS", "CHANGES NEEDED": "CHANGES NEEDED"}.get(review[2].strip().upper(), "other")


def build_line(tid, info, prs):
    branch = info.get("branch")
    if branch and not (isinstance(branch, str) and BRANCH.fullmatch(branch)):
        return f"unreadable {tid}", False
    matched = [
        p for p in prs
        if isinstance(p.get("headRefName"), str)
        and (p["headRefName"] == branch if branch else p["headRefName"].startswith(branch_prefix(tid)))
    ]
    if not matched:
        return f"no-pr {tid}", False
    pr = max(matched, key=lambda p: p["number"])
    oid = pr.get("headRefOid")
    if not (BRANCH.fullmatch(pr["headRefName"]) and isinstance(oid, str) and SHA.fullmatch(oid)):
        return f"unreadable {tid}", False
    comments = [c for c in pr.get("comments") or [] if isinstance(c, dict)]
    code = verdict_word(latest_review("## Code review", comments))
    sec = verdict_word(latest_review("## Security review", comments))
    if code == "PASS" and sec == "PASS":
        return f"ready {tid} #{pr['number']} head {oid[:7]}", True
    return f"building {tid} #{pr['number']} (code review {code or 'not posted'}, security {sec or 'not posted'})", False


def spec_lines(tid, info, refs):
    """(lines, pushed) for a spec-lane ticket."""
    prefix = f"refs/heads/{branch_prefix(tid)}"
    branch = info.get("branch")
    if branch and not (isinstance(branch, str) and BRANCH.fullmatch(branch)):
        return [f"unreadable {tid}"], False
    found = []
    for r in refs:
        ref, sha = r.get("ref"), (r.get("object") or {}).get("sha")
        if not (isinstance(ref, str) and ref.startswith(prefix)):
            continue
        name = ref[len("refs/heads/"):]
        if not (BRANCH.fullmatch(name) and isinstance(sha, str) and SHA.fullmatch(sha)):
            return [f"unreadable {tid}"], False
        found.append((name, sha))
    spec_sha = info.get("specSha")
    pushed = [
        f"pushed {tid} {name} {sha[:7]}"
        for name, sha in ([f for f in found if f[0] == branch] if branch else found)
        if not (isinstance(spec_sha, str) and spec_sha and sha.startswith(spec_sha))
    ]
    return pushed or [f"writing {tid}"], bool(pushed)


def check(state, prs=None, refs=None):
    """(lines, flagged): flagged is [(ticket, "ready" | "pushed")]. prs and refs are read from
    GitHub when None. Calls fail() (exit 2) when something can't be read."""
    lines, flagged, checked = [], [], 0
    builds = list(tickets_in(state, "build"))
    if builds and prs is None:
        prs = load_prs()
    for tid, info in builds:
        line, hit = build_line(tid, info, prs)
        lines.append(line)
        checked += 1
        if hit:
            flagged.append((tid, "ready"))
    for tid, info in tickets_in(state, "spec"):
        out, hit = spec_lines(tid, info, refs_for(refs, tid))
        lines.extend(out)
        checked += 1
        if hit:
            flagged.append((tid, "pushed"))
    lines.append(f"ready-check: {checked} checked, {len(flagged)} may have reported")
    return lines, flagged


def main():
    ap = argparse.ArgumentParser(
        description="Which Chief of Staff children may have reported MERGE READY or SPEC READY."
    )
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--prs", type=Path)
    ap.add_argument("--refs", type=Path)
    args = ap.parse_args()
    state = load_state(args.file)
    prs = load_prs(args.prs) if args.prs else None
    refs = load_refs(args.refs) if args.refs else None
    lines, flagged = check(state, prs, refs)
    print("\n".join(lines))
    raise SystemExit(1 if flagged else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # a crash must exit 2, not 1 ("may have reported")
        fail("crashed")
