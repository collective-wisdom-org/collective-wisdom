#!/usr/bin/env python3
"""Update the agent-gantt plugin when the clone's mod is newer. One line on stdout, exit 0 whatever happens.

Usage:
    python3 -I ~/.collective-wisdom/scripts/gantt_plugin.py [--dry-run]

Compares the user-scope `agent-gantt@collective-wisdom` entry of `claude plugin list --json` with the version in
mods/agent-gantt/.claude-plugin/plugin.json of the clone this script sits in, and runs
`claude plugin update agent-gantt --scope user` when the installed one is older. It never installs.
A version reads only when it is dot-separated non-negative integers; versions compare part by part, a missing part as 0.
The line is one of:
    gantt-plugin: no claude
    gantt-plugin: not installed
    gantt-plugin: left alone (<why>)
    gantt-plugin: current <installed>
    gantt-plugin: would update <old> -> <new>        (--dry-run)
    gantt-plugin: updated <old> -> <new>
    gantt-plugin: todo <what to do by hand>
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_ID = "agent-gantt@collective-wisdom"
UPDATE = ["claude", "plugin", "update", "agent-gantt", "--scope", "user"]
UPDATE_TIMEOUT = 120
LIST_TIMEOUT = 60
CLONE = Path(__file__).resolve().parents[2]  # scripts/ -> agent-team/ -> the clone
MANIFEST = CLONE / "mods/agent-gantt/.claude-plugin/plugin.json"


def parse(value):
    """A version as a tuple of ints, or None when it is not dot-separated non-negative integers."""
    if isinstance(value, str) and re.fullmatch(r"\d+(\.\d+)*", value):
        return tuple(int(p) for p in value.split("."))
    return None


def older(a, b):
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) < b + (0,) * (n - len(b))


def clone_version():
    try:
        return json.loads(MANIFEST.read_text()).get("version")
    except (OSError, ValueError, AttributeError):
        return None


def installed_entries():
    """The plugin's list entries, or None when the list fails or is not a JSON array."""
    try:
        r = subprocess.run(["claude", "plugin", "list", "--json"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=LIST_TIMEOUT)
        plugins = json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if not isinstance(plugins, list):
        return None
    return [p for p in plugins if isinstance(p, dict) and p.get("id") == PLUGIN_ID]


def run_update():
    """None on success, else the reason, which is the last line of the output when there is one."""
    try:
        r = subprocess.run(UPDATE, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=UPDATE_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return "it failed"
    if r.returncode == 0:
        return None
    lines = (r.stdout + r.stderr).strip().splitlines()
    return f"it failed: {lines[-1].strip()}" if lines else "it failed"


def decide(dry_run):
    if not shutil.which("claude"):
        return "no claude"
    entries = installed_entries()
    if not entries:
        return "not installed"
    user = [e for e in entries if e.get("scope") == "user"]
    if not user:
        return "left alone (no user-scope entry)"
    have_text = user[0].get("version")
    have = parse(have_text)
    if have is None:
        return "left alone (the installed version does not read)"
    want_text = clone_version()
    want = parse(want_text)
    if want is None:
        return f"todo Check the agent-gantt plugin version by hand: {MANIFEST.relative_to(CLONE)} in {CLONE} has no readable version, so it is unknown whether  {' '.join(UPDATE)}  is needed."
    if not older(have, want):
        return f"current {have_text}"
    if dry_run:
        return f"would update {have_text} -> {want_text}"
    failed = run_update()
    if failed:
        return f"todo Update the agent-gantt plugin (the Gantt pane) by hand: {' '.join(UPDATE)} ({failed})"
    return f"updated {have_text} -> {want_text}"


def main():
    try:
        line = decide("--dry-run" in sys.argv[1:])
    except Exception as e:  # never take down an install or a Chief of Staff pass
        line = f"left alone ({type(e).__name__})"
    print(f"gantt-plugin: {line}")


if __name__ == "__main__":
    main()
