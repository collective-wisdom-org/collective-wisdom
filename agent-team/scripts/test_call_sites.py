"""Skills, role docs and templates reach the machine install through `~/.collective-wisdom/`.

A bare `scripts/x.py` or `./scripts/x.sh` only works in a repo that carries its own copy of the scripts.
A bare `docs/agents/<role doc>.md` only works in a repo that carries its own copy of the role docs.
Only `docs/agents/project.md` lives in the app.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = [".claude/skills", ".claude/agents", "docs/agents", "templates"]
SKIPPED = {"machine-instruction.md"}  # shipped text that names the folder itself
RULES = {  # name -> (pattern for a bare path, what to write instead, folders to check)
    "script call": (
        re.compile(r"(?<![\w~/.-])(?:\./)?scripts/[\w*-]+\.(?:py|sh)\b"),
        "call scripts as ~/.collective-wisdom/scripts/<name>",
        FOLDERS,
    ),
    "role doc": (
        re.compile(r"(?<![\w~/.-])docs/agents/(?!project\.md)(?:[\w-]+\.md|trackers/)"),
        "read role docs as ~/.collective-wisdom/docs/agents/<path>; only docs/agents/project.md is an app path",
        FOLDERS,
    ),
    # A template is copied into an app, where a relative link to a role doc points at nothing.
    # Role docs link to each other relatively, which resolves inside the machine install.
    "role doc link": (
        re.compile(r"\]\((?!project\.md)(?:trackers/|[\w-]+\.md)"),
        "link role docs as ~/.collective-wisdom/docs/agents/<path>; a relative link breaks in an app",
        ["templates"],
    ),
}


@pytest.mark.parametrize("rule", RULES)
def test_shared_files_are_reached_through_the_machine_install(rule):
    pattern, fix, folders = RULES[rule]
    bad = [
        f"{path.relative_to(ROOT)}:{number}: {match.group()}"
        for folder in folders
        for path in sorted((ROOT / folder).rglob("*.md"))
        if path.name not in SKIPPED
        for number, line in enumerate(path.read_text().splitlines(), 1)
        for match in pattern.finditer(line)
    ]
    assert not bad, fix + ":\n" + "\n".join(bad)
