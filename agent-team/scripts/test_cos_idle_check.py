import importlib.util
import json
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
