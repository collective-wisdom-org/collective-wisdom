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


@pytest.mark.parametrize(
    "module, attr, rel",
    [
        ("project_config", "DEFAULT", "docs/agents/project.md"),
        ("cos_state", "DEFAULT_FILE", ".agent-team/state.json"),
        ("cos_idle_check", "DEFAULT_STATE", ".agent-team/state.json"),
        ("cos_parent_check", "DEFAULT_STATE", ".agent-team/state.json"),
        ("docs_index", "INDEX", "docs/superpowers/index"),
        ("merge_pr", "ROOT", ""),
        ("pr_diff_delta", "ROOT", ""),
        ("cos_merged_check", "ROOT", ""),
        ("cos_rotation_check", "ROOT", ""),
    ],
)
def test_root_is_the_link_parent(app, module, attr, rel):
    # `python3 scripts/x.py` puts the RESOLVED folder on sys.path[0] while __file__ keeps the link path.
    code = (
        "import runpy, sys; sys.path.insert(0, sys.argv[2]); "
        "g = runpy.run_path(sys.argv[1], run_name='linked'); "
        f"print(g[{attr!r}])"
    )
    link = app / "scripts" / f"{module}.py"
    out = subprocess.run(
        [sys.executable, "-I", "-c", code, str(link), str((app / "scripts").resolve())],
        capture_output=True, text=True, env=_env(), check=True, cwd=app,
    ).stdout.strip()
    assert out == str(app / rel if rel else app)


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
    assert agent_usage.project_name(app / "scripts" / "agent_usage.py") == "app"
