import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("compact_check.py")
SKILL = "agent-team/.claude/skills/demo/SKILL.md"
VENDORED = "agent-team/.claude/skills/owasp-security/SKILL.md"


@pytest.mark.parametrize(
    "install, edits, base, code, last",
    [
        (True, {SKILL: "x" * 150}, "main", 0, "compact: run (+50 characters)"),
        (True, {SKILL: "x" * 40}, "main", 0, "compact: skip (net -60 characters)"),
        (True, {SKILL: "w" * 100}, "main", 0, "compact: skip (net 0 characters)"),
        (True, {"README.md": "y" * 500}, "main", 0, "compact: skip (no agent files changed)"),
        (True, {VENDORED: "z" * 500}, "main", 0, "compact: skip (no agent files changed)"),
        (True, {"agent-team/docs/agents/new.md": "n" * 30}, "main", 0, "compact: run (+30 characters)"),
        (True, {SKILL: "x" * 150}, "nope", 2, None),
        (False, {SKILL: "x" * 150}, "main", 0, "compact: skip (not collective-wisdom)"),
    ],
)
def test_compact_check(tmp_path, install, edits, base, code, last):
    def git(*args):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=tmp_path, capture_output=True, check=True,
        )

    def write(files):
        for rel, text in files.items():
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / rel).write_text(text)

    git("init", "-b", "main")
    write({SKILL: "x" * 100, VENDORED: "z", "README.md": "y"})
    if install:
        write({"install.sh": "#!/bin/sh\n"})
    git("add", "-A")
    git("commit", "-m", "base")
    write(edits)  # left uncommitted: a solo build doesn't commit

    p = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--base", base],
        cwd=tmp_path, capture_output=True, text=True,
    )
    out = p.stdout.splitlines()
    assert p.returncode == code
    if last:
        assert out[-1] == last
    else:
        assert out[-1].startswith("compact: cannot read")
