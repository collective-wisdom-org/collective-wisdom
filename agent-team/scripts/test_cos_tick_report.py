"""`cos_tick.py --next` prints the finished `Filling stopped:` text after the `report` line (report-format.md § Report format)."""

import pytest

from test_cos_tick import BUILD, FRESH, NH, SPEC1, run, tk

FULL = {"ABC-1": BUILD, "ABC-2": tk("build", "c2"), "ABC-3": SPEC1, "ABC-4": tk("spec", "c4")}
ONE = {"ABC-1": BUILD}


def ranked(*entries):
    return {"pm": {**FRESH["pm"], "ranked": [{"id": i, "title": t, "reason": "r", "readiness": r, "priority": "High", "createdAt": "2026-11-01T00:00:00Z"} for i, t, r in entries]}}


HELD = ("ABC-9", "Search page", "held: PR #210 (ABC-3: Test cleanup) changes the same test files")

# tickets, extra state, text (None: no filling-stopped line)
CASES = [
    (FULL, {}, "Filling stopped: lanes full."),
    (ONE, {}, "Filling stopped: no ready ticket in the Backlog."),
    (ONE, ranked(), "Filling stopped: no ready ticket in the Backlog."),
    (ONE, ranked(("ABC-8", "Needs an answer", "needs: which pages")), "Filling stopped: no ready ticket in the Backlog."),
    (ONE, ranked(HELD), "Filling stopped: Backlog held. ABC-9: Search page waits on PR #210."),
    # up to three, six words each, in rank order, `; ` between
    (ONE, ranked(HELD, ("ABC-10", "Billing page for the new plan screens today", "held: PR #7 (ABC-1) same files"), ("ABC-11", "C", "held: PR #8"), ("ABC-12", "D", "held: PR #9")),
     "Filling stopped: Backlog held. ABC-9: Search page waits on PR #210; ABC-10: Billing page for the new plan waits on PR #7; ABC-11: C waits on PR #8."),
    # a reason that names no PR is carried as it is; a title with a marker word leaves the ID alone
    (ONE, ranked(("ABC-9", "BUILD READY now", "held: the design review")), "Filling stopped: Backlog held. ABC-9 waits on the design review."),
    # a ready entry is still ranked: the Backlog pick will start it, so no line
    (ONE, ranked(HELD, ("ABC-8", "Ready one", "ready")), None),
    # a No Hands drain
    (ONE, {"noHands": {**NH, "drain": "blocked ABC-1"}}, "Filling stopped: No Hands blocked ABC-1."),
    # a rate limited turn has no slot fill and no parenthetical
    (ONE, {"rateLimitedAt": "2026-11-08T11:00:00Z", "wakeTaskId": "w1", "wakeAt": "2026-11-08T13:00:00Z"}, None),
]


@pytest.mark.parametrize("tickets, extra, text", CASES)
def test_finished_filling_stopped_text(tmp_path, capsys, tickets, extra, text):
    state = {"tickets": tickets, **FRESH, **extra}
    out = run(tmp_path, capsys, state, "notice:zz", "--after-reads", "--next")
    got = [x for x in out if x.startswith("filling-stopped: ")]
    assert got == ([f"filling-stopped: {text}"] if text else [])
    # the text comes right after the `report` line, and only a `report` line has one
    if text:
        assert out[out.index(got[0]) - 1].startswith("report ")


@pytest.mark.parametrize("tickets, extra, text", CASES)
def test_without_the_flag_the_plan_is_what_it_was(tmp_path, capsys, tickets, extra, text):
    state = {"tickets": tickets, **FRESH, **extra}
    plain = run(tmp_path, capsys, state, "notice:zz", "--after-reads")
    flagged = run(tmp_path, capsys, state, "notice:zz", "--after-reads", "--next")
    kept = [x.removesuffix(" --next") for x in flagged if not x.startswith(("next: ", "filling-stopped: "))]
    assert kept == plain and not any(x.startswith(("next: ", "filling-stopped: ")) for x in plain)
