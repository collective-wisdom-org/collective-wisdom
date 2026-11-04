import re
from pathlib import Path

import pytest

ROOT = Path(__file__).absolute().parent.parent
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


def test_expected_agents():
    assert {p.stem for p in AGENTS} == {"code-reviewer", "documenter", "implementer", "security-reviewer"}


def test_models():
    models = {p.stem: parse(p)[0]["model"] for p in AGENTS}
    assert models["implementer"] == "sonnet"
    assert models["documenter"] == "sonnet"
    assert models["code-reviewer"] == "opus"
    assert models["security-reviewer"] == "opus"
