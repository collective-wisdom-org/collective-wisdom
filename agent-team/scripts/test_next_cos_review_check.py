"""`cos_review_check.py --route --next`: each route line has its `next:` text (approvals.md § Approval requests)."""

import re

import pytest

import cos_review_check

LINES = [
    ("route awaiting-merge", ["`awaiting-merge`", "`headSha`"]),
    ("route awaiting-merge (unreadable: bad PR data)", ["`awaiting-merge`"]),
    ("route awaiting-review needs bob", ["`awaiting-review`", "Waiting on: bob (GitHub review)", "approve N", "{since}", "waits for `awaiting-merge`"]),
    ("route awaiting-review needs a teammate", ["Waiting on: a teammate (GitHub review)"]),
    ("route moved head ccccccc", ["send the child back"]),
]


@pytest.mark.parametrize("line, has", LINES)
def test_each_route_line_has_its_next(monkeypatch, capsys, line, has):
    monkeypatch.setattr(cos_review_check, "route", lambda n, head, prs: line)
    assert cos_review_check.main(["--route", "5", "--head", "abcdef1", "--next"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == line and out[1].startswith("next: ") and len(out) == 2
    assert all(x in out[1] for x in has)
    assert "<names>" not in out[1] and not re.search(r"\{(?!since\})[a-z]+\}", out[1])


def test_without_the_flag_there_is_no_next(monkeypatch, capsys):
    monkeypatch.setattr(cos_review_check, "route", lambda n, head, prs: "route awaiting-merge")
    assert cos_review_check.main(["--route", "5", "--head", "abcdef1"]) == 0
    assert capsys.readouterr().out == "route awaiting-merge\n"


def test_next_without_route_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as e:
        cos_review_check.main(["--next"])
    assert e.value.code == 2
