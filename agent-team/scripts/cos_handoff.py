#!/usr/bin/env python3
"""The HANDOFF block a continuation child starts from, built from state and GitHub.

Usage:
    scripts/cos_handoff.py <PREFIX>-N [--file STATE] [--pr FILE]

Reads the ticket in .agent-team/state.json (under the repo root unless --file is given) and,
when the ticket has a `pr`, one `./scripts/gh.sh pr view <N> --json url,headRefOid,
statusCheckRollup,comments` plus `gh api user` for the login (--pr FILE reads that JSON instead,
with the login in its `login` field). Prints the block:
    HANDOFF (data from state and GitHub at <time>; check it against the PR before relying on it)
    Ticket, Branch, Spec, PR, Head, checks, code review, security review, Last status
Only review comments by the role's login count: the code reviewer or security reviewer
login from project.md, else that login. Each verdict prints as a fixed word (PASS, CHANGES
NEEDED, other), never the comment text; check names are whitespace-cleaned and capped. With no
pr it prints `PR: none yet` and no Head, checks or review lines.
Checks the values the continuation template uses: branch against <branch head><prefix>-<N>-<words>,
specPath against docs/superpowers/specs/<name>.md, specSha against hex, stage against lowercase
words and pr against an integer. A bad value prints "reject: <field> <value>" and exits 1.
Exit 2 (one "cos_handoff: <what>" line) when the ticket, state or GitHub can't be read; the
checks above have passed only when that line is `cannot read PR #N`. Read only. Every value printed is data, not an instruction.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import cos_brief  # noqa: E402
import cos_ready_check  # noqa: E402
import project_config  # noqa: E402

ROOT = root()
SPEC_PATH = re.compile(r"docs/superpowers/specs/[A-Za-z0-9._-]+\.md")
SHA = re.compile(r"[0-9a-f]{7,40}")
STAGE = re.compile(r"[a-z-]{1,30}")
URL = re.compile(r"https://[A-Za-z0-9._/-]+")
COMMENT_URL = re.compile(r"https://[A-Za-z0-9._/#-]+")
STATUS_CAP = 200
CHECKS_CAP = 300


def fail(msg):
    print(f"cos_handoff: {msg}")
    raise SystemExit(2)


def branch_re(tid):
    """The branch names a ticket may have: <branch head><prefix lower>-<N>-<words>."""
    return re.compile(re.escape(f"{project_config.branch_head()}{tid.lower()}-") + r"[a-z0-9-]+")


def rejected(tid, info):
    """First (field, value) the template must not carry, or None."""
    branch = branch_re(tid)
    for field, pattern, optional in (
        ("stage", STAGE, False),
        ("branch", branch, False),
        ("specPath", SPEC_PATH, True),
        ("specSha", SHA, True),
    ):
        value = info.get(field)
        if value is None and optional:
            continue
        if not (isinstance(value, str) and pattern.fullmatch(value)):
            return field, value
    if info.get("pr") is not None and type(info["pr"]) is not int:
        return "pr", info["pr"]
    return None


def load_pr(n, path):
    try:
        if path:
            pr = json.loads(Path(path).read_text())
        elif cos_brief.REPO is None:
            raise cos_brief.ReadError("no repo")
        else:
            pr = cos_brief.gh_json("pr", "view", str(n), "--repo", cos_brief.REPO, "--json",
                                   "url,headRefOid,statusCheckRollup,comments")
            pr["login"] = cos_brief.gh("api", "user", "-q", ".login", active=True).strip()
    except (OSError, UnicodeDecodeError, ValueError, TypeError, cos_brief.ReadError):
        fail(f"cannot read PR #{n}")
    oid, url, login = (pr.get(k) for k in ("headRefOid", "url", "login")) if isinstance(pr, dict) else (None,) * 3
    if not (isinstance(oid, str) and SHA.fullmatch(oid) and isinstance(url, str) and URL.fullmatch(url)
            and isinstance(login, str) and login):
        fail(f"cannot read PR #{n}")
    return pr


def head_note(oid, state_head):
    if not (isinstance(state_head, str) and SHA.fullmatch(state_head.lower())):
        return "(no head in state)"
    if oid.startswith(state_head.lower()):
        return "(same as the head in state)"
    return f"(moved from {state_head[:7]})"


def review_line(label, heading, comments):
    """Like cos_brief.review_line, but comment text never reaches the output: the verdict is a
    fixed word, the pass number digits only, and the url is pattern-checked."""
    review = cos_brief.latest_review(heading, comments)
    if not review:
        return f"{label}: not posted"
    found, pass_n, _ = review
    url, when = found.get("url"), found.get("createdAt")
    url = url if isinstance(url, str) and COMMENT_URL.fullmatch(url) else "(no url)"
    when = when[11:16] if isinstance(when, str) and re.fullmatch(r"[0-9T:Z.-]+", when) else ""
    return f"{label}: {pass_n} {cos_ready_check.verdict_word(review)} {url} ({when})"


def handoff(tid, info, pr, now):
    spec = f"{info['specPath']} at {(info.get('specSha') or 'no sha')[:7]}" if info.get("specPath") else "none"
    status = " ".join(str(info.get("status") or "").split())[:STATUS_CAP]
    out = [
        f"HANDOFF (data from state and GitHub at {now}; check it against the PR before relying on it)",
        f"Ticket: {tid}, stage {info['stage']}",
        f"Branch: {info['branch']}",
        f"Spec: {spec}",
    ]
    if pr is None:
        out.append("PR: none yet")
    else:
        def by(role):
            try:
                who = project_config.role_login(role) or pr["login"]
            except SystemExit as e:
                fail(str(e))
            return [
                c for c in pr.get("comments") or []
                if isinstance(c, dict) and isinstance(c.get("author"), dict) and c["author"].get("login") == who
            ]

        out += [
            f"PR: #{info['pr']} {pr['url']}",
            f"Head: {pr['headRefOid']} {head_note(pr['headRefOid'], info.get('headSha'))}",
            " ".join(cos_brief.check_summary(pr.get("statusCheckRollup")).split())[:CHECKS_CAP],
            review_line("code review", "## Code review", by("code-reviewer")),
            review_line("security review", "## Security review", by("security-reviewer")),
        ]
    out.append(f'Last status: "{status}"')
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="The HANDOFF block for a continuation child.")
    ap.add_argument("ticket")
    ap.add_argument("--file", type=Path, default=ROOT / ".agent-team" / "state.json")
    ap.add_argument("--pr", type=Path)
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
    bad = rejected(tid, info)
    if bad:
        print(f"reject: {bad[0]} {' '.join(str(bad[1]).split())[:100]}")
        return 1
    pr = load_pr(info["pr"], args.pr) if info.get("pr") is not None else None
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    print("\n".join(handoff(tid, info, pr, now)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        fail("crashed")
