import os
import subprocess
from pathlib import Path

import pytest

GH_SH = Path(__file__).with_name("gh.sh")
# Fake gh: `auth token -u cw-sam` prints a token, any other login fails; everything else records env and args.
FAKE = """#!/usr/bin/env bash
if [ "$1 $2 $3" = "auth token -u" ]; then
  [ "$4" = cw-sam ] && echo fake-token && exit 0
  exit 1
fi
echo "GH_TOKEN=${GH_TOKEN-unset} GITHUB_TOKEN=${GITHUB_TOKEN-unset} ARGS=$*" >> "$RECORD"
"""
SAM = "| Builder login | `cw-sam` |\n"


@pytest.mark.parametrize(
    "role, row, code, seen, stderr",
    [
        (None, SAM, 0, "GH_TOKEN=unset GITHUB_TOKEN=unset ARGS=api user", ""),
        ("builder", "| Builder login | `none` |\n", 0, "GH_TOKEN=unset GITHUB_TOKEN=unset ARGS=api user", ""),
        ("builder", SAM, 0, "GH_TOKEN=fake-token GITHUB_TOKEN=unset ARGS=api user", ""),
        ("janitor", SAM, 2, None, "unknown role"),
        ("builder", "| Builder login | `cw-gone` |\n", 2, None, "no gh login for cw-gone"),
    ],
)
def test_gh_sh_runs_as_the_role_login(tmp_path, role, row, code, seen, stderr):
    (tmp_path / "gh").write_text(FAKE)
    (tmp_path / "gh").chmod(0o755)
    (tmp_path / "project.md").write_text("| Key | Value |\n|---|---|\n" + row)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "RECORD": str(tmp_path / "rec"),
           "PROJECT_MD": str(tmp_path / "project.md"), "GITHUB_TOKEN": "pat", "GH_TOKEN": "pat"}
    env.pop("AGENT_GH_ROLE", None)
    if role:
        env["AGENT_GH_ROLE"] = role
    p = subprocess.run([str(GH_SH), "api", "user"], env=env, capture_output=True, text=True)
    assert p.returncode == code
    assert stderr in p.stderr and "fake-token" not in p.stdout + p.stderr
    rec = tmp_path / "rec"
    assert (rec.read_text().strip() if rec.exists() else None) == seen
