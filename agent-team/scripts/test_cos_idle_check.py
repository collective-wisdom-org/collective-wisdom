import importlib.util
import json
import sqlite3
import sys
from io import StringIO
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cos_idle_check", Path(__file__).with_name("cos_idle_check.py")
)
cos_idle_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_idle_check)


@pytest.mark.parametrize(
    "run_status, updated, extra, want_line, want_code",
    [
        ("completed", "04:45", [], "full ABC-125 lost-notice", 1),
        ("failed", "04:45", [], "full ABC-125 lost-notice", 1),
        ("running", "04:49", [], "ok ABC-125", 0),
        ("completed", "04:45", ["--skip", "ABC-125"], "idle-check: 0 active", 0),
    ],
)
def test_finished_child_with_lost_notice_is_flagged(
    tmp_path, capsys, monkeypatch, run_status, updated, extra, want_line, want_code
):
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "tickets": {
                    "ABC-125": {"stage": "build", "lastSeenAt": "2026-11-02T04:30:00Z"}
                }
            }
        )
    )
    reads = [
        {
            "ticket": "ABC-125",
            "runStatus": run_status,
            "updatedAt": f"2026-11-02T{updated}:00Z",
        }
    ]
    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps(reads)))
    argv = ["cos_idle_check", "--file", str(state), "--now", "2026-11-02T04:50:00Z", *extra]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as e:
        cos_idle_check.main()
    assert e.value.code == want_code
    assert capsys.readouterr().out.startswith(want_line)


def wait_call(matched=(), unmatched=(), content=False, structured=True):
    found = {"matched": list(matched), "unmatched": list(unmatched)}
    output = {"content": json.dumps(found)} if content else {}
    if structured:
        output["structuredContent"] = found
    return json.dumps({"toolName": "mcp__t3-code__t3_background_wait", "output": output})


def cut_before(call_text, key):
    """The call's JSON text up to just before "key", as maxCharsPerItem cuts it."""
    return call_text[: call_text.index(f'"{key}"')]


def wait_read(run_id="r2", completed="04:45", matched=(), unmatched=(), text=None, run_of_wait="r2",
              content=False, structured=True):
    items = []
    if text is not None or matched or unmatched:
        call = wait_call(matched, unmatched, content, structured)
        items.append({"runId": run_of_wait, "type": "dynamic_tool", "text": text or call})
    run = {"runId": run_id, "status": "completed", "completedAt": f"2026-11-02T{completed}:00Z"}
    return json.dumps({"recentRuns": [run], "items": items})


CUT = '{"toolName": "mcp__t3-code__t3_background_wait", "output": {"structuredContent": {"matched": '


@pytest.mark.parametrize(
    "stdin, want_code, want_line",
    [
        (wait_read(matched=["bg1"]), 0, "waiting ABC-1 on bg1"),
        (wait_read(matched=["bg1"], completed="04:00"), 1, "stalled ABC-1 wait-expired 50m"),
        (wait_read(unmatched=["bg1"]), 1, "stalled ABC-1 unmatched"),
        (wait_read(), 1, "stalled ABC-1 no-wait"),
        (wait_read(matched=["bg1"], run_of_wait="r1"), 1, "stalled ABC-1 no-wait"),
        ("not json", 2, "cos_idle_check:"),
        (wait_read(text=CUT + '["bg1", "bg2'), 0, "waiting ABC-1"),
        (wait_read(text=CUT + "[], \"unm"), 2, "cos_idle_check:"),
        (wait_read(text=CUT + "[], \"unm", completed="04:00"), 1, "stalled ABC-1 wait-expired 50m"),
        (wait_read(text=cut_before(wait_call(["bg1"], content=True), "structuredContent")), 0, "waiting ABC-1"),
        (wait_read(text=cut_before(wait_call(["bg1"]), "output")), 2, "cos_idle_check:"),
        (wait_read(matched=["bg1"], content=True, structured=False), 0, "waiting ABC-1 on bg1"),
    ],
)
def test_wait_tells_waiting_child_from_stalled(capsys, monkeypatch, stdin, want_code, want_line):
    monkeypatch.setattr(sys, "stdin", StringIO(stdin))
    monkeypatch.setattr(
        sys, "argv", ["cos_idle_check", "--wait", "ABC-1", "--now", "2026-11-02T04:50:00Z"]
    )
    with pytest.raises(SystemExit) as e:
        cos_idle_check.main()
    assert e.value.code == want_code
    assert capsys.readouterr().out.startswith(want_line)


def make_store(path, threads, runs=(), tools=()):
    """A store with only the columns --store reads. threads: (id, title, updated, provider, parent, archived)."""
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE orchestration_v2_projection_threads (thread_id, title, updated_at, provider_instance_id, default_provider, archived_at, deleted_at, payload_json)")
    con.execute("CREATE TABLE orchestration_v2_projection_runs (run_id, thread_id, ordinal, status, completed_at)")
    con.execute("CREATE TABLE orchestration_v2_projection_turn_items (turn_item_id, thread_id, run_id, type, payload_json)")
    con.execute("CREATE TABLE orchestration_v2_turn_item_positions (thread_id, turn_item_id, ordinal)")
    for tid, title, updated, provider, parent, archived in threads:
        lineage = {"parentThreadId": parent, "relationshipToParent": "subagent" if parent else None}
        con.execute("INSERT INTO orchestration_v2_projection_threads VALUES (?, ?, ?, ?, 'claudeAgent', ?, NULL, ?)", (tid, title, updated, provider, archived, json.dumps({"lineage": lineage})))
    for n, run in enumerate(runs, 1):
        con.execute("INSERT INTO orchestration_v2_projection_runs VALUES (?, ?, ?, ?, ?)", (f"r{n}", "c1", n, run[0], run[1]))
    for n, (tool, output) in enumerate(tools, 1):
        con.execute("INSERT INTO orchestration_v2_projection_turn_items VALUES (?, 'c1', 'r1', 'dynamic_tool', ?)", (f"i{n}", json.dumps({"toolName": tool, "output": output})))
        con.execute("INSERT INTO orchestration_v2_turn_item_positions VALUES ('c1', ?, ?)", (f"i{n}", n))
    con.commit()
    con.close()


ENV = "<t3-thread://v2/env-1/c1>"
SUBS = [
    ("s1", "old [one]", "2026-11-02T04:10:00Z", None, "c1", None),
    ("s2", "new\ntwo", "2026-11-02T04:40:00Z", None, "c1", None),
    ("s3", "archived", "2026-11-02T04:45:00Z", None, "c1", "x"),
    ("o1", "other", "2026-11-02T04:45:00Z", None, "c9", None),
]
RUNNING = ("c1", "t", "2026-11-02T04:49:00Z", "claudeAgent", None, None)


@pytest.mark.parametrize(
    "threads, runs, env, saved, want, code",
    [
        # running child: ok line with its link, newest sub-threads first, archived and other parents left out
        ([RUNNING, *SUBS], [("running", None)], "env-1\n", "claudeAgent", f"ok ABC-1 (running, updated 04:49) {ENV}\n  sub new two <t3-thread://v2/env-1/s2>\n  sub old one <t3-thread://v2/env-1/s1>\nidle-check: 1 active, 0", 0),
        # no environment id: the thread id stands in for the link; a changed provider is reported
        ([RUNNING], [("running", None)], None, "codex", "ok ABC-1 (running, updated 04:49) c1\nprovider ABC-1 claudeAgent\nidle-check: 1 active, 0", 0),
        ([RUNNING], [("completed", None)], "env-1", "claudeAgent", "full ABC-1 lost-notice (completed, updated 04:49, seen 04:30)", 1),
        ([("c1", "t", "2026-11-02T04:00:00Z", "claudeAgent", None, None)], [("running", None)], "env-1", "claudeAgent", "full ABC-1 idle 50m", 1),
        ([], [], "env-1", "claudeAgent", "full ABC-1 unread", 1),
    ],
)
def test_store_gives_the_stdin_lines_plus_link_subs_and_provider(tmp_path, capsys, monkeypatch, threads, runs, env, saved, want, code):
    db = tmp_path / "statev2.sqlite"
    make_store(db, threads, runs)
    if env:
        (tmp_path / "environment-id").write_text(env)
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {"ABC-1": {"stage": "build", "childThreadId": "c1", "provider": saved, "lastSeenAt": "2026-11-02T04:30:00Z"}}}))
    monkeypatch.setattr(sys, "argv", ["cos_idle_check", "--store", "--db", str(db), "--file", str(state), "--now", "2026-11-02T04:50:00Z"])
    with pytest.raises(SystemExit) as e:
        cos_idle_check.main()
    assert e.value.code == code
    assert want in capsys.readouterr().out


@pytest.mark.parametrize(
    "tools, runs, want_code, want",
    [
        ([("mcp__t3-code__t3_background_wait", {"content": json.dumps({"matched": ["bg1"]})})], [("completed", "2026-11-02T04:45:00Z")], 0, "waiting ABC-1 on bg1"),
        ([("Bash", {"content": "x"})], [("completed", "2026-11-02T04:45:00Z")], 1, "stalled ABC-1 no-wait"),
        ([], [], 2, "cos_idle_check: no recent run"),
    ],
)
def test_store_wait_check_uses_the_same_rules(tmp_path, capsys, monkeypatch, tools, runs, want_code, want):
    db = tmp_path / "statev2.sqlite"
    make_store(db, [], runs, tools)
    monkeypatch.setattr(sys, "argv", ["cos_idle_check", "--wait", "ABC-1", "--store", "c1", "--db", str(db), "--now", "2026-11-02T04:50:00Z"])
    with pytest.raises(SystemExit) as e:
        cos_idle_check.main()
    assert e.value.code == want_code
    assert capsys.readouterr().out.startswith(want)


@pytest.mark.parametrize("extra", [["--store"], ["--wait", "ABC-1", "--store", "c1"]])
def test_store_error_is_exit_2(tmp_path, capsys, monkeypatch, extra):
    db = tmp_path / "statev2.sqlite"
    sqlite3.connect(db).close()
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {"ABC-1": {"stage": "build", "childThreadId": "c1"}}}))
    monkeypatch.setattr(sys, "argv", ["cos_idle_check", *extra, "--db", str(db), "--file", str(state)])
    with pytest.raises(SystemExit) as e:
        cos_idle_check.main()
    assert e.value.code == 2
    assert capsys.readouterr().out.strip() == "cos_idle_check: schema changed"
