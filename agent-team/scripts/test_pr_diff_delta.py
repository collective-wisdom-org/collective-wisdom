import importlib.util
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "pr_diff_delta", Path(__file__).with_name("pr_diff_delta.py")
)
pr_diff_delta = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pr_diff_delta)


def lines(**edits):
    """A 30-line file; edits like l25="x" replace that line."""
    return "".join(edits.get(f"l{i}", f"line {i}") + "\n" for i in range(1, 31))


def moved_check(removed):
    """Two blocks with identical 3-line context; the CHECK line is dropped from block `removed` only."""
    block = ["-", "p", "q", "CHECK", "r", "s", "-"]
    blocks = [[l for l in block if not (l == "CHECK" and i == removed)] for i in (0, 1)]
    return "".join(l + "\n" for b in blocks for l in b + ["-"] * 10)


@pytest.mark.parametrize(
    "main_files, resolved, pr_files, changed",
    [
        ({"other.txt": "x\n"}, None, {}, []),
        ({"a.py": lines(l1="main edit")}, None, {}, ["a.py"]),
        ({"a.py": lines(l25="main edit")}, {"a.py": lines(l25="both")}, {}, ["a.py"]),
        ({}, None, {"a.py": lines(l25="PR edit", l26="more")}, ["a.py"]),
        ({}, None, {"new.py": "x\n"}, ["new.py"]),
        ({}, None, {"a.py": lines(l25="PR  edit")}, ["a.py"]),
        ({}, None, {"dup.py": moved_check(1)}, ["dup.py"]),
        ({}, None, {"a.py": lines(l25="PR edit\r")}, ["a.py"]),
    ],
)
def test_delta(tmp_path, main_files, resolved, pr_files, changed):
    def git(*args, check=True):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path, capture_output=True, text=True, check=check,
        ).stdout

    def write_commit(files):
        for path, text in files.items():
            (tmp_path / path).write_bytes(text.encode())
        git("add", "-A")
        git("commit", "-m", "c")
        return git("rev-parse", "HEAD").strip()

    git("init", "-b", "main")
    root = write_commit({"a.py": lines(), "dup.py": moved_check(None)})
    git("tag", "origin/main", root)  # a pusher's tag must not stand in for the real merge base
    git("checkout", "-b", "pr")
    reviewed = write_commit({"a.py": lines(l25="PR edit"), "dup.py": moved_check(0)})
    if main_files:
        git("checkout", "main")
        write_commit(main_files)
        git("checkout", "pr")
        git("merge", "main", "-m", "merge main", check=False)
        if resolved:
            write_commit(resolved)
        git("update-ref", "refs/remotes/origin/main", "main")
    else:
        git("update-ref", "refs/remotes/origin/main", "main")
        write_commit(pr_files)
    head = git("rev-parse", "HEAD").strip()

    def run(cmd):
        return subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, check=True).stdout

    assert pr_diff_delta.delta(reviewed, head, run) == (("changed", changed) if changed else ("same", []))
