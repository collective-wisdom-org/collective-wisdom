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


def pr_repo(tmp_path, files):
    """Commit base.txt on main, then files on a pr branch. Return (run, base SHA, head SHA)."""

    def git(*args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path, capture_output=True, text=True, check=True,
        ).stdout

    git("init", "-b", "main")
    (tmp_path / "base.txt").write_text("base\n")
    git("add", "-A")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD").strip()
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

    def run(cmd):
        p = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True)
        if p.returncode:
            raise review_scope.CmdError(p.stderr.strip())
        return p.stdout

    return run, base, git("rev-parse", "HEAD").strip()


@pytest.mark.parametrize(
    "files, expected",
    [
        ({"docs/superpowers/specs/a.md": DOC}, ("docs-only", "1 files")),
        ({"README.md": DOC}, ("docs-only", "1 files")),
        ({"docs/agents/project.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/Agents/project.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/agent\u017f/project.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/.claude/skills/s/SKILL.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/superpowers/CLAUDE.md": DOC}, ("small", "1 lines in 1 files")),
        ({"sub/README.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/link.md": ("link", "../scripts/s.py")}, ("small", "1 lines in 1 files")),
        ({".claude/skills/s/SKILL.md": DOC}, ("small", "1 lines in 1 files")),
        ({"docs/plan.md": CODE(500), "s.py": CODE(200)}, ("small", "200 lines in 1 files")),
        ({"s.py": CODE(201)}, ("full", "201 lines in 1 files")),
        ({"img.png": b"\0\1\2"}, ("full", "binary 'img.png'")),
    ],
)
def test_classify(tmp_path, files, expected):
    run, _, head = pr_repo(tmp_path, files)
    assert review_scope.classify(head, run) == expected


@pytest.mark.parametrize(
    "files, expected",
    [
        ({"docs/superpowers/specs/a.md": DOC}, ("skip", "skip")),
        ({"README.md": DOC, "docs/x.md": DOC}, ("skip", "skip")),
        ({".claude/skills/s/SKILL.md": DOC}, ("run", "skip")),
        ({"docs/agents/x.md": DOC}, ("run", "skip")),
        ({"install.sh": "#!/bin/sh\n"}, ("run", "run")),
        ({"agent-team/scripts/x.py": CODE(1)}, ("run", "skip")),
        ({".github/workflows/ci.yml": CODE(1)}, ("run", "run")),
        ({"sub/.shellcheckrc": "disable=SC2086\n"}, ("run", "run")),
        ({"shellcheckrc": "disable=SC2086\n"}, ("run", "run")),
    ],
)
def test_ci_scope(tmp_path, files, expected, capsys):
    run, base, head = pr_repo(tmp_path, files)
    assert review_scope.main(["--ci", base, head], run=run) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "ci-scope: tests=%s shellcheck=%s" % expected


def test_failed_read_exits_2(capsys):
    def run(cmd):
        raise review_scope.CmdError("bad object")

    assert review_scope.main(["7", "0" * 40], run=run) == 2
    assert capsys.readouterr().out.splitlines()[-1].startswith("review-scope: cannot ")
    assert review_scope.main(["--ci", "a", "b"], run=run) == 2
    assert capsys.readouterr().out.splitlines()[-1].startswith("ci-scope: cannot ")
