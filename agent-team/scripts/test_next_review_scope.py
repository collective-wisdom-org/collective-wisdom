import pytest

from test_review_scope import CODE, DOC, pr_repo, review_scope

# files, args (--next added), exit code, class of the line, the tag the next text comes from
ROWS = [
    ({"docs/x.md": DOC}, ["7", "{head}"], 0, "docs-only"),
    ({"s.py": CODE(3)}, ["7", "{head}"], 0, "small"),
    ({"s.py": CODE(300)}, ["7", "{head}"], 0, "full"),
    ({"docs/x.md": DOC}, ["7", "{head}", "--skip-comment", "1"], 0, "skip"),
    ({"s.py": CODE(300)}, ["7", "{head}", "--skip-comment", "1"], 1, "full"),
    ({"s.py": CODE(3)}, ["x"], 2, "args"),
]


def run_scope(tmp_path, monkeypatch, capsys, files, args, flag):
    run, _, head = pr_repo(tmp_path, files)
    monkeypatch.setattr(review_scope, "fetch", lambda *a: None)
    code = review_scope.main([a.format(head=head) for a in args] + flag, run=run)
    return code, capsys.readouterr().out.splitlines(), head


def test_every_output_has_its_next_text_and_the_output_without_the_flag_is_unchanged(tmp_path, monkeypatch, capsys):
    seen = set()
    for i, (files, args, want_code, tag) in enumerate(ROWS):
        sub = tmp_path / str(i)
        sub.mkdir()
        code, out, head = run_scope(sub, monkeypatch, capsys, files, args, ["--next"])
        assert code == want_code
        assert out[-1] == "next: " + review_scope.NEXT[tag].format(n="7", head=head)
        assert out.count(out[-1]) == 1 and not any(l.startswith("next: ") for l in out[:-1])
        seen.add(tag)
        sub2 = tmp_path / f"{i}-plain"
        sub2.mkdir()
        plain_code, plain, head2 = run_scope(sub2, monkeypatch, capsys, files, args, [])
        assert plain_code == want_code and [l.replace(head2, head) for l in plain] == out[:-1]  # each repo has its own head SHA
    assert seen == set(review_scope.NEXT) - {"cannot"}, "every class and the argument error is exercised"


def test_a_failed_read_has_a_next_text(capsys):
    def run(cmd):
        raise review_scope.CmdError("bad object")

    assert review_scope.main(["7", "0" * 40, "--next"], run=run) == 2
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("review-scope: cannot classify") and out[1] == f"next: {review_scope.NEXT['cannot']}"
