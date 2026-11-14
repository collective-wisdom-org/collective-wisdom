#!/usr/bin/env python3
"""Save the Todo or Backlog list the Chief of Staff just read, for the dashboard.

Usage:
    ~/.collective-wisdom/scripts/cos_lists.py [--file PATH] <todo|backlog> < list-tickets JSON

stdin is the `list-tickets` result as the tracker adapter returns it: a JSON list, or an object holding an `issues` or
`tickets` list. --file defaults to .agent-team/tracker-lists.json under the repo root. Replaces that one kind with
{"at": <now, UTC>, "list": <the first 250 entries, as given>} and keeps the other kind. Writes through a temp file and a
rename, and writes nothing when .agent-team is not a real folder or the file is not a regular file.
Prints `lists: saved <kind> <n>` and exits 0. Exit 2 with `lists: cannot <what>` when stdin is not one of those shapes or
the write fails; the caller goes on. cos_todo.py calls save() on its first pass.
"""

import argparse
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

DEFAULT_FILE = root() / ".agent-team" / "tracker-lists.json"
KINDS = ("todo", "backlog")
MAX = 250


class Cannot(Exception):
    pass


def entries(text):
    try:
        data = json.loads(text)
    except ValueError:
        raise Cannot("read stdin")
    if isinstance(data, dict):
        data = data.get("issues") if isinstance(data.get("issues"), list) else data.get("tickets")
    if not isinstance(data, list):
        raise Cannot("read stdin: not a ticket list")
    return data[:MAX]


def regular(path):
    """True when path is absent or a regular file."""
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except FileNotFoundError:
        return True


def save(kind, tickets, file=None):
    """Replace one kind in the file. `tickets` is the stdin text or an already parsed list. Raises Cannot."""
    if kind not in KINDS:
        raise Cannot(f"save {kind}")
    items = entries(tickets) if isinstance(tickets, str) else list(tickets)[:MAX]
    path = Path(file) if file else DEFAULT_FILE
    try:
        if not stat.S_ISDIR(os.lstat(path.parent).st_mode) or not regular(path):
            raise Cannot("write: not a regular file or folder")
        try:
            held = json.loads(path.read_text()) if path.exists() else {}
        except (OSError, ValueError):
            held = {}
        held = held if isinstance(held, dict) else {}
        held[kind] = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "list": items}
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # never through a planted link
            with os.fdopen(fd, "w") as f:
                f.write(json.dumps(held))
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
    except OSError as e:
        raise Cannot(f"write: {e.strerror or e}")
    return len(items)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"lists: cannot {message}")
        raise SystemExit(2)


def main(argv=None):
    ap = Parser(description="Save the Todo or Backlog list for the dashboard.")
    ap.add_argument("--file")
    ap.add_argument("kind", choices=KINDS)
    args = ap.parse_args(argv)
    try:
        n = save(args.kind, sys.stdin.read(), args.file)
    except Cannot as e:
        print(f"lists: cannot {e}")
        return 2
    print(f"lists: saved {args.kind} {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
