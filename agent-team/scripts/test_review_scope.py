import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "review_scope", Path(__file__).with_name("review_scope.py")
)
review_scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_scope)

DOC = "# t\n"
CODE = lambda n: "x\n" * n  # noqa: E731


@pytest.mark.parametrize(
    "files, expected",
    [
        ({"docs/superpowers/specs/a.md": DOC}, ("docs-only", "1 files")),
        ({"README.md": DOC}, ("docs-only", "1 files")),
        ({"docs/agents/project.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/Agents/project.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/agent\u017f/project.md": DOC}, ("small", "1 lines in 1 files")),
        ({"sub/README.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/link.md": ("link", "../scripts/s.py")}, ("small", "1 lines in 1 files")),
        ({".claude/skills/s/SKILL.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/plan.md": CODE(500), "s.py": CODE(200)}, ("small", "200 lines in 1 files")),
        ({"s.py": CODE(201)}, ("full", "201 lines in 1 files")),
        ({"img.png": b"\0\1\2"}, ("full", "binary 'img.png'")),
    ],
)
def test_classify(tmp_path, files, expected):
    def git(*args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path, capture_output=True, text=True, check=True,
        ).stdout

    git("init", "-b", "main")
    (tmp_path / "base.txt").write_text("base\n")
    git("add", "-A")
    git("commit", "-m", "base")
    git("tag", "origin/main")  # a pusher's tag must not stand in for the real merge base
    git("update-ref", "refs/remotes/origin/main", "main")
    git("checkout", "-b", "pr")
    for path, content in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, tuple):
            os.symlink(content[1], tmp_path / path)
        else:
            (tmp_path / path).write_bytes(content if isinstance(content, bytes) else content.encode())
    git("add", "-A")
    git("commit", "-m", "pr")
    head = git("rev-parse", "HEAD").strip()

    def run(cmd):
        return subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, check=True).stdout

    assert review_scope.classify(head, run) == expected


def test_failed_read_exits_2(capsys):
    def run(cmd):
        raise review_scope.CmdError("bad object")

    assert review_scope.main(["7", "0" * 40], run=run) == 2
    assert capsys.readouterr().out.splitlines()[-1].startswith("review-scope: cannot ")
