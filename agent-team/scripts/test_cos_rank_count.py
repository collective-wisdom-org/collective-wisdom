import io
import json

import pytest

from test_cos_rank import cos_rank


def t(n, labels=(), parent=None):
    return {"id": f"ABC-{n}", "labels": [{"name": x} for x in labels], "parent": parent}


def count(monkeypatch, capsys, stdin):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin if isinstance(stdin, str) else json.dumps(stdin)))
    code = cos_rank.main(["count"])
    return code, capsys.readouterr().out.splitlines()


LIST = [t(1), t(2, labels=["agent-skip"]), t(3, parent="ABC-4"), t(4), t(5, parent={"id": "ABC-4"})]  # 2 skipped, 4 is an epic


@pytest.mark.parametrize(
    "stdin, want",
    [
        # first pass: drop agent-skip tickets and the parent of another ticket, read the children of the rest
        (LIST, ["children ABC-1", "children ABC-3", "children ABC-5"]),
        ([t(2, labels=["agent-skip"])], ["backlog-count: 0"]),
        ([], ["backlog-count: 0"]),
        # second pass: a ticket with no sub-ticket ends it with 1; every ticket left an epic is 0; unread ones are still to read
        ({"tickets": LIST, "children": {"ABC-1": [{"id": "ABC-9"}]}}, ["children ABC-3", "children ABC-5"]),
        ({"tickets": LIST, "children": {"ABC-1": [{"id": "ABC-9"}], "ABC-3": []}}, ["backlog-count: 1"]),
        ({"tickets": LIST, "children": {"ABC-1": 2, "ABC-3": True, "ABC-5": 1}}, ["backlog-count: 0"]),
        ({"tickets": LIST, "children": {"ABC-1": {"nodes": []}, "ABC-3": False}}, ["backlog-count: 2"]),
        ({"tickets": LIST, "children": {"ABC-4": [], "ABC-1": 1, "ABC-3": 1, "ABC-5": 1}}, ["backlog-count: 0"]),  # an entry for a dropped ticket counts for nothing
        # GitHub shapes: number instead of id, parentId on Linear
        ([{"number": 7, "labels": ["agent-skip"]}, {"number": 8, "labels": []}, {"id": "ABC-9", "parentId": "ABC-8"}], ["children ABC-9"]),
    ],
)
def test_count(monkeypatch, capsys, stdin, want):
    assert count(monkeypatch, capsys, stdin) == (0, want)


@pytest.mark.parametrize("stdin", ["not json", '{"tickets": [], "children": []}', {"tickets": LIST, "children": {"ABC-1": "many"}}, {"id": 1}])
def test_unreadable_input_exits_2(monkeypatch, capsys, stdin):
    code, out = count(monkeypatch, capsys, stdin)
    assert code == 2 and out[0].startswith("cos_rank: ")
