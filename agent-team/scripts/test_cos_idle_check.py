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


def thread_read(*items, ended="04:45"):
    return json.dumps(
        {
            "recentRuns": [
                {"runId": "r2", "status": "completed", "completedAt": f"2026-11-02T{ended}:00Z"}
            ],
            "items": [
                {"runId": r, "type": "dynamic_tool", "text": t if isinstance(t, str) else json.dumps(t)}
                for r, t in items
            ],
        }
    )


def cut_off(call, before):
    """The call's text cut off just before `before`, as maxCharsPerItem does."""
    text = json.dumps(call)
    return text[: text.index(before)]


def wait_call(matched, unmatched=()):
    sc = {"matched": matched, "unmatched": list(unmatched)}
    return {
        "toolName": "mcp__t3-code__t3_background_wait",
        "output": {"content": json.dumps(sc), "structuredContent": sc},
    }


@pytest.mark.parametrize(
    "stdin, want_line, want_code",
    [
        (thread_read(("r2", wait_call(["b1"]))), "waiting ABC-9 on b1", 0),
        (thread_read(("r2", wait_call(["b1"])), ended="03:55"), "stalled ABC-9 wait-expired", 1),
        (thread_read(("r2", wait_call([], ["b1"]))), "stalled ABC-9 unmatched", 1),
        (thread_read(("r2", {"toolName": "Bash"})), "stalled ABC-9 no-wait", 1),
        (thread_read(("r1", wait_call(["b1"]))), "stalled ABC-9 no-wait", 1),
        (thread_read(("r2", cut_off(wait_call(["b1"]), '"structuredContent"'))), "waiting ABC-9", 0),
        (thread_read(("r2", cut_off(wait_call(["b1"]), '"output"'))), "cos_idle_check:", 2),
        ("not json", "cos_idle_check:", 2),
    ],
)
def test_wait_mode_tells_waiting_child_from_stalled(
    capsys, monkeypatch, stdin, want_line, want_code
):
    monkeypatch.setattr(sys, "stdin", StringIO(stdin))
    monkeypatch.setattr(
        sys, "argv", ["cos_idle_check", "--wait", "ABC-9", "--now", "2026-11-02T04:50:00Z"]
    )
    with pytest.raises(SystemExit) as e:
        cos_idle_check.main()
    assert e.value.code == want_code
    assert capsys.readouterr().out.startswith(want_line)
