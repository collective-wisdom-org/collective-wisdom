import json

import pytest

import cos_merge_wait as w

MERGE = {"stage": "merge", "pr": 7}


@pytest.mark.parametrize(
    "ticket, gh, want",
    [
        (MERGE, "MERGED", ("merge-wait: ABC-1 #7 merged", 0)),
        (MERGE, "CLOSED", ("merge-wait: ABC-1 #7 closed", 0)),
        (MERGE, "OPEN", None),
        (MERGE, None, None),
        ({**MERGE, "stage": "build"}, "OPEN", ("merge-wait: ABC-1 left merge", 0)),
        (None, None, ("merge-wait: ABC-1 left merge", 0)),
        ({"stage": "merge"}, "MERGED", ("merge-wait: cannot find an integer pr", 2)),
        ({"stage": "merge", "pr": "7"}, None, ("merge-wait: cannot find an integer pr", 2)),
    ],
)
def test_decide(ticket, gh, want):
    assert w.decide("ABC-1", ticket, gh) == want


def fake_wait(reads, every=30, limit=1800, ticket=MERGE):
    """Run wait() against scripted gh replies; a clock that only sleep moves. Returns (result, reads used)."""
    now, replies = [0], iter(reads)
    try:
        out = w.wait("ABC-1", lambda: ticket, every, limit, gh=lambda pr: next(replies), clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s))
    except w.Cannot as e:
        out = (str(e), 2)
    return out, len(reads) - len(list(replies))


OPEN, MERGED = json.dumps({"state": "OPEN"}), json.dumps({"state": "MERGED"})


@pytest.mark.parametrize(
    "reads, limit, want, used",
    [
        ([OPEN, OPEN, MERGED], 1800, ("merge-wait: ABC-1 #7 merged", 0), 3),
        ([None, "not json", OPEN, None, None, MERGED], 1800, ("merge-wait: ABC-1 #7 merged", 0), 6),  # a good read resets the failure count
        ([None, "{", None, "[]", None, OPEN], 1800, ("read the PR from GitHub 5 times in a row", 2), 5),
        ([OPEN] * 5, 90, ("merge-wait: ABC-1 #7 still open after 1m", 1), 3),
    ],
)
def test_wait_loop(reads, limit, want, used):
    assert fake_wait(reads, limit=limit) == (want, used)
