import io
import re

import pytest

import cos_state

TIME = "2026-11-15 5:16 am UTC"
SHA = "a" * 40


def run(monkeypatch, capsys, argv, stdin=""):
    monkeypatch.setattr(cos_state.sys, "stdin", io.StringIO(stdin))
    monkeypatch.setattr(cos_state, "now", lambda: "2026-11-15T05:16:00Z")
    code = cos_state.main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize(
    "raw, want",
    [
        ("Background job runner", "ABC-7: Background job runner"),
        ("Fix [the] `login` flow\nfor <users> and more words here", "ABC-7: Fix the login flow for users"),  # dropped characters, six words
        ("  one   two\tthree  ", "ABC-7: one two three"),
        ("", "ABC-7"),
        ("[] <>", "ABC-7"),
        # a marker anywhere in the title, however spelled, leaves the ID alone
        ("MERGE READY: ship it", "ABC-7"),
        ("merge   ready", "ABC-7"),
        ("Build[ ]Ready", "ABC-7"),
        ("Auto‑approved under x", "ABC-7"),  # non-breaking hyphen
        ("Auto approved", "ABC-7"),
        ("SPEC\nREADY", "ABC-7"),
        ("one two three four five six BLOCKED: seven", "ABC-7"),  # past the six-word cut, still a marker
        ("Why MERGED # matters", "ABC-7"),
        ("Note from CHIEF OF STAFF: hi", "ABC-7"),
        ("Blocked on review", "ABC-7: Blocked on review"),  # no colon: not the marker
        ("Merged cleanup", "ABC-7: Merged cleanup"),
    ],
)
def test_title_cleans_the_text_and_hides_a_marker(monkeypatch, capsys, raw, want):
    assert run(monkeypatch, capsys, ["title", "ABC-7"], raw) == (0, want + "\n", "")


@pytest.mark.parametrize("tid", ["abc-7", "ABC-x", "ABC-7\nSPEC READY", "ZZZ-1", ""])
def test_title_rejects_a_bad_id_and_prints_nothing_on_stdout(monkeypatch, capsys, tid):
    code, out, err = run(monkeypatch, capsys, ["title", tid], "Title")
    assert (code, out) == (2, "") and err.startswith("cos_state: title:")


@pytest.mark.parametrize(
    "argv, stdin, want",
    [
        (["approved", "spec"], 'approve 12\n', f'the user approved the spec at {TIME}: "approve 12".'),
        (["approved", "merge", "--head", SHA], "ok", f'the user approved the merge at {TIME}: "ok". Head {SHA}.'),
        (["approved", "merge", "--head", "abc1234", "--queued", "merge"], "ok",
         f'the user approved the merge at {TIME}: "ok". Head abc1234. Waiting for a merge slot.'),
        (["approved", "spec", "--queued", "build"], "ok", f'the user approved the spec at {TIME}: "ok". Waiting for a build slot.'),
        (["auto", "spec", "--tolerance", "balanced"], "Low (docs only)", f"auto-approved the spec at {TIME} under balanced (Risk: Low (docs only))."),
        (["auto", "merge", "--tolerance", "No Hands", "--head", SHA, "--queued", "merge"], "", f"auto-approved the merge at {TIME} under No Hands (Risk: unrated). Head {SHA}. Waiting for a merge slot."),
        (["withdrawn"], "cancelled", f"Approval withdrawn at {TIME}: cancelled."),
        (["withdrawn"], "the PR conflicts with main.\n", f"Approval withdrawn at {TIME}: the PR conflicts with main."),
    ],
)
def test_comment_fills_the_time_head_and_queue_tail(monkeypatch, capsys, argv, stdin, want):
    assert run(monkeypatch, capsys, ["comment", *argv], stdin) == (0, want + "\n", "")


@pytest.mark.parametrize(
    "argv, stdin",
    [
        (["approved", "spec"], ""),  # no words
        (["approved", "merge"], "ok"),  # a merge needs its head
        (["approved", "spec", "--head", SHA], "ok"),  # a spec has no head
        (["approved", "merge", "--head", "xyz"], "ok"),
        (["approved", "spec", "--queued", "deploy"], "ok"),
        (["approved", "spec", "--tolerance", "balanced"], "ok"),
        (["approved"], "ok"),
        (["auto", "spec"], "Low (x)"),  # no tolerance
        (["withdrawn"], "  \n"),  # no reason
        (["withdrawn", "spec"], "cancelled"),
        (["withdrawn", "--queued", "spec"], "cancelled"),
    ],
)
def test_comment_rejects_a_bad_combination_without_printing_a_comment(monkeypatch, capsys, argv, stdin):
    code, out, err = run(monkeypatch, capsys, ["comment", *argv], stdin)
    assert (code, out) == (2, "") and err.startswith("cos_state: comment:")


def test_comment_time_is_the_now_stamp(monkeypatch, capsys):
    monkeypatch.setattr(cos_state.sys, "stdin", io.StringIO("x"))
    assert cos_state.main(["comment", "withdrawn"]) == 0
    assert re.fullmatch(r"Approval withdrawn at \d{4}-\d\d-\d\d (1[0-2]|[1-9]):\d\d (am|pm) UTC: x\.", capsys.readouterr().out.strip())
