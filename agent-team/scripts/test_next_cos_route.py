import io
import json

import pytest

import cos_route
import project_config

ME = "me"
FULL = {"ABC-8": {"stage": "build", "parentThreadId": ME}, "ABC-9": {"stage": "build", "parentThreadId": ME}}


def tk(stage, **kw):
    return {"stage": stage, "parentThreadId": ME, **kw}


# ticket, others, argv: one row per kind of line the script prints
ROWS = [
    (tk("awaiting-build"), {}, ["approve-spec"]),  # stage, run-wait, send
    (tk("awaiting-merge", parentThreadId=None), {}, ["approve-merge"]),  # stage, moving, merge-wait, send
    (tk("awaiting-build"), FULL, ["approve-spec"]),  # stage, queue
    (tk("awaiting-review"), {}, ["changes"]),  # stage, send
    (tk("awaiting-review", parentThreadId="old"), {}, ["changes"]),  # fallback, continuation
    (tk("awaiting-review", parentThreadId="old"), {}, ["conflict-stand"]),  # fallback, set, continuation
    (tk("awaiting-build"), {}, ["approve-merge"]),  # no
    (tk("awaiting-build"), {}, ["approve-spec", "--relay"]),  # no --thread: cannot
    (tk("awaiting-review"), {}, ["changes", "--relay"]),  # a relay block comes last and has no next
]


def run(tmp_path, capsys, monkeypatch, ticket, others, argv):
    monkeypatch.setattr(project_config, "review_after_conflict", lambda: "off")
    monkeypatch.setattr("sys.stdin", io.StringIO("words"))
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"chiefThreadId": ME, "tickets": {"ABC-1": ticket, **others}}))
    code = cos_route.main(["ABC-1", argv[0], "--file", str(f), *argv[1:]])
    return code, capsys.readouterr().out.splitlines()


def test_every_line_has_its_next_text_and_the_output_without_the_flag_is_unchanged(tmp_path, capsys, monkeypatch):
    seen = set()
    for i, (ticket, others, argv) in enumerate(ROWS):
        code, out = run(tmp_path, capsys, monkeypatch, ticket, others, [*argv, "--next"])
        plain_code, plain = run(tmp_path, capsys, monkeypatch, ticket, others, argv)
        assert plain_code == code and not any(l.startswith("next: ") for l in plain)
        assert [l for l in out if not l.startswith("next: ")] == plain
        last = next(l for l in plain if l.startswith("route: "))
        relay_at = plain.index("relay:") if "relay:" in plain else len(plain)
        k = 0
        for line in plain[:relay_at]:
            tag = cos_route.tag_of(line, last)
            assert tag, f"no next text for {line!r}"
            k = out.index(line, k)
            assert out[k + 1] == f"next: {cos_route.next_text(line, last, argv[0])}"
            seen.add(tag)
        if "relay:" in plain:  # the relay block runs to the end and has no next: line
            assert out[out.index("relay:"):] == plain[relay_at:]
    assert seen | {"route-cannot"} == set(cos_route.NEXT), "every row of the NEXT table is printed by some line"


def test_the_caller_note_is_added_for_a_spec_approval(tmp_path, capsys, monkeypatch):
    _, out = run(tmp_path, capsys, monkeypatch, tk("awaiting-build"), {}, ["approve-spec", "--next"])
    assert any(l.startswith("next: ") and "Models switch" in l for l in out)
    _, out = run(tmp_path, capsys, monkeypatch, tk("awaiting-review"), {}, ["changes", "--next"])
    assert not any("Models switch" in l for l in out)


@pytest.mark.parametrize("argv", [["ABC-x", "changes"], ["ABC-1", "nonsense"], ["ABC-99", "changes"]])
def test_a_cannot_line_has_its_next_text(tmp_path, capsys, monkeypatch, argv):
    f = tmp_path / "state.json"
    f.write_text(json.dumps({"chiefThreadId": ME, "tickets": {"ABC-1": tk("awaiting-review")}}))
    try:
        code = cos_route.main([*argv, "--file", str(f), "--next"])
    except SystemExit as e:
        code = e.code
    out = capsys.readouterr().out.splitlines()
    assert code == 2 and out[0].startswith("route: cannot ") and out[1] == f"next: {cos_route.NEXT['route-cannot']}"
