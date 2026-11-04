import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent

# gh.sh stub: `pr view` prints a SHA; `pr checks` prints $CHECKS (exit $RC); `--watch` exits $WATCH_RC.
GH = """#!/usr/bin/env bash
if [ "$2" = view ]; then echo aaaa; exit 0; fi
if [[ " $* " == *" --watch "* ]]; then printf '%b' "$CHECKS"; exit "$WATCH_RC"; fi
printf '%b' "$CHECKS"; exit "$RC"
"""
PASS = "build\\tpass\\t1s\\turl\\n"
FAIL = "build\\tfail\\t1s\\turl\\n"


@pytest.mark.parametrize(
    "row, checks, rc, watch_rc, code, last",
    [
        ("| Required CI checks | `none (no CI yet)` |", "", 1, 1, 0, "no CI declared"),
        ("| Required CI checks | `none (no CI yet)` |", FAIL, 1, 1, 1, "fail"),
        ("| Required CI checks | `none (no CI yet)` |", PASS, 0, 0, 0, "pass"),
        ("| Required CI checks | `build, test` |", "", 1, 1, 2, "no checks"),
        ("| Test | `make test` |", "", 1, 1, 2, "no checks"),
        ("| Required CI checks | `none (no CI yet)` |", "", 4, 4, 2, "no checks"),
    ],
)
def test_required_ci_checks_row(tmp_path, row, checks, rc, watch_rc, code, last):
    (tmp_path / "scripts").mkdir()
    for name in ("wait-for-ci.sh", "project_config.py"):
        shutil.copy(SCRIPTS / name, tmp_path / "scripts" / name)
    gh = tmp_path / "scripts" / "gh.sh"
    gh.write_text(GH)
    gh.chmod(0o755)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "sleep").write_text("#!/bin/sh\nexit 0\n")
    (bin_dir / "sleep").chmod(0o755)
    md = tmp_path / "project.md"
    md.write_text(f"| Key | Value |\n|---|---|\n{row}\n")
    env = {
        **os.environ,
        "PROJECT_MD": str(md),
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "CHECKS": checks,
        "RC": str(rc),
        "WATCH_RC": str(watch_rc),
    }
    r = subprocess.run(
        ["bash", str(tmp_path / "scripts" / "wait-for-ci.sh"), "7"],
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert r.returncode == code, r.stdout + r.stderr
    assert last in r.stdout.strip().splitlines()[-1]
