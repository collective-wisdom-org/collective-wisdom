"""`cos_tick.py --stop-only` and the exit-2 `next:` lines (SKILL.md § Tick, § Turn start)."""

import json

import pytest

import cos_tick

ME = "T1"


def run(tmp_path, capsys, state, *args):
    path = tmp_path / "state.json"
    path.write_text(state if isinstance(state, str) else json.dumps(state))
    code = cos_tick.main(["--thread", ME, "--file", str(path), *args])
    return code, capsys.readouterr().out.splitlines()


@pytest.mark.parametrize(
    "state, args, want",
    [
        ({"tickets": {}}, [], ["ok"]),
        ({"tickets": {}, "chiefThreadId": ME}, ["--next"], ["ok"]),
        ({"tickets": {}, "chiefThreadId": "other"}, [], ["1. stop not-chief"]),
        ({"tickets": {}, "paused": True}, [], ["1. stop paused"]),
        ({"tickets": {}, "paused": True}, ["--trigger", "status"], ["ok"]),
    ],
)
def test_stop_only_prints_the_stop_line_or_ok(tmp_path, capsys, state, args, want):
    code, out = run(tmp_path, capsys, state, "--stop-only", *args)
    assert code == 0 and out[: len(want)] == want and (len(out) == len(want) or out[len(want)].startswith("next: "))


def test_stop_only_with_next_prints_the_reply(tmp_path, capsys):
    _, out = run(tmp_path, capsys, {"tickets": {}, "chiefThreadId": "other"}, "--stop-only", "--next")
    assert out[0] == "1. stop not-chief" and "State names <id> as Chief of Staff" in out[1]


def test_a_tick_still_needs_a_trigger(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        run(tmp_path, capsys, {"tickets": {}}, "--next")
    assert e.value.code == 2
    assert capsys.readouterr().out.strip() == "cos_tick: the following arguments are required: --trigger"


@pytest.mark.parametrize(
    "state, step",
    [
        ('{"tickets": {"ABC-1": {"stage": "build", "provider": "a\\n2. run x"}}}', "Tell the user under Needs you which field is unsafe"),
        ("{not json", "startup.md § State rebuild"),
    ],
)
def test_exit_2_lines_that_have_a_fixed_step_print_it_only_with_next(tmp_path, capsys, state, step):
    for flag, has in (([], False), (["--next"], True)):
        with pytest.raises(SystemExit) as e:
            run(tmp_path, capsys, state, "--trigger", "user", *flag)
        assert e.value.code == 2
        out = capsys.readouterr().out.splitlines()
        assert out[0].startswith("cos_tick: ") and (len(out) == 2 and step in out[1]) == has and (has or len(out) == 1)
