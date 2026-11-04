#!/usr/bin/env python3
"""Does the Chief of Staff thread need to rotate? One line: "ok ..." or "rotate: <reason>".

Usage:
    scripts/cos_rotation_check.py [--record-takeover]   # the model's call, every working turn
    scripts/cos_rotation_check.py --skill-commit        # print the current skill commit only
    scripts/cos_rotation_check.py --hook                # the Stop hook's call (hook JSON on stdin)

Reads the thread's context size (agent_usage.py --context), the skill commit and the
branch (git), and the state file. Exit 0 for "ok" and "rotate"; exit 2 with
"rotation-check: cannot read <what>" when the context, git or state is unreadable.
Plain mode saves chiefSessionId (when it differs from $CLAUDE_CODE_SESSION_ID) and,
with --record-takeover, takeoverContext, through cos_state.py. It never rotates anything.
--hook is silent unless the session is the Chief of Staff's (session_id equals
chiefSessionId) and stop_hook_active is false; then it blocks the stop on "rotate:" or
exit 2. It never writes and any error exits 0 silently.
COS_STATE_FILE and COS_PROJECTS_DIR override the state file and the transcripts directory.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

HERE = Path(__file__).absolute().parent


def _root():
    # The Stop hook runs from wherever the session's cwd has wandered; Claude Code names the project.
    # Move there first, so every script this one loads (project.md, agent_usage) finds the same repo.
    d = os.environ.get("CLAUDE_PROJECT_DIR")
    if d and "--hook" in sys.argv:
        try:
            os.chdir(d)
        except OSError:
            pass  # the hook exits 0 silently on any error
    return root()


ROOT = _root()
SIZE_CAP = 220_000
AGE_HOURS = 4
AGE_MIN_CONTEXT = 120_000
SKILL_PATHS = [
    ".claude/skills/chief-of-staff",
    ".claude/skills/project-manager",
    "docs/agents/chief-of-staff.md",
]


class Unreadable(Exception):
    pass


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_ts(s):
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def k(n):
    return f"{n // 1000}k"


def decide(state, context, started, now, commit, branch, cap=SIZE_CAP):
    """The one line. started and now are datetimes; context is a token count."""
    if state.get("paused"):
        return "ok (held: paused)"
    if state.get("rotation") is not None:
        return "ok (held: rotation)"
    until = parse_ts(state.get("rotationHeldUntil"))
    if until and until > now:
        return "ok (held: rotationHeldUntil)"
    old = state.get("skillCommit")
    if branch == "main" and old and commit != old:
        return f"rotate: skill changed {old[:7]}..{commit[:7]}"
    note = None
    if context >= cap:
        tk = state.get("takeoverContext")
        chief = state.get("chiefThreadId")
        off = (
            isinstance(tk, dict)
            and chief
            and tk.get("threadId") == chief
            and isinstance(tk.get("tokens"), int)
            and tk["tokens"] >= cap
        )
        if not off:
            return f"rotate: size {k(context)} >= {k(cap)}"
        note = f"ok (size trigger off: take-over ended at {k(tk['tokens'])})"
    hours = (now - started).total_seconds() / 3600
    if hours >= AGE_HOURS and context >= AGE_MIN_CONTEXT:
        return f"rotate: age {int(hours)}h, size {k(context)}"
    if note:
        return note
    if not old:
        return f"ok; set skillCommit {commit}"
    return f"ok context={k(context)}"


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise Unreadable("git")
    if r.returncode:
        raise Unreadable("git")
    return r.stdout.strip()


def skill_paths():
    """SKILL_PATHS resolved through symlinks, relative to the git top level; missing entries are skipped."""
    top = os.path.realpath(git("rev-parse", "--show-toplevel"))
    out = []
    for p in SKILL_PATHS:
        real = os.path.realpath(ROOT / p)
        if os.path.exists(real):
            out.append(os.path.relpath(real, top))
    return out


def skill_commit():
    paths = skill_paths()
    if not paths:
        raise Unreadable("git")
    commit = git("log", "-1", "--format=%H", "--", *[f":(top){p}" for p in paths])
    if not commit:
        raise Unreadable("git")
    return commit


def branch():
    return git("branch", "--show-current")


def read_context(sid=None):
    """(tokens, start time) of session sid, or of $CLAUDE_CODE_SESSION_ID."""
    projects = Path(os.environ.get("COS_PROJECTS_DIR") or Path.home() / ".claude" / "projects")
    try:
        with contextlib.redirect_stderr(io.StringIO()), mock.patch.dict(
            os.environ, {"CLAUDE_CODE_SESSION_ID": sid} if sid else {}
        ):
            line = load_module("agent_usage").context_line(projects)
    except SystemExit:
        raise Unreadable("context")
    m = re.fullmatch(r"context=(\d+) started=(\S+)", line)
    started = parse_ts(m.group(2)) if m else None
    if not started:
        raise Unreadable("context")
    return int(m.group(1)), started


def read_state(path):
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            return load_module("cos_state").load(path)
    except SystemExit:
        raise Unreadable("state")


def save_top(path, **keys):
    """Save top-level state keys through cos_state.py. False if it could not."""
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return load_module("cos_state").apply_file(path, [{"op": "top", "set": keys}]) == 0
    except (Exception, SystemExit):
        return False


def check(state, record=False, sid=None):
    """(line, takeoverContext to save or None). Raises Unreadable."""
    context, started = read_context(sid)
    tk = None
    if record and state.get("chiefThreadId"):
        tk = {"threadId": state["chiefThreadId"], "tokens": context}
        state = {**state, "takeoverContext": tk}
    now = datetime.now(timezone.utc)
    return decide(state, context, started, now, skill_commit(), branch()), tk


def run_hook(path):
    try:
        if not path.exists():
            return 0
        data = json.loads(sys.stdin.read())
        state = read_state(path)
        sid = data.get("session_id")
        if not sid or sid != state.get("chiefSessionId") or data.get("stop_hook_active"):
            return 0
        try:
            line = check(state, sid=sid)[0]
        except Unreadable as e:
            line = f"rotation-check: cannot read {e}"
        if not line.startswith("ok"):
            reason = f"{line}; run chief-of-staff § Thread rotation"
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    except Exception:
        pass
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Does the Chief of Staff thread need to rotate?")
    ap.add_argument("--hook", action="store_true")
    ap.add_argument("--record-takeover", action="store_true")
    ap.add_argument("--skill-commit", action="store_true")
    args = ap.parse_args(argv)
    path = Path(os.environ.get("COS_STATE_FILE") or ROOT / ".agent-team" / "state.json")
    if args.hook:
        return run_hook(path)
    try:
        if args.skill_commit:
            print(skill_commit())
            return 0
        state = read_state(path)
        sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
        if sid and sid != state.get("chiefSessionId"):
            save_top(path, chiefSessionId=sid)
        line, tk = check(state, record=args.record_takeover)
    except Unreadable as e:
        print(f"rotation-check: cannot read {e}")
        return 2
    if tk and not save_top(path, takeoverContext=tk):
        line += "; takeoverContext not saved"
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
