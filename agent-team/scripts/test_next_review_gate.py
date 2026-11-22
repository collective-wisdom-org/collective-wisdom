import pytest

from test_review_gate_lines import ALICE, comment, docs, pr, review_gate, run_gate

BAD = pr(extra=[comment("## Code review\n\nx\n\n**Verdict:** CHANGES NEEDED\n", "2026-11-02T10:10:00Z")])

# argv, facts, mode, exit code: one row per kind of line the script prints (None facts: gh fails)
ROWS = [
    (["7"], pr([docs("d", "2026-11-02T10:20:00Z")], [ALICE]), "agents", 0),  # reviews-needed, docs-check done, pass
    (["7"], pr(), "agents", 0),  # docs-check run
    (["7"], pr(late=True), "agents", 0),  # the note text, `note`
    (["7"], BAD, "agents", 0),  # rerun
    (["7"], pr(), "ci", 0),  # ci
    (["7"], None, "agents", 2),  # cannot read PR
    (["x"], pr(), "agents", 2),  # cannot read arguments
]


def gate(tmp_path, monkeypatch, capsys, argv, facts, mode):
    if facts is not None:
        code, out, _ = run_gate(tmp_path, monkeypatch, capsys, argv, facts, mode)
        return code, out
    md = tmp_path / "project.md"
    md.write_text(f"| Key | Value |\n|---|---|\n| Review mode | `{mode}` |\n")
    monkeypatch.setenv("PROJECT_MD", str(md))

    def broken(cmd, input=None):
        raise review_gate.merge_pr.CmdError("gh failed")

    return review_gate.main(argv, broken), capsys.readouterr().out.splitlines()


def test_every_line_has_its_next_text_and_the_output_without_the_flag_is_unchanged(tmp_path, monkeypatch, capsys):
    seen = set()
    for i, (argv, facts, mode, want_code) in enumerate(ROWS):
        sub = tmp_path / str(i)
        sub.mkdir()
        code, out = gate(sub, monkeypatch, capsys, [*argv, "--next"], facts, mode)
        assert code == want_code
        for k, line in enumerate(out):
            if line.startswith("next: "):
                continue
            nxt = out[k + 1] if k + 1 < len(out) else ""
            if line.startswith(review_gate.NO_NEXT):
                assert not nxt.startswith("next: "), line
            else:
                text = review_gate.next_for(line)
                assert text, f"no next text for {line!r}"
                assert nxt == f"next: {text}"
                seen.add(next(p for p, _ in review_gate.NEXT if line.startswith(p)))
        plain_code, plain = gate(sub, monkeypatch, capsys, argv, facts, mode)
        assert plain_code == want_code
        # --next adds the --lines lines and the next: lines, and changes nothing else
        assert [l for l in out if not l.startswith(("next: ", "reviews-needed: ", "docs-check: "))] == [l for l in plain if not l.startswith(("reviews-needed: ", "docs-check: "))]
        assert not any(l.startswith("next: ") for l in plain)
    assert seen == {p for p, _ in review_gate.NEXT}, "every row of the NEXT table is printed by some line"
