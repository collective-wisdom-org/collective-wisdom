import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent

# gh.sh stub: `pr view` prints a SHA, or $ROLLUP (exit $ROLLUP_RC) for the rollup query;
# the merge-state query prints "$MERGEABLE $MERGE_STATE" (exit $MERGE_RC);
# `pr checks` prints $CHECKS (exit $RC); `--watch` exits $WATCH_RC.
GH = """#!/usr/bin/env bash
if [[ " $* " == *mergeStateStatus* ]]; then echo "$MERGEABLE $MERGE_STATE"; exit "${MERGE_RC:-0}"; fi
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
def run_script(tmp_path, row, checks, rc, rollup, rollup_rc, merge=("MERGEABLE", "CLEAN", 0)):
    """The script runs from its own copy of the helpers, in a repo of its own, not the checkout around the tests."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("wait-for-ci.sh", "project_config.py", "app_root.py"):
        shutil.copy(SCRIPTS / name, scripts / name)
    (scripts / "gh.sh").write_text(GH)
    (scripts / "gh.sh").chmod(0o755)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "sleep").write_text(f"#!/bin/sh\necho >> {tmp_path / 'sleeps'}\nexit 0\n")
    (tmp_path / "bin" / "sleep").chmod(0o755)
    (tmp_path / "project.md").write_text(f"| Key | Value |\n|---|---|\n{row}\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    env = {
        **os.environ, "PROJECT_MD": str(tmp_path / "project.md"), "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
        "CHECKS": checks, "RC": str(rc), "WATCH_RC": str(rc), "ROLLUP": rollup, "ROLLUP_RC": str(rollup_rc),
        "MERGEABLE": merge[0], "MERGE_STATE": merge[1], "MERGE_RC": str(merge[2]),
    }
    r = subprocess.run(["bash", str(scripts / "wait-for-ci.sh"), "7"], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=60)
    sleeps = (tmp_path / "sleeps").read_text().count("\n") if (tmp_path / "sleeps").exists() else 0
    return r, sleeps


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
    r, _ = run_script(tmp_path, row, checks, rc, rollup, rollup_rc)
    assert r.returncode == code, r.stdout + r.stderr
    assert last in r.stdout.strip().splitlines()[-1]


CI = "| Required CI checks | `build` |"


@pytest.mark.parametrize(
    "row, checks, rc, merge, code, last, sleeps",
    [
        (CI, "", 1, ("CONFLICTING", "DIRTY", 0), 3, "conflict with main", 0),  # stops at once, no 20-poll loop
        (CI, "", 1, ("UNKNOWN", "DIRTY", 0), 3, "conflict with main", 0),  # DIRTY alone is a conflict
        (CI, "", 1, ("CONFLICTING", "UNKNOWN", 0), 3, "conflict with main", 0),  # so is CONFLICTING alone
        (NONE, "", 1, ("CONFLICTING", "DIRTY", 0), 3, "conflict with main", 0),  # a repo with no CI cannot merge it either
        (CI, "", 1, ("MERGEABLE", "CLEAN", 0), 2, "no checks on PR #7 at aaaa (mergeable MERGEABLE, mergeStateStatus CLEAN)", 19),
        (CI, "", 1, ("UNKNOWN", "UNKNOWN", 0), 2, "(mergeable UNKNOWN, mergeStateStatus UNKNOWN)", 19),  # polls on
        (CI, "", 1, ("", "", 1), 2, "(mergeable unknown, mergeStateStatus unknown)", 19),  # a failed read is not a conflict
        (CI, FAIL, 1, ("CONFLICTING", "DIRTY", 0), 1, "fail", 0),  # checks ran: watched as today
    ],
)
def test_conflict_line(tmp_path, row, checks, rc, merge, code, last, sleeps):
    r, slept = run_script(tmp_path, row, checks, rc, "0", 0, merge)
    assert r.returncode == code, r.stdout + r.stderr
    assert last in r.stdout.strip().splitlines()[-1]
    assert slept == sleeps
