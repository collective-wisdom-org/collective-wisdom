#!/usr/bin/env python3
"""Approval inputs for the Chief of Staff, read from GitHub in one call each.

Usage:
    scripts/cos_brief.py spec <path> <sha> [--branch B]
    scripts/cos_brief.py pr <N> [--head SHA]

spec prints the spec's title, a blob link, its Goals, Non-goals and Calls I made
sections (each capped at 40 lines) and the headings of its Design sections. The
link uses --branch, or the commit when it is not given.
pr prints the title, url, head SHA (checked against --head), check counts, the
latest code review and security review verdicts, a line when a `Head moved to` note
names the head, file areas, flag lines and the migration number check. The PR body
is not printed.

Read only: calls ./scripts/gh.sh with GET requests against the repo in docs/agents/project.md.
Exits 2 with a one-line "cos_brief: ..." message when a read fails.
"""

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_config  # noqa: E402

REPO = project_config.repo()  # <owner>/<repo> from docs/agents/project.md
if REPO is None:
    raise SystemExit("cos_brief: docs/agents/project.md has no `<owner>/<repo>` in its Repo row")
GH = str(Path(__file__).resolve().parent / "gh.sh")
SECTIONS = ("Goals", "Non-goals", "Calls I made")
SECTION_CAP = 40
FLAG_CAP = 10
MIGRATIONS_DIR = project_config.migrations_dir()  # None when project.md says the repo has none
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
MOVED_RE = re.compile(r"Head moved to ([0-9a-f]{40})\b.*?unchanged since ([0-9a-f]{40})", re.I | re.S)
PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
REF_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

# Path words that mark what the approval block must name. A word matches a whole
# token of the path (split on anything not a letter or digit), plural or not.
FLAG_WORDS = {
    "auth": "auth",
    "email": "user email",
    "mail": "user email",
    "price": "money",
    "currency": "money",
    "money": "money",
    "billing": "money",
    "plan": "money",
    "entitlement": "money",
}

FAIL = {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE", "ERROR", "STALE"}
SKIP = {"SKIPPED", "NEUTRAL"}


class ReadError(Exception):
    pass


def die(msg):
    print(f"cos_brief: {msg}")
    sys.exit(2)


def gh(*args):
    """Run gh.sh, return stdout. Raises ReadError on any failure."""
    try:
        r = subprocess.run([GH, *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ReadError(str(e))
    if r.returncode != 0:
        raise ReadError(r.stderr.strip() or f"gh exited {r.returncode}")
    return r.stdout


def gh_json(*args):
    try:
        return json.loads(gh(*args))
    except json.JSONDecodeError as e:
        raise ReadError(str(e))


# --- spec -------------------------------------------------------------------


def parse_spec(text):
    """Return (title, {section name: [lines]}, [design headings])."""
    title = None
    sections = {}
    design = []
    current = None  # name of the ## section being read
    in_design = False
    fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        elif not fence:
            if line.startswith("# ") and title is None:
                title = line[2:].strip()
                continue
            if line.startswith("## "):
                name = line[3:].strip()
                in_design = name == "Design"
                current = name if name in SECTIONS and name not in sections else None
                if current:
                    sections[current] = []
                continue
            if in_design and line.startswith("### "):
                design.append(line.strip())
        if current:
            sections[current].append(line)
    return title, sections, design


def section_text(lines):
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    out = lines[:SECTION_CAP]
    if len(lines) > SECTION_CAP:
        out.append(f"({len(lines) - SECTION_CAP} more lines)")
    return "\n".join(out)


def cmd_spec(args):
    path, sha = args.path, args.sha
    if not (PATH_RE.match(path) and ".." not in path and SHA_RE.match(sha)):
        die(f"spec not found at {sha}")
    branch = args.branch
    if branch is not None and not REF_RE.match(branch):
        die(f"bad branch {branch!r}")
    try:
        data = gh_json("api", f"repos/{REPO}/contents/{path}?ref={sha}")
        if not isinstance(data, dict) or data.get("encoding") != "base64":
            raise ReadError("not a file")
        text = base64.b64decode(data["content"]).decode("utf-8")
    except (ReadError, ValueError, KeyError):
        die(f"spec not found at {sha}")
    title, sections, design = parse_spec(text)
    out = [
        f"spec {path} @ {sha[:7]}",
        f"title: {title or '(missing)'}",
        f"link: https://github.com/{REPO}/blob/{branch or sha}/{path}",
    ]
    for name in SECTIONS:
        out.append(f"## {name}")
        body = section_text(sections[name]) if name in sections else ""
        out.append(body if body else "(missing)")
    out.append("design: " + ("; ".join(design) if design else "(none)"))
    print("\n".join(out))


# --- pr ---------------------------------------------------------------------


def check_summary(rollup):
    counts = {"pass": 0, "fail": 0, "pending": 0, "skipped": 0}
    skipped = []
    for c in rollup or []:
        name = c.get("name") or c.get("context") or "?"
        if c.get("__typename") == "StatusContext":
            state = (c.get("state") or "").upper()
            done, result = state not in ("PENDING", "EXPECTED", ""), state
        else:
            done = (c.get("status") or "").upper() == "COMPLETED"
            result = (c.get("conclusion") or "").upper()
        if not done:
            counts["pending"] += 1
        elif result in SKIP:
            counts["skipped"] += 1
            skipped.append(name)
        elif result in FAIL:
            counts["fail"] += 1
        else:
            counts["pass"] += 1
    line = "checks: {pass} pass, {fail} fail, {pending} pending, {skipped} skipped".format(**counts)
    if skipped:
        line += " (skipped: " + ", ".join(skipped) + ")"
    return line


def review_line(label, heading, comments):
    """Latest comment whose body starts with `heading`."""
    found = None
    for c in comments:
        if (c.get("body") or "").startswith(heading):
            found = c  # comments come oldest first; keep the last
    if not found:
        return f"{label}: not posted"
    body = found["body"]
    m = re.match(r"## \w+ review \(pass (\d+)\)", body.splitlines()[0])
    pass_n = f"pass {m.group(1)}" if m else "pass ?"
    verdicts = re.findall(r"^\W*Verdict:\W*(.+?)\W*$", body, re.MULTILINE)
    verdict = verdicts[-1] if verdicts else "(no verdict)"
    when = (found.get("createdAt") or "")[11:16]
    return f"{label}: {pass_n} {verdict} {found.get('url', '')} ({when})"


def moved_line(oid, comments, login):
    """Line for the latest `Head moved to` note when it names the current head."""
    found = None
    for c in comments:
        if (c.get("body") or "").startswith("Head moved to ") and (c.get("author") or {}).get("login") == login:
            found = c
    m = found and MOVED_RE.match(found["body"])
    if not m or not oid.startswith(m.group(1).lower()):
        return None
    return f"head moved by merging main since {m.group(2)[:7].lower()}; reviews stand {found.get('url', '')}"


def flags_for(paths):
    flags = []
    for p in sorted(paths, key=lambda p: ("/tests/" in p or p.startswith("docs/"), p)):
        if p.startswith("docs/"):
            continue
        labels = []
        if MIGRATIONS_DIR and p.startswith(MIGRATIONS_DIR + "/"):
            labels.append("migration")
        for tok in re.split(r"[^a-z0-9]+", p.lower()):
            label = FLAG_WORDS.get(tok) or FLAG_WORDS.get(tok.rstrip("s"))
            if label and label not in labels:
                labels.append(label)
        if labels:
            flags.append(f"flag: {p} ({', '.join(labels)})")
    if len(flags) > FLAG_CAP:
        extra = len(flags) - (FLAG_CAP - 1)
        flags = flags[: FLAG_CAP - 1] + [f"flag: ... {extra} more"]
    return flags


def migration_numbers(paths):
    nums = set()
    if not MIGRATIONS_DIR:
        return []
    for p in paths:
        m = re.match(re.escape(MIGRATIONS_DIR) + r"/(\d+)_[^/]*\.py$", p)
        if m:
            nums.add(m.group(1))
    return sorted(nums)


def migrations_line(n, nums):
    if not nums:
        return "migrations: none"
    try:
        others = gh_json("pr", "list", "--repo", REPO, "--state", "open", "--limit", "100",
                         "--json", "number,files")
        main_files = gh_json("api", f"repos/{REPO}/contents/{MIGRATIONS_DIR}?ref=main")
    except ReadError:
        die(f"cannot read PR #{n}")
    clashes = []
    for o in others:
        if o.get("number") == n:
            continue
        theirs = set(migration_numbers([f["path"] for f in o.get("files", [])]))
        for num in nums:
            if num in theirs:
                clashes.append(f"#{o['number']} also adds {num}")
    on_main = [int(m.group(1)) for f in main_files
               if (m := re.match(r"(\d+)_", f.get("name", "")))]
    highest = max(on_main) if on_main else None
    low = [num for num in nums if highest is not None and int(num) <= highest]
    line = f"migrations: {', '.join(nums)}; open PRs: " + ("; ".join(clashes) if clashes else "none")
    line += f"; main highest: {highest:03d}" if highest is not None else "; main highest: ?"
    if low:
        line += f" (AT OR BELOW: {', '.join(low)})"
    return line


def cmd_pr(args):
    n = args.number
    try:
        pr = gh_json("pr", "view", str(n), "--repo", REPO, "--json",
                     "url,title,headRefOid,files,statusCheckRollup,comments")
    except ReadError:
        die(f"cannot read PR #{n}")
    oid = pr.get("headRefOid") or ""
    if args.head is None:
        head = oid[:8] + "…"
    else:
        want = args.head.lower()
        ok = bool(SHA_RE.match(want)) and oid.startswith(want)
        head = oid[:8] + "… (matches reported)" if ok else f"{oid[:8]}… MISMATCH: reported {args.head}"
    paths = [f["path"] for f in pr.get("files") or []]
    areas = {}
    for p in paths:
        area = p.split("/")[0] if "/" in p else "root"
        areas[area] = areas.get(area, 0) + 1
    by_count = sorted(areas.items(), key=lambda kv: (-kv[1], kv[0]))
    comments = pr.get("comments") or []
    try:
        moved = moved_line(oid, comments, gh("api", "user", "-q", ".login").strip())
    except ReadError:
        die(f"cannot read PR #{n}")
    out = [
        f"pr #{n} {pr.get('title', '')}",
        f"url: {pr.get('url', '')}",
        f"head: {head}",
        check_summary(pr.get("statusCheckRollup")),
        review_line("code review", "## Code review", comments),
        review_line("security review", "## Security review", comments),
        *([moved] if moved else []),
        f"files: {len(paths)} (" + ", ".join(f"{a} {c}" for a, c in by_count) + ")",
        *flags_for(paths),
        migrations_line(n, migration_numbers(paths)),
    ]
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("spec")
    sp.add_argument("path")
    sp.add_argument("sha")
    sp.add_argument("--branch")
    sp.set_defaults(fn=cmd_spec)
    pp = sub.add_parser("pr")
    pp.add_argument("number", type=int)
    pp.add_argument("--head")
    pp.set_defaults(fn=cmd_pr)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
