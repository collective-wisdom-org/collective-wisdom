#!/usr/bin/env python3
"""Remove the copied agent team from an app that was installed the old way.

Usage, with the app as the current directory:
    ~/.collective-wisdom/scripts/remove_app_copies.py [--dry-run] [--force]

Reads docs/agents/installed-from.txt (`collective-wisdom <40-character SHA>`, optionally followed by
` v0.N`) and lists the files that commit's agent-team/ has under .claude/skills, .claude/agents,
.claude/mods, scripts and docs/agents, except docs/agents/project.md. The commit must be in the clone
this script sits in. Deletes each listed file the app still has, then any directory under those five roots left empty,
then the pin last (so a failed delete leaves it), then the .agents/skills link to ../.claude/skills once
.claude/skills is gone. Anything reached through a link out of the app is skipped, never written.
A listed file that differs from the pinned copy is a hand edit: it stops the run with exit 1 and
nothing is written, unless --force. --dry-run prints the same lines and writes nothing.
Never touches AGENTS.md, .gitignore, project.md or settings.json, and never commits.
Exit 0 for done or nothing to remove; 1 for a refusal; 2 for a pin or clone problem, or a bad argument.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

CLONE = Path(__file__).resolve().parents[2]
ROOTS = [".claude/skills", ".claude/agents", ".claude/mods", "scripts", "docs/agents"]
PIN = "docs/agents/installed-from.txt"
PIN_RE = re.compile(r"collective-wisdom ([0-9a-f]{40})( v0\.[0-9]+)?")
KEEP = "docs/agents/project.md"


def junk(name):
    return name in ("__pycache__", ".DS_Store") or name.endswith(".pyc")


def git_clone(*args):
    env = {**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"}
    return subprocess.run(["git", "-C", str(CLONE), *args], capture_output=True, env=env)


def pinned_files(sha):
    """{path in the app: blob id} for the files the pinned commit ships."""
    files = {}
    for r in ROOTS:
        out = git_clone("ls-tree", "-r", "-z", sha, "--", f"agent-team/{r}").stdout.decode("utf-8", "surrogateescape")
        for entry in filter(None, out.split("\0")):
            meta, path = entry.split("\t", 1)
            path = path.removeprefix("agent-team/")
            if path != KEEP and not any(junk(part) for part in path.split("/")):
                files[path] = meta.split()[2]
    return files


def inside(app, d):
    """True when directory d, with its links resolved, is the app or under it."""
    return app.resolve() in (d.resolve(), *d.resolve().parents)


def blob_id(p):
    data = os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Remove the copied agent team from an old app.")
    ap.add_argument("--dry-run", action="store_true", help="print what would be removed and write nothing")
    ap.add_argument("--force", action="store_true", help="remove hand-edited copies too")
    args = ap.parse_args()
    app = root()
    tag = "[dry-run] " if args.dry_run else ""

    def say(line):
        print(tag + line)

    if (app / "install.sh").is_file() and (app / "agent-team").is_dir():
        print("Refusing: this is collective-wisdom itself. Run this in an app.", file=sys.stderr)
        return 1
    pin = app / PIN
    if not pin.is_file():
        print("nothing to remove: no installed-from.txt")
        return 0
    m = PIN_RE.fullmatch(pin.read_text(errors="replace").rstrip("\n"))
    if not m:
        print(f"{PIN} is not 'collective-wisdom <40-character SHA>' (optionally followed by a v0.N tag).", file=sys.stderr)
        return 2
    sha = m.group(1)
    if git_clone("cat-file", "-e", f"{sha}^{{commit}}").returncode:
        print(f"collective-wisdom {sha} is not in {CLONE}; run 'git fetch origin' in {CLONE} and try again.", file=sys.stderr)
        return 2

    pin_ok = inside(app, pin.parent)
    if not pin_ok:
        say(f"skip    {PIN}: it is reached through a link out of the app")
    present = []  # (path, blob id) of listed files the app still has, and that are inside the app
    for path, blob in sorted(pinned_files(sha).items()):
        p = app / path
        if not (p.exists() or p.is_symlink()):
            continue
        if not inside(app, p.parent):
            say(f"skip    {path}: it is reached through a link out of the app")
            continue
        present.append((path, blob))
    changed = []
    for path, blob in present:
        try:
            same = blob_id(app / path) == blob
        except OSError:
            same = False
        if not same:
            changed.append(path)
    if changed and not args.force:
        for path in changed:
            say(f"changed  {path}")
        print("Stopped: these files differ from the pinned copy. Nothing was removed. Review them, or run with --force.", file=sys.stderr)
        return 1

    removed = {path for path, _ in present} | ({PIN} if pin_ok else set())
    for path in sorted(removed - {PIN}):
        say(f"remove  {path}")
        if not args.dry_run:
            try:
                (app / path).unlink(missing_ok=True)
            except OSError as e:
                print(f"Stopped: cannot remove {path}: {e}. The pin is still there.", file=sys.stderr)
                return 1

    gone = set()
    later = []  # directories holding the pin, removed once the pin is

    def prune(d):
        """Remove d when only removed files and junk are left in it; True when it is (or would be) gone."""
        empty = True
        for c in sorted(d.iterdir()):
            rel = c.relative_to(app).as_posix()
            if c.is_dir() and not c.is_symlink() and not junk(c.name):
                empty = prune(c) and empty
            elif rel not in removed and not junk(c.name):
                empty = False
        if empty:
            rel = d.relative_to(app).as_posix()
            say(f"remove  {rel}/")
            gone.add(rel)
            if not args.dry_run:
                if pin.is_relative_to(d):
                    later.append(d)
                else:
                    shutil.rmtree(d)
        return empty

    for r in ROOTS:
        if not (app / r).is_dir() or (app / r).is_symlink():
            continue
        if inside(app, app / r):
            prune(app / r)
        else:
            say(f"skip    {r}/: it is reached through a link out of the app")

    if pin_ok:
        say(f"remove  {PIN}")
        if not args.dry_run:
            try:
                pin.unlink()
                for d in later:
                    shutil.rmtree(d)
            except OSError as e:
                print(f"Stopped: cannot remove {PIN}: {e}", file=sys.stderr)
                return 1

    link = app / ".agents/skills"
    if link.is_symlink() and os.readlink(link) == "../.claude/skills" and (".claude/skills" in gone or not os.path.lexists(app / ".claude/skills")):
        say("remove  .agents/skills")
        if not args.dry_run:
            link.unlink()
        if not set(os.listdir(app / ".agents")) - {"skills"}:
            say("remove  .agents/")
            if not args.dry_run:
                shutil.rmtree(app / ".agents")

    settings = app / ".claude/settings.json"
    if settings.is_file() and "cos_rotation_check.py" in settings.read_text(errors="replace"):
        say("TODO: .claude/settings.json runs cos_rotation_check.py; the machine install runs that hook now, so remove it from this file by hand.")
    say("TODO: commit this removal as a PR in the app.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
