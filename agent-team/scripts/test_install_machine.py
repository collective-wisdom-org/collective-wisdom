import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

TOP = Path(__file__).absolute().parent.parent.parent
pytestmark = pytest.mark.skipif(not (TOP / "install.sh").exists(), reason="only meaningful in collective-wisdom")

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
BEGIN, END = "<!-- collective-wisdom:begin -->", "<!-- collective-wisdom:end -->"
SKILLS = [".claude/skills", ".agents/skills", ".cursor/skills"]
HOOK = "cos_rotation_check.py"
RULE = ".cursor/rules/collective-wisdom.mdc"
RULE_TEXT = "---\ndescription: collective-wisdom agent team. Where the team runs and where it does not.\nalwaysApply: true\n---\n\nTeam text v1.\n"


def git(cwd, *args):
    subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def world(tmp_path):
    """A throwaway clone with two skills, one agent and the instruction template, and an empty HOME."""
    cw, home = tmp_path / "cw", tmp_path / "home"
    at = cw / "agent-team"
    for rel, text in {
        ".claude/skills/alpha/SKILL.md": "a\n", ".claude/skills/beta/SKILL.md": "b\n", ".claude/agents/ag.md": "ag\n", ".cursor/agents/ag.md": "ag\n",
        "scripts/cos_rotation_check.py": "x\n", "templates/machine-instruction.md": "Team text v1.\n",
    }.items():
        (at / rel).parent.mkdir(parents=True, exist_ok=True)
        (at / rel).write_text(text)
    shutil.copy(TOP / "install.sh", cw / "install.sh")
    git(cw, "init", "-q", "-b", "main")
    git(cw, "add", "-A")
    git(cw, "commit", "-q", "-m", "init")
    home.mkdir()
    return cw.resolve(), home


def install(cw, home, *args):
    r = subprocess.run(["bash", str(cw / "install.sh"), *args], env={**os.environ, "HOME": str(home)}, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def tree(home):
    return sorted((str(p.relative_to(home)), os.readlink(p) if p.is_symlink() else p.read_text() if p.is_file() else "") for p in home.rglob("*"))


def test_fresh_install_links_everything_and_a_rerun_changes_nothing(world):
    cw, home = world
    rc, out = install(cw, home)
    assert rc == 0, out
    assert os.readlink(home / ".collective-wisdom") == str(cw / "agent-team")
    for base in SKILLS:
        for name in ("alpha", "beta"):
            assert os.readlink(home / base / name) == str(cw / "agent-team/.claude/skills" / name)
    assert os.readlink(home / ".claude/agents/ag.md") == str(cw / "agent-team/.claude/agents/ag.md")
    assert os.readlink(home / ".cursor/agents/ag.md") == str(cw / "agent-team/.cursor/agents/ag.md")
    hooks = json.loads((home / ".claude/settings.json").read_text())["hooks"]["Stop"]
    assert [h["command"] for e in hooks for h in e["hooks"]] == ['python3 -I "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true']
    for f in (".claude/CLAUDE.md", ".codex/AGENTS.md"):
        assert (home / f).read_text() == f"{BEGIN}\nTeam text v1.\n{END}\n"
    assert (home / RULE).read_text() == RULE_TEXT and "Paste this into Cursor" not in out
    assert "installed collective-wisdom " + subprocess.run(["git", "rev-parse", "HEAD"], cwd=cw, capture_output=True, text=True).stdout.strip() in out
    before = tree(home)
    rc, out = install(cw, home)
    assert rc == 0 and "Done: 0 change(s)" in out and tree(home) == before


# name, settings file text (None: absent), keys that must survive, the hook command count after, a TODO substring (None: no TODO about settings)
SETTINGS = [
    ("existing keys survive", json.dumps({"model": "x", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}}), ["model"], 2, None),
    ("a hook already there is not added twice", json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": f"python3 x/{HOOK}"}]}]}}), [], 1, None),
    ("invalid JSON is left alone", "{not json", [], 0, "Stop hook to ~/.claude/settings.json by hand"),
]


@pytest.mark.parametrize("name, text, keys, count, todo", SETTINGS, ids=[c[0] for c in SETTINGS])
def test_settings_merge(world, name, text, keys, count, todo):
    cw, home = world
    (home / ".claude").mkdir()
    (home / ".claude/settings.json").write_text(text)
    rc, out = install(cw, home)
    assert rc == 0, out
    raw = (home / ".claude/settings.json").read_text()
    assert ("Stop hook to ~/.claude/settings.json by hand" in out) == (todo is not None)
    if todo:
        assert raw == text
        return
    data = json.loads(raw)
    assert all(k in data for k in keys)
    assert sum(HOOK in h["command"] or h["command"] == "echo hi" for e in data["hooks"]["Stop"] for h in e["hooks"]) == count


CMD = 'python3 -I "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true'
OTHER = {"command": "echo hi", "timeout": 5}
# name, ~/.cursor/hooks.json before (None: absent; a str is written as is), the file after a run and after a second run (None: left as it was, with a TODO)
CURSOR_HOOKS = [
    ("missing", None, {"version": 1, "hooks": {"stop": [{"command": CMD}]}}),
    ("other hooks and keys survive", {"version": 1, "extra": 1, "hooks": {"stop": [OTHER], "beforeShellExecution": [OTHER]}},
     {"version": 1, "extra": 1, "hooks": {"stop": [OTHER, {"command": CMD}], "beforeShellExecution": [OTHER]}}),
    ("already there", {"version": 1, "hooks": {"stop": [{"command": f"python3 x/{HOOK}"}]}}, {"version": 1, "hooks": {"stop": [{"command": f"python3 x/{HOOK}"}]}}),
    ("no version gets 1", {"hooks": {}}, {"version": 1, "hooks": {"stop": [{"command": CMD}]}}),
    ("not an object", "[1]", None),
    ("stop is not a list", {"hooks": {"stop": {}}}, None),
]


@pytest.mark.parametrize("name, before, after", CURSOR_HOOKS, ids=[c[0] for c in CURSOR_HOOKS])
def test_cursor_hooks_merge_once(world, name, before, after):
    cw, home = world
    f = home / ".cursor/hooks.json"
    if before is not None:
        f.parent.mkdir()
        f.write_text(before if isinstance(before, str) else json.dumps(before))
    for _ in range(2):  # a rerun adds nothing
        rc, out = install(cw, home)
        assert rc == 0, out
        assert ("stop hook to ~/.cursor/hooks.json by hand" in out) == (after is None)
        if after is None:
            assert f.read_text() == before if isinstance(before, str) else json.loads(f.read_text()) == before
        else:
            assert json.loads(f.read_text()) == after


def test_own_names_are_kept_and_listed_and_dead_links_are_dropped(world):
    cw, home = world
    (home / ".claude/skills/alpha").mkdir(parents=True)  # the person's own folder of a shipped name
    (home / ".agents/skills").mkdir(parents=True)
    (home / ".agents/skills/beta").symlink_to(home / "elsewhere")  # a dangling link that is not ours
    (home / ".claude/skills/old").symlink_to(cw / "agent-team/.claude/skills/old")  # ours: dropped by a newer release
    (home / ".cursor/skills").mkdir(parents=True)
    (home / ".cursor/skills/mine").symlink_to(home / "elsewhere")  # not ours, not shipped
    (home / ".cursor/agents").mkdir(parents=True)
    (home / ".cursor/agents/old.md").symlink_to(cw / "agent-team/.cursor/agents/old.md")  # ours: dropped by a newer release
    rc, out = install(cw, home)
    assert rc == 0, out
    assert not (home / ".cursor/agents/old.md").is_symlink()
    assert (home / ".claude/skills/alpha").is_dir() and not (home / ".claude/skills/alpha").is_symlink()
    assert os.readlink(home / ".agents/skills/beta") == str(home / "elsewhere")
    assert os.readlink(home / ".cursor/skills/mine") == str(home / "elsewhere")
    assert not (home / ".claude/skills/old").is_symlink()
    assert f"Kept {home}/.claude/skills/alpha" in out and f"Kept {home}/.agents/skills/beta" in out and "old" in out.split("TODO:")[0]
    assert os.readlink(home / ".claude/skills/beta")  # the other names still linked


def test_instruction_block_is_replaced_and_outside_text_stays(world):
    cw, home = world
    (home / ".claude").mkdir()
    (home / ".claude/CLAUDE.md").write_text(f"mine above\n\n{BEGIN}\nold text\n{END}\n\nmine below\n")
    assert install(cw, home)[0] == 0
    assert (home / ".claude/CLAUDE.md").read_text() == f"mine above\n\n{BEGIN}\nTeam text v1.\n{END}\n\nmine below\n"


def test_linked_worktree_is_refused_and_dry_run_writes_nothing(world, tmp_path):
    cw, home = world
    git(cw, "worktree", "add", "-q", str(tmp_path / "wt"))
    rc, out = install(tmp_path / "wt", home)
    assert rc == 1 and "linked git worktree" in out and not list(home.iterdir())
    rc, out = install(cw, home, "--dry-run")
    assert rc == 0 and "[dry-run] link" in out and not list(home.iterdir())


# name, args: any argument but --dry-run, including the old call from an app's agent-team-update.sh
REFUSED_FORMS = [("a target path", ["{app}"]), ("update from a tag", ["--update", "--from", "v0.4", "{app}"]), ("a flag without a path", ["--check"]), ("--to takes its value", ["--to", "HEAD"])]


@pytest.mark.parametrize("name, args", REFUSED_FORMS, ids=[c[0] for c in REFUSED_FORMS])
def test_any_argument_but_dry_run_is_refused_and_writes_nothing(world, tmp_path, name, args):
    cw, home = world
    app = tmp_path / "app"
    app.mkdir()
    before = (tree(home), tree(app))
    rc, out = install(cw, home, *[a.format(app=app) for a in args])
    assert rc == 2 and "install.sh no longer installs into an app. Run ./install.sh with no path to install on this machine." in out, out
    assert "remove_app_copies.py" in out and (tree(home), tree(app)) == before


# name, what is at ~/.collective-wisdom before the run (a link to a folder, or a real folder)
OCCUPIED = [("a link elsewhere", "link"), ("a real folder", "dir")]


@pytest.mark.parametrize("name, kind", OCCUPIED, ids=[c[0] for c in OCCUPIED])
@pytest.mark.parametrize("flags", [[], ["--dry-run"]], ids=["real", "dry-run"])
def test_a_foreign_collective_wisdom_path_is_refused_before_any_write(world, name, kind, flags):
    cw, home = world
    (home / "elsewhere").mkdir()
    if kind == "link":
        (home / ".collective-wisdom").symlink_to(home / "elsewhere")
    else:
        (home / ".collective-wisdom").mkdir()
    before = tree(home)
    rc, out = install(cw, home, *flags)
    assert rc == 1 and "Refusing: ~/.collective-wisdom" in out and "Remove it and run ./install.sh again." in out
    assert tree(home) == before


def test_an_unreadable_instruction_file_is_listed_and_the_rest_still_installs(world):
    cw, home = world
    (home / ".codex/AGENTS.md").mkdir(parents=True)  # a folder where the file should be
    rc, out = install(cw, home)
    assert rc == 0, out
    assert (home / ".codex/AGENTS.md").is_dir()
    assert "Fix ~/.codex/AGENTS.md by hand" in out and "Fix ~/.claude/CLAUDE.md" not in out
    assert (home / ".claude/CLAUDE.md").read_text() == f"{BEGIN}\nTeam text v1.\n{END}\n"
    assert os.readlink(home / ".collective-wisdom") == str(cw / "agent-team")


# name, what is at the rule path before the run (a file with this text, or None for a folder), the Fix TODO expected
RULE_CASES = [("a stale file is replaced", "old text\n", False), ("a folder is listed and the rest installs", None, True)]


@pytest.mark.parametrize("name, text, todo", RULE_CASES, ids=[c[0] for c in RULE_CASES])
def test_cursor_rule_file(world, name, text, todo):
    cw, home = world
    (home / RULE).parent.mkdir(parents=True)
    (home / RULE).write_text(text) if text else (home / RULE).mkdir()
    rc, out = install(cw, home)
    assert rc == 0, out
    assert ("Fix ~/.cursor/rules/collective-wisdom.mdc by hand" in out) == todo
    assert (home / RULE).is_dir() == todo and (todo or (home / RULE).read_text() == RULE_TEXT)
    assert (home / ".claude/CLAUDE.md").read_text() == f"{BEGIN}\nTeam text v1.\n{END}\n"
