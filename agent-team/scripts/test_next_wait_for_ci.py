import os
import shutil
import subprocess

import pytest

from test_wait_for_ci import CI, FAIL, GH, NONE, PASS, SCRIPTS


def run_script(tmp_path, row, checks, rc, rollup, rollup_rc, merge, args):
    """test_wait_for_ci.run_script with extra arguments: the script runs from its own copy, in a repo of its own."""
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
        "MERGEABLE": merge[0], "MERGE_STATE": merge[1], "MERGE_RC": "0",
    }
    return subprocess.run(["bash", str(scripts / "wait-for-ci.sh"), "7", *args], capture_output=True, text=True, env=env, cwd=tmp_path, timeout=60)


CLEAN = ("MERGEABLE", "CLEAN")
DIRTY = ("CONFLICTING", "DIRTY")

# row, checks, exit code of gh checks, rollup, rollup exit, merge state, flags, wanted exit, last line, words in the next text
ROWS = [
    (CI, PASS, 0, "1", 0, CLEAN, [], 0, "pass", ["go on", "run wait-for-ci.sh again"]),
    (CI, FAIL, 1, "1", 0, CLEAN, [], 1, "fail", ["CI failed", "fix them, push"]),
    (NONE, "", 1, "0", 0, CLEAN, [], 0, "no CI declared", ["treat it like pass"]),
    # a conflict: merge, resolve, push, wait again, with the count one higher; the third is BLOCKED
    (CI, "", 1, "0", 0, DIRTY, [], 3, "conflict with main", ["merge origin/main", "--conflicts 1"]),
    (CI, "", 1, "0", 0, DIRTY, ["--conflicts", "1"], 3, "conflict with main", ["--conflicts 2"]),
    (CI, "", 1, "0", 0, DIRTY, ["--conflicts", "2"], 3, "conflict with main", ["third conflict line", "BLOCKED:"]),
    # exit 2: a retry the first time, BLOCKED the second
    (CI, "", 1, "0", 0, CLEAN, [], 2, "no checks on PR #7", ["run wait-for-ci.sh again once", "--attempt 2"]),
    (CI, "", 1, "0", 0, CLEAN, ["--attempt", "2"], 2, "no checks on PR #7", ["BLOCKED:", "quoting this line"]),
    (NONE, "", 1, "", 1, CLEAN, ["--attempt", "1"], 2, "cannot watch PR #7", ["--attempt 2"]),
    (NONE, "", 1, "", 1, CLEAN, ["--attempt", "2"], 2, "cannot watch PR #7", ["BLOCKED:"]),
]


@pytest.mark.parametrize("row, checks, rc, rollup, rollup_rc, merge, flags, code, last, words", ROWS)
def test_the_result_line_is_followed_by_its_next_text(tmp_path, row, checks, rc, rollup, rollup_rc, merge, flags, code, last, words):
    runs = {}
    for name, args in (("plain", []), ("counted", flags), ("next", [*flags, "--next"])):
        (tmp_path / name).mkdir()
        runs[name] = run_script(tmp_path / name, row, checks, rc, rollup, rollup_rc, merge, args)
    assert all(r.returncode == code for r in runs.values()), runs["next"].stdout + runs["next"].stderr
    *body, text = runs["next"].stdout.splitlines()
    assert body[-1].startswith("wait-for-ci: ") and last in body[-1]
    assert text.startswith("next: ") and all(w in text for w in words), text
    # the counts alone change nothing; --next adds the one line after the result line
    assert runs["counted"].stdout == runs["plain"].stdout
    assert body == runs["plain"].stdout.splitlines()


@pytest.mark.parametrize("args", [["--attempt"], ["--attempt", "x"], ["--conflicts", "-1"], ["--bogus"], ["8"]])
def test_bad_flags_are_a_usage_error(tmp_path, args):
    r = run_script(tmp_path, CI, PASS, 0, "1", 0, CLEAN, args)
    assert r.returncode == 2 and r.stdout == "" and r.stderr.startswith("usage: ~/.collective-wisdom/scripts/wait-for-ci.sh <PR number>")
