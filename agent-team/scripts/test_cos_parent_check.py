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
        ("build", "NEW", [], 0),
        ("build", "OLD", ["full ABC-1 old-parent OLD"], 1),
        ("build", None, ["full ABC-1 unknown-parent"], 1),
        ("awaiting-merge", "OLD", ["idle ABC-1 old-parent OLD"], 1),
    ],
)
def test_parent_comparison(tmp_path, capsys, stage, parent, expected, code):
    ticket = {"stage": stage}
    if parent:
        ticket["parentThreadId"] = parent
    state = {"tickets": {"ABC-1": ticket}}
    f = tmp_path / "state.json"
    f.write_text(json.dumps(state))
    assert cos_parent_check.main(["--thread", "NEW", "--file", str(f)]) == code
    out = capsys.readouterr().out.splitlines()
    assert out[:-1] == expected


@pytest.mark.parametrize(
    "state, code, first",
    [
        ({"tickets": {"ABC-1\nfull EVIL": {"stage": "build"}}}, 2, "cos_parent_check: unreadable state file"),
    ],
)
def test_never_print_odd_ids(tmp_path, capsys, state, code, first):
    f = tmp_path / "state.json"
    f.write_text(json.dumps(state))
    assert cos_parent_check.main(["--thread", "NEW", "--file", str(f)]) == code
    assert capsys.readouterr().out.splitlines()[0] == first
