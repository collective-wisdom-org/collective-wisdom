"""`cos_sweep.py --next`: the step after each review-check line (what review.md § Review check used to hold), filled in from the line."""

import pytest

import cos_sweep

# line, words in the next: text, words that must not be in it
CASES = [
    ("approved ABC-1 #5 head aaaaaaa by anna, bo", ["`get` ABC-1 first", "`awaiting-merge`", "cos_approve_pr.py ABC-1", "`ABC-1: <short title>, anna, bo approved on GitHub; merging", "anna, bo approved on GitHub; the merge waits on you."], []),
    ("approved ABC-1 #5 head aaaaaaa by github", ["`ABC-1: <short title>, approved on GitHub; merging", ", approved on GitHub; the merge waits on you."], ["github approved"]),
    ("approved ABC-1 #5 head aaaaaaa by codeowner", ["`ABC-1: <short title>, merging with your approval", "ready to merge, waiting on you."], ["approved on GitHub"]),
    ("approved ABC-1 #5 head aaaaaaa by none", ["ready to merge, waiting on you."], ["approved on GitHub"]),
    ("changes ABC-2 #6 by bo, cy at 2026-11-02T10:00:00Z", ["`reviewer-changes`", "PR #6 at head <short>: bo, cy.", "`bo, cy requested changes on GitHub at 2026-11-02T10:00:00Z; back to build.`", '"at": "2026-11-02T10:00:00Z"', "`changesRelayed`"], []),
    ("moved ABC-3 #7 head bbbbbbb", ["`head-moved`", "cos_head_check.py"], []),
    ("closed ABC-4 #8", ["Close ABC-4 out as `cancel N` does", "`PR closed on GitHub`"], []),
    ("unreadable ABC-5 #?", ["`ABC-5: <short title>, review check unreadable`", "`blocked`"], []),
]


@pytest.mark.parametrize("line, has, hasnt", CASES)
def test_each_review_line_has_its_next(line, has, hasnt):
    words = line.split()
    text = cos_sweep.NEXT["review", words[0]](words)
    assert text.startswith("review.md § Review check")
    assert all(x in text for x in has) and not any(x in text for x in hasnt)


def test_the_conflict_line_carries_the_relay_steps():
    words = "conflict ABC-6 #6 head bbbbbbb".split()
    text = cos_sweep.NEXT["ready", "conflict"](words)
    assert "sweep.md § Conflict relay" in text and "`conflictHead`" in text and "`ABC-6: <short title>, PR conflicts with <target>, sent back to resolve it`" in text
    assert "CHIEF OF STAFF: the PR conflicts with <target>. Resolve it per open-pr § Conflict resolution and report MERGE READY." in text
