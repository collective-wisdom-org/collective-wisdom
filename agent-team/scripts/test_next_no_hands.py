"""Every result `no_hands.py check --next` can print has its `next:` text, taken from no-hands.md § What each `check` line means."""

import json

import pytest

import no_hands
from test_no_hands import OPEN, ON, msg, world

LIVE = {"ABC-1": {"stage": "build"}, "ABC-2": {"stage": "awaiting-merge"}}
STOPPED = {"msgs": [msg(), msg("m3", "stop everything", created="2026-11-08T10:30:00Z")]}


def check(tmp_path, capsys, run, tickets=None, setting=ON, cost=lambda t, s: 10.0, **kw):
    state, db = world(tmp_path, run, **kw)
    if tickets is not None:
        data = json.loads(state.read_text())
        state.write_text(json.dumps({**data, "tickets": tickets}))
    assert no_hands.main(["--file", str(state), "--db", str(db), "check", "--next"], setting=lambda: setting, cost=cost) == 0
    out = capsys.readouterr().out.splitlines()
    assert [x.split(":")[0] for x in out].count("next") == 1 and out[-1].startswith("next: ")  # one instruction, last
    return out[-1]


# run, tickets in state, what the instruction holds, what it must not hold
@pytest.mark.parametrize(
    "run, tickets, has, lacks",
    [
        (None, None, ["Nothing"], ["start-todo"]),
        (OPEN, LIVE, ["at most 1 `start-todo` lines this turn", "Approvals are No Hands"], ["drain"]),
        ({**OPEN, "started": ["ABC-1"]}, LIVE, ["at most 2 `start-todo` lines"], []),
        # a drain with its reason in state and a ticket of the run live: no extra step
        ({**OPEN, "drain": "blocked ABC-1"}, LIVE, ["Print no `start-todo` and make no Backlog pick; queued sends still go"], ["no_hands.py drain", "end the run"]),
        # the cap reached: the reason is not in state yet
        ({**OPEN, "started": ["ABC-1", "ABC-2", "ABC-3"]}, {**LIVE, "ABC-3": {"stage": "spec-queued"}}, ["no_hands.py drain ticket-cap"], ["end the run"]),
        # no ticket of the run live (gone, awaiting or merged): end it, but only after the auto checks
        ({**OPEN, "drain": "blocked ABC-1"}, {"ABC-1": {"stage": "blocked"}, "ABC-2": {"stage": "awaiting-merge"}},
         ["auto checks for every spec or merge", "end the run: no-hands.md § End a run"], ["no_hands.py drain"]),
        ({**OPEN, "drain": "blocked ABC-1"}, {}, ["auto checks", "end the run"], []),
    ],
)
def test_next_per_result(tmp_path, capsys, run, tickets, has, lacks):
    text = check(tmp_path, capsys, run, tickets)
    assert all(x in text for x in has) and not any(x in text for x in lacks)


@pytest.mark.parametrize(
    "why, kw, cost",
    [
        ("cost-cap", {}, lambda t, s: 50.0),
        ("cost unknown", {}, lambda t, s: None),
        ("stopped-by-user", STOPPED, lambda t, s: 10.0),
        ("start message not verified", {"msgs": []}, lambda t, s: 10.0),
    ],
)
def test_stop_next_names_the_reason_check_recorded(tmp_path, capsys, why, kw, cost):
    text = check(tmp_path, capsys, OPEN, LIVE, cost=cost, **kw)
    assert f"stopped by No Hands: {why}" in text and f"no_hands.py end {why}" in text
    assert "kill-switch.md § Kill switch steps 1 to 4" in text and "send nothing from the plan" in text


def test_setting_off_is_a_stop_too(tmp_path, capsys):
    assert "stopped by No Hands: setting off" in check(tmp_path, capsys, OPEN, LIVE, setting=(False, 0, 0, ""))
