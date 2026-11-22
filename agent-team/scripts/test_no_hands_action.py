"""`no_hands.py check --next` prints the action word and the report line after the check line (S5), and `next:` for the action."""

import pytest

from test_no_hands import OPEN, ON, call, msg

# run, setting, kw, cost, check line, action, report line
CASES = [
    (None, ON, {}, None, "no-hands: off", "off", None),
    ({**OPEN, "endedAt": "2026-11-08T11:00:00Z"}, ON, {}, None, "no-hands: off", "off", None),
    (OPEN, ON, {}, None, "no-hands: on 2/3 $20/$100", "fill", "No Hands on: 2 of 3 tickets, $20 of $100."),
    ({**OPEN, "drain": "blocked ABC-1"}, ON, {}, None, "no-hands: drain blocked ABC-1 2/3 $20/$100", "drain",
     "No Hands draining: blocked ABC-1, 2 of 3 tickets, $20 of $100."),
    ({**OPEN, "started": ["ABC-1", "ABC-2", "ABC-3"]}, ON, {}, None, "no-hands: drain ticket-cap 3/3 $30/$100", "drain",
     "No Hands draining: ticket-cap, 3 of 3 tickets, $30 of $100."),
    (OPEN, ON, {}, lambda t, s: 50.0, "no-hands: stop cost-cap $100/$100", "stop", None),
    (OPEN, ON, {}, lambda t, s: None, "no-hands: stop cost unknown (ABC-1)", "stop", None),
    (OPEN, (False, 0, 0, ""), {}, None, "no-hands: stop setting off", "stop", None),
    (OPEN, ON, {"msgs": []}, None, "no-hands: stop start message not verified", "stop", None),
    (OPEN, ON, {"msgs": [msg(), msg("m3", "stop everything", created="2026-11-08T10:30:00Z")]}, None, "no-hands: stop stopped-by-user", "stop", None),
]


@pytest.mark.parametrize("run, setting, kw, cost, line, action, report", CASES)
def test_check_next_prints_action_and_report_line_after_the_check_line(tmp_path, capsys, run, setting, kw, cost, line, action, report):
    code, out, _, _ = call(tmp_path, capsys, ["check", "--next"], run, setting, cost or (lambda t, s: 10.0), **kw)
    lines = out.splitlines()
    assert code == 0
    assert lines[:2] == [line, f"action: {action}"]
    assert [x for x in lines[2:] if not x.startswith("next: ")] == ([report] if report else [])


@pytest.mark.parametrize("run, setting, kw, cost, line, action, report", CASES)
def test_without_the_flag_the_output_is_the_check_line_alone(tmp_path, capsys, run, setting, kw, cost, line, action, report):
    code, out, _, _ = call(tmp_path, capsys, ["check"], run, setting, cost or (lambda t, s: 10.0), **kw)
    assert (code, out) == (0, line)
