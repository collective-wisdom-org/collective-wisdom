"""`compact_check.py --next`: every line that can end a run has its `next:` text (build-from-plan § Compaction pass); without the flag the output is unchanged."""

import subprocess
import sys
from pathlib import Path

import pytest

import compact_check

SCRIPT = Path(__file__).with_name("compact_check.py")
SKILL = "agent-team/.claude/skills/demo/SKILL.md"


def run_in(tmp_path, edits, args):
    def git(*a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a], cwd=tmp_path, capture_output=True, check=True)

    git("init", "-b", "main")
    (tmp_path / SKILL).parent.mkdir(parents=True)
    (tmp_path / SKILL).write_text("x" * 100)
    (tmp_path / "install.sh").write_text("#!/bin/sh\n")
    git("add", "-A")
    git("commit", "-m", "base")
    (tmp_path / SKILL).write_text("x" * edits)
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], cwd=tmp_path, capture_output=True, text=True)


@pytest.mark.parametrize(
    "size, args, code, last, words",
    [
        (150, ["--base", "main"], 0, "compact: run (+50 characters)", ["start the compacter", "revert any hunk"]),
        (40, ["--base", "main"], 0, "compact: skip (net -60 characters)", ["go on", "`total` line"]),
        (150, ["--base", "nope"], 2, "compact: cannot read the change set", ["run it once more", "BLOCKED:"]),
        (150, ["--bogus"], 2, "compact: cannot read arguments", ["fix the call"]),
    ],
)
def test_every_ending_line_has_its_next(tmp_path, size, args, code, last, words):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    plain = run_in(tmp_path / "a", size, args)
    nxt = run_in(tmp_path / "b", size, [*args, "--next"])
    assert plain.returncode == nxt.returncode == code
    *body, text = nxt.stdout.splitlines()
    assert body == plain.stdout.splitlines() and body[-1].startswith(last)
    assert text.startswith("next: ") and all(w in text for w in words), text
    assert not any(l.startswith("next: ") for l in plain.stdout.splitlines())


def test_the_table_has_a_row_for_each_line_kind():
    assert [compact_check.next_for(l) is not None for l in ("compact: run (+1 characters)", "compact: skip (x)", "compact: cannot read arguments; usage", "compact: cannot read the change set: x")] == [True] * 4
