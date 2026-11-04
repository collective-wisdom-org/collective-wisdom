import subprocess
from pathlib import Path

import pytest

TOP = Path(__file__).absolute().parent.parent.parent

pytestmark = pytest.mark.skipif(
    not (TOP / "install.sh").exists(), reason="collective-wisdom root only"
)


def symlinks():
    out = subprocess.run(
        ["git", "ls-files", "-s", "-co", "--exclude-standard"],
        cwd=TOP, capture_output=True, text=True, check=True,
    ).stdout
    found = set()
    for line in out.splitlines():
        if "\t" in line:  # staged entry: "<mode> <sha> <stage>\t<path>"
            meta, path = line.split("\t", 1)
            if meta.split()[0] == "120000":
                found.add(path)
        elif (TOP / line).is_symlink():  # untracked entry: bare path
            found.add(line)
    return sorted(found)


def test_every_symlink_resolves():
    links = symlinks()
    assert links, "no symlinks found"
    dangling = [p for p in links if not (TOP / p).exists()]
    assert not dangling, f"dangling links: {dangling}"


def test_every_shared_agent_doc_is_linked():
    shared = TOP / "agent-team" / "docs" / "agents"
    missing = [p.name for p in shared.iterdir() if not p.name.startswith(".") and not (TOP / "docs" / "agents" / p.name).is_symlink()]
    assert not missing, f"missing links in docs/agents: {missing}"


def test_project_md_is_local_only():
    assert (TOP / "docs/agents/project.md").is_file()
    assert not (TOP / "docs/agents/project.md").is_symlink()
    assert not (TOP / "agent-team/docs/agents/project.md").exists()


@pytest.mark.parametrize(
    "rel",
    [".claude/skills", ".claude/agents", "scripts", ".claude/settings.json", ".agents/skills", "docs/superpowers/README.md"],
)
def test_root_links_point_into_agent_team(rel):
    target = (TOP / rel).resolve()
    assert target.is_relative_to((TOP / "agent-team").resolve()), target


def test_agents_skills_is_the_claude_skills_folder():
    assert (TOP / ".agents/skills").resolve() == (TOP / ".claude/skills").resolve()
