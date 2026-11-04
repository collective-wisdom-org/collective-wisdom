import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
TOP = SCRIPTS.parent.parent

# Apps have a real scripts/ folder holding their own scripts too; this checks the symlinked layout of collective-wisdom only.
pytestmark = pytest.mark.skipif(not (TOP / "install.sh").exists(), reason="only meaningful in collective-wisdom")


@pytest.fixture
def app(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    shutil.copytree(SCRIPTS, real / "scripts", ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    root = tmp_path / "app"
    root.mkdir()
    (root / "scripts").symlink_to(real / "scripts")
    (root / "docs" / "agents").mkdir(parents=True)
    (root / "docs" / "agents" / "project.md").write_text("| Issue identifier prefix | `ZZ` |\n| Repo | `acme/widgets` |\n")
    return root


def _env():
    return {k: v for k, v in os.environ.items() if k != "PROJECT_MD"}


ROOTS = [
    ("project_config", "DEFAULT", "docs/agents/project.md"),
    ("cos_state", "DEFAULT_FILE", ".agent-team/state.json"),
    ("cos_idle_check", "DEFAULT_STATE", ".agent-team/state.json"),
    ("cos_parent_check", "DEFAULT_STATE", ".agent-team/state.json"),
    ("docs_index", "INDEX", "docs/superpowers/index"),
    ("release_notes", "NOTES", "docs/superpowers/release-notes"),
    ("merge_pr", "ROOT", ""),
    ("pr_diff_delta", "ROOT", ""),
    ("cos_merged_check", "ROOT", ""),
    ("cos_ready_check", "ROOT", ""),
    ("cos_rotation_check", "ROOT", ""),
    ("cos_handoff", "ROOT", ""),
    ("cos_sweep", "ROOT", ""),
    ("cos_worktree_check", "ROOT", ""),
]
# Loads a script file by path like `python3 scripts/x.py` does and prints one module attribute.
CODE = (
    "import runpy, sys; sys.path.insert(0, sys.argv[2]); "
    "g = runpy.run_path(sys.argv[1], run_name='linked'); "
    "print(g[sys.argv[3]])"
)


def _attr(script, folder, attr, cwd):
    return subprocess.run(
        [sys.executable, "-I", "-c", CODE, str(script), str(folder), attr],
        capture_output=True, text=True, env=_env(), check=True, cwd=cwd,
    ).stdout.strip()


@pytest.mark.parametrize("module, attr, rel", ROOTS)
def test_root_is_the_link_parent(app, module, attr, rel):
    # Run through the link like `python3 scripts/x.py` (the RESOLVED folder is on sys.path[0]); with the app not a git repo, root() is the cwd.
    out = _attr(app / "scripts" / f"{module}.py", (app / "scripts").resolve(), attr, app)
    assert out == str(app / rel if rel else app)


@pytest.fixture
def git_app(tmp_path):
    """An app repo with a worktree, and a real copy of the scripts outside both."""
    scripts = tmp_path / "tools" / "scripts"
    shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    top, wt = tmp_path / "app", tmp_path / "wt"
    (top / "sub").mkdir(parents=True)
    (top / "docs" / "agents").mkdir(parents=True)
    (top / "docs" / "agents" / "project.md").write_text("| Issue identifier prefix | `ZZ` |\n| Repo | `acme/widgets` |\n")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "x"], ["worktree", "add", "-q", str(wt)]):
        subprocess.run([*git, *args], cwd=top, check=True, capture_output=True)
    return scripts, top, wt


@pytest.mark.parametrize("module, attr, rel", ROOTS)
def test_root_is_the_working_repo(git_app, module, attr, rel):
    scripts, top, wt = git_app
    for repo, cwd in ((top, top), (top, top / "sub"), (wt, wt)):
        want = repo.resolve() / rel if rel else repo.resolve()
        assert Path(_attr(scripts / f"{module}.py", scripts, attr, cwd)) == want, cwd


SCRIPT_NAMES = sorted(
    p.name for p in SCRIPTS.glob("*.py")
    if not p.name.startswith("test_") and p.name not in ("conftest.py", "project_config.py", "agent_usage.py")
)
MARKERS = ("has no usable", "has no `<owner>/<repo>`", "ModuleNotFoundError", "Traceback")


@pytest.mark.parametrize("name", SCRIPT_NAMES)
def test_script_runs_by_link_path(app, name):
    # no -I: like `python3 scripts/x.py`, sys.path[0] is then the resolved folder
    r = subprocess.run(
        [sys.executable, f"scripts/{name}", "--help"],
        capture_output=True, text=True, env=_env(), cwd=app,
    )
    out = r.stdout + r.stderr
    assert not any(m in out for m in MARKERS), out
    if name not in ("merge_pr.py", "pr_diff_delta.py"):  # these exit 2 on any bad args
        assert r.returncode == 0, out


def test_agent_usage_names_the_repo_not_agent_team(app):
    subprocess.run(["git", "init", "-q"], cwd=app, check=True)
    sys.path.insert(0, str(SCRIPTS))
    try:
        import agent_usage
    finally:
        sys.path.remove(str(SCRIPTS))
    assert agent_usage.project_name(app) == "app"
