import re
from pathlib import Path

import pytest

ROOT = Path(__file__).absolute().parent.parent
TOP = ROOT.parent

pytestmark = pytest.mark.skipif(
    not (TOP / "install.sh").exists(), reason="collective-wisdom root only"
)

AGENTS = sorted((ROOT / ".claude" / "agents").glob("*.md"))


def parse(path):
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert m, f"{path.name}: no frontmatter"
    meta = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"')
    return meta, m.group(2)


@pytest.mark.parametrize("path", AGENTS, ids=lambda p: p.stem)
def test_agent_file_shape(path):
    meta, body = parse(path)
    for key in ("name", "description", "model", "tools"):
        assert meta.get(key), f"{path.name}: missing {key}"
    assert meta["name"] == path.stem
    docs = re.findall(r"docs/agents/[\w.-]+\.md", body)
    assert docs, f"{path.name}: body names no docs/agents path"
    for doc in docs:
        assert (ROOT / doc).is_file(), f"{path.name}: {doc} does not exist"


def test_project_md_is_local_and_never_shipped():
    local = TOP / "docs" / "agents" / "project.md"
    assert local.is_file() and not local.is_symlink()
    assert not (ROOT / "docs" / "agents" / "project.md").exists()
