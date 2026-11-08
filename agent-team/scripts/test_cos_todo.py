import io
import json

import pytest

import cos_todo


def t(i, priority=None, at="2026-11-01T00:00:00Z", labels=(), **kw):
    return {"id": f"ABC-{i}", "priority": priority, "createdAt": at, "labels": [{"name": x} for x in labels], **kw}


def run(monkeypatch, capsys, stdin, *flags):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin if isinstance(stdin, str) else json.dumps(stdin)))
    code = cos_todo.main(list(flags))
    return code, capsys.readouterr().out.splitlines()


@pytest.mark.parametrize(
    "tickets, want",
    [
        # agent-skip dropped; priority Urgent to Low then none; ties by oldest createdAt, then list order
        (
            [t(1, "Low"), t(2), t(3, {"name": "High", "value": 2}), t(4, 1), t(5, "Medium", at="2026-11-02T00:00:00Z"),
             t(6, "Medium", at="2026-10-01T00:00:00Z"), t(7, "Urgent", labels=["agent-skip"]), t(8, labels=["priority:high"]), t(9)],
            ["get ABC-4", "get ABC-3", "get ABC-8", "get ABC-6", "get ABC-5", "get ABC-1", "get ABC-2", "get ABC-9"],
        ),
        # a ticket with no createdAt goes after its equals
        ([t(1, "High", at=None), t(2, "High")], ["get ABC-2", "get ABC-1"]),
        # a GitHub issue list: numbers and priority labels
        ({"issues": [{"number": 7, "labels": [{"name": "priority:low"}]}, {"number": 8, "labels": [{"name": "priority:urgent"}]}]}, ["get ABC-8", "get ABC-7"]),
        ([], ["todo: none"]),
        ([t(1, labels=["agent-skip"])], ["todo: none"]),
    ],
)
def test_first_pass_orders_and_drops_agent_skip(monkeypatch, capsys, tickets, want):
    assert run(monkeypatch, capsys, tickets) == (0, want)


def got(*blockers, rel="blockedBy"):
    return {"relations": {rel: list(blockers)}}


@pytest.mark.parametrize(
    "tickets, tickets_got, want",
    [
        # an open blocker drops the ticket; a closed one does not; a bare id counts as open
        (
            [t(1, "High"), t(2, "High", at="2026-11-02T00:00:00Z"), t(3, "Low"), t(4, "Low", at="2026-11-02T00:00:00Z"), t(5)],
            {"ABC-1": got({"id": "ABC-9", "state": "In Progress"}), "ABC-2": got({"id": "ABC-9", "state": "Done"}), "ABC-3": got({"id": "ABC-8", "state": "Canceled"}, rel="blockers"),
             "ABC-4": got("ABC-7"), "ABC-5": {"relations": [{"type": "blocked_by", "issue": {"id": "ABC-6", "state": "Todo"}}, {"type": "related", "issue": {"id": "ABC-6", "state": "Todo"}}]}},
            ["start ABC-2", "start ABC-3"],
        ),
        ([t(1), t(2)], {"ABC-1": {"relations": None}, "ABC-2": {"relations": {"blocks": [{"id": "ABC-1", "state": "Todo"}]}}}, ["start ABC-1", "start ABC-2"]),
        # github blockers are issues with OPEN or CLOSED
        ([t(1), t(2)], {"ABC-1": got({"number": 3, "state": "OPEN"}), "ABC-2": got({"number": 3, "state": "CLOSED", "stateReason": "COMPLETED"})}, ["start ABC-2"]),
        # `state` and `status` name the blocker's state alike; a bare number has none and stays open
        ([t(1), t(2), t(3)], {"ABC-1": got({"number": 3, "state": "closed"}), "ABC-2": got({"id": "ABC-9", "status": "Done"}), "ABC-3": got(3)}, ["start ABC-1", "start ABC-2"]),
        ([t(1)], {"ABC-1": got({"id": "ABC-9", "state": "Todo"})}, ["todo: none"]),
        ([], {}, ["todo: none"]),
        ([t(1, labels=["agent-skip"])], {}, ["todo: none"]),
    ],
)
def test_second_pass_drops_open_blockers(monkeypatch, capsys, tickets, tickets_got, want):
    assert run(monkeypatch, capsys, {"list": tickets, "tickets": tickets_got}, "--relations") == (0, want)


@pytest.mark.parametrize(
    "stdin, flags",
    [("not json", ()), ({"x": 1}, ()), ([t(1)], ("--relations",)), ({"list": [t(1)], "tickets": {}}, ("--relations",)), ({"list": 5, "tickets": {}}, ("--relations",))],
)
def test_unusable_stdin_exits_2(monkeypatch, capsys, stdin, flags):
    code, out = run(monkeypatch, capsys, stdin, *flags)
    assert code == 2 and out[-1].startswith("todo: cannot ")
