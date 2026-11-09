"""Every model the Cursor routing names has a price and none is a Claude model (CW-272)."""

import re
from pathlib import Path

import agent_usage

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"


def routed_models():
    """(where, model id) for each Cursor model: agent files, the § Models Cursor table, and cursor values in skills."""
    found = []
    for f in sorted((ROOT / ".cursor" / "agents").glob("*.md")):
        found += [(f.name, m) for m in re.findall(r"^model:\s*(\S+)", f.read_text(), re.M)]
    cos = (SKILLS / "chief-of-staff" / "SKILL.md").read_text()
    table = re.search(r"^### Cursor\n(.*?)(?=^#{1,3} |\Z)", cos, re.M | re.S).group(1)
    for row in (r for r in table.splitlines() if r.startswith("|")):
        found += [("chief-of-staff Cursor table", m) for m in re.findall(r"`([^`]+)`", row.split("|")[2])]
    for f in sorted(SKILLS.glob("**/*.md")):
        found += [(str(f.relative_to(ROOT)), m) for m in re.findall(r'[iI]nstanceId: "cursor", model: "([^"]+)"', f.read_text())]
    return found


def test_every_cursor_model_is_priced_and_none_is_claude():
    found = routed_models()
    assert {m for _, m in found} >= {"grok-4.7", "composer-2.5"}  # the collection found the routing, not nothing
    for where, model in found:
        assert agent_usage.family(model) in agent_usage.PRICES, f"{where}: no price for {model}"
        assert "claude" not in model, f"{where}: Claude model {model} on Cursor"
