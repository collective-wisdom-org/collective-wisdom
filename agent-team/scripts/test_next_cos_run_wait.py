"""`cos_run_wait.py --next`: every line the wait can end on has its `next:` text (sweep.md § Run wait step 2)."""

import json

import pytest

import cos_run_wait as w

TICK = "cos_tick.py --thread <this thread's id> --trigger 'notice:c9' --next"
CASES = [
    ("run-wait: ABC-1 left build", 0, ["Nothing: no tick, no message"]),
    ("run-wait: ABC-1 run failed", 0, [TICK, "failed, was interrupted or was cancelled"]),
    ("run-wait: ABC-1 run interrupted", 0, [TICK]),
    ("run-wait: ABC-1 run cancelled", 0, [TICK]),
    ("run-wait: ABC-1 BUILD READY", 0, [TICK, "the same plan as the finish notice that never came"]),
    ("run-wait: ABC-1 MERGE READY", 0, [TICK]),
    ("run-wait: ABC-1 BLOCKED", 0, [TICK]),
    ("run-wait: ABC-1 MERGED", 0, [TICK]),
    ("run-wait: ABC-1 still working after 110m", 1, [TICK, "then start a new run wait", "same lane with the same child"]),
    ("run-wait: cannot find ABC-1 in state", 2, ["Run wait for <PREFIX>-N: <short title>, <its line>"]),
]


@pytest.mark.parametrize("line, code, has", CASES)
def test_every_ending_has_its_next_and_the_line_is_unchanged(tmp_path, capsys, monkeypatch, line, code, has):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {"ABC-1": {"stage": "build", "childThreadId": "c9"}}}))
    monkeypatch.setattr(w, "wait", lambda *a, **k: (line, code))
    argv = ["ABC-1", "--file", str(state)]
    assert w.main(argv) == code
    plain = capsys.readouterr().out
    assert w.main([*argv, "--next"]) == code
    out = capsys.readouterr().out.splitlines()
    assert plain == line + "\n" and out[0] == line and out[1].startswith("next: ") and len(out) == 2
    assert all(x in out[1] for x in has)


def test_a_bad_ticket_id_prints_cannot_and_its_next(capsys):
    assert w.main(["nope", "--next"]) == 2
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "run-wait: cannot use a ticket id like <PREFIX>-N" and "Cleanup line" in out[1]
