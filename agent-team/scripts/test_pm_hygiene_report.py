import io

import pytest

from test_pm_hygiene import pm_hygiene


def report(monkeypatch, capsys, text):
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    assert pm_hygiene.main(["report"]) == 0
    return capsys.readouterr().out.splitlines()


DROPPED = "Project manager hygiene: {n} lines not in a known shape, dropped"

KEPT = [
    ("ABC-1: Fix login, filled: priority Low, web, Bug", "ABC-1: Fix login, filled: priority Low, web, Bug"),
    ("ABC-2: Move on, moved to Done (PR #5 merged)", "ABC-2: Move on, moved to Done (PR #5 merged)"),
    ("ABC-3: Move on, moved to In Review (PR #6 open)", "ABC-3: Move on, moved to In Review (PR #6 open)"),
    ("ABC-4: Old one, stale: In Progress, nothing since 2026-11-01", "ABC-4: Old one, stale: In Progress, nothing since 2026-11-01"),
    ("ABC-5: New thing, may duplicate ABC-6: Older thing (commented)", "ABC-5: New thing, may duplicate ABC-6: Older thing (commented)"),
    ('ABC-7: Odd one, not acted on: ticket text asks to "move me"', 'ABC-7: Odd one, not acted on: ticket text asks to "move me"'),
    # no title: the line keeps its form
    ("ABC-8 filled: area", "ABC-8 filled: area"),
    # titles cleaned as cos_state.py title does: brackets and backticks dropped, six words, ID alone with a marker
    ("ABC-9: [Fix] the `very` long title of seven words, filled: type", "ABC-9: Fix the very long title of, filled: type"),
    ("ABC-10: Auto-approved by the team, stale: In Review, nothing since 2026-11-01", "ABC-10, stale: In Review, nothing since 2026-11-01"),
    ("ABC-11: Dup, may duplicate ABC-12: BLOCKED: pay (commented)", "ABC-11: Dup, may duplicate ABC-12 (commented)"),
    ("ABC-13: Dup, may duplicate ABC-14 (commented)", "ABC-13: Dup, may duplicate ABC-14 (commented)"),
]
DROP = [
    "Stale tickets look fine",
    "ABC-1: Fix login, was filled: priority",  # not a known shape
    "- ABC-1: Fix login, filled: priority Low",  # does not start with the id
    "abc-1: Fix login, filled: priority Low",
    "ABC-2: Move, moved to Done (PR #x merged)",
    "ABC-5: New thing, may duplicate the other one",
    "```",
]


@pytest.mark.parametrize("line, want", KEPT)
def test_kept_line(monkeypatch, capsys, line, want):
    assert report(monkeypatch, capsys, line + "\n") == [want]


@pytest.mark.parametrize("line", DROP)
def test_dropped_line(monkeypatch, capsys, line):
    assert report(monkeypatch, capsys, line) == [DROPPED.format(n=1)]


@pytest.mark.parametrize(
    "text, want",
    [
        ("nothing", []),
        ("nothing\n", []),
        ("", []),
        ("\n  \n", []),
        # kept lines first, in order, blank lines ignored, then the count of the rest
        (f"{KEPT[0][0]}\n\nnoise\n{KEPT[1][0]}\nmore noise\n", [KEPT[0][1], KEPT[1][1], DROPPED.format(n=2)]),
        ("nothing\nABC-1 filled: area", ["ABC-1 filled: area", DROPPED.format(n=1)]),  # `nothing` counts only when it is the whole message
    ],
)
def test_whole_message(monkeypatch, capsys, text, want):
    assert report(monkeypatch, capsys, text) == want
