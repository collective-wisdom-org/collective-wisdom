import io
import json
import os

import pytest

import cos_lists

OLD = {"at": "2020-01-01T00:00:00Z", "list": [{"id": "ABC-9"}]}
ENTRIES = [{"id": "ABC-1", "title": "a"}, {"key": "ABC-2", "fields": {"summary": "b"}}]


def run(monkeypatch, capsys, path, stdin, kind="todo"):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin if isinstance(stdin, str) else json.dumps(stdin)))
    code = cos_lists.main(["--file", str(path), kind])
    return code, capsys.readouterr().out.strip()


@pytest.mark.parametrize(
    "stdin, kind, want",
    [
        # a list, an `issues` object and a `tickets` object all save their entries as given (Jira `key` too); the other kind stays
        (ENTRIES, "todo", ENTRIES),
        ({"issues": ENTRIES}, "backlog", ENTRIES),
        ({"tickets": ENTRIES}, "todo", ENTRIES),
        ([{"id": f"ABC-{i}"} for i in range(300)], "backlog", [{"id": f"ABC-{i}"} for i in range(250)]),
    ],
)
def test_saves_one_kind_and_keeps_the_other(monkeypatch, capsys, tmp_path, stdin, kind, want):
    f = tmp_path / "tracker-lists.json"
    other = "backlog" if kind == "todo" else "todo"
    f.write_text(json.dumps({other: OLD, kind: OLD}))
    assert run(monkeypatch, capsys, f, stdin, kind) == (0, f"lists: saved {kind} {len(want)}")
    got = json.loads(f.read_text())
    assert got[kind]["list"] == want and got[other] == OLD
    assert got[kind]["at"].endswith("Z") and len(got[kind]["at"]) == 20
    assert os.listdir(tmp_path) == ["tracker-lists.json"]


def test_a_missing_or_unreadable_file_starts_empty(monkeypatch, capsys, tmp_path):
    f = tmp_path / "tracker-lists.json"
    f.write_text("{not json")
    assert run(monkeypatch, capsys, f, ENTRIES)[0] == 0 and list(json.loads(f.read_text())) == ["todo"]


@pytest.mark.parametrize("stdin", ["not json", {"x": 1}, 5, {"issues": "no"}])
def test_a_bad_shape_writes_nothing_and_exits_2(monkeypatch, capsys, tmp_path, stdin):
    f = tmp_path / "tracker-lists.json"
    code, out = run(monkeypatch, capsys, f, stdin)
    assert code == 2 and out.startswith("lists: cannot ") and not f.exists()


def test_writes_nothing_over_a_non_regular_file_or_into_a_link(monkeypatch, capsys, tmp_path):
    (tmp_path / "dir").mkdir()
    (tmp_path / "real").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "real")
    for target in (tmp_path / "dir", tmp_path / "link" / "tracker-lists.json", tmp_path / "nope" / "tracker-lists.json"):
        code, out = run(monkeypatch, capsys, target, ENTRIES)
        assert code == 2 and out.startswith("lists: cannot ")
    assert os.listdir(tmp_path / "real") == []
