import os
import shutil
import subprocess
from pathlib import Path

import pytest

TOP = Path(__file__).absolute().parent.parent.parent
pytestmark = pytest.mark.skipif(not (TOP / "tag-release.sh").exists(), reason="only meaningful in collective-wisdom")

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]


def git(cwd, *args):
    return subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(cwd, name):
    (cwd / "f.txt").write_text(name)
    git(cwd, "add", "-A")
    git(cwd, "commit", "-q", "-m", name)
    return git(cwd, "rev-parse", "HEAD")


@pytest.fixture
def world(tmp_path):
    """A throwaway repo (commits A and B on origin/main, S on an unpushed branch; tags v0.1 on A, v0.2 on B, v0.9 on S, on origin only)."""
    cw = tmp_path / "cw"
    cw.mkdir()
    git(tmp_path, "init", "-q", "--bare", "-b", "main", "origin.git")
    git(cw, "init", "-q", "-b", "main")
    git(cw, "remote", "add", "origin", str(tmp_path / "origin.git"))
    sha = {"A": commit(cw, "A")}
    sha["B"] = commit(cw, "B")
    git(cw, "push", "-q", "origin", "main")
    git(cw, "tag", "-a", "v0.1", sha["A"], "-m", "t")
    git(cw, "tag", "-a", "v0.2", sha["B"], "-m", "t")
    git(cw, "checkout", "-q", "-b", "side")
    sha["S"] = commit(cw, "S")
    git(cw, "tag", "origin/main", sha["S"])  # a hostile tag: the short name origin/main must not resolve to it
    git(cw, "tag", "-a", "v0.9", sha["S"], "-m", "t")
    git(cw, "push", "-q", "origin", "refs/tags/v0.1", "refs/tags/v0.2", "refs/tags/v0.9")
    git(cw, "tag", "-d", "v0.1", "v0.2", "v0.9")  # the release script must read tags from origin itself
    git(cw, "checkout", "-q", "main")
    return cw, sha


# name, tags to keep on origin, local-only tags, args, exit code, tags on origin after (tag: commit)
RELEASE = [
    ("no tags makes v0.1", [], [], [], 0, {"v0.1": "B"}),
    ("the next number is numeric", ["v0.1", "v0.9"], [], [], 0, {"v0.1": "A", "v0.9": "S", "v0.10": "B"}),
    ("a stale local tag does not count", ["v0.1"], ["v0.2"], [], 0, {"v0.1": "A", "v0.2": "B"}),
    ("a tagged origin/main is refused", ["v0.2"], [], [], 1, {"v0.2": "B"}),
    ("dry run pushes nothing", ["v0.1"], [], ["--dry-run"], 0, {"v0.1": "A"}),
]


@pytest.mark.parametrize("name, keep, local, args, code, tags", RELEASE, ids=[c[0] for c in RELEASE])
def test_tag_release(world, name, keep, local, args, code, tags):
    cw, sha = world
    origin, rel = cw.parent / "origin.git", cw.parent / "rel"
    for t in git(origin, "tag", "--list").split():
        if t not in keep:
            git(origin, "tag", "-d", t)
    git(cw.parent, "clone", "-q", str(origin), str(rel))
    shutil.copy(TOP / "tag-release.sh", rel / "tag-release.sh")
    for t in local:
        git(rel, "tag", t, "HEAD~1")
    ident = {k: "t" for k in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME")} | {k: "t@t" for k in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL")}
    r = subprocess.run(["bash", str(rel / "tag-release.sh"), *args], env={**os.environ, **ident, "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "tag.gpgsign", "GIT_CONFIG_VALUE_0": "false"}, capture_output=True, text=True)
    assert r.returncode == code, r.stdout + r.stderr
    assert {t: git(origin, "rev-parse", t + "^{commit}") for t in git(origin, "tag", "--list").split()} == {t: sha[c] for t, c in tags.items()}
