#!/usr/bin/env python3
"""Did the user write it? Reads T3's local message store, read-only, and prints one line.

Usage:
    scripts/cos_user_check.py [--db PATH] latest <threadId> [--after ISO] < words
    scripts/cos_user_check.py [--db PATH] item <threadId> <itemId> < words

The command's own words are always on stdin. Matching folds case and collapses whitespace on
both sides (after NFKC and dropping zero-width characters), and the words must match on token boundaries (word characters on neither side), so
"approve 25" does not match "approve 253".

A match is negated when the same sentence holds a negation word outside the matched words,
before or after them: "do not approve 30 yet", "don't approve 30", "never approve 30" and
"approve 30, no rush" are not the user's "approve 30". A sentence ends at ., !, ? or ; followed
by whitespace or the end of the text (a period inside a token such as v0.3 does not end it). A
negation word is no, not, never, nor, cannot, dont, cant, wont or anything ending in n't. If any
occurrence of the words is negated, the message is negated. Words inside the match are ignored,
so a whole-message match still works.

latest checks the newest user-role message in the thread whose text contains the words; with
--after, only messages created after that ISO time count. Exit 0 and
"user <itemId> <createdAt> <first 80 characters>" when its createdBy is exactly "user" and
the words are not negated, otherwise exit 1 and "not-user <createdBy or missing> <itemId>
<first 80 characters>" (not-user missing - - when nothing matches; "not-user negated <itemId>
<first 80 characters>" when the user's newest message with the words negates them, with no
fall back to an older message). Tying the check to the words means an agent
message with other words can't stand in for the command, an older approval with the same
words is ignored with --after, and an agent copy of their words that is newer than their own fails
closed. Empty or missing words, or a --after that is not a full ISO date-time with a timezone
(2026-11-02T14:05:00Z), is an error (exit 2). Matching also applies NFKC and drops invisible
format characters (zero-width spaces), so look-alike copies of their words match the same way.
item checks the queued-approval message <itemId> (turn-item:message:<message id>, or the
bare message id) against the words on stdin. Exit 0 and "ok" only if the message is in that
thread, was created by "user" and its text contains the words, not negated (same matching),
otherwise exit 1 and "reject: <not found | not from the user | words not found | words negated>". A message still being written
counts as not found.

--db defaults to ~/.t3/userdata/statev2.sqlite and is opened with mode=ro. Exit 2 and
"cos_user_check: schema changed" when the database or the messages table is not as expected.
"""

import argparse
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

DEFAULT_DB = Path.home() / ".t3" / "userdata" / "statev2.sqlite"
PREFIX = "turn-item:message:"
SELECT = (
    "SELECT message_id, created_at, json_extract(payload_json, '$.createdBy'), "
    "json_extract(payload_json, '$.text') FROM orchestration_v2_projection_messages "
    "WHERE thread_id = ? AND streaming = 0 "
)


def query(db, sql, args):
    try:
        con = sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()
    except sqlite3.Error:
        print("cos_user_check: schema changed", file=sys.stderr)
        sys.exit(2)


def snippet(text):
    return " ".join((text or "").split())[:80]


def norm(text):
    text = unicodedata.normalize("NFKC", text or "")
    return " ".join("".join(c for c in text if unicodedata.category(c) != "Cf").split()).casefold()


ISO_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})")


def valid_after(s):
    if not ISO_TIME.fullmatch(s):
        return False
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def has_words(words, text):
    return re.search(r"(?<!\w)" + re.escape(norm(words)) + r"(?!\w)", norm(text)) is not None


SENTENCE_END = re.compile(r"[.!?;](?=\s|$)")
NEGATIONS = {"no", "not", "never", "nor", "cannot", "dont", "cant", "wont"}


def negated_in(text):
    tokens = re.findall(r"[\w']+", text.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'"))
    return any(t.strip("'") in NEGATIONS or t.strip("'").endswith("n't") for t in tokens)


def command_in(words, text):
    """None if the words are not in text, "negated" if any occurrence shares a sentence with a negation word, else "ok"."""
    t = norm(text)
    matches = list(re.finditer(r"(?<!\w)" + re.escape(norm(words)) + r"(?!\w)", t))
    if not matches:
        return None
    ends = [m for m in SENTENCE_END.finditer(t)]
    for m in matches:
        start = max([e.end() for e in ends if e.end() <= m.start()], default=0)
        end = min([e.start() for e in ends if e.start() >= m.end()], default=len(t))
        if negated_in(t[start:m.start()]) or negated_in(t[m.end():end]):
            return "negated"
    return "ok"


def latest(db, thread, words, after=None):
    where = "AND julianday(created_at) > julianday(?) " if after is not None else ""
    rows = query(
        db,
        SELECT + "AND role = 'user' " + where + "ORDER BY created_at DESC, message_id DESC",
        (thread, *([after] if after is not None else [])),
    )
    rows = [r for r in rows if has_words(words, r[3])][:1]
    if not rows:
        print("not-user missing - -")
        return 1
    mid, created_at, by, text = rows[0]
    if by == "user" and command_in(words, text) == "negated":
        print(f"not-user negated {PREFIX}{mid} {snippet(text)}")
        return 1
    if by == "user":
        print(f"user {PREFIX}{mid} {created_at} {snippet(text)}")
        return 0
    print(f"not-user {by or 'missing'} {PREFIX}{mid} {snippet(text)}")
    return 1


def item(db, thread, item_id, words):
    bare = item_id[len(PREFIX):] if item_id.startswith(PREFIX) else item_id
    rows = query(db, SELECT + "AND role = 'user' AND message_id IN (?, ?)", (thread, bare, item_id))
    if not rows:
        reason = "not found"
    elif rows[0][2] != "user":
        reason = "not from the user"
    elif not norm(words) or not has_words(words, rows[0][3]):
        reason = "words not found"
    elif command_in(words, rows[0][3]) == "negated":
        reason = "words negated"
    else:
        print("ok")
        return 0
    print(f"reject: {reason}")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("latest")
    lp.add_argument("thread")
    lp.add_argument("--after")
    p = sub.add_parser("item")
    p.add_argument("thread")
    p.add_argument("item_id")
    a = ap.parse_args(argv)
    if a.cmd == "latest":
        words = sys.stdin.read().strip()
        if not words or a.after == "":
            print("cos_user_check: latest needs the command's words on stdin and, if given, a non-empty --after", file=sys.stderr)
            return 2
        if a.after is not None and not valid_after(a.after):
            print("cos_user_check: --after must be a full ISO date-time with a timezone, e.g. 2026-11-02T14:05:00Z", file=sys.stderr)
            return 2
        return latest(a.db, a.thread, words, a.after)
    return item(a.db, a.thread, a.item_id, sys.stdin.read().strip())


if __name__ == "__main__":
    sys.exit(main())
