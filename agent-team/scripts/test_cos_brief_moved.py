import pytest

import cos_brief

OID = "a" * 40
OLD = "c" * 40
NOTE = f"Head moved to {OID} by merging main; PR diff unchanged since {OLD}. Reviews from {OLD} stand."


@pytest.mark.parametrize(
    "who, oid, counts",
    [
        ("sam", OID, True),
        ("me", OID, False),
        ("sam", "b" * 40, False),
    ],
)
def test_moved_line_counts_the_note_only_from_the_given_login(who, oid, counts):
    comments = [{"body": NOTE, "url": "https://x/n", "author": {"login": who}}]
    got = cos_brief.moved_line(oid, comments, "sam")
    assert (got is not None) == counts
    if counts:
        assert "since ccccccc" in got
