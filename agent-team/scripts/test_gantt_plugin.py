import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).absolute().parent / "gantt_plugin.py"
UPDATE = "plugin update agent-gantt --scope user"
TODO_FAILED = "gantt-plugin: todo Update the agent-gantt plugin (the Gantt pane) by hand: claude plugin update agent-gantt --scope user ({why})"


def entry(version="0.1.12", scope="user"):
    return {"id": "agent-gantt@collective-wisdom", "version": version, "scope": scope}


# name, `claude plugin list` output (None: claude is not on PATH), clone version (None: no readable one), update output and exit code, --dry-run,
# the line expected ({clone} is the clone's folder), whether the update ran
CASES = [
    ("older", json.dumps([entry("0.1.11")]), "0.1.12", ("", 0), False, "gantt-plugin: updated 0.1.11 -> 0.1.12", True),
    ("older by a longer version", json.dumps([entry("1.0")]), "1.0.1", ("", 0), False, "gantt-plugin: updated 1.0 -> 1.0.1", True),
    ("numbers, not text", json.dumps([entry("0.9.0")]), "0.10.0", ("", 0), False, "gantt-plugin: updated 0.9.0 -> 0.10.0", True),
    ("same", json.dumps([entry("0.1.12")]), "0.1.12", ("", 0), False, "gantt-plugin: current 0.1.12", False),
    ("same with a missing part", json.dumps([entry("1.0")]), "1.0.0", ("", 0), False, "gantt-plugin: current 1.0", False),
    ("newer", json.dumps([entry("0.2.0")]), "0.1.12", ("", 0), False, "gantt-plugin: current 0.2.0", False),
    ("installed version unreadable", json.dumps([entry("0.2.0-beta")]), "0.2.0", ("", 0), False, "gantt-plugin: left alone (the installed version does not read)", False),
    ("installed without a version", json.dumps([{"id": "agent-gantt@collective-wisdom", "scope": "user"}]), "0.2.0", ("", 0), False, "gantt-plugin: left alone (the installed version does not read)", False),
    ("project scope only", json.dumps([entry("0.1.0", "project")]), "0.1.12", ("", 0), False, "gantt-plugin: left alone (no user-scope entry)", False),
    ("user entry beside a project one", json.dumps([entry("0.1.0", "project"), entry("0.1.11")]), "0.1.12", ("", 0), False, "gantt-plugin: updated 0.1.11 -> 0.1.12", True),
    ("other plugins only", json.dumps([{"id": "other@x", "version": "1", "scope": "user"}]), "0.1.12", ("", 0), False, "gantt-plugin: not installed", False),
    ("list is not an array", "{}", "0.1.12", ("", 0), False, "gantt-plugin: not installed", False),
    ("list is not JSON", "oops", "0.1.12", ("", 0), False, "gantt-plugin: not installed", False),
    ("no claude", None, "0.1.12", ("", 0), False, "gantt-plugin: no claude", False),
    ("update fails", json.dumps([entry("0.1.11")]), "0.1.12", ("fetching\nnetwork down\n", 1), False, TODO_FAILED.format(why="it failed: network down"), True),
    ("update fails without output", json.dumps([entry("0.1.11")]), "0.1.12", ("", 1), False, TODO_FAILED.format(why="it failed"), True),
    ("dry run, older", json.dumps([entry("0.1.11")]), "0.1.12", ("", 0), True, "gantt-plugin: would update 0.1.11 -> 0.1.12", False),
    ("clone version unreadable", json.dumps([entry("0.1.11")]), None, ("", 0), False, "gantt-plugin: todo Check the agent-gantt plugin version by hand: mods/agent-gantt/.claude-plugin/plugin.json in {clone} has no readable version, so it is unknown whether  claude plugin update agent-gantt --scope user  is needed.", False),
]


@pytest.mark.parametrize("name, listed, clone, update, dry, line, called", CASES, ids=[c[0] for c in CASES])
def test_gantt_plugin(tmp_path, name, listed, clone, update, dry, line, called):
    clone_dir, stub = tmp_path / "cw", tmp_path / "bin"
    (clone_dir / "agent-team/scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, clone_dir / "agent-team/scripts/gantt_plugin.py")
    manifest = clone_dir / "mods/agent-gantt/.claude-plugin/plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"name": "agent-gantt", **({"version": clone} if clone else {})}))
    stub.mkdir()
    if listed is not None:
        (tmp_path / "list.json").write_text(listed)
        (tmp_path / "update.out").write_text(update[0])
        (stub / "claude").write_text(f'#!/bin/sh\necho "$*" >> "{tmp_path}/claude.log"\ncase "$1 $2" in\n  "plugin list") cat "{tmp_path}/list.json" ;;\n  "plugin update") cat "{tmp_path}/update.out" >&2; exit {update[1]} ;;\nesac\n')
        (stub / "claude").chmod(0o755)
    r = subprocess.run([sys.executable, "-I", str(clone_dir / "agent-team/scripts/gantt_plugin.py"), *(["--dry-run"] if dry else [])], env={**os.environ, "PATH": f"{stub}:/usr/bin:/bin"}, capture_output=True, text=True)
    log = (tmp_path / "claude.log").read_text().splitlines() if (tmp_path / "claude.log").exists() else []
    assert r.returncode == 0, r.stderr
    assert r.stdout == line.format(clone=clone_dir.resolve()) + "\n"
    assert (UPDATE in log) == called
