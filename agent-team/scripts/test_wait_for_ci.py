import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent

# gh.sh stub: `pr view` prints a SHA, or $ROLLUP (exit $ROLLUP_RC) for the rollup query;
# `pr checks` prints $CHECKS (exit $RC); `--watch` exits $WATCH_RC.
GH = """#!/usr/bin/env bash
if [[ " $* " == *statusCheckRollup* ]]; then echo "$ROLLUP"; exit "$ROLLUP_RC"; fi
if [ "$2" = view ]; then echo aaaa; exit 0; fi
printf '%b' "$CHECKS"; if [[ " $* " == *" --watch "* ]]; then exit "$WATCH_RC"; fi; exit "$RC"
"""
NONE = "| Required CI checks | `none (no CI yet)` |"
PASS = "build\\tpass\\t1s\\turl\\n"
FAIL = "build\\tfail\\t1s\\turl\\n"


@pytest.mark.parametrize(
    "row, checks, rc, rollup, rollup_rc, code, last",
    [
        (NONE, "", 1, "0", 0, 0, "no CI declared"),
        ("| Required CI checks | none |", "", 1, "0", 0, 0, "no CI declared"),
        (NONE, FAIL, 1, "1", 0, 1, "fail"),
        (NONE, PASS, 0, "1", 0, 0, "pass"),
        (NONE, "", 1, "1", 0, 2, "no checks"),  # a check registered late: not "no CI"
        (NONE, "", 1, "", 1, 2, "cannot watch"),  # gh failed: not "no CI"
        ("| Required CI checks | `build, test` |", "", 1, "0", 0, 2, "no checks"),
        ("| Test | `make test` |", "", 1, "0", 0, 2, "no checks"),
    ],
)
def test_no_ci_declared(tmp_path, row, checks, rc, rollup, rollup_rc, code, last):
    """The script runs from its own copy of the helpers, in a repo of its own, not the checkout around the tests."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("wait-for-ci.sh", "project_config.py", "app_root.py"):
        shutil.copy(SCRIPTS / name, scripts / name)
    (scripts / "gh.sh").write_text(GH)
    (scripts / "gh.sh").chmod(0o755)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "sleep").write_text("#!/bin/sh\nexit 0\n")
    (tmp_path / "bin" / "sleep").chmod(0o755)
    (tmp_path / "project.md").write_text(f"| Key | Value |\n|---|---|\n{row}\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    env = {
        **os.environ, "PROJECT_MD": str(tmp_path / "project.md"), "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
        "CHECKS": checks, "RC": str(rc), "WATCH_RC": str(rc), "ROLLUP": rollup, "ROLLUP_RC": str(rollup_rc),
    }
    r = subprocess.run(["bash", str(scripts / "wait-for-ci.sh"), "7"], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=60)
    assert r.returncode == code, r.stdout + r.stderr
    assert last in r.stdout.strip().splitlines()[-1]
