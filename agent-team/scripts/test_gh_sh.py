import os
import subprocess
from pathlib import Path

GH_SH = Path(__file__).with_name("gh.sh")
FAKE = """#!/usr/bin/env bash
echo "GH_TOKEN=${GH_TOKEN-unset} GITHUB_TOKEN=${GITHUB_TOKEN-unset} ARGS=$*"
"""


def test_gh_sh_runs_gh_without_the_token_variables(tmp_path):
    (tmp_path / "gh").write_text(FAKE)
    (tmp_path / "gh").chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "GITHUB_TOKEN": "pat", "GH_TOKEN": "pat"}
    p = subprocess.run([str(GH_SH), "api", "user"], env=env, capture_output=True, text=True)
    assert p.returncode == 0
    assert p.stdout.strip() == "GH_TOKEN=unset GITHUB_TOKEN=unset ARGS=api user"
