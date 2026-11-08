import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).absolute().parent
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
SHIPPED = {
    ".claude/skills/alpha/SKILL.md": "a\n", ".claude/agents/ag.md": "ag\n", ".claude/mods/m/mod.json": "{}\n",
    "scripts/tool.py": "print(1)\n", "docs/agents/role.md": "role\n", "docs/agents/project.md": "template\n",
}
OWN = {  # the app's own files: byte for byte the same after any run
    "docs/agents/project.md": "mine\n", "AGENTS.md": "agents\n", ".gitignore": ".agent-team/\n",
    ".claude/settings.json": '{"hooks": "cos_rotation_check.py"}\n', ".claude/skills/own/SKILL.md": "own\n",
}


def git(cwd, *args):
    return subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def snapshot(base):  # files, links and empty directories under base
    return {str(p.relative_to(base)): p.readlink() if p.is_symlink() else p.is_dir() or p.read_bytes() for p in sorted(base.rglob("*"))} if base.exists() else {}


def put(base, files):
    for rel, text in files.items():
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_text(text)


def tree(app):
    return {str(p.relative_to(app)): p.is_symlink() or p.read_bytes() for p in sorted(app.rglob("*")) if (p.is_symlink() or p.is_file()) and ".git" not in p.parts}


@pytest.fixture
def world(tmp_path):
    """A clone with a few shipped files in each root, and an old app holding copies of them, the pin and its own files."""
    clone, app = tmp_path / "clone", tmp_path / "app"
    put(clone / "agent-team", SHIPPED)
    for name in ("remove_app_copies.py", "app_root.py"):
        shutil.copy(HERE / name, clone / "agent-team/scripts" / name)
    git(tmp_path, "init", "-q", "-b", "main", str(clone))
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "init")
    app.mkdir()
    git(app, "init", "-q", "-b", "main")
    shipped = {rel: (clone / "agent-team" / rel).read_text() for rel in SHIPPED if rel != "docs/agents/project.md"}
    put(app, {**shipped, **OWN, "docs/agents/installed-from.txt": f"collective-wisdom {git(clone, 'rev-parse', 'HEAD')} v0.9\n"})
    (app / ".agents").mkdir()
    (app / ".agents/skills").symlink_to("../.claude/skills")
    return clone, app


def run(clone, app, *args):
    r = subprocess.run([sys.executable, "-I", str(clone / "agent-team/scripts/remove_app_copies.py"), *args], cwd=app, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def edit_tool(app):
    (app / "scripts/tool.py").write_text("print(2)\n")


def set_pin(text):
    return lambda app: (app / "docs/agents/installed-from.txt").write_text(text)


def link_out(app):  # all five roots and .agents sit outside the app, reached through links; an empty dir sits in two of them
    out = app.parent / "outside"
    out.mkdir()
    for top in (".claude", "scripts", "docs", ".agents"):
        shutil.move(app / top, out / top)
        (app / top).symlink_to(f"../outside/{top}")
    if not (out / ".agents/skills").is_symlink():
        (out / ".agents/skills").symlink_to("../.claude/skills")
    shutil.rmtree(out / ".claude/skills")  # .claude/skills is gone, so the .agents/skills link is due for removal
    (out / "docs/agents/empty").mkdir()
    (out / ".claude/mods/empty").mkdir()


def in_collective_wisdom(app):  # a malformed pin too: the refusal must come first
    set_pin("junk\n")(app)
    (app / "install.sh").write_text("#!/bin/bash\n")
    (app / "agent-team").mkdir()


# name, what to do to the app first, args, exit code, text in the output, whether the run removes the copies
CASES = [
    ("no pin", lambda app: (app / "docs/agents/installed-from.txt").unlink(), [], 0, "nothing to remove: no installed-from.txt", False),
    ("clean old app", lambda app: None, [], 0, "TODO: .claude/settings.json runs cos_rotation_check.py", True),
    ("clean old app, no skill of its own", lambda app: shutil.rmtree(app / ".claude/skills/own"), [], 0, "remove  .agents/skills", True),
    ("hand edit stops the run", edit_tool, [], 1, "changed  scripts/tool.py", False),
    ("hand edit with --force", edit_tool, ["--force"], 0, "remove  scripts/tool.py", True),
    ("dry run", lambda app: None, ["--dry-run"], 0, "[dry-run] remove  scripts/tool.py", False),
    ("malformed pin", set_pin("collective-wisdom abc\n"), [], 2, "is not 'collective-wisdom", False),
    ("pinned commit not in the clone", set_pin(f"collective-wisdom {'0' * 40}\n"), [], 2, "run 'git fetch origin'", False),
    ("roots reached through links out of the app", link_out, [], 0, "skip    .agents/skills: it is reached through a link out of the app", False),
    ("inside collective-wisdom", in_collective_wisdom, [], 1, "collective-wisdom itself", False),
]


@pytest.mark.parametrize("name, setup, args, rc, text, removes", CASES, ids=[c[0] for c in CASES])
def test_remove_app_copies(world, name, setup, args, rc, text, removes):
    clone, app = world
    setup(app)
    before, outside = tree(app), snapshot(app.parent / "outside")
    code, out = run(clone, app, *args)
    assert (code, text in out) == (rc, True), out
    assert snapshot(app.parent / "outside") == outside
    after = tree(app)
    if not removes:
        assert after == before
        return
    own_skill = ".claude/skills/own/SKILL.md" in before  # .claude/skills stays, so the link to it does too
    assert after == {k: v for k, v in before.items() if k in OWN or (own_skill and k == ".agents/skills")}
    assert not any((app / d).exists() for d in ("scripts", ".claude/agents", ".claude/mods"))
    assert (app / ".agents").exists() == own_skill


def test_failed_delete_keeps_the_pin(world):
    clone, app = world
    (app / "scripts/tool.py").unlink()
    (app / "scripts/tool.py").mkdir()  # a directory where a listed file should be: the delete raises
    code, out = run(clone, app, "--force")
    assert code == 1 and "scripts/tool.py" in out, out
    assert (app / "docs/agents/installed-from.txt").is_file()
