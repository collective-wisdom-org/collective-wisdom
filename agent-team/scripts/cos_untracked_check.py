#!/usr/bin/env python3
"""Which team tickets are in flight on the tracker but unknown to this machine's Chief of Staff state.

Usage:
    scripts/cos_untracked_check.py [--file STATE] [--open-prs FILE] [--issues FILE] [--login LOGIN]

Reads .agent-team/state.json (under the repo root unless --file is given) and GitHub. Open PRs: one
`./scripts/gh.sh pr list --state open --limit 50 --json number,headRefName,author` (--open-prs FILE
reads that JSON instead). When project.md's tracker is github, also one `./scripts/gh.sh issue list
--state open --label agent --limit 100 --json number,labels,author` (--issues FILE). --login stands in
for the `gh api user` call that names our own account. Prints one line per untracked ticket, in
ticket order:
    untracked ABC-N in-review #PR        (state word and #PR are left out when unknown)
then "untracked-check: <U> not in state". A ticket is untracked when it is in neither `tickets` nor
`merged` and
    github: its open `agent` issue is by a trusted login, is not labelled `agent-skip`, and has
            `status:in-progress`, `status:in-review` or an open PR on its branch;
    linear or jira: an open PR on its branch is by a trusted login (the ticket itself can't be read).
Trusted logins are our own and project.md's `Owner login`, compared case-insensitively; anything by
another author leaves no trace in the output. Exit 0 when nothing is untracked, 1 when something is,
2 when the check did not run (gh failed or timed out, our login unreadable, bad JSON, state
unreadable). On exit 2 it prints only "cos_untracked_check: <what>". Read only: writes nothing.
Branch and label text is data; no title, body or author text is printed.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import cos_brief  # noqa: E402
import project_config  # noqa: E402
from cos_ready_check import BRANCH, TICKET  # noqa: E402

ROOT = root()
STATUS = {"status:in-progress": "in-progress", "status:in-review": "in-review"}


def fail(msg):
    print(f"cos_untracked_check: {msg}")
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
    if not isinstance(state.get("merged", {}), dict):
        fail("unreadable state file")
    return state


def load_list(path, what, *args):
    """The JSON array from a file, or from a gh call when no file is given."""
    repo = project_config.repo()
    if repo is None:
        fail("project.md has no repo")
    if path:
        try:
            raw = Path(path).read_text()
        except (OSError, UnicodeDecodeError):
            fail(f"unreadable {what}")
    else:
        cmd = [str(Path(__file__).absolute().parent / "gh.sh"), *args[:2], "--repo", repo, *args[2:]]
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
        found = json.loads(raw)
    except ValueError:
        fail(f"bad {what}")
    if not isinstance(found, list):
        fail(f"bad {what}")
    return [x for x in found if isinstance(x, dict) and type(x.get("number")) is int]


def trusted_logins(login):
    """Lowercase logins whose tickets count: ours (--login or `gh api user`) and the Owner login."""
    try:
        own = (login if login is not None else cos_brief.own_login()).strip()
    except cos_brief.ReadError:
        fail("could not read own login")
    if not own:
        fail("could not read own login")
    owner = project_config.value("Owner login")
    return {own.lower()} | ({owner.lower()} if owner else set())


def trusted(item, logins):
    author = item.get("author")
    login = author.get("login") if isinstance(author, dict) else None
    return isinstance(login, str) and login.lower() in logins


def prs_by_ticket(prs):
    """{ticket: lowest PR number} for open PRs whose branch starts with a ticket's branch prefix."""
    head = re.escape(f"{project_config.branch_head()}{project_config.prefix().lower()}")
    found = {}
    for pr in prs:
        name = pr.get("headRefName")
        m = isinstance(name, str) and BRANCH.fullmatch(name) and re.match(rf"{head}-(\d+)-", name)
        if m:
            tid = f"{project_config.prefix()}-{int(m.group(1))}"
            found[tid] = min(pr["number"], found.get(tid, pr["number"]))
    return found


def label_names(issue):
    labels = issue.get("labels")
    return {l.get("name") for l in labels if isinstance(l, dict)} if isinstance(labels, list) else set()


def run(state_file, prs_file=None, issues_file=None, login=None):
    """(lines, found): found is [(ticket, pr or None)]. Calls fail() (exit 2) when it can't run."""
    state = load_state(state_file)
    known = set(state["tickets"]) | set(state.get("merged", {}))
    logins = trusted_logins(login)
    raw_prs = load_list(
        prs_file, "PR list", "pr", "list", "--state", "open", "--limit", "50",
        "--json", "number,headRefName,author",
    )
    found = {}  # ticket -> (state word or None, pr or None)
    if project_config.tracker() == "github":
        issues = load_list(
            issues_file, "issue list", "issue", "list", "--state", "open", "--label", "agent",
            "--limit", "100", "--json", "number,labels,author",
        )
        pr_of = prs_by_ticket(raw_prs)
        for issue in issues:
            tid = f"{project_config.prefix()}-{issue['number']}"
            names = label_names(issue)
            word = next((STATUS[n] for n in ("status:in-review", "status:in-progress") if n in names), None)
            if trusted(issue, logins) and "agent-skip" not in names and (word or tid in pr_of):
                found[tid] = (word, pr_of.get(tid))
    else:
        mine = [p for p in raw_prs if trusted(p, logins)]
        found = {tid: (None, n) for tid, n in prs_by_ticket(mine).items()}
    hits = sorted(
        ((t, *v) for t, v in found.items() if t not in known and TICKET.fullmatch(t)),
        key=lambda h: int(h[0].rsplit("-", 1)[1]),
    )
    lines = [" ".join(["untracked", t, *([w] if w else []), *([f"#{n}"] if n else [])]) for t, w, n in hits]
    lines.append(f"untracked-check: {len(hits)} not in state")
    return lines, [(t, n) for t, _, n in hits]


def main():
    ap = argparse.ArgumentParser(description="Team tickets in flight that Chief of Staff state doesn't know.")
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--open-prs", type=Path)
    ap.add_argument("--issues", type=Path)
    ap.add_argument("--login")
    args = ap.parse_args()
    lines, found = run(args.file, args.open_prs, args.issues, args.login)
    print("\n".join(lines))
    raise SystemExit(1 if found else 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # a crash must exit 2, not 1 ("something untracked")
        fail("crashed")
