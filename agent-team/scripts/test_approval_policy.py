import ast
import json
from pathlib import Path

import pytest

import approval_policy as ap
import cos_state
import project_config

ROW = "| Approval risk tolerance (`strict`, `balanced` or `permissive`) | {} |\n"
HEADER = "| Key | Value |\n|---|---|\n"


def reader(root, text=None, fail=None):
    """A git runner whose root checkout is `root`; it serves `text` for the git show, or fails the named command."""
    def run(cmd):
        if fail and fail in cmd:
            raise OSError("boom")
        if cmd[1] == "worktree":
            return f"worktree {root}\nHEAD x\n"
        return text if cmd[1] == "show" else ""
    return run


# (project.md on origin/main, or None for a failed git call, expected tolerance)
SETTINGS = [
    (HEADER + ROW.format("`strict`. Which approvals..."), "strict"),
    (HEADER + ROW.format("`balanced`. Which approvals..."), "balanced"),
    (HEADER + ROW.format("`permissive`"), "permissive"),
    (HEADER + ROW.format("`Permissive`"), "permissive"),
    (HEADER + ROW.format("`yolo`"), "strict"),
    (HEADER + ROW.format("permissive, no backticks"), "strict"),
    (HEADER + "| Repo | `a/b` |\n", "strict"),
    ("", "strict"),
    (None, "strict"),
    ("show fails", "strict"),
]


@pytest.mark.parametrize("text, tolerance", SETTINGS)
def test_setting_reads_origin_main_and_fails_closed(tmp_path, text, tolerance):
    fail = {None: "fetch", "show fails": "show"}.get(text)
    run = reader(tmp_path, "" if fail else text, fail)
    (tmp_path / "docs" / "agents").mkdir(parents=True)
    (tmp_path / "docs" / "agents" / "project.md").write_text("| Repo | `a/b` |\n")
    assert project_config.approval_tolerance(run) == tolerance


# tolerance x level -> auto. Anything not in the table asks.
AUTO = {
    ("balanced", "Low"), ("permissive", "Low"), ("permissive", "Medium"),
}


@pytest.mark.parametrize("tolerance", ["strict", "balanced", "permissive", "", "yolo", None])
@pytest.mark.parametrize("level", ["Low", "Medium", "High", None, "Critical"])
def test_decide(tolerance, level):
    assert ap.decide(tolerance, level)[0] == ((tolerance, level) in AUTO)


PATHS = [
    ("docs/agents/project.md", True),
    ("agent-team/templates/project.md", True),
    ("templates/project.md", True),
    ("scripts/cos_approve_pr.py", True),
    ("agent-team/scripts/approval_policy.py", True),
    ("agent-team/scripts/cos_rank.py", True),
    ("scripts/test_cos.py", True),
    (".claude/skills/write-ticket/SKILL.md", True),
    ("agent-team/.claude/agents/code-reviewer.md", True),
    ("agent-team/.github/workflows/ci.yml", True),
    (".github/CODEOWNERS", True),
    ("docs/agents/code-review.md", True),
    ("agent-team/docs/agents/security-review.md", True),
    ("docs/agents/trackers/linear.md", True),
    ("scripts", True),
    ("packages/foo/.claude/skills/x/SKILL.md", True),
    ("install.sh", True),
    ("agent-team/templates/machine-instruction.md", True),
    ("templates/machine-instruction.md", True),
    (".agents/skills", True),
    ("agent-team/Scripts/x.py", True),
    ("AGENTS.md", True),
    ("agent-team/CLAUDE.md", True),
    ("agent-team/docs/superpowers/specs/x.md", False),
    ("src/docs/agents/project.md", False),
    ("src/scripts/x.py", False),
    (".cursor/hooks.json", True),
    (".codex/config.toml", True),
    ("AGENTS.override.md", True),
    ("CLAUDE.local.md", True),
    (".mcp.json", True),
    (".vscode/tasks.json", True),
    ("docs/superpowers/specs/CLAUDE.md", True),
    ("agent-team/templates/AGENTS.md", True),
    ("agent-team/templates/other.md", False),
]


@pytest.mark.parametrize("path, on", PATHS)
def test_approval_path(path, on):
    assert ap.on_approval_path(path) is on


TAILS = [
    ("Build ready. Risk: Low (copy only).", "Low"),
    ("Title Risk: Low (copy). Build ready. Risk: High (auth).", None),
    ("Risk: Medium (changes how the team works)", "Medium"),
    ("PR #4 ready. Risk: High (auth (login) path).", "High"),
    ("Risk: High (see Risk: Low (a)).", None),
    ("Risk: Low (x). More text after", None),
    ("Risk: Severe (x).", None),
    ("Risk: low (x).", None),
    ("no rating here", None),
    ("", None),
    (None, None),
]


@pytest.mark.parametrize("status, level", TAILS)
def test_risk_level(status, level):
    assert ap.risk_level(status) == level


# CLI: (state ticket or None, argv, setting, exit code, last-line part)
def ticket(stage="awaiting-build", status="Build ready. Risk: Medium (x).", **more):
    return {"stage": stage, "status": status, **more}


AUTO_TEXT = "CHIEF OF STAFF: auto-approved the spec under `permissive`."


CLI = [
    (ticket(), ["auto", "ABC-1", "spec"], "permissive", 0, "auto spec ABC-1 under permissive (Risk: Medium)"),
    (ticket(), ["auto", "ABC-1", "spec"], "balanced", 1, "ask ABC-1 (Medium)"),
    (ticket(), ["auto", "ABC-1", "spec"], "strict", 1, "ask ABC-1 (strict)"),
    (ticket(status="Build ready."), ["auto", "ABC-1", "spec"], "permissive", 1, "(not rated)"),
    (ticket(stage="build"), ["auto", "ABC-1", "spec"], "permissive", 1, "not in awaiting-build"),
    (None, ["auto", "ABC-1", "spec"], "permissive", 1, "not in awaiting-build"),
    (ticket(stage="build-queued", pendingRelay=AUTO_TEXT), ["auto", "ABC-1", "spec"], "permissive", 0, "auto spec ABC-1"),
    (ticket(stage="build-queued", pendingRelay="CHIEF OF STAFF: the user approved"), ["auto", "ABC-1", "spec"], "permissive", 1, "not in awaiting-build"),
    (ticket(), ["auto", "XYZ-1", "spec"], "permissive", 2, "cannot read arguments"),
    (ticket(), ["auto", "ABC-1", "merge"], "permissive", 2, "cannot decide a merge"),
    (ticket(), ["check", "Low"], "balanced", 0, "auto spec under balanced (Risk: Low)"),
    (ticket(), ["check", "High"], "permissive", 1, "ask (High)"),
    (ticket(), ["check", "Huge"], "permissive", 2, "cannot read arguments"),
    (ticket(), [], "permissive", 2, "cannot read arguments"),
]


@pytest.mark.parametrize("t, argv, tolerance, code, line", CLI)
def test_cli(tmp_path, monkeypatch, capsys, t, argv, tolerance, code, line):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {"ABC-1": t} if t else {}}))
    monkeypatch.setattr(cos_state, "DEFAULT_FILE", state)
    assert ap.main(argv, lambda: (tolerance, "")) == code
    assert line in capsys.readouterr().out.strip().splitlines()[-1]


def test_cli_state_failure_is_cannot(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cos_state, "DEFAULT_FILE", tmp_path / "missing.json")
    assert ap.main(["auto", "ABC-1", "spec"], lambda: ("permissive", "")) == 2
    assert "approval: cannot read the state file" in capsys.readouterr().out


# No Hands: with a run active every level is auto (High and unrated too), the tolerance is not read, and the ask rules for a spec's stage still hold.
def no_setting():
    raise AssertionError("the tolerance is not read under No Hands")


HANDS_CLI = [
    (ticket(status="Build ready. Risk: High (auth)."), ["auto", "ABC-1", "spec"], 0, "auto spec ABC-1 under No Hands (Risk: High)"),
    (ticket(status="Build ready."), ["auto", "ABC-1", "spec"], 0, "under No Hands (Risk: unrated)"),
    (ticket(stage="build"), ["auto", "ABC-1", "spec"], 1, "not in awaiting-build"),
    (ticket(), ["check", "no-hands"], 0, "auto spec under No Hands"),
]


@pytest.mark.parametrize("t, argv, code, line", HANDS_CLI)
def test_cli_under_a_run(tmp_path, monkeypatch, capsys, t, argv, code, line):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"tickets": {"ABC-1": t}}))
    monkeypatch.setattr(cos_state, "DEFAULT_FILE", state)
    monkeypatch.setattr(ap.no_hands, "active", lambda: True)
    assert ap.main(argv, no_setting) == code
    assert line in capsys.readouterr().out.strip().splitlines()[-1]


def test_check_no_hands_asks_without_a_run(capsys):
    assert ap.main(["check", "no-hands"], no_setting) == 1
    assert "ask (no active No Hands run)" in capsys.readouterr().out


HANDS = [
    ("docs/agents/project.md", True),
    ("agent-team/templates/project.md", True),
    ("install.sh", True),
    (".github/workflows/ci.yml", True),
    ("packages/x/.github/CODEOWNERS", True),
    ("AGENTS.md", True),
    ("agent-team/scripts/approval_policy.py", True),
    ("scripts/test_approval_policy.py", True),
    ("scripts/gh.sh", True),
    ("scripts/prices.json", True),
    (".claude/skills/chief-of-staff/approvals.md", True),
    ("agent-team/.claude/skills/merge-pr/SKILL.md", True),
    ("agent-team/.claude/agents/code-reviewer.md", True),
    ("agent-team/.claude/skills/owasp-security/SKILL.md", True),
    ("agent-team/templates/machine-instruction.md", True),
    (".claude/settings.local.json", True),
    (".cursor/mcp.json", True),
    (".mcp.json", True),
    (".codex/config.toml", True),
    ("mods/agent-gantt/hooks/x.ts", True),
    (".claude-plugin/marketplace.json", True),
    ("agent-team/.claude/mods/status-pane/hooks/x.ts", True),
    (".claude/hooks/stop.sh", True),
    ("agent-team/scripts/cos_rank.py", False),
    ("scripts/cos_restart.py", False),
    ("agent-team/.claude/skills/write-ticket/SKILL.md", False),
    ("README.md", False),
]


@pytest.mark.parametrize("path, on", HANDS)
def test_hands_path(path, on):
    assert ap.on_hands_path(path) is on


def test_hands_path_scripts_import_only_hands_path_scripts():
    """A gate cannot move into a helper the list leaves out: every local module a listed script loads is listed too."""
    here = Path(__file__).parent
    local = {f.stem for f in here.glob("*.py") if not f.name.startswith("test_")}
    listed = {n.removesuffix(".py") for n in ap.HANDS_SCRIPTS}
    missing = {}
    for name in sorted(listed & local):
        for node in ast.walk(ast.parse((here / f"{name}.py").read_text())):
            if isinstance(node, ast.Import):
                found = {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                found = {node.module}
            elif isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) in ("_load", "spec_from_file_location"):
                found = {a.value for a in node.args[:1] if isinstance(a, ast.Constant)}  # how the scripts load a sibling by name
            else:
                continue
            for mod in found & local - listed:
                missing.setdefault(name, set()).add(mod)
    assert not missing, f"hands-path scripts import scripts that are not on HANDS_SCRIPTS: {missing}"
