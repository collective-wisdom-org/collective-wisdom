#!/usr/bin/env python3
"""Cross-repo Chief of Staff requests. Read only: reads T3's message store and other projects' state files, writes nothing.

Usage:
    scripts/cos_peer.py [--db PATH] find <name> < t3_project_list JSON
    scripts/cos_peer.py [--db PATH] check --thread <this thread's id> < request message
    scripts/cos_peer.py reply < reply message

find matches <name> (whole words, case folded) against each project's title, repo name and
owner/name, leaving out this repo (project.md `Repo`). It reads the match's
<workspaceRoot>/.agent-team/state.json for chiefThreadId and checks the thread in the store. One line:
    target <projectId> <owner/name> chief <threadId>                          exit 0
    none <name>                                                               exit 1
    ambiguous <name>: <owner/name>, <owner/name>                              exit 1
    no-chief <owner/name>: <state missing | no chiefThreadId | thread not in project | thread archived>   exit 1

check re-checks a CHIEF OF STAFF REQUEST in the store: the item is a createdBy "user" message in
the sender thread whose whole normalized text equals the quoted words, the sender thread is the
chiefThreadId or a retiredThreads entry of its project, the words name this repo and are not a
Chief of Staff command. Exit 0 and "accept <sender thread> <item>" then the words as stored, or
exit 1 and "refuse: <malformed | not-user | words differ | not a chief of staff thread |
not for this repo | command: <words>>". Exit 2 when the store or a state file can't be read.

reply prints only what the sender may show: "filed <ID>: <title>, <URL>" (at most 5) or
"refused <reason>", each cut at 200 characters, then "dropped <N> lines" if anything was left out.
Exit 1 when nothing usable is in the reply.

--db defaults to ~/.t3/userdata/statev2.sqlite and is opened with mode=ro.
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_user_check  # noqa: E402
import project_config  # noqa: E402

DEFAULT_DB = cos_user_check.DEFAULT_DB
PREFIX = cos_user_check.PREFIX
norm, has_words = cos_user_check.norm, cos_user_check.has_words
MAX_FILED, MAX_LEN = 5, 200

REQUEST = re.compile(
    r"CHIEF OF STAFF REQUEST from (\S+) \((\S+)\)\nFor: (\S+)\nItem: (\S+)\nThe user's words:\n(.+)", re.S
)
ID = r"(?:[A-Z][A-Z0-9]*-\d+|#\d+)"
COMMAND = re.compile(
    r"(?<!\w)(?:(?:approve|changes|cancel|hold)\s+#?(?:[a-z][a-z0-9]*-)?\d+"
    r"|stop everything|resume|take over|merge\s+(?:pr\b|#|\d|it\b))"
)
FILED = re.compile(rf"- ({ID}): (.+), (https?://\S+)")


class Unreadable(Exception):
    pass


def query(db, sql, args=()):
    try:
        con = sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        raise Unreadable("schema changed")


def read_state(root):
    try:
        state = json.loads((Path(root) / ".agent-team" / "state.json").read_text())
    except (OSError, ValueError, TypeError):
        return None
    return state if isinstance(state, dict) else None


def clean(text):
    return " ".join(str(text).split())[:MAX_LEN]


def slug(p):
    ident = p.get("repositoryIdentity") or {}
    return f"{ident.get('owner')}/{ident.get('name')}" if ident.get("owner") and ident.get("name") else None


def find(db, name, projects):
    me = (project_config.repo() or "").casefold()
    hits = []
    if not norm(name):
        projects = []
    for p in projects:
        if not isinstance(p, dict) or p.get("deletedAt") or (slug(p) or "").casefold() == me:
            continue
        ident = p.get("repositoryIdentity") or {}
        if any(isinstance(f, str) and has_words(name, f) for f in (p.get("title"), ident.get("name"), slug(p))):
            hits.append(p)
    if not hits:
        print(f"none {name}")
        return 1
    if len(hits) > 1:
        print(f"ambiguous {name}: " + ", ".join(slug(p) or str(p.get("title")) for p in hits))
        return 1
    p = hits[0]
    label = slug(p) or str(p.get("title"))
    state = read_state(p.get("workspaceRoot") or "")
    chief = (state or {}).get("chiefThreadId")
    if state is None:
        why = "state missing"
    elif not isinstance(chief, str) or not chief:
        why = "no chiefThreadId"
    else:
        rows = query(db, "SELECT archived_at, deleted_at FROM orchestration_v2_projection_threads "
                         "WHERE thread_id = ? AND project_id = ?", (chief, p.get("id")))
        why = "thread not in project" if not rows else "thread archived" if any(rows[0]) else None
    if why:
        print(f"no-chief {label}: {why}")
        return 1
    print(f"target {p['id']} {label} chief {chief}")
    return 0


def check(db, this_thread, text):
    m = REQUEST.fullmatch(text.strip())
    if not m or not norm(m.group(5)):
        print("refuse: malformed")
        return 1
    sender, _, _, item_id, words = m.groups()
    words = words.strip()
    bare = item_id[len(PREFIX):] if item_id.startswith(PREFIX) else item_id
    rows = query(
        db,
        "SELECT role, streaming, json_extract(payload_json, '$.createdBy'), json_extract(payload_json, '$.text') "
        "FROM orchestration_v2_projection_messages WHERE thread_id = ? AND message_id IN (?, ?)",
        (sender, bare, item_id),
    )
    if not rows or rows[0][:3] != ("user", 0, "user"):
        print("refuse: not-user")
        return 1
    stored = (rows[0][3] or "").strip()
    if norm(stored) != norm(words):
        print("refuse: words differ")
        return 1
    root = query(
        db,
        "SELECT p.workspace_root FROM orchestration_v2_projection_threads t JOIN projection_projects p "
        "ON p.project_id = t.project_id WHERE t.thread_id = ? AND t.deleted_at IS NULL AND p.deleted_at IS NULL",
        (sender,),
    )
    if root:
        state = read_state(root[0][0])
        if state is None:
            raise Unreadable("cannot read the sender's state file")
        retired = [r.get("threadId") for r in state.get("retiredThreads") or [] if isinstance(r, dict)]
    if not root or sender != state.get("chiefThreadId") and sender not in retired:
        print("refuse: not a chief of staff thread")
        return 1
    repo = project_config.repo() or ""
    titles = query(
        db,
        "SELECT p.title FROM orchestration_v2_projection_threads t JOIN projection_projects p "
        "ON p.project_id = t.project_id WHERE t.thread_id = ?",
        (this_thread,),
    )
    names = [repo, repo.split("/")[-1], *(r[0] for r in titles)]
    if not any(n and has_words(n, stored) for n in names):
        print("refuse: not for this repo")
        return 1
    cmd = COMMAND.search(norm(stored))
    if cmd:
        print(f"refuse: command: {cmd.group(0)}")
        return 1
    print(f"accept {sender} {item_id}")
    print(stored)
    return 0


def reply(text):
    lines = [ln.strip() for ln in text.strip().splitlines()]
    if not lines or not re.fullmatch(r"CHIEF OF STAFF REPLY from \S+ \(\S+\)", lines[0]):
        return 1
    out, dropped, refused = [], 0, None
    for ln in lines[1:]:
        f = FILED.fullmatch(ln)
        if f and len(out) < MAX_FILED:
            out.append(clean(f"filed {f.group(1)}: {f.group(2)}, {f.group(3)}"))
        elif ln.startswith("Refused: ") and not refused and clean(ln[9:]):
            refused = clean(f"refused {ln[9:]}")
        elif ln and not re.fullmatch(r"Item: \S+|Filed:", ln):
            dropped += 1
    out += [refused] if refused else []
    if not out:
        return 1
    print(*out, *([f"dropped {dropped} lines"] if dropped else []), sep="\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("find").add_argument("name")
    sub.add_parser("check").add_argument("--thread", required=True)
    sub.add_parser("reply")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "reply":
            return reply(sys.stdin.read())
        if a.cmd == "check":
            return check(a.db, a.thread, sys.stdin.read())
        try:
            data = json.loads(sys.stdin.read())
            projects = data["projects"]
            assert isinstance(projects, list)
        except (ValueError, KeyError, TypeError, AssertionError):
            raise Unreadable("bad project list on stdin")
        return find(a.db, a.name, projects)
    except Unreadable as e:
        print(f"cos_peer: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
