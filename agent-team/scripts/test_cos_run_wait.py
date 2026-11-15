import pytest

import cos_run_wait as w

IN = {"stage": "build", "childThreadId": "c1", "lastPosition": 4}
RUNNING, DONE, NEW = ("r2", "running"), ("r1", "completed"), ("r2", "completed")


def fake_wait(start, rounds, limit=6600, first=IN):
    """Run wait() against scripted rounds of (ticket, newest run, marker); a clock that only sleep moves. Returns (result, positions asked)."""
    now, asked = [0], []
    tickets, stores = iter([first] + [t for t, _, _ in rounds]), iter([(start, None)] + [(r, m) for _, r, m in rounds])

    def store(thread, after):
        asked.append(after)
        return next(stores)

    try:
        out = w.wait("ABC-1", lambda: next(tickets), store, 30, limit, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s))
    except w.Cannot as e:
        out = (str(e), 2)
    return out, asked[1:]


@pytest.mark.parametrize(
    "start, rounds, want",
    [
        (DONE, [(IN, RUNNING, None), (IN, RUNNING, None), (None, None, None)], ("run-wait: ABC-1 left build", 0)),  # the finish notice moved the ticket
        (DONE, [({**IN, "stage": "build-queued"}, RUNNING, None)], ("run-wait: ABC-1 left build", 0)),
        (DONE, [({**IN, "childThreadId": "c2"}, RUNNING, None)], ("run-wait: ABC-1 left build", 0)),
        (DONE, [(IN, DONE, "BUILD READY"), (IN, None, None), (IN, RUNNING, None), (IN, NEW, None), (None, None, None)], ("run-wait: ABC-1 left build", 0)),  # an old run and a marker with no new run
        (DONE, [(IN, ("r2", "failed"), None)], ("run-wait: ABC-1 run failed", 0)),
        (DONE, [(IN, ("r2", "cancelled"), None)], ("run-wait: ABC-1 run cancelled", 0)),
        (RUNNING, [(IN, RUNNING, None), (IN, ("r2", "interrupted"), None)], ("run-wait: ABC-1 run interrupted", 0)),
        (DONE, [(IN, NEW, None), (IN, RUNNING, None), (IN, NEW, "MERGE READY"), (IN, NEW, "MERGE READY")], ("run-wait: ABC-1 MERGE READY", 0)),  # no marker keeps waiting
        (RUNNING, [(IN, NEW, "BLOCKED"), (IN, NEW, "BLOCKED")], ("run-wait: ABC-1 BLOCKED", 0)),  # the run seen at the start was running, so its end counts
        (DONE, [(IN, NEW, "BUILD READY"), (IN, NEW, "BUILD READY"), (IN, NEW, "BUILD READY")], ("run-wait: ABC-1 BUILD READY", 0)),  # one grace round, then it prints
        (DONE, [(IN, NEW, "BUILD READY"), (None, None, None)], ("run-wait: ABC-1 left build", 0)),  # the notice came in the grace round
        (DONE, [(IN, RUNNING, None)] * 5, ("run-wait: ABC-1 still working after 2m", 1)),
    ],
)
def test_wait_loop(start, rounds, want):
    limit = 120 if want[1] == 1 else 6600
    assert fake_wait(start, rounds, limit)[0] == want


def test_the_ticket_position_is_the_floor_and_a_missing_one_is_zero():
    assert fake_wait(DONE, [(IN, ("r2", "failed"), None)])[1] == [4]
    assert fake_wait(DONE, [({"stage": "spec", "childThreadId": "c1"}, ("r2", "failed"), None)], first={"stage": "spec", "childThreadId": "c1"})[1] == [0]


@pytest.mark.parametrize("first", [None, {"stage": "merge", "childThreadId": "c1"}, {"stage": "spec"}, {"stage": "build", "childThreadId": ""}])
def test_a_ticket_with_no_lane_child_is_cannot(first):
    out, _ = fake_wait(DONE, [], first=first)
    assert out[1] == 2
