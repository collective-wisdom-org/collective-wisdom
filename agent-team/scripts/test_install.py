import os
import shutil
import subprocess
from pathlib import Path

import pytest

TOP = Path(__file__).absolute().parent.parent.parent
pytestmark = pytest.mark.skipif(not (TOP / "install.sh").exists(), reason="only meaningful in collective-wisdom")

PIN = "docs/agents/installed-from.txt"
SKILL = ".claude/skills/x/SKILL.md"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]


def git(cwd, *args):
    return subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def put(root, files):
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)


def commit(cwd, msg):
    git(cwd, "add", "-A")
    git(cwd, "commit", "-q", "-m", msg)
    return git(cwd, "rev-parse", "HEAD")


@pytest.fixture
def world(tmp_path):
    """A throwaway collective-wisdom (commits A and B on origin/main, S on an unpushed branch; tags v0.1 on A, v0.2 on B, v0.9 on S, on origin only) and an app repo."""
    cw, app = tmp_path / "cw", tmp_path / "app"
    cw.mkdir()
    shutil.copy(TOP / "install.sh", cw / "install.sh")
    git(tmp_path, "init", "-q", "--bare", "-b", "main", "origin.git")
    git(cw, "init", "-q", "-b", "main")
    git(cw, "remote", "add", "origin", str(tmp_path / "origin.git"))
    at = cw / "agent-team"
    put(at, {
        SKILL: "v1\n", ".claude/agents/r.md": "r\n", ".claude/settings.json": "{}\n", "scripts/a.py": "a\n",
        "scripts/old.py": "old\n", "docs/agents/a.md": "a\n", "docs/superpowers/README.md": "readme\n",
        "templates/project.md": "p\n", "templates/AGENTS.md": "agents\n", "templates/gitignore": ".env\n",
    })
    sha = {"A": commit(cw, "feat: first")}
    put(at, {SKILL: "v2\n", "scripts/new.py": "new\n"})
    (at / "scripts/old.py").unlink()
    sha["B"] = commit(cw, "feat: second")
    git(cw, "push", "-q", "origin", "main")
    git(cw, "tag", "-a", "v0.1", sha["A"], "-m", "t")
    git(cw, "tag", "-a", "v0.2", sha["B"], "-m", "t")
    git(cw, "checkout", "-q", "-b", "side")
    put(at, {"scripts/a.py": "side\n"})
    sha["S"] = commit(cw, "feat: unmerged")
    git(cw, "tag", "origin/main", sha["S"])  # a hostile tag: the short name origin/main must not resolve to it
    git(cw, "tag", "-a", "v0.9", sha["S"], "-m", "t")
    git(cw, "push", "-q", "origin", "refs/tags/v0.1", "refs/tags/v0.2", "refs/tags/v0.9")
    git(cw, "tag", "-d", "v0.1", "v0.2", "v0.9")  # the installer must fetch tags itself
    git(cw, "checkout", "-q", "main")
    app.mkdir()
    git(app, "init", "-q")
    git(app, "commit", "-q", "--allow-empty", "-m", "init")
    return cw, app, sha


def run(cw, app, sha, *args):
    args = [a.format(**sha) for a in args]
    r = subprocess.run(["bash", str(cw / "install.sh"), *args, str(app)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def apply(app, steps):
    for rel, text in steps:
        if text is None:
            (app / rel).unlink()
        else:
            put(app, {rel: text})


EDIT = [(SKILL, "mine\n")]

# name, steps after installing A (None: no install), args, exit code, output substrings, pin after, files after
INSTALL = [
    ("fresh install at A", None, ["--to", "{A}"], 0, ["add     " + SKILL], "A", {SKILL: "v1\n", "scripts/old.py": "old\n"}),
    ("dry run writes nothing", None, ["--dry-run", "--to", "{A}"], 0, ["[dry-run] add     " + SKILL], None, {SKILL: None}),
    ("a commit off origin/main is refused", None, ["--to", "{S}"], 1, ["not on origin/main"], None, {SKILL: None}),
    (
        "update moves to origin/main and lists deletions", [], ["--update"], 0,
        ["{A12} -> {B12} (1 commit)", "feat: second", "update  " + SKILL, "add     scripts/new.py",
         "Delete scripts/old.py: collective-wisdom no longer ships it"],
        "B", {SKILL: "v2\n", "scripts/new.py": "new\n", "scripts/old.py": "old\n"},
    ),
    ("update dry run", [], ["--dry-run", "--update"], 0, ["[dry-run] update  " + SKILL], "A", {SKILL: "v1\n"}),
    ("update at the same commit", [], ["--update", "--to", "{A}"], 0, ["already at {A}"], "A", {SKILL: "v1\n"}),
    ("update refuses a hand edit", EDIT, ["--update"], 1, ["changed  " + SKILL], "A", {SKILL: "mine\n"}),
    ("update --force overwrites it", EDIT, ["--update", "--force"], 0, ["update  " + SKILL], "B", {SKILL: "v2\n"}),
    ("update needs an install first", None, ["--update"], 1, ["plain install"], None, {SKILL: None}),
]


@pytest.mark.parametrize("name, steps, args, code, out, pin, files", INSTALL, ids=[c[0] for c in INSTALL])
def test_install_and_update(world, name, steps, args, code, out, pin, files):
    cw, app, sha = world
    if steps is not None:
        assert run(cw, app, sha, "--to", "{A}")[0] == 0
        apply(app, steps)
        commit(app, "install A")
    sha = {**sha, "A12": sha["A"][:12], "B12": sha["B"][:12]}
    rc, text = run(cw, app, sha, *args)
    assert rc == code, text
    for s in out:
        assert s.format(**sha) in text
    pin_file = app / PIN
    assert (pin_file.read_text().strip() if pin_file.exists() else None) == (f"collective-wisdom {sha[pin]}" if pin else None)
    for rel, want in files.items():
        assert ((app / rel).read_text() if (app / rel).exists() else None) == want, rel


def test_a_planted_tag_cannot_stand_in_for_a_missing_origin_main(world):
    # git guesses refs/tags/refs/remotes/origin/main when refs/remotes/origin/main is missing (a single-branch clone).
    cw, app, sha = world
    git(cw, "tag", "refs/remotes/origin/main", sha["S"])
    git(cw, "update-ref", "-d", "refs/remotes/origin/main")
    for args in (["--to", "{S}"], ["--to", "{A}"]):
        rc, text = run(cw, app, sha, *args)
        assert rc == 1 and "no origin/main" in text, text
    assert not (app / PIN).exists()


BAD = "collective-wisdom " + "f" * 40 + "\n"
CHECK = [
    ("clean app matches", [], 0, ["check: matches collective-wisdom {A}"]),
    (
        "one changed and one missing file", [*EDIT, ("scripts/a.py", None)], 1,
        ["changed  " + SKILL, "missing  scripts/a.py", "check: drift in 2 file(s) against collective-wisdom {A}"],
    ),
    ("an app-owned skill is not drift", [(".claude/skills/mine/SKILL.md", "m\n")], 0, ["check: matches"]),
    ("a commit the clone lacks", [(PIN, BAD)], 2, ["git fetch"]),
    ("a malformed pin", [(PIN, "collective-wisdom main\n")], 2, ["installed-from.txt"]),
    ("no pin", [(PIN, None)], 2, ["installed-from.txt"]),
]


@pytest.mark.parametrize("name, steps, code, out", CHECK, ids=[c[0] for c in CHECK])
def test_check(world, name, steps, code, out):
    cw, app, sha = world
    assert run(cw, app, sha, "--to", "{A}")[0] == 0
    apply(app, steps)
    before = git(app, "status", "--porcelain", "--ignored")
    rc, text = run(cw, app, sha, "--check")
    assert rc == code, text
    for s in out:
        assert s.format(**sha) in text
    assert git(app, "status", "--porcelain", "--ignored") == before


def pin_of(app):
    f = app / PIN
    return f.read_text().strip().removeprefix("collective-wisdom ") if f.exists() else None


def installed(cw, app, sha, *args):
    if args:
        assert run(cw, app, sha, *args)[0] == 0
        commit(app, "install")


# name, local tags to force first, install args first (None: none), args, exit code, output substrings, pin after
FROM = [
    ("install --from pins the tag", {}, None, ["--from", "v0.1"], 0, [], "{A} v0.1"),
    ("update --from moves to the next tag", {}, ["--from", "v0.1"], ["--update", "--from", "v0.2"], 0, ["v0.1 {A12} -> v0.2 {B12} (1 commit)"], "{B} v0.2"),
    ("check names the tag", {}, ["--from", "v0.1"], ["--check"], 0, ["check: matches collective-wisdom {A} (v0.1)"], "{A} v0.1"),
    ("--to leaves the tag out", {}, None, ["--to", "{A}"], 0, [], "{A}"),
    ("same commit gains the tag", {}, ["--to", "{A}"], ["--update", "--from", "v0.1"], 0, ["update  " + PIN], "{A} v0.1"),
    ("a tag off origin/main is refused", {}, None, ["--from", "v0.9"], 1, ["not on origin/main"], None),
    ("a missing tag is refused", {}, None, ["--from", "v0.7"], 1, ["cannot fetch"], None),
    ("origin's tag replaces a local one", {"v0.2": "S"}, None, ["--from", "v0.2"], 0, [], "{B} v0.2"),
    ("--from with --to is refused", {}, None, ["--from", "v0.1", "--to", "{A}"], 2, ["cannot be used together"], None),
    ("a tag that is not v0.N is refused", {}, None, ["--from", "-x"], 2, ["bad tag"], None),
]


@pytest.mark.parametrize("name, local, first, args, code, out, pin", FROM, ids=[c[0] for c in FROM])
def test_from_tag(world, name, local, first, args, code, out, pin):
    cw, app, sha = world
    installed(cw, app, sha, *(first or []))
    for tag, at in local.items():
        git(cw, "tag", "-f", tag, sha[at])
    sha = {**sha, "A12": sha["A"][:12], "B12": sha["B"][:12]}
    rc, text = run(cw, app, sha, *args)
    assert rc == code, text
    for s in out:
        assert s.format(**sha) in text
    assert pin_of(app) == (pin.format(**sha) if pin else None)


def wrapper(world, args, cwd, env=None):
    cw, app, _ = world
    tmpdir = cw.parent / "tmpdir"
    tmpdir.mkdir(exist_ok=True)
    env = {**os.environ, "COLLECTIVE_WISDOM_REPO": str(cw.parent / "origin.git"), "TMPDIR": str(tmpdir), **(env or {})}
    script = TOP / "agent-team/scripts/agent-team-update.sh"
    r = subprocess.run(["bash", str(script), *args], cwd=cw if cwd == "cw" else app, env=env, capture_output=True, text=True)
    assert list(tmpdir.iterdir()) == []  # the temp clone is gone
    return r.returncode, r.stdout + r.stderr


# name, args, where to run, env, exit code, output substrings, pin after
WRAPPER = [
    ("no tag takes the newest on origin/main", [], "app", {}, 0, ["collective-wisdom {A12} -> v0.2 {B12}"], "{B} v0.2"),
    ("a named tag", ["v0.1"], "app", {}, 0, [], "{A} v0.1"),
    ("dry run writes nothing", ["--dry-run"], "app", {}, 0, ["[dry-run] update  " + SKILL], "{A}"),
    ("a tag off origin/main is refused", ["v0.9"], "app", {}, 1, ["not on origin/main"], "{A}"),
    ("a failed clone points at credentials", [], "app", {"COLLECTIVE_WISDOM_REPO": "/nonexistent"}, 1, ["gh auth setup-git"], "{A}"),
    ("collective-wisdom itself is refused", [], "cw", {}, 1, ["collective-wisdom itself"], "{A}"),
]


@pytest.mark.parametrize("name, args, where, env, code, out, pin", WRAPPER, ids=[c[0] for c in WRAPPER])
def test_update_wrapper(world, name, args, where, env, code, out, pin):
    cw, app, sha = world
    installed(cw, app, sha, "--to", "{A}")
    sha = {**sha, "A12": sha["A"][:12], "B12": sha["B"][:12]}
    rc, text = wrapper(world, args, where, env)
    assert rc == code, text
    for s in out:
        assert s.format(**sha) in text
    assert pin_of(app) == pin.format(**sha)


# name, tags to keep on origin, args, exit code, tags on origin after (tag: commit)
RELEASE = [
    ("no tags makes v0.1", [], [], 0, {"v0.1": "B"}),
    ("the next number is numeric", ["v0.1", "v0.9"], [], 0, {"v0.1": "A", "v0.9": "S", "v0.10": "B"}),
    ("a tagged origin/main is refused", ["v0.2"], [], 1, {"v0.2": "B"}),
    ("dry run pushes nothing", ["v0.1"], ["--dry-run"], 0, {"v0.1": "A"}),
]


@pytest.mark.parametrize("name, keep, args, code, tags", RELEASE, ids=[c[0] for c in RELEASE])
def test_tag_release(world, name, keep, args, code, tags):
    cw, _, sha = world
    origin, rel = cw.parent / "origin.git", cw.parent / "rel"
    for t in git(origin, "tag", "--list").split():
        if t not in keep:
            git(origin, "tag", "-d", t)
    git(cw.parent, "clone", "-q", str(origin), str(rel))
    shutil.copy(TOP / "tag-release.sh", rel / "tag-release.sh")
    ident = {k: "t" for k in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME")} | {k: "t@t" for k in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL")}
    r = subprocess.run(["bash", str(rel / "tag-release.sh"), *args], env={**os.environ, **ident}, capture_output=True, text=True)
    assert r.returncode == code, r.stdout + r.stderr
    assert {t: git(origin, "rev-parse", t + "^{commit}") for t in git(origin, "tag", "--list").split()} == {t: sha[c] for t, c in tags.items()}
