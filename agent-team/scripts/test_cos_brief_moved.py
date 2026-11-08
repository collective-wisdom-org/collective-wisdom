import pytest

import cos_brief

OID = "a" * 40
OLD = "c" * 40
NOTE = f"Head moved to {OID} by merging main; PR diff unchanged since {OLD}. Reviews from {OLD} stand."
DOCS = f"Head moved to {OID}; PR diff changed only in docs files since {OLD}: ['README.md']. Reviews from {OLD} stand."


@pytest.mark.parametrize(
    "note, want",
    [
        (NOTE, "head moved by merging "),
        (DOCS, "head moved by docs-file changes only since ccccccc; reviews stand https://x/n"),
        (f"Head moved to {'b' * 40}; PR diff changed only in docs files since {OLD}: []. Reviews from {OLD} stand.", None),
    ],
)
def test_moved_line_words_each_note_and_skips_one_that_misses_the_head(note, want):
    got = cos_brief.moved_line(OID, [{"body": note, "url": "https://x/n", "author": {"login": "cw-builder"}}], "cw-builder")
    assert (got is None) if want is None else got.startswith(want)


@pytest.mark.parametrize(
    "who, oid, counts",
    [
        ("cw-builder", OID, True),
        ("me", OID, False),
        ("cw-builder", "b" * 40, False),
    ],
)
def test_moved_line_counts_the_note_only_from_the_given_login(who, oid, counts):
    comments = [{"body": NOTE, "url": "https://x/n", "author": {"login": who}}]
    got = cos_brief.moved_line(oid, comments, "cw-builder")
    assert (got is not None) == counts
    if counts:
        assert "since ccccccc" in got
