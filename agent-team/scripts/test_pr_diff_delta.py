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
    "main_files, resolved, pr_files, expected",
    [
        ({"other.txt": "x\n"}, None, {}, ("same", [])),
        ({"a.py": lines(l1="main edit")}, None, {}, ("changed", ["a.py"])),
        ({"a.py": lines(l25="main edit")}, {"a.py": lines(l25="both")}, {}, ("changed", ["a.py"])),
        ({}, None, {"a.py": lines(l25="PR edit", l26="more")}, ("changed", ["a.py"])),
        ({}, None, {"new.py": "x\n"}, ("changed", ["new.py"])),
        ({}, None, {"a.py": lines(l25="PR  edit")}, ("changed", ["a.py"])),
        ({}, None, {"dup.py": moved_check(1)}, ("changed", ["dup.py"])),
        ({}, None, {"a.py": lines(l25="PR edit\r")}, ("changed", ["a.py"])),
        ({}, None, {"docs/superpowers/specs/x.md": "x\n"}, ("docs", ["docs/superpowers/specs/x.md"])),
        ({}, None, {"docs/superpowers/specs/x.md": "x\n", "a.py": lines(l25="PR edit", l26="more")}, ("changed", ["a.py", "docs/superpowers/specs/x.md"])),
    ],
)
def test_delta(tmp_path, main_files, resolved, pr_files, expected):
    def git(*args, check=True):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path, capture_output=True, text=True, check=check,
        ).stdout

    def write_commit(files):
        for path, text in files.items():
            (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
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

    assert pr_diff_delta.delta(reviewed, head, run) == expected


SKILL = "agent-team/.claude/skills/foo/SKILL.md"
CONFIG = ("CW", ["README.md", "AGENTS.md", "docs/agents/project.md", "agent-team/docs/agents/", "agent-team/.claude/skills/"])
FIX = "docs: bring docs in line with CW-362"


def boom():
    raise OSError("no origin")


@pytest.mark.parametrize(
    "edits, subject, shape, config, expected",
    [
        ({SKILL: "x\n", "README.md": "x\n"}, FIX, "one", CONFIG, "living"),
        ({SKILL: "x\n"}, FIX, "one", CONFIG, "living"),
        ({SKILL: "x\n", "a.py": lines(l1="x")}, FIX, "one", CONFIG, "changed"),  # a script
        ({"docs/agents/project.md": "x\n"}, FIX, "one", CONFIG, "changed"),  # hands path
        ({"agent-team/.claude/skills/open-pr/SKILL.md": "x\n"}, FIX, "one", CONFIG, "changed"),  # hands path
        ({"AGENTS.md": "x\n"}, FIX, "one", CONFIG, "changed"),  # hands path
        ({SKILL: "x\n"}, "docs: tidy", "one", CONFIG, "changed"),
        ({SKILL: "x\n"}, "docs: bring docs in line with CW-362 now", "one", CONFIG, "changed"),
        ({SKILL: "x\n"}, FIX, "two", CONFIG, "changed"),
        ({SKILL: "x\n"}, FIX, "merge", CONFIG, "changed"),
        ({SKILL: "x\n"}, FIX, "one", None, "changed"),
        ({SKILL: "x\n"}, FIX, "one", boom, "changed"),  # a failed read of the list on origin
        ({"agent-team/.claude/skills/foo/run.sh": "x\n"}, FIX, "one", CONFIG, "changed"),  # not .md
        ({SKILL: "x\n"}, FIX, "one", ("CW", ["agent-team/docs/agents/"]), "changed"),  # not in the list
        ({"docs/superpowers/specs/x.md": "x\n"}, "docs: tidy", "one", boom, "docs"),
    ],
)
def test_delta_living(tmp_path, edits, subject, shape, config, expected):
    def git(*args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path, capture_output=True, text=True, check=True,
        ).stdout

    def commit(files, msg):
        for path, text in files.items():
            (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / path).write_text(text)
        git("add", "-A")
        git("commit", "-m", msg)
        return git("rev-parse", "HEAD").strip()

    git("init", "-b", "main")
    commit({"a.py": lines(), "README.md": "r\n", SKILL: "s\n", "docs/agents/project.md": "p\n", "AGENTS.md": "a\n",
            "agent-team/.claude/skills/open-pr/SKILL.md": "o\n", "agent-team/.claude/skills/foo/run.sh": "r\n"}, "root")
    git("update-ref", "refs/remotes/origin/main", "main")
    git("checkout", "-b", "pr")
    reviewed = commit({"a.py": lines(l25="PR edit")}, "feat: pr")
    if shape == "merge":
        git("checkout", "-b", "side")
        commit(edits, "side")
        git("checkout", "pr")
        git("merge", "--no-ff", "side", "-m", subject)
    else:
        commit(edits, subject)
        if shape == "two":
            commit({"docs/superpowers/specs/y.md": "y\n"}, subject)
    head = git("rev-parse", "HEAD").strip()

    def run(cmd):
        return subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, check=True).stdout

    cfg = config if callable(config) else (lambda: config)
    assert pr_diff_delta.delta(reviewed, head, run, cfg)[0] == expected
