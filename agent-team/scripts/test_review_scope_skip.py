import pytest

from test_review_scope import CODE, DOC, pr_repo, review_scope


def scope(tmp_path, monkeypatch, capsys, files, args):
    """Run review_scope.main on a repo with these files, the PR head filled in where args has {head}."""
    run, _, head = pr_repo(tmp_path, files)
    monkeypatch.setattr(review_scope, "fetch", lambda *a: None)
    code = review_scope.main([a.format(head=head) for a in args], run=run)
    return code, capsys.readouterr().out, head


@pytest.mark.parametrize(
    "files, code, body",
    [
        # docs-only: the whole skip comment, and nothing else
        ({"docs/x.md": DOC}, 0, "## Security review (pass 2)\n\nSkipped: docs-only diff. review-scope: docs-only at {head}: 1 files\n\nVerdict: PASS\n"),
        ({"README.md": DOC, "docs/y.md": DOC}, 0, "## Security review (pass 2)\n\nSkipped: docs-only diff. review-scope: docs-only at {head}: 2 files\n\nVerdict: PASS\n"),
        # any other class: the usual line, exit 1, no comment
        ({"s.py": CODE(3)}, 1, "review-scope: small at {head}: 3 lines in 1 files\n"),
        ({"docs/x.md": DOC, "s.py": CODE(300)}, 1, "review-scope: full at {head}: 300 lines in 1 files\n"),
    ],
)
def test_skip_comment(tmp_path, monkeypatch, capsys, files, code, body):
    got, out, head = scope(tmp_path, monkeypatch, capsys, files, ["7", "{head}", "--skip-comment", "2"])
    assert (got, out) == (code, body.format(head=head))


@pytest.mark.parametrize(
    "args",
    [
        ["7", "--skip-comment", "2"],  # the head is required
        ["7", "{head}", "--skip-comment"],
        ["7", "{head}", "--skip-comment", "0"],
        ["7", "{head}", "--skip-comment", "x"],
    ],
)
def test_skip_comment_bad_arguments(tmp_path, monkeypatch, capsys, args):
    got, out, _ = scope(tmp_path, monkeypatch, capsys, {"docs/x.md": DOC}, args)
    assert got == 2 and out.startswith("review-scope: cannot read arguments")


def test_without_the_flag_the_output_is_the_class_line(tmp_path, monkeypatch, capsys):
    got, out, head = scope(tmp_path, monkeypatch, capsys, {"docs/x.md": DOC}, ["7", "{head}"])
    assert (got, out) == (0, f"review-scope: docs-only at {head}: 1 files\n")
