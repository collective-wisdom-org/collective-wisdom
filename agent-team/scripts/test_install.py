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
    """A throwaway collective-wisdom (commits A and B on origin/main, S on an unpushed branch) and an app repo."""
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
    git(cw, "checkout", "-q", "-b", "side")
    put(at, {"scripts/a.py": "side\n"})
    sha["S"] = commit(cw, "feat: unmerged")
    git(cw, "tag", "origin/main", sha["S"])  # a hostile tag: the short name origin/main must not resolve to it
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
