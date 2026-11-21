import io
import json

import pytest

import cos_unblocked


def run(monkeypatch, capsys, stdin):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin if isinstance(stdin, str) else json.dumps(stdin)))
    code = cos_unblocked.main([])
    return code, capsys.readouterr().out.splitlines()


def got(state, *blockers, labels=()):
    return {"state": state, "labels": [{"name": x} for x in labels], "relations": {"blockedBy": list(blockers)}}


A, D = {"id": "ABC-1", "state": "Todo"}, {"id": "ABC-9", "state": "In Progress"}  # A is still open in the read: the merge may not have reached the tracker


def test_only_a_backlog_ticket_with_no_other_open_blocker_moves_to_todo(monkeypatch, capsys):
    tickets = {
        "ABC-2": got("Backlog", A),
        "ABC-3": got("Backlog", A, D),
        "ABC-4": got("Backlog", A, labels=["agent-skip"]),
        "ABC-5": got("In Progress", A),
        "ABC-6": {"untrusted": True},
        "ABC-7": {"state": "OPEN", "labels": [], "relations": {"blockedBy": [{"number": 1, "state": "OPEN"}]}},  # GitHub: no status label means Backlog
        "ABC-8": got("Backlog", A, {"number": 12, "state": "CLOSED"}),
    }
    assert run(monkeypatch, capsys, {"merged": "ABC-1", "tickets": tickets}) == (
        0,
        ["todo ABC-2", "stay ABC-3 blocked by ABC-9", "stay ABC-4 agent-skip", "stay ABC-5 state In Progress", "stay ABC-6 untrusted", "todo ABC-7", "todo ABC-8", "unblocked: 7 checked, 3 to Todo"],
    )


@pytest.mark.parametrize("stdin", ["not json", {"tickets": {}}, {"merged": "ABC-1", "tickets": []}, {"merged": "ABC-1", "tickets": {"ABC-2": 5}}])
def test_unusable_stdin_exits_2(monkeypatch, capsys, stdin):
    code, out = run(monkeypatch, capsys, stdin)
    assert code == 2 and out[-1].startswith("unblocked: cannot ")


def test_no_blocked_tickets_is_fine(monkeypatch, capsys):
    assert run(monkeypatch, capsys, {"merged": "ABC-1", "tickets": {}}) == (0, ["unblocked: 0 checked, 0 to Todo"])
