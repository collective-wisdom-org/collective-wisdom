#!/usr/bin/env python3
"""Decide whether a spec or merge needs the user's approval, from the `Approval risk tolerance` setting.

Usage:
    ~/.collective-wisdom/scripts/approval_policy.py auto <PREFIX>-N spec   Chief of Staff, root checkout: the ticket's awaiting-build status line
    ~/.collective-wisdom/scripts/approval_policy.py check <Level>          ship-loop child: a relayed level (Low, Medium or High)
    ~/.collective-wisdom/scripts/approval_policy.py check no-hands [<PREFIX>-N]   ship-loop child: exit 0 only while a No Hands run is active
                                                                                  (and, with a ticket id, the run started that ticket)

The setting is read from project.md as committed on refs/remotes/origin/<merge target branch> (project_config.approval_setting); the level is never read
from a working tree, and the merge target branch is read from the root checkout. A missing row, an unknown value or a failed read is `strict`. The rule:

    strict      asks for everything
    balanced    auto for Low
    permissive  auto for Low and Medium
    High, or a ticket that is not rated, always asks

A spec queued for the build lane with an auto-approved relay (`build-queued`) is checked again the same way.

While a No Hands run is active (no_hands.active()), every level is auto, High and unrated included, and the last line says
`under No Hands`, for a ticket the run started (the `noHands.started` list) only; a ticket in flight when the run began keeps the tolerance.
With no run nothing above changes. HANDS_PATH is the short list of files a No Hands merge may not change.

Exit 0: auto. Last line: approval: auto spec [<PREFIX>-N] under <tolerance> (Risk: <Level>)  (under No Hands: Risk may be `unrated`)
Exit 1: ask.  Last line: approval: ask [<PREFIX>-N] (<why>)
Exit 2: bad arguments, or the state file failed. Last line: approval: cannot <what>. Treat as ask.

~/.collective-wisdom/scripts/cos_approve_pr.py --auto imports the rule, the Risk tail reader and the approval and hands path lists from here.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import cos_state  # noqa: E402
import no_hands  # noqa: E402
import project_config  # noqa: E402

AUTO_UP_TO = {"strict": (), "balanced": ("Low",), "permissive": ("Low", "Medium")}
LEVELS = ("Low", "Medium", "High")
AUTO_RELAY = "CHIEF OF STAFF: auto-approved"  # a queued auto approval is re-checked just before it is sent
RISK_TAIL = re.compile(r"Risk: (\w+) \(.*\)\.?\s*$")

# Files a PR may not change and still be auto-approved: the setting, the review rules and every other role doc
# (all of docs/agents/), everything that enforces them (all scripts) and every dot-directory or dot-file at any depth
# (.claude, .github, .agents, .cursor, .codex, .vscode, .mcp.json, .gitignore ...), plus agent instruction files
# (AGENTS.md, CLAUDE.md, AGENTS.override.md, CLAUDE.local.md ...) at any depth and the shipped project and machine-instruction templates.
# Matched with or without a leading `agent-team/`, ignoring case. It also matches the bare name `scripts`, because `gh`
# lists a link by that name as a file, and an old branch may still carry one.
PATH_FILES = {"templates/project.md", "templates/agents.md", "templates/machine-instruction.md", "scripts", "install.sh", "tag-release.sh"}
PATH_DIRS = ("docs/agents/", "scripts/")

# The hands path: what a No Hands merge may not change (the files that decide approvals, the mode and its caps, the merge and
# review gates, the security review skills, hook, permission and MCP configs, mods, CI and the always-on instructions). Matched like the approval path. Each script is listed with its test, and
# test_approval_policy.py fails when a listed script imports a local helper that is not listed, so a gate cannot move out of the list.
HANDS_SCRIPTS = (
    "approval_policy.py", "no_hands.py", "cos_approve_pr.py", "cos_user_check.py", "merge_pr.py", "review_gate.py", "review_scope.py",
    "ci_review.py", "wait-for-ci.sh", "gh.sh", "cos_brief.py", "cos_state.py", "cos_tick.py", "cos_route.py", "cos_head_check.py",
    "agent_usage.py", "prices.json", "project_config.py", "user_config.py", "app_root.py",
    "release_notes.py", "pr_diff_delta.py",  # imported by merge_pr.py and review_scope.py
)
HANDS_TESTS = {"scripts/test_" + re.sub(r"\W", "_", n.removesuffix(".py")) + ".py" for n in HANDS_SCRIPTS if n.endswith((".py", ".sh"))}
TEST_CONFIG = {"conftest.py", "pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"}  # change how CI runs the tests, at the repo root or under agent-team/
HANDS_PATH = frozenset(
    TEST_CONFIG | {"docs/agents/project.md", "templates/project.md", "templates/machine-instruction.md", "install.sh", "tag-release.sh",
     ".cursor/hooks.json", ".cursor/mcp.json", ".mcp.json",
     "docs/agents/security-review.md", "docs/agents/code-review.md", "docs/agents/chief-of-staff.md", "docs/agents/github-auth.md",
     ".claude/agents/code-reviewer.md", ".claude/agents/security-reviewer.md"}
    | {f"scripts/{n}" for n in HANDS_SCRIPTS} | HANDS_TESTS
)
HANDS_DIRS = (
    *(f".claude/skills/{n}/" for n in ("chief-of-staff", "ship-loop", "open-pr", "security-review", "merge-pr", "owasp-security", "agent-security", "auditing-security")),
    ".codex/", ".claude-plugin/", "mods/", ".claude/mods/", ".claude/hooks/",  # agent config, the marketplace and the mods
)


def risk_level(status):
    """Level from the `Risk: <Level> (<reason>).` tail of a status line, or None when absent or unknown.

    More than one `Risk: ` is ambiguous (a title or reason could carry a fake rating), so it is not rated.
    """
    status = status or ""
    i = status.find("Risk: ")
    m = RISK_TAIL.match(status[i:]) if i >= 0 and status.count("Risk: ") == 1 else None
    return m.group(1) if m and m.group(1) in LEVELS else None


def decide(tolerance, level, hands=False):
    """(auto, why). Anything unknown is asked. hands: a No Hands run is active, so every level, unrated included, is auto."""
    if hands:
        return True, level or "unrated"
    if tolerance not in AUTO_UP_TO:
        return False, "strict"
    if level is None:
        return False, "not rated"
    if level in AUTO_UP_TO[tolerance]:
        return True, level
    return False, "strict" if tolerance == "strict" else level


def _norm(path):
    p = path.lower().removeprefix("./").removeprefix("agent-team/")
    name = p.rsplit("/", 1)[-1]
    return p, name, name.startswith(("agents.", "claude.")) and name.endswith(".md")  # path, file name, an agent instruction file


def on_approval_path(path):
    p, _, instructions = _norm(path)
    return p in PATH_FILES or p.startswith(PATH_DIRS + (".",)) or "/." in p or instructions


SHADOWS = frozenset(sys.stdlib_module_names) | {"sitecustomize", "usercustomize", "conftest"}
HANDS_STEMS = frozenset(n.split(".")[0] for n in HANDS_SCRIPTS)
PYTHONISH = (".py", ".so", ".pyd", ".pyc", ".pth")  # file types Python imports or loads


def shadows_imports(p, name):
    """True for a file that changes what the gate scripts import or how their tests run, though no listed script imports it.

    Under scripts/, each path part cut at its first `.` is a stem: a part that names a package (any directory above the file) or a
    Python-ish file (.py .so .pyd .pyc .pth) whose stem is a standard-library module, sitecustomize, usercustomize, conftest or the
    stem of a HANDS_SCRIPTS file (scripts/json/__init__.py, scripts/no_hands/__init__.py, scripts/cos_state.cpython-313-darwin.so,
    scripts/encodings/x.py). A last part with no `.` (a symlink) gets the same stem check. A test config file (TEST_CONFIG) at any depth under scripts/. Any `*.pth` file; anything in a `__pycache__` directory.
    """
    parts = p.split("/")
    if name.endswith(".pth") or "__pycache__" in parts:
        return True
    if parts[0] != "scripts":
        return False
    names = SHADOWS | HANDS_STEMS
    if name in TEST_CONFIG:
        return True
    last_loads = name.endswith(PYTHONISH) or "." not in name  # a symlink or extensionless entry named like a module can be a package
    return any(part.split(".")[0] in names for part in parts[1:-1]) or (last_loads and name.split(".")[0] in names)


def on_hands_path(path):
    p, name, instructions = _norm(path)
    settings = p.startswith(".claude/settings") and name.endswith(".json")  # .claude/settings.json, settings.local.json
    return (p in HANDS_PATH or p.startswith(HANDS_DIRS) or settings or ".github" in p.split("/")[:-1] or name == "codeowners" or instructions
            or shadows_imports(p, name))


def _verdict(kind, who, level, setting, ticket=None):
    """(code, last line) for a level and a setting: a function giving (tolerance, note), read only when No Hands does not apply.

    No Hands applies when a run is active and `ticket` is one the run started; any other ticket (in flight when the run began) uses the tolerance.
    """
    hands = no_hands.active(ticket=ticket)
    tolerance, note = ("No Hands", "") if hands else setting()
    auto, why = decide(tolerance, level, hands)
    tag = f" {who}" if who else ""
    if auto:
        return 0, f"approval: auto {kind}{tag} under {tolerance} (Risk: {level or 'unrated'})"
    return 1, f"approval: ask{tag} ({why}{'; ' + note if note else ''})"


def cmd_auto(tid, kind, setting):
    if kind != "spec":
        return 2, "approval: cannot decide a merge here; run ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto"
    if not project_config.ticket_re(anchored=True).match(tid):
        return 2, "approval: cannot read arguments; usage: ~/.collective-wisdom/scripts/approval_policy.py auto <PREFIX>-N spec"
    try:
        t = cos_state.load(cos_state.DEFAULT_FILE).get("tickets", {}).get(tid)
        queued = isinstance(t, dict) and t.get("stage") == "build-queued" and str(t.get("pendingRelay") or "").startswith(AUTO_RELAY)
        if not isinstance(t, dict) or (t.get("stage") != "awaiting-build" and not queued):
            return 1, f"approval: ask {tid} (not in awaiting-build)"
        status = t.get("status")
    except (SystemExit, AttributeError):
        return 2, "approval: cannot read the state file"
    return _verdict("spec", tid, risk_level(status if isinstance(status, str) else None), setting, tid)


def cmd_check(level, setting, ticket=None):
    if level == "no-hands":
        if ticket is not None and not project_config.ticket_re(anchored=True).match(ticket):
            return 2, "approval: cannot read arguments; usage: ~/.collective-wisdom/scripts/approval_policy.py check no-hands [<PREFIX>-N]"
        if no_hands.active(ticket=ticket):
            return 0, "approval: auto spec under No Hands"
        return 1, "approval: ask (no active No Hands run" + (f" that started {ticket}" if ticket else "") + ")"
    if level not in LEVELS:
        return 2, "approval: cannot read arguments; usage: ~/.collective-wisdom/scripts/approval_policy.py check Low|Medium|High|no-hands"
    return _verdict("spec", "", level, setting)


def main(argv, setting=project_config.approval_setting):
    if argv in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(argv) == 3 and argv[0] == "auto":
        code, line = cmd_auto(argv[1], argv[2], setting)
    elif len(argv) == 2 and argv[0] == "check":
        code, line = cmd_check(argv[1], setting)
    elif len(argv) == 3 and argv[:2] == ["check", "no-hands"]:
        code, line = cmd_check(argv[1], setting, argv[2])
    else:
        code, line = 2, "approval: cannot read arguments; usage: ~/.collective-wisdom/scripts/approval_policy.py auto <PREFIX>-N spec | check <Level>|no-hands [<PREFIX>-N]"
    print(line)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
