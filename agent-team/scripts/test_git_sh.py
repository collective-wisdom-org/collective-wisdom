import os
import subprocess
from pathlib import Path

import pytest

GIT_SH = Path(__file__).with_name("git.sh")
# Fake gh: only cw-builder is in the keyring; `api user` answers only to that token.
FAKE = """#!/usr/bin/env bash
if [ "$1 $2 $3" = "auth token -u" ]; then
  [ "$4" = cw-builder ] && echo fake-token && exit 0
  exit 1
fi
[ "$1 $2 $GH_TOKEN" = "api user fake-token" ] && printf '4242\\nBuilder Test\\n'
"""
OWN = "own@example.com"
BUILDER = "4242+cw-builder@users.noreply.github.com"


def run(*args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


PUSH = ["push", "origin", "HEAD:refs/heads/feat"]
COMMIT = ["commit", "-q", "--allow-empty", "-m", "work"]
SSH = "git@github.com:x/y.git"


@pytest.mark.parametrize(
    "role, login, owner_commit_on, origin, cmd, code, author, stderr",
    [
        (None, "cw-builder", None, None, COMMIT, 0, OWN, ""),
        ("builder", "none", None, None, COMMIT, 0, OWN, ""),
        ("builder", "cw-builder", None, None, COMMIT, 0, BUILDER, ""),
        ("builder", "cw-gone", None, None, COMMIT, 2, None, "no gh login for cw-gone"),
        ("builder", "cw-builder", "HEAD", None, PUSH, 2, None, f"is by {OWN}"),
        ("builder", "cw-builder", "side", None, ["push", "origin", "side:refs/heads/x"], 2, None, f"is by {OWN}"),
        ("builder", "cw-builder", None, SSH, PUSH, 2, None, "is not https"),
    ],
)
def test_git_sh_commits_and_pushes_as_the_role_login(tmp_path, role, login, owner_commit_on, origin, cmd, code, author, stderr):
    gh = tmp_path / "gh"
    gh.write_text(FAKE)
    gh.chmod(0o755)
    (tmp_path / "project.md").write_text(f"| Key | Value |\n|---|---|\n| Builder login | `{login}` |\n")
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "PROJECT_MD": str(tmp_path / "project.md"),
           "GITHUB_TOKEN": "pat", "GH_TOKEN": "pat", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "AGENT_GH_ROLE": role or "",
           "GIT_TERMINAL_PROMPT": "0", **{f"GIT_{w}_{k}": v for w in ("AUTHOR", "COMMITTER") for k, v in (("NAME", "Own"), ("EMAIL", OWN))}}
    remote, repo = str(tmp_path / "remote.git"), str(tmp_path / "repo")
    git = ["git", "-C", repo]
    run("git", "init", "-q", "--bare", remote, env=env)
    run("git", "init", "-q", repo, env=env)
    run(*git, "remote", "add", "origin", remote, env=env)
    run(*git, "commit", "-q", "--allow-empty", "-m", "base", env=env)
    run(*git, "push", "-q", "origin", "HEAD:refs/heads/main", env=env)
    if owner_commit_on == "side":
        run(*git, "checkout", "-q", "-b", "side", env=env)
    if owner_commit_on:
        run(*git, "commit", "-q", "--allow-empty", "-m", "by owner", env=env)
    if owner_commit_on == "side":
        run(*git, "checkout", "-q", "-", env=env)
    if origin:
        run(*git, "remote", "set-url", "origin", origin, env=env)
    hook = Path(repo) / ".git" / "hooks" / "pre-commit"
    hook.write_text(f'#!/bin/sh\nenv > "{tmp_path}/hook.env"\n')
    hook.chmod(0o755)
    head = run(*git, "rev-parse", "HEAD").stdout.strip()

    p = run(str(GIT_SH), "-C", repo, *cmd, env=env)
    assert p.returncode == code
    assert stderr in p.stderr and "fake-token" not in p.stdout + p.stderr
    if code == 2:
        assert len(p.stderr.splitlines()) == 1 and run(*git, "rev-parse", "HEAD").stdout.strip() == head
        assert run("git", "-C", remote, "for-each-ref", "--format=%(refname)").stdout.split() == ["refs/heads/main"]
        return
    assert run(*git, "log", "-1", "--format=%ae %ce").stdout.split() == [author, author]
    if author == BUILDER:
        assert "fake-token" not in (tmp_path / "hook.env").read_text()
        assert run(str(GIT_SH), "-C", repo, *PUSH[:2], "-q", PUSH[2], env=env).returncode == 0
        assert run("git", "-C", remote, "log", "-1", "--format=%ae", "feat").stdout.strip() == BUILDER
        assert "fake-token" not in run(*git, "config", "--list", env=env).stdout + (Path(repo) / ".git" / "config").read_text()
        for host, got in (("protocol=https\nhost=github.com", True), ("protocol=https\nhost=evil.example", False), ("protocol=http\nhost=github.com", False)):
            fill = run(str(GIT_SH), "credential", "fill", env=env, cwd=repo, input=f"{host}\n\n")
            assert ("password=fake-token" in fill.stdout) == got and "fake-token" not in fill.stderr
