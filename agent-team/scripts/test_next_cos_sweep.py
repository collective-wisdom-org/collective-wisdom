"""`cos_sweep.py --next`: each line the Chief of Staff acts on has its `next:` text (sweep.md § Sweep), the last line has one, nothing else does."""

import pytest

import cos_sweep

# What each part prints, one line per word the Chief of Staff acts on, and the lines it does not (`open`, `idle`, ...).
PARTS = {
    "merged": (["merged ABC-2 #7 at 2026-11-03T02:40:00Z", "mismatch ABC-3 #8 head feat/x", "unreadable ABC-4 #9", "open ABC-5 #1", "merged-check: 4 checked, 1 merged"], [("ABC-2", 7)]),
    "ready": (["ready ABC-1 #5 head aaaaaaa", "conflict ABC-6 #6 head bbbbbbb", "pushed ABC-7 feat/abc-7-x ccccccc", "building ABC-8 #3 (code review not posted, security not posted)", "no-pr ABC-9", "writing ABC-10", "unreadable ABC-11", "ready-check: 8 checked, 3 may have reported"],
              [("ABC-1", "ready"), ("ABC-6", "conflict"), ("ABC-7", "pushed")]),
    "parent": (["full ABC-12 old-parent t0", "idle ABC-13 old-parent unknown", "parent-check: 2 tickets, 2 under an older thread, 1 need a full read"], None),
    "untracked": (["untracked ABC-14 in-review #132", "untracked ABC-15", "untracked-check: 2 not in state"], [("ABC-14", 132), ("ABC-15", None)]),
    "review": (["approved ABC-16 #20 head aaaaaaa by anna", "changes ABC-17 #21 by bo at 2026-11-02T10:00:00Z", "moved ABC-18 #22 head ddddddd", "closed ABC-19 #23", "unreadable ABC-20 #24", "waiting ABC-21 #25 needs cy", "review-check: 6 checked, 5 to act on"],
               [("ABC-16", "approved"), ("ABC-17", "changes"), ("ABC-18", "moved"), ("ABC-19", "closed"), ("ABC-20", "unreadable")]),
}
ACTION_LINES = {  # the lines above that need a `next:`
    "merged ABC-2 #7 at 2026-11-03T02:40:00Z", "mismatch ABC-3 #8 head feat/x", "unreadable ABC-4 #9", "ready ABC-1 #5 head aaaaaaa", "conflict ABC-6 #6 head bbbbbbb",
    "pushed ABC-7 feat/abc-7-x ccccccc", "full ABC-12 old-parent t0", "untracked ABC-14 in-review #132", "untracked ABC-15", "approved ABC-16 #20 head aaaaaaa by anna",
    "changes ABC-17 #21 by bo at 2026-11-02T10:00:00Z", "moved ABC-18 #22 head ddddddd", "closed ABC-19 #23", "unreadable ABC-20 #24",
}


@pytest.fixture
def parts(monkeypatch):
    def patch(failing=()):
        def make(name):
            def fn(*a, **k):
                if name in failing:
                    raise SystemExit(2)
                return PARTS[name] if name != "parent" else (PARTS["parent"][0], None)
            return fn

        monkeypatch.setattr(cos_sweep.cos_merged_check, "run", make("merged"))
        monkeypatch.setattr(cos_sweep.cos_ready_check, "load_state", lambda f: {})
        monkeypatch.setattr(cos_sweep.cos_ready_check, "check", lambda s, p, r: make("ready")())
        monkeypatch.setattr(cos_sweep.cos_parent_check, "run", make("parent"))
        monkeypatch.setattr(cos_sweep.cos_untracked_check, "run", make("untracked"))
        monkeypatch.setattr(cos_sweep.cos_review_check, "load_state", lambda f: {})
        monkeypatch.setattr(cos_sweep.cos_review_check, "check", lambda s, p: make("review")())
    return patch


def sweep(capsys, *flags):
    code = cos_sweep.main(["--thread", "ME", "--file", "none.json", *flags])
    return code, capsys.readouterr().out.splitlines()


@pytest.mark.parametrize("verbose", [[], ["--verbose"]])
def test_every_action_line_has_a_next_and_no_other_line_does(parts, capsys, verbose):
    parts()
    _, out = sweep(capsys, "--next", *verbose)
    printed = [x for x in out if not x.startswith("next: ")]
    for i, line in enumerate(out):
        if line.startswith("next: "):
            continue
        nxt = out[i + 1].startswith("next: ") if i + 1 < len(out) else False
        assert nxt == (line in ACTION_LINES or line.startswith("sweep: ")), line
    assert ACTION_LINES <= set(printed)
    assert out[-1].startswith("next: ") and out[-2].startswith("sweep: ")


@pytest.mark.parametrize("verbose", [[], ["--verbose"]])
def test_without_the_flag_the_output_is_unchanged(parts, capsys, verbose):
    parts()
    code, plain = sweep(capsys, *verbose)
    code_next, flagged = sweep(capsys, "--next", *verbose)
    assert code == code_next and [x for x in flagged if not x.startswith("next: ")] == plain


def text_after(out, line):
    return out[out.index(line) + 1].removeprefix("next: ")


def test_next_texts_fill_in_the_line(parts, capsys):
    parts()
    _, out = sweep(capsys, "--next")
    merged = text_after(out, "merged ABC-2 #7 at 2026-11-03T02:40:00Z")
    assert "`ABC-2: <short title>, merged (#7), found by the merged check`" in merged and "readiness.md § Unblocked after a merge" in merged and "`(merged #7)`" in merged
    assert "Full-read this ticket's child" in text_after(out, "ready ABC-1 #5 head aaaaaaa")
    assert "sweep.md § Conflict relay" in text_after(out, "conflict ABC-6 #6 head bbbbbbb")
    one = text_after(out, "untracked ABC-14 in-review #132")
    assert "(in review, PR #132; child" in one and 'titleContains: "ABC-14"' in one and "Say adopt ABC-14 to take it here." in one
    assert "(in flight; child" in text_after(out, "untracked ABC-15")
    assert "review.md § Review check" in text_after(out, "closed ABC-19 #23")
    last = out[-1]
    assert "found by the sweep" in last and "(merge ready)" in last and "didn't run" not in last


@pytest.mark.parametrize(
    "failing, has",
    [
        (["merged"], ["merged: no fallback"]),
        (["ready", "untracked"], ["ready: the idle check", "untracked: no fallback"]),
        (["parent"], ["parent: full-read every active child whose `parentThreadId` isn't this thread"]),
        (["review"], ["review: no fallback (say the `awaiting-review` tickets were not checked)"]),
    ],
)
def test_the_last_next_names_the_fallback_of_each_failed_part(parts, capsys, failing, has):
    parts(failing)
    code, out = sweep(capsys, "--next")
    assert code == 2 and out[-2].endswith(f"didn't run: {', '.join(failing)}")
    assert all(x in out[-1] for x in has) and "Sweep part didn't run: <its line>" in out[-1]
