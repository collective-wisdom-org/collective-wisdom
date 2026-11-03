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
