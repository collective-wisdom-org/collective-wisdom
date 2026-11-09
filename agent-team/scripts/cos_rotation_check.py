#!/usr/bin/env python3
"""Does the Chief of Staff thread need to rotate? One line: "ok ..." or "rotate: <reason>".

Usage:
    ~/.collective-wisdom/scripts/cos_rotation_check.py [--record-takeover]   # the model's call, every working turn
    ~/.collective-wisdom/scripts/cos_rotation_check.py --skill-commit        # print the current skill commit only
    ~/.collective-wisdom/scripts/cos_rotation_check.py --hook                # the Stop hook's call (hook JSON on stdin)

Reads the thread's context size (agent_usage.py --context), the skill commit (git history
of the clone this script sits in), the app's branch (git), and the state file. Exit 0 for "ok" and "rotate"; exit 2 with
"rotation-check: cannot read <what>" when the context, git or state is unreadable, or the `Merge target branch` row of project.md is invalid.
Plain mode saves chiefSessionId (when it differs from $CLAUDE_CODE_SESSION_ID) and,
with --record-takeover, takeoverContext, through cos_state.py. It never rotates anything.
With no $CLAUDE_CODE_SESSION_ID, plain mode looks for the newest Cursor transcript of the app changed in the last
2 minutes. If there is one, the run is on Cursor: that conversation id is saved as chiefSessionId and the size
trigger is off (no context size on Cursor), so only a skill change rotates.
--hook is silent in a repo with no docs/agents/project.md, when ~/.collective-wisdom/scripts/cos_rotation_check.py exists and is another file, and unless the session is the Chief of Staff's.
It reads Claude Code's Stop payload (session_id equals chiefSessionId, stop_hook_active false) and blocks the stop with
{"decision": "block", "reason": ...} on "rotate:" or exit 2. It reads Cursor's stop payload (conversation_id equals
chiefSessionId, loop_count 0, status completed), with the size trigger off, and answers {"followup_message": reason}.
It never writes and any error exits 0 silently.
COS_STATE_FILE, COS_PROJECTS_DIR and COS_CURSOR_PROJECTS_DIR override the state file, the Claude Code transcripts
directory and the Cursor projects directory (~/.cursor/projects).
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
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

HERE = Path(__file__).absolute().parent
# The clone's agent-team/ folder, through any ~/.collective-wisdom link. SKILL_PATHS and their history live here, not in the app.
TEAM = Path(os.path.realpath(HERE)).parent


def _root():
    # The Stop hook runs from wherever the session's cwd has wandered (Cursor starts it in ~/.cursor); both name the project.
    # Move there first, so every script this one loads (project.md, agent_usage) finds the same repo.
    d = os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if d and "--hook" in sys.argv:
        try:
            os.chdir(d)
        except OSError:
            pass  # the hook exits 0 silently on any error
    return root()


ROOT = _root()
import project_config  # noqa: E402  (after _root(): it must find the same repo)
SIZE_CAP = 220_000
CURSOR_FRESH_SECONDS = 120
QUIET_RELAY_MIN = 10
QUIET_ROTATED_MIN = 60
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


def minutes_since(ts, now):
    t = parse_ts(ts)
    return None if t is None else max(0, int((now - t).total_seconds() // 60))


def quiet_wait(state, now):
    """Why a skill change should wait for a quieter turn, or None when the turn is quiet."""
    tickets = state.get("tickets") if isinstance(state.get("tickets"), dict) else {}
    queued = sorted(
        (i for i, t in tickets.items() if isinstance(t, dict) and str(t.get("stage")).endswith("-queued")),
        key=lambda i: [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", i)],
    )
    if queued:
        return f"queued {queued[0]}"
    relay = minutes_since(state.get("lastRelayAt"), now)
    if relay is not None and relay < QUIET_RELAY_MIN:
        return f"relay {relay}m ago"
    rotated = [m for r in state.get("retiredThreads") or [] if isinstance(r, dict)
               for m in [minutes_since(r.get("retiredAt"), now)] if m is not None]
    if rotated and min(rotated) < QUIET_ROTATED_MIN:
        return f"rotated {min(rotated)}m ago"
    return None


def decide(state, context, now, commit, branch, cap=SIZE_CAP):
    """The one line. now is a datetime; context is a token count, or None when the size is unknown (Cursor)."""
    if state.get("paused"):
        return "ok (held: paused)"
    if state.get("rotation") is not None:
        return "ok (held: rotation)"
    until = parse_ts(state.get("rotationHeldUntil"))
    if until and until > now:
        return "ok (held: rotationHeldUntil)"
    old = state.get("skillCommit")
    waits = None
    if branch == project_config.target_branch() and old and commit != old:
        why = quiet_wait(state, now)
        if not why:
            return f"rotate: skill changed {old[:7]}..{commit[:7]}"
        waits = f"ok (skill change waits: {why})"
    note = None
    if context is not None and context >= cap:
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
    if note or waits:
        return note or waits
    if not old:
        return f"ok; set skillCommit {commit}"
    return "ok (size unknown on Cursor)" if context is None else f"ok context={k(context)}"


def git(*args, cwd=None):
    try:
        r = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise Unreadable("git")
    if r.returncode:
        raise Unreadable("git")
    return r.stdout.strip()


def skill_paths():
    """SKILL_PATHS resolved through symlinks, relative to the clone's git top level; missing entries are skipped."""
    top = os.path.realpath(git("rev-parse", "--show-toplevel", cwd=TEAM))
    out = []
    for p in SKILL_PATHS:
        real = os.path.realpath(TEAM / p)
        if os.path.exists(real):
            out.append(os.path.relpath(real, top))
    return out


def skill_commit():
    paths = skill_paths()
    if not paths:
        raise Unreadable("git")
    commit = git("log", "-1", "--format=%H", "--", *[f":(top){p}" for p in paths], cwd=TEAM)
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


def bare(cid):
    """A Cursor conversation id without the `agent-` prefix that sessions started from T3 Code carry in their folder name."""
    return cid[6:] if isinstance(cid, str) and cid.startswith("agent-") else cid


def cursor_conversation():
    """The id of the newest Cursor transcript of this app changed in the last 2 minutes, or None."""
    projects = Path(os.environ.get("COS_CURSOR_PROJECTS_DIR") or Path.home() / ".cursor" / "projects")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(ROOT)).strip("-")  # how Cursor names a project folder
    now = time.time()
    fresh = []
    for f in (projects / slug / "agent-transcripts").glob("*/*.jsonl"):
        try:
            m = f.stat().st_mtime
        except OSError:
            continue
        if f.stem == f.parent.name and 0 <= now - m <= CURSOR_FRESH_SECONDS:
            fresh.append((m, f.stem))
    return max(fresh)[1] if fresh else None


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


def check(state, record=False, sid=None, sized=True):
    """(line, takeoverContext to save or None). Raises Unreadable. sized=False: no context size (Cursor)."""
    context = read_context(sid)[0] if sized else None
    tk = None
    if record and context is not None and state.get("chiefThreadId"):
        tk = {"threadId": state["chiefThreadId"], "tokens": context}
        state = {**state, "takeoverContext": tk}
    now = datetime.now(timezone.utc)
    try:
        project_config.target_branch()
    except SystemExit:
        raise Unreadable("the Merge target branch row of project.md")
    line = decide(state, context, now, skill_commit(), branch())
    return (f"{line}; take-over context={k(context)}" if record and context is not None else line), tk


def run_hook(path):
    try:
        if not (ROOT / "docs" / "agents" / "project.md").is_file():
            return 0  # not a repo the agent team serves
        machine = Path.home() / ".collective-wisdom" / "scripts" / "cos_rotation_check.py"
        if machine.exists() and os.path.realpath(machine) != os.path.realpath(__file__):
            return 0  # an app's own copy: the user-level hook runs the machine copy, which reads the clone's history
        if not path.exists():
            return 0
        data = json.loads(sys.stdin.read())
        state = read_state(path)
        cursor = "conversation_id" in data and data.get("hook_event_name") == "stop"
        if cursor:  # sent back once already, or the user stopped it or it errored: leave it be
            sid, skip = data["conversation_id"], bool(data.get("loop_count")) or data.get("status") != "completed"
        else:
            sid, skip = data.get("session_id"), bool(data.get("stop_hook_active"))
        mine = state.get("chiefSessionId")
        if not sid or (bare(sid) != bare(mine) if cursor else sid != mine) or skip:
            return 0
        try:
            line = check(state, sid=sid, sized=not cursor)[0]
        except Unreadable as e:
            line = f"rotation-check: cannot read {e}"
        if not line.startswith("ok"):
            reason = f"{line}; run chief-of-staff/rotation.md § Thread rotation"
            answer = {"followup_message": reason} if cursor else {"decision": "block", "reason": reason}
            print(json.dumps(answer, ensure_ascii=False))
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
        cursor_id = None if sid else cursor_conversation()
        sid = sid or cursor_id
        if sid and sid != state.get("chiefSessionId"):
            save_top(path, chiefSessionId=sid)
        line, tk = check(state, record=args.record_takeover, sized=not cursor_id)
    except Unreadable as e:
        print(f"rotation-check: cannot read {e}")
        return 2
    if tk and not save_top(path, takeoverContext=tk):
        line += "; takeoverContext not saved"
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
