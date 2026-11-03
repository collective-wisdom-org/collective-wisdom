import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "cos_parent_check", Path(__file__).with_name("cos_parent_check.py")
)
cos_parent_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_parent_check)


@pytest.mark.parametrize(
    "stage, parent, expected, code",
    [
        ("build", "NEW", ["archive OLD"], 0),
        ("build", "OLD", ["full ABC-1 old-parent OLD", "keep OLD (ABC-1)"], 1),
        ("build", None, ["full ABC-1 unknown-parent", "keep OLD (unknown parent: ABC-1)"], 1),
        ("awaiting-merge", "OLD", ["idle ABC-1 old-parent OLD", "keep OLD (ABC-1)"], 1),
    ],
)
def test_parent_comparison(tmp_path, capsys, stage, parent, expected, code):
    ticket = {"stage": stage}
    if parent:
        ticket["parentThreadId"] = parent
    state = {
        "retiredThreads": [{"threadId": "OLD", "archivedAt": None}],
        "tickets": {"ABC-1": ticket},
    }
    f = tmp_path / "state.json"
    f.write_text(json.dumps(state))
    assert cos_parent_check.main(["--thread", "NEW", "--file", str(f)]) == code
    out = capsys.readouterr().out.splitlines()
    assert out[:-1] == expected


def test_older_archived_holder_blocks_newer_entry(tmp_path, capsys):
    state = {
        "retiredThreads": [
            {"threadId": "A", "archivedAt": "2026-11-02T10:00:00Z"},
            {"threadId": "B", "archivedAt": None},
        ],
        "tickets": {"ABC-1": {"stage": "build", "parentThreadId": "A"}},
    }
    f = tmp_path / "state.json"
    f.write_text(json.dumps(state))
    assert cos_parent_check.main(["--thread", "NEW", "--file", str(f)]) == 1
    assert "keep B (ABC-1)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "state, code, first",
    [
        ({"retiredThreads": [{"threadId": "NEW"}], "tickets": {}}, 0, "keep NEW (current thread)"),
        ({"tickets": {"ABC-1\narchive EVIL": {"stage": "build"}}}, 2, "cos_parent_check: unreadable state file"),
    ],
)
def test_never_archive_current_thread_or_print_odd_ids(tmp_path, capsys, state, code, first):
    f = tmp_path / "state.json"
    f.write_text(json.dumps(state))
    assert cos_parent_check.main(["--thread", "NEW", "--file", str(f)]) == code
    assert capsys.readouterr().out.splitlines()[0] == first
