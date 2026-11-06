"""Skills, role docs and templates call scripts through `~/.collective-wisdom/scripts/`.

A bare `scripts/x.py` or `./scripts/x.sh` only works in a repo that carries its own copy of the scripts.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = [".claude/skills", ".claude/agents", "docs/agents", "templates"]
SKIPPED = {"machine-instruction.md"}  # shipped text that names the folder itself
EDITED = {  # source files a doc tells you to edit, not scripts to run
    "docs/agents/trackers/README.md": {"scripts/test_tracker_docs.py", "scripts/project_config.py"},
}
BARE_CALL = re.compile(r"(?<![\w~/.-])(?:\./)?scripts/[\w*-]+\.(?:py|sh)\b")


def test_scripts_are_called_through_the_machine_install():
    bad = [
        f"{path.relative_to(ROOT)}:{number}: {match.group()}"
        for folder in FOLDERS
        for path in sorted((ROOT / folder).rglob("*.md"))
        if path.name not in SKIPPED
        for number, line in enumerate(path.read_text().splitlines(), 1)
        for match in BARE_CALL.finditer(line)
        if match.group() not in EDITED.get(path.relative_to(ROOT).as_posix(), ())
    ]
    assert not bad, "call scripts as ~/.collective-wisdom/scripts/<name>:\n" + "\n".join(bad)
