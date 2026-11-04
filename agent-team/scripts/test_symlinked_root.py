import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent


@pytest.fixture
def app(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    shutil.copytree(SCRIPTS, real / "scripts", ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    root = tmp_path / "app"
    root.mkdir()
    (root / "scripts").symlink_to(real / "scripts")
    (root / "docs" / "agents").mkdir(parents=True)
    (root / "docs" / "agents" / "project.md").write_text("| Issue identifier prefix | `ZZ` |\n")
    return root


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
    env = {k: v for k, v in os.environ.items() if k != "PROJECT_MD"}
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        f"import {module}; print({module}.{attr})"
    )
    out = subprocess.run(
        [sys.executable, "-I", "-c", code, str(app / "scripts")],
        capture_output=True, text=True, env=env, check=True,
    ).stdout.strip()
    assert out == str(app / rel if rel else app)


def test_agent_usage_names_the_repo_not_agent_team(app):
    subprocess.run(["git", "init", "-q"], cwd=app, check=True)
    sys.path.insert(0, str(SCRIPTS))
    try:
        import agent_usage
    finally:
        sys.path.remove(str(SCRIPTS))
    assert agent_usage.project_name(app / "scripts" / "agent_usage.py") == "app"
