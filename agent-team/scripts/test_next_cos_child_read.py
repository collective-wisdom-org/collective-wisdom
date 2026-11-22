"""`cos_child_read.py --next`: each line that carries a step has its `next:` text (SKILL.md § Child path); the child's own lines get none."""

import pytest
from test_cos_child_read import BUILD, MERGE, TALL, items, store

import cos_child_read

# (message text, run status, --after, (line prefix, words in the next: line that follows it)...)
CASES = [
    (BUILD, "completed", None, [("child ", ["`lastPosition` 4", "`provider` claudeAgent", "rejects a `set`"]), ("marker BUILD READY", ["`awaiting-build`", "approvals.md"])]),
    (MERGE, "completed", None, [("marker MERGE READY", ["cos_review_check.py --route <pr> --head <headSha>", "route moved head"])]),
    ("BLOCKED: stuck", "completed", 3, [("marker BLOCKED", ["cos_head_check.py ABC-5 --next", "`blocked`", "Rate limit"])]),
    ("MERGED #14", "completed", None, [("marker MERGED", ["`merged` op", "readiness.md § Unblocked after a merge"])]),
    ("a step\nmore", "failed", None, [("marker none", ["Stuck check"]), ("tail:", ["does not settle `--step`"])]),
    (BUILD, "completed", 4, [("marker none new=0", ["Stuck check"])]),
    (MERGE.replace("pull/12", "pull/x"), "completed", None, [("field pr=? ", ["A `?` value"])]),
    (TALL, "completed", 3, [("cut turn-item:4 at 1500", ["`itemId` turn-item:4", "`textOffset` 1500"])]),
]


@pytest.mark.parametrize("text, run, after, expect", CASES)
def test_each_line_with_a_step_is_followed_by_its_next(tmp_path, capsys, text, run, after, expect):
    db = tmp_path / "s.sqlite"
    store(db, items(text), run)
    args = ["--db", str(db), "ABC-5", "t"] + ([] if after is None else ["--after", str(after)])
    cos_child_read.main(args)
    plain = capsys.readouterr().out.splitlines()
    cos_child_read.main([*args, "--next"])
    out = capsys.readouterr().out.splitlines()
    assert [x for x in out if not x.startswith("next: ")] == plain
    for prefix, words in expect:
        i = next(n for n, x in enumerate(out) if x.startswith(prefix))
        assert out[i + 1].startswith("next: ") and all(w in out[i + 1] for w in words)


def test_a_field_with_all_values_and_the_childs_own_lines_get_no_next(tmp_path, capsys):
    db = tmp_path / "s.sqlite"
    store(db, items(BUILD))
    cos_child_read.main(["--db", str(db), "ABC-5", "t", "--next"])
    out = capsys.readouterr().out.splitlines()
    for i, line in enumerate(out[:-1]):
        if line.startswith(("field ", "block:", "| ")):
            assert not out[i + 1].startswith("next: ")
