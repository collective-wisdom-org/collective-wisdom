"""`ci_review.py --next`: every output the CLI can end on has its `next:` text (open-pr/reference.md § CI review mode); without the flag the output is unchanged."""

import json

import pytest

import ci_review
from test_ci_review import ci_mode, page, run_with, thread  # noqa: F401  (ci_mode is a fixture)

DONE = page([thread(resolved=True, last="Fixed in a1. ok")])
OPEN = page([thread()])
RESOLVED = json.dumps({"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}})


@pytest.mark.parametrize(
    "argv, pages, code, kind",
    [
        (["list", "5"], [OPEN], 1, "unresolved"),
        (["list", "5"], [DONE], 0, "clear"),
        (["list", "5"], [ci_review.CiError("gh exited 1")], 2, "cannot"),
        (["list", "x"], [], 2, "cannot"),
        (["resolve", "PRRT_1"], [RESOLVED], 0, "resolved"),
        (["resolve", "PRRT_1"], [ci_review.CiError("gh exited 1")], 2, "cannot"),
    ],
)
def test_every_ending_has_its_next(ci_mode, capsys, argv, pages, code, kind):  # noqa: F811
    assert ci_review.main(argv, run_with(list(pages))[0]) == code
    plain = capsys.readouterr().out.splitlines()
    assert ci_review.main([*argv, "--next"], run_with(list(pages))[0]) == code
    out = capsys.readouterr().out.splitlines()
    assert out[:-1] == plain and out[-1] == "next: " + ci_review.NEXT[kind].format(n="5")
    assert not any(l.startswith("next: ") for l in plain)
