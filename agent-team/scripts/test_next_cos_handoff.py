"""`cos_handoff.py --next`: the step after the block, `reject:` and each exit 2 line (continuation.md § Continuation child); no flag, no `next:`."""

import json

import pytest

import cos_handoff

HEAD = "a1b2c3d4e5f6" + "0" * 28
PR = {"url": "https://github.com/example/app/pull/14", "headRefOid": HEAD, "statusCheckRollup": [], "login": "bot", "comments": []}
GOOD = {"stage": "awaiting-merge", "branch": "feat/abc-1-x", "pr": 14, "headSha": HEAD, "status": "s"}


def run(tmp_path, capsys, ticket, pr, flags):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {"ABC-1": ticket}}))
    argv = ["ABC-1", "--file", str(state), *flags]
    if pr is not None:
        prf = tmp_path / "pr.json"
        prf.write_text(json.dumps(pr))
        argv += ["--pr", str(prf)]
    try:
        code = cos_handoff.main(argv)
    except SystemExit as e:
        code = e.code
    return code, capsys.readouterr().out.splitlines()


# ticket, pr file, exit code, last line before next, words in the next: text
CASES = [
    (GOOD, PR, 0, None, ["replaces the template's `Spec: … PR: …` line"]),
    ({**GOOD, "branch": "main"}, None, 1, "reject: branch main", ["Mark the ticket `blocked`", "start no child"]),
    (GOOD, {"headRefOid": "zz"}, 2, "cos_handoff: cannot read PR #14", ["as written", "Handoff block unavailable for <PREFIX>-N"]),
    ({**GOOD, "pr": None, "stage": "bad stage"}, None, 1, "reject: stage bad stage", ["Mark the ticket `blocked`"]),
]


@pytest.mark.parametrize("ticket, pr, code, last, has", CASES)
def test_each_outcome_has_its_next(tmp_path, capsys, ticket, pr, code, last, has):
    plain_code, plain = run(tmp_path, capsys, ticket, pr, [])
    got_code, out = run(tmp_path, capsys, ticket, pr, ["--next"])
    assert plain_code == got_code == code
    assert out[:-1] == plain and out[-1].startswith("next: ") and all(x in out[-1] for x in has)
    if last:
        assert out[-2] == last


def test_other_exit_2_lines_say_start_nothing(tmp_path, capsys):
    state = tmp_path / "missing.json"
    with pytest.raises(SystemExit) as e:
        cos_handoff.main(["ABC-1", "--file", str(state), "--next"])
    assert e.value.code == 2
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "cos_handoff: no state file" and out[1].startswith("next: Start no child") and "quote the line" in out[1]
