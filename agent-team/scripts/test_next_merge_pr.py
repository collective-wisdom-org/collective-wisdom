"""`merge_pr.py --next`: the last line of a merge prints the After merge steps (merge-pr/SKILL.md); a stop or a failure prints none."""

import copy

import pytest

import merge_pr
from test_merge_pr import fake, green

# change to the PR facts, exit code, whether a next: follows
CASES = [
    (lambda f: None, 0, True),                                                              # merged
    (lambda f: f.update(state="MERGED", mergeCommit={"oid": "m" * 40}), 0, True),           # already merged
    (lambda f: f.update(approved="bbbbbbb"), 1, False),                                     # a gate stops: judgement
    (lambda f: f.update(login="agent"), 1, False),
]


@pytest.mark.parametrize("change, code, has_next", CASES)
def test_next_follows_only_a_merged_last_line(capsys, monkeypatch, change, code, has_next):
    monkeypatch.setattr(merge_pr, "publish", lambda *a: None)
    f = green()
    change(f)
    assert merge_pr.main(["7", f["approved"]], fake(copy.deepcopy(f))[0]) == code
    plain = capsys.readouterr().out.splitlines()
    assert merge_pr.main(["7", "--next", f["approved"]], fake(copy.deepcopy(f))[0]) == code  # the flag may sit anywhere after the PR number
    out = capsys.readouterr().out.splitlines()
    if has_next:
        assert out[:-1] == plain and out[-2].startswith("merge-pr: ") and out[-1].startswith("next: ")
        assert "`set-state` the linked ticket to Done" in out[-1] and out[-1].endswith("Make `MERGED #7` the last line of the report.")
        assert "merge-pr: warn" in out[-1] and "don't offer or run cleanup" in out[-1]
    else:
        assert out == plain


def test_a_failed_cleanup_after_the_merge_has_no_next(capsys, monkeypatch):
    """Exit 2 after the merge (`merge-pr: merged #7 as <sha>; cannot ...`) is not a finished merge: no After merge steps."""
    monkeypatch.setattr(merge_pr, "publish", lambda *a: None)
    monkeypatch.setattr(merge_pr, "cleanup", lambda f, run: (_ for _ in ()).throw(RuntimeError("delete the branch")))
    f = green()
    assert merge_pr.main(["7", f["approved"], "--next"], fake(f)[0]) == 2
    assert not [x for x in capsys.readouterr().out.splitlines() if x.startswith("next: ")]


def test_bad_arguments_print_the_same_usage_line_with_the_flag(capsys):
    assert merge_pr.main(["x", "--next"]) == 2
    out = capsys.readouterr().out
    assert out.startswith("merge-pr: cannot read arguments; usage:") and "next:" not in out
