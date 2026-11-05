#!/usr/bin/env python3
"""Decide whether a spec or merge needs the user's approval, from the `Approval risk tolerance` setting.

Usage:
    scripts/approval_policy.py auto <PREFIX>-N spec   Chief of Staff, root checkout: the ticket's awaiting-spec status line
    scripts/approval_policy.py check <Level>          ship-loop child: a relayed level (Low, Medium or High)

The setting is read from project.md as committed on refs/remotes/origin/main (project_config.approval_setting), never from a
working tree. A missing row, an unknown value or a failed read is `strict`. The rule:

    strict      asks for everything
    balanced    auto for Low
    permissive  auto for Low and Medium
    High, or a ticket that is not rated, always asks

A spec queued for the build lane with an auto-approved relay (`build-queued`) is checked again the same way.

Exit 0: auto. Last line: approval: auto spec [<PREFIX>-N] under <tolerance> (Risk: <Level>)
Exit 1: ask.  Last line: approval: ask [<PREFIX>-N] (<why>)
Exit 2: bad arguments, or the state file failed. Last line: approval: cannot <what>. Treat as ask.

scripts/cos_approve_pr.py --auto imports the rule, the Risk tail reader and the approval path list from here.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402
import project_config  # noqa: E402

AUTO_UP_TO = {"strict": (), "balanced": ("Low",), "permissive": ("Low", "Medium")}
LEVELS = ("Low", "Medium", "High")
AUTO_RELAY = "CHIEF OF STAFF: auto-approved"  # a queued auto approval is re-checked just before it is sent
RISK_TAIL = re.compile(r"Risk: (\w+) \(.*\)\.?\s*$")

# Files a PR may not change and still be auto-approved: the setting, the review rules and every other role doc
# (all of docs/agents/), and everything that enforces them (all scripts and all skills, agents and settings under
# .claude/). Matched with or without a leading `agent-team/`, ignoring case, and also by the bare name of a root
# link (`scripts`, `.claude`, `.github`, `.agents`), which `gh` can list as a file.
PATH_FILES = {"templates/project.md", "agents.md", "claude.md", "scripts", ".claude", ".github", ".agents"}
PATH_DIRS = ("docs/agents/", "scripts/", ".claude/", ".github/", ".agents/")


def risk_level(status):
    """Level from the `Risk: <Level> (<reason>).` tail of a status line, or None when absent or unknown.

    More than one `Risk: ` is ambiguous (a title or reason could carry a fake rating), so it is not rated.
    """
    status = status or ""
    i = status.find("Risk: ")
    m = RISK_TAIL.match(status[i:]) if i >= 0 and status.count("Risk: ") == 1 else None
    return m.group(1) if m and m.group(1) in LEVELS else None


def decide(tolerance, level):
    """(auto, why). Anything unknown is asked."""
    if tolerance not in AUTO_UP_TO:
        return False, "strict"
    if level is None:
        return False, "not rated"
    if level in AUTO_UP_TO[tolerance]:
        return True, level
    return False, "strict" if tolerance == "strict" else level


def on_approval_path(path):
    p = path.lower().removeprefix("./").removeprefix("agent-team/")
    return p in PATH_FILES or p.startswith(PATH_DIRS)


def _verdict(kind, who, level, setting):
    """(code, last line) for a level and a (tolerance, note) setting."""
    tolerance, note = setting
    auto, why = decide(tolerance, level)
    tag = f" {who}" if who else ""
    if auto:
        return 0, f"approval: auto {kind}{tag} under {tolerance} (Risk: {level})"
    return 1, f"approval: ask{tag} ({why}{'; ' + note if note else ''})"


def cmd_auto(tid, kind, setting):
    if kind != "spec":
        return 2, "approval: cannot decide a merge here; run scripts/cos_approve_pr.py <PREFIX>-N --auto"
    if not project_config.ticket_re(anchored=True).match(tid):
        return 2, "approval: cannot read arguments; usage: scripts/approval_policy.py auto <PREFIX>-N spec"
    try:
        t = cos_state.load(cos_state.DEFAULT_FILE).get("tickets", {}).get(tid)
        queued = isinstance(t, dict) and t.get("stage") == "build-queued" and str(t.get("pendingRelay") or "").startswith(AUTO_RELAY)
        if not isinstance(t, dict) or (t.get("stage") != "awaiting-spec" and not queued):
            return 1, f"approval: ask {tid} (not in awaiting-spec)"
        status = t.get("status")
        if not isinstance(status, str):
            return 1, f"approval: ask {tid} (not rated)"
    except (SystemExit, AttributeError):
        return 2, "approval: cannot read the state file"
    return _verdict("spec", tid, risk_level(status), setting())


def cmd_check(level, setting):
    if level not in LEVELS:
        return 2, "approval: cannot read arguments; usage: scripts/approval_policy.py check Low|Medium|High"
    return _verdict("spec", "", level, setting())


def main(argv, setting=project_config.approval_setting):
    if argv in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(argv) == 3 and argv[0] == "auto":
        code, line = cmd_auto(argv[1], argv[2], setting)
    elif len(argv) == 2 and argv[0] == "check":
        code, line = cmd_check(argv[1], setting)
    else:
        code, line = 2, "approval: cannot read arguments; usage: scripts/approval_policy.py auto <PREFIX>-N spec | check <Level>"
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
