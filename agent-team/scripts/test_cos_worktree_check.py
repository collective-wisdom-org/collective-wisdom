import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_worktree_check", Path(__file__).with_name("cos_worktree_check.py"))
cos_worktree_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_worktree_check)

BRANCH = "feat/abc-1-x"


def git(cwd, *args):
    out = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-C", str(cwd), *args],
                         check=True, capture_output=True, text=True)
    return out.stdout.strip()


def commit(wt, name="f", text="x"):
    (wt / name).write_text(text)
    git(wt, "add", name)
    git(wt, "commit", "-m", name)


def write(wt, name, text):
    (wt / name).write_text(text)


def run(argv):
    try:
        return cos_worktree_check.main(argv)
    except SystemExit as e:  # fail() exits 2
        return e.code


def ignore_only(wt):
    commit(wt, ".gitignore", "*.pyc\n")
    git(wt, "push", "origin", BRANCH)
    write(wt, "a.pyc", "x")


def not_a_worktree(wt):
    other = wt.parent / "other"
    git(wt.parent, "clone", str(wt.parent / "origin.git"), "other")
    return other


# (mutation of the pushed worktree, line the script prints, exit code); a mutation may return another path to check
ROWS = [
    (lambda wt: None, "safe ABC-1 feat/abc-1-x ", 0),
    (lambda wt: write(wt, "new", "x"), "unsafe ABC-1: uncommitted changes (1 file)", 1),
    (lambda wt: write(wt, "README", "changed"), "unsafe ABC-1: uncommitted changes (1 file)", 1),
    (lambda wt: commit(wt), "unsafe ABC-1: not pushed (local ", 1),
    (lambda wt: git(wt, "push", "origin", "--delete", BRANCH), "remote none)", 1),
    (lambda wt: git(wt, "switch", "-c", "other"), "unsafe ABC-1: on another branch", 1),
    (lambda wt: git(wt, "switch", "--detach"), "unsafe ABC-1: detached HEAD", 1),
    (not_a_worktree, "unsafe ABC-1: not a worktree of this repo", 1),
    (ignore_only, "safe ABC-1 feat/abc-1-x ", 0),
]


@pytest.mark.parametrize("mutate, want, code", ROWS)
def test_worktree_check(tmp_path, capsys, mutate, want, code):
    git(tmp_path, "init", "--bare", "-b", "main", "origin.git")
    root = tmp_path / "root"
    git(tmp_path, "clone", str(tmp_path / "origin.git"), "root")
    commit(root, "README", "hi")
    git(root, "push", "origin", "HEAD:main")
    wt = tmp_path / "wt"
    git(root, "worktree", "add", "-b", BRANCH, str(wt))
    git(wt, "push", "-u", "origin", BRANCH)
    path = mutate(wt) or wt
    (tmp_path / "state.json").write_text(json.dumps({"tickets": {"ABC-1": {"branch": BRANCH}}}))
    assert run(["ABC-1", str(path), "--file", str(tmp_path / "state.json"), "--root", str(root)]) == code
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 1 and want in out[0]
    if code == 0:
        assert out[0].split()[-1] == git(wt, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    "ticket, state, code",
    [
        ("ABC-1", {"ABC-1": {"branch": "feat/abc-11-x"}}, 1),
        ("ABC-1", {"ABC-1": {"branch": "feat/abc-1-x\nsafe ABC-1"}}, 1),
        ("ABC-1", {"ABC-1": {}}, 1),
        ("ABC-2", {"ABC-1": {"branch": BRANCH}}, 2),
        ("nope", {}, 2),
    ],
)
def test_check_refuses_before_touching_git(tmp_path, capsys, ticket, state, code):
    (tmp_path / "state.json").write_text(json.dumps({"tickets": state}))
    assert run([ticket, str(tmp_path), "--file", str(tmp_path / "state.json"), "--root", str(tmp_path)]) == code
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 1 and not out[0].startswith("safe")
