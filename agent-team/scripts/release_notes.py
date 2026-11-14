#!/usr/bin/env python3
"""Print every release note, newest first: the docs/superpowers/release-notes/*.md files and the `## Release note` section of every PR merged into the merge target branch (the `Merge target branch` row of project.md, `main` when unset).

Exit 1 when the merged PRs cannot be read (no gh login, offline): the notes on disk are still printed.
"""

import json
import re
import subprocess
import sys
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402
import project_config  # noqa: E402

NOTES = root() / "docs" / "superpowers" / "release-notes"
GH = str(Path(__file__).absolute().parent / "gh.sh")
DATED = re.compile(r"# (\d{4}-\d{2}-\d{2}) \S")
PREFIX = re.compile(r"^[a-z]+(\([^)]*\))?!?:\s*")
FOLDER = "docs/superpowers/release-notes/"
SQUASH_PR = re.compile(r"\(#(\d+)\)\s*$")
Added = namedtuple("Added", "at pr")  # UTC merge time and the PR number from the squash subject (None without one)


def natural(name):
    """Split digits out so cw-13 sorts after cw-9."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)]


def section(body, heading="Release note"):
    """Text of the body's `## <heading>` section, up to the next `## ` heading; empty when absent."""
    out = None
    for line in (body or "").splitlines():
        if out is None:
            if re.fullmatch(rf"## {re.escape(heading)}\s*", line):
                out = []
        elif line.startswith("## "):
            break
        else:
            out.append(line)
    return "\n".join(out or []).strip()


def merged_prs():
    """Merged PRs into the merge target branch as dicts; raises RuntimeError with the reason when gh fails."""
    cmd = [GH, "pr", "list", "--state", "merged", "--base", project_config.target_branch(),
           "--json", "number,title,body,mergedAt", "--limit", "500"]
    try:
        p = subprocess.run(cmd, cwd=root(), capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError((p.stderr or p.stdout).strip() or f"exit {p.returncode}")
        return json.loads(p.stdout)
    except (OSError, ValueError) as e:
        raise RuntimeError(f"{type(e).__name__} {e}")


def utc(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_added(log):
    """{file name: Added(at, pr)} from `git log --format=%x00%cI %s --name-only` output, newest commit first; the newest add of a file wins; a commit that adds several notes is skipped."""
    added = {}
    for commit in log.split("\0")[1:]:
        head, *paths = commit.split("\n")
        when, _, subject = head.partition(" ")
        names = [p[len(FOLDER):] for p in paths if p.startswith(FOLDER)]
        if len(names) == 1:  # a commit adding several notes is a backfill or a shallow boundary, not their merge
            m = SQUASH_PR.search(subject)
            added.setdefault(names[0], Added(utc(when), int(m[1]) if m else None))
    return added


def file_merge_times():
    """{file name: Added(at, pr)} for the notes on origin/<merge target branch>; empty when git cannot tell."""
    cmd = ["git", "log", project_config.target_ref(), "--diff-filter=A", "--format=%x00%cI %s", "--name-only", "--", FOLDER]
    try:
        p = subprocess.run(cmd, cwd=root(), capture_output=True, text=True, timeout=30)
        return parse_added(p.stdout) if p.returncode == 0 else {}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}


def pr_note(pr):
    """A PR's release note: its `## Release note` section cut before any `Context size:` line; empty when none."""
    kept = []
    for line in section(pr["body"]).splitlines():
        if line.startswith("Context size:"):
            break
        kept.append(line)
    return "\n".join(kept).strip()


def stamp(text, at, headed):
    """Put `Merged <time> UTC.` under the note's heading line, or above its text when it has none."""
    if not at:
        return text
    head, _, rest = text.partition("\n") if headed else ("", "", text)
    return "\n\n".join(filter(None, [head, f"Merged {at:%Y-%m-%d %H:%M} UTC.", rest.strip()]))


def render(files, prs, merged=None):
    """The release notes text: `files` is (file name, text) pairs, `prs` the merged PR list, `merged` {file name: Added} from `file_merge_times()`.

    Raises KeyError, TypeError or ValueError when a PR is malformed. Warns on stderr about an undated note file.
    """
    merged = merged or {}
    texts = [(pr, pr_note(pr)) for pr in prs]
    covered = {pr["number"] for pr, text in texts if text}  # a PR note replaces the file that PR added
    notes = []  # (sort key, text)
    for name, text in files:
        if name in merged and merged[name].pr in covered:
            continue
        text = text.strip()
        m = DATED.match(text)
        if not m:
            print(f"release-notes: {name} has no dated heading", file=sys.stderr)
        at = merged[name].at if name in merged else None
        day = (at.date().isoformat() if at else m[1]) if m else ""
        notes.append(((day, at.time().isoformat() if at else "", 0, natural(name)), stamp("#" + text if m else text, at, bool(m))))
    for pr, text in texts:
        if text:
            at = utc(pr["mergedAt"])
            date = at.date().isoformat()
            title = PREFIX.sub("", pr["title"])
            notes.append(((date, at.time().isoformat(), 1, [pr["number"]]), stamp(f"## {date} {title} (#{pr['number']})\n\n{text}", at, True)))
    # Dated notes first, newest merge first (notes without a merge time after the timed ones of their day); undated notes last.
    notes.sort(key=lambda n: (bool(n[0][0]), *n[0]), reverse=True)
    out = ["# Release notes"]
    if not notes:
        out.append("\nNo release notes yet.")
    out += ["\n" + text for _, text in notes]
    return "\n".join(out)


def main(argv=()):
    if argv:
        print(__doc__)
        return 0
    files = [(path.name, path.read_text()) for path in NOTES.glob("*.md")]
    merged = file_merge_times()
    failed = None
    try:
        text = render(files, merged_prs(), merged)
    except (RuntimeError, KeyError, TypeError, ValueError) as e:
        failed = e
        text = render(files, [], merged)
    print(text)
    if failed:
        print(f"release-notes: cannot read merged PRs: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
