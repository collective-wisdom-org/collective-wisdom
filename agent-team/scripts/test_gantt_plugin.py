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


def landed(version):
    return json.dumps([entry(version)])


# name, `claude plugin list` output (None: claude is not on PATH), clone version (None: no readable one), update output and exit code, --dry-run,
# the line expected ({clone} is the clone's folder), whether the update ran, the list output after the update ran (None: the same as before)
CASES = [
    ("older", json.dumps([entry("0.1.11")]), "0.1.12", ("", 0), False, "gantt-plugin: updated 0.1.11 -> 0.1.12", True, landed("0.1.12")),
    ("older by a longer version", json.dumps([entry("1.0")]), "1.0.1", ("", 0), False, "gantt-plugin: updated 1.0 -> 1.0.1", True, landed("1.0.1")),
    ("numbers, not text", json.dumps([entry("0.9.0")]), "0.10.0", ("", 0), False, "gantt-plugin: updated 0.9.0 -> 0.10.0", True, landed("0.10.0")),
    ("same", json.dumps([entry("0.1.12")]), "0.1.12", ("", 0), False, "gantt-plugin: current 0.1.12", False, None),
    ("same with a missing part", json.dumps([entry("1.0")]), "1.0.0", ("", 0), False, "gantt-plugin: current 1.0", False, None),
    ("newer", json.dumps([entry("0.2.0")]), "0.1.12", ("", 0), False, "gantt-plugin: current 0.2.0", False, None),
    ("installed version unreadable", json.dumps([entry("0.2.0-beta")]), "0.2.0", ("", 0), False, "gantt-plugin: left alone (the installed version does not read)", False, None),
    ("installed without a version", json.dumps([{"id": "agent-gantt@collective-wisdom", "scope": "user"}]), "0.2.0", ("", 0), False, "gantt-plugin: left alone (the installed version does not read)", False, None),
    ("project scope only", json.dumps([entry("0.1.0", "project")]), "0.1.12", ("", 0), False, "gantt-plugin: left alone (no user-scope entry)", False, None),
    ("user entry beside a project one", json.dumps([entry("0.1.0", "project"), entry("0.1.11")]), "0.1.12", ("", 0), False, "gantt-plugin: updated 0.1.11 -> 0.1.12", True, json.dumps([entry("0.1.0", "project"), entry("0.1.12")])),
    ("other plugins only", json.dumps([{"id": "other@x", "version": "1", "scope": "user"}]), "0.1.12", ("", 0), False, "gantt-plugin: not installed", False, None),
    ("list is not an array", "{}", "0.1.12", ("", 0), False, "gantt-plugin: not installed", False, None),
    ("list is not JSON", "oops", "0.1.12", ("", 0), False, "gantt-plugin: not installed", False, None),
    ("no claude", None, "0.1.12", ("", 0), False, "gantt-plugin: no claude", False, None),
    ("update fails", json.dumps([entry("0.1.11")]), "0.1.12", ("fetching\nnetwork down\n", 1), False, TODO_FAILED.format(why="it failed: network down"), True, None),
    ("update fails without output", json.dumps([entry("0.1.11")]), "0.1.12", ("", 1), False, TODO_FAILED.format(why="it failed"), True, None),
    ("dry run, older", json.dumps([entry("0.1.11")]), "0.1.12", ("", 0), True, "gantt-plugin: would update 0.1.11 -> 0.1.12", False, None),
    ("update exits 0, the version is still old", json.dumps([entry("0.1.11")]), "0.1.12", ("", 0), False, TODO_FAILED.format(why="it ran, but the installed version is still 0.1.11"), True, landed("0.1.11")),
    ("update lands newer than the clone", json.dumps([entry("0.1.11")]), "0.1.12", ("", 0), False, "gantt-plugin: updated 0.1.11 -> 0.1.13", True, landed("0.1.13")),
    ("update lands partway, still older", json.dumps([entry("0.1.10")]), "0.1.12", ("", 0), False, TODO_FAILED.format(why="it ran, but the installed version is still 0.1.11"), True, landed("0.1.11")),
    ("update ran, the second list does not read", json.dumps([entry("0.1.11")]), "0.1.12", ("", 0), False, "gantt-plugin: updated 0.1.11 -> 0.1.12", True, "oops"),
    ("clone version unreadable", json.dumps([entry("0.1.11")]), None, ("", 0), False, "gantt-plugin: todo Check the agent-gantt plugin version by hand: mods/agent-gantt/.claude-plugin/plugin.json in {clone} has no readable version, so it is unknown whether  claude plugin update agent-gantt --scope user  is needed.", False, None),
]


@pytest.mark.parametrize("name, listed, clone, update, dry, line, called, after", CASES, ids=[c[0] for c in CASES])
def test_gantt_plugin(tmp_path, name, listed, clone, update, dry, line, called, after):
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
        (tmp_path / "list-after.json").write_text(after if after is not None else listed)
        # the list after the update ran (the flag file is its mark) is the second list
        (stub / "claude").write_text(f'#!/bin/sh\necho "$*" >> "{tmp_path}/claude.log"\ncase "$1 $2" in\n  "plugin list") if [ -e "{tmp_path}/ran" ]; then cat "{tmp_path}/list-after.json"; else cat "{tmp_path}/list.json"; fi ;;\n  "plugin update") touch "{tmp_path}/ran"; cat "{tmp_path}/update.out" >&2; exit {update[1]} ;;\nesac\n')
        (stub / "claude").chmod(0o755)
    r = subprocess.run([sys.executable, "-I", str(clone_dir / "agent-team/scripts/gantt_plugin.py"), *(["--dry-run"] if dry else [])], env={**os.environ, "PATH": f"{stub}:/usr/bin:/bin"}, capture_output=True, text=True)
    log = (tmp_path / "claude.log").read_text().splitlines() if (tmp_path / "claude.log").exists() else []
    assert r.returncode == 0, r.stderr
    assert r.stdout == line.format(clone=clone_dir.resolve()) + "\n"
    assert (UPDATE in log) == called
