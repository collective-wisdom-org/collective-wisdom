"""`no_hands.py end --next` prints the summary template after the summary, the first two lines filled from the summary."""

import pytest

from test_no_hands import OPEN, ON, call

ENDED = {**OPEN, "endedAt": "2026-11-08T11:05:00Z", "endReason": "stopped-by-user"}


@pytest.mark.parametrize("run, reason, first", [
    (OPEN, "backlog-empty", "  No Hands ended: backlog-empty."),
    (ENDED, "ignored", "  No Hands ended: stopped-by-user."),  # a run that already ended keeps its recorded reason
])
def test_end_next_follows_the_summary(tmp_path, capsys, run, reason, first):
    code, plain, _, _ = call(tmp_path, capsys, ["end", reason], run)
    code2, out, _, _ = call(tmp_path, capsys, ["end", "--next", reason], run)
    assert code == code2 == 0 and plain.splitlines()[0].startswith("no-hands: ended")
    lines = out.splitlines()
    assert lines[:4][0].startswith("no-hands: ended") and lines[3].startswith("cost: ")  # the summary, then the next step
    assert lines[4].startswith("next: post the summary below") and lines[5] == first
    assert lines[6].startswith("  Ran ") and ", 2 tickets started, $20 of $100." in lines[6]
    assert lines[-1] == '  Say "resume" to go on without No Hands, or "no hands" for a new run.'


def test_end_next_prints_nothing_when_end_is_refused(tmp_path, capsys):
    code, out, _, _ = call(tmp_path, capsys, ["end", "--next", "x"], None)
    assert code == 1 and out == "no-hands: no active run"
