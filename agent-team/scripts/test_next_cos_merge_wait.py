"""`cos_merge_wait.py --next`: every line the wait can end on has its `next:` text (sweep.md § Merge wait step 3)."""

import json

import pytest

import cos_merge_wait as w

TICK = "cos_tick.py --thread <this thread's id> --trigger 'notice:c9' --next"
# the last line, exit code, words the next: text holds
CASES = [
    ("merge-wait: ABC-1 #7 merged", 0, [TICK, "The PR merged", "merged check"]),
    ("merge-wait: ABC-1 #7 closed", 0, [TICK, "The PR was closed"]),
    ("merge-wait: ABC-1 #7 still open after 30m", 1, [TICK, "once, and start no new wait"]),
    ("merge-wait: ABC-1 left merge", 0, ["Nothing: no tick, no message"]),
    ("merge-wait: cannot find an integer pr", 2, ["Merge wait for <PREFIX>-N: <short title>, <its line>"]),
    ("merge-wait: cannot read the PR from GitHub 5 times in a row", 2, ["Merge wait for <PREFIX>-N: <short title>, <its line>"]),
]


@pytest.mark.parametrize("line, code, has", CASES)
def test_every_ending_has_its_next_and_the_line_is_unchanged(tmp_path, capsys, monkeypatch, line, code, has):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {"ABC-1": {"stage": "merge", "pr": 7, "childThreadId": "c9"}}}))
    monkeypatch.setattr(w, "wait", lambda *a, **k: (line, code))
    argv = ["ABC-1", "--file", str(state)]
    assert w.main(argv) == code
    plain = capsys.readouterr().out
    assert w.main([*argv, "--next"]) == code
    out = capsys.readouterr().out.splitlines()
    assert plain == line + "\n" and out[0] == line and out[1].startswith("next: ") and len(out) == 2
    assert all(x in out[1] for x in has)


def test_a_ticket_gone_from_state_leaves_the_thread_id_to_the_model(tmp_path, capsys, monkeypatch):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {}}))
    monkeypatch.setattr(w, "wait", lambda *a, **k: ("merge-wait: ABC-1 #7 merged", 0))
    assert w.main(["ABC-1", "--file", str(state), "--next"]) == 0
    assert "'notice:<childThreadId>'" in capsys.readouterr().out


def test_a_bad_ticket_id_prints_cannot_and_its_next(capsys):
    assert w.main(["nope", "--next"]) == 2
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "merge-wait: cannot use a ticket id like <PREFIX>-N" and "Cleanup line" in out[1]
