import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_child_read  # noqa: E402

SHA = "a" * 40
SPEC = "docs/superpowers/specs/x.md"
BUILD = f"BUILD READY\nSpec: {SPEC}\nLink: https://github.com/o/r/blob/feat/abc-5-x/{SPEC}\nCommit: {SHA}\nBuilds:\n- a thing"
MERGE = f"MERGE READY\nPR: https://github.com/o/r/pull/12\nHead: {SHA}\nChanges:\n- a thing"
WIDE = "BLOCKED: stuck\n" + "z" * 250 + "\nafter"
TALL = "BLOCKED: stuck\n" + "\n".join("w" * 199 for _ in range(10))
HEAD = "child ABC-5 run={} updated=2026-11-14T10:02:00Z provider=claudeAgent next={} item=turn-item:4\n"


def store(path, items, run="completed"):
    """A store with only the columns the script reads. items: (run ordinal, item ordinal, type, text, streaming)."""
    con = sqlite3.connect(path)
    for sql in (
        "CREATE TABLE orchestration_v2_projection_threads (thread_id, updated_at, provider_instance_id, default_provider)",
        "CREATE TABLE orchestration_v2_projection_runs (run_id, thread_id, ordinal, status)",
        "CREATE TABLE orchestration_v2_projection_turn_items (turn_item_id, thread_id, run_id, type, payload_json)",
        "CREATE TABLE orchestration_v2_turn_item_positions (thread_id, turn_item_id, ordinal)",
    ):
        con.execute(sql)
    con.execute("INSERT INTO orchestration_v2_projection_threads VALUES ('t', '2026-11-14T10:02:00Z', NULL, 'claudeAgent')")
    con.execute("INSERT INTO orchestration_v2_projection_runs VALUES ('r1', 't', 1, 'completed')")
    con.execute("INSERT INTO orchestration_v2_projection_runs VALUES ('r2', 't', 2, ?)", (run,))
    for n, (r, ordinal, kind, text, streaming) in enumerate(items):
        con.execute(
            "INSERT INTO orchestration_v2_projection_turn_items VALUES (?, 't', ?, ?, ?)",
            (f"turn-item:{n}", f"r{r}", kind, json.dumps({"text": text, "streaming": streaming})),
        )
        con.execute("INSERT INTO orchestration_v2_turn_item_positions VALUES ('t', ?, ?)", (f"turn-item:{n}", ordinal))
    con.commit()
    con.close()


def items(text, streaming=0):
    """A first run with two items, then a second run whose items rank 2, 3 and 4 by ordinal (not 2000001...)."""
    return [
        (1, 1000001, "user_message", "go", 0),
        (1, 1000002, "assistant_message", "older", 0),
        (2, 2000001, "user_message", "again", 0),
        (2, 2000002, "command_execution", "", 0),
        (2, 2000003, "assistant_message", text, streaming),
    ]


@pytest.mark.parametrize(
    "text, run, after, want",
    [
        (BUILD, "completed", None, f"marker BUILD READY\nfield specPath={SPEC} specSha={SHA} branch=feat/abc-5-x\nblock:\n{BUILD}\n"),
        (BUILD.replace("BUILD", "SPEC").replace(SHA, "zz"), "completed", None, f"field specPath={SPEC} specSha=? branch=feat/abc-5-x\n"),
        (BUILD.replace("/blob/", "/tree/"), "completed", None, "branch=?\n"),
        (MERGE, "completed", None, f"marker MERGE READY\nfield pr=12 headSha={SHA}\nblock:\n{MERGE}\n"),
        (MERGE.replace("pull/12", "pull/x"), "completed", None, "field pr=? headSha="),
        ("working\nBLOCKED: rate limited", "completed", None, "marker BLOCKED\nblock:\nBLOCKED: rate limited\n"),
        ("done\nMERGED #14", "completed", None, "marker MERGED\nfield pr=14\n"),
        ("MERGED #x.", "completed", None, "field pr=?\n"),
        ("a step\n" + "y" * 500, "completed", None, "marker none\ntail:\n" + "y" * 400 + "\n"),
        ("the BUILD READY block is above", "completed", None, "marker none\ntail:\n"),
        (BUILD, "running", None, "marker none\n"),
        (BUILD, "completed", 4, "marker none new=0\n"),
        (WIDE, "completed", 3, "block:\nBLOCKED: stuck\n" + "z" * 200 + "\nafter\ncut turn-item:4 at 215\n"),
        (TALL, "completed", 3, "cut turn-item:4 at 1500\n"),
    ],
)
def test_child_read_lines(tmp_path, capsys, text, run, after, want):
    db = tmp_path / "s.sqlite"
    store(db, items(text), run)
    args = ["--db", str(db), "ABC-5", "t"] + ([] if after is None else ["--after", str(after)])
    assert cos_child_read.main(args) == 0
    out = capsys.readouterr().out
    assert want in out
    assert out.startswith("child ABC-5 run=" + run)
    assert len(out) < 2000


def test_next_is_the_rank_among_the_threads_items(tmp_path, capsys):
    db = tmp_path / "s.sqlite"
    store(db, items(BUILD))
    cos_child_read.main(["--db", str(db), "ABC-5", "t"])
    assert capsys.readouterr().out.startswith(HEAD.format("completed", 4))


@pytest.mark.parametrize("kind", ["no tables", "no thread"])
def test_unreadable_store_exits_2(tmp_path, capsys, kind):
    db = tmp_path / "s.sqlite"
    if kind == "no tables":
        sqlite3.connect(db).close()
    else:
        store(db, [])
    with pytest.raises(SystemExit) as e:
        cos_child_read.main(["--db", str(db), "ABC-5", "missing" if kind == "no thread" else "t"])
    assert e.value.code == 2
    assert capsys.readouterr().err.strip() == "cos_child_read: " + ("schema changed" if kind == "no tables" else "thread not found")
