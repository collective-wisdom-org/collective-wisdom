"""`setup_repo.py write --next` prints the steps after the diff, each as a `next:` line with the paths filled in."""

import json
import subprocess

import setup_repo as sr
from test_setup_repo import GITHUB, offline, repo, run  # noqa: F401  (the fixtures)


def test_write_next_prints_the_steps_after_the_paths(repo, capsys):
    root, wt = repo
    base = ["write", "--root", root, "--dir", wt, "--answers", json.dumps(GITHUB)]
    plain = run(capsys, *base)[1]
    (wt / "docs" / "agents" / "project.md").unlink()
    (wt / ".gitignore").unlink()
    code, out, _ = run(capsys, *base, "--next")
    assert code == 0 and out.startswith(plain)  # without the flag the output is only the two paths
    nxt = [x for x in out[len(plain):].splitlines()]
    assert len(nxt) == len(sr.WRITE_NEXT) and all(x.startswith("next: ") for x in nxt)
    text = "\n".join(nxt)
    assert f'git -C "{wt}" diff' in text and f'git -C "{wt}" push -u origin agent-team-setup' in text
    assert "--base main --head agent-team-setup" in text and f'rmdir "{wt.parent}"' in text


def test_write_next_prints_the_pin_offer_only_when_pinned(repo, capsys):
    root, wt = repo
    base = ["write", "--root", root, "--dir", wt, "--answers", json.dumps(GITHUB), "--next"]
    assert "pin offer" not in run(capsys, *base)[1]
    (root / "docs" / "agents").mkdir(parents=True)
    (root / "docs" / "agents" / "installed-from.txt").write_text("x")
    for cmd in (["add", "-A"], ["commit", "-q", "-m", "p"], ["update-ref", "refs/remotes/origin/main", "HEAD"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True, capture_output=True)
    lines = run(capsys, *base)[1].splitlines()
    assert [x for x in lines if "pin offer" in x] and lines.index([x for x in lines if "pin offer" in x][0]) == 3  # after the paths and the diff step
