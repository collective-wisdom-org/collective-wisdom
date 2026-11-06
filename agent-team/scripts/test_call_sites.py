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
EDITED = {  # source files a doc tells you to edit, not scripts to run
    "docs/agents/trackers/README.md": {"scripts/test_tracker_docs.py", "scripts/project_config.py"},
}
RULES = {  # name -> (pattern for a bare path, what to write instead)
    "script call": (
        re.compile(r"(?<![\w~/.-])(?:\./)?scripts/[\w*-]+\.(?:py|sh)\b"),
        "call scripts as ~/.collective-wisdom/scripts/<name>",
    ),
    "role doc": (
        re.compile(r"(?<![\w~/.-])docs/agents/(?!project\.md)(?:[\w-]+\.md|trackers/)"),
        "read role docs as ~/.collective-wisdom/docs/agents/<path>; only docs/agents/project.md is an app path",
    ),
}


@pytest.mark.parametrize("rule", RULES)
def test_shared_files_are_reached_through_the_machine_install(rule):
    pattern, fix = RULES[rule]
    bad = [
        f"{path.relative_to(ROOT)}:{number}: {match.group()}"
        for folder in FOLDERS
        for path in sorted((ROOT / folder).rglob("*.md"))
        if path.name not in SKIPPED
        for number, line in enumerate(path.read_text().splitlines(), 1)
        for match in pattern.finditer(line)
        if match.group() not in EDITED.get(path.relative_to(ROOT).as_posix(), ())
    ]
    assert not bad, fix + ":\n" + "\n".join(bad)
