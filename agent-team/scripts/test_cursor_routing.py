"""Every model the Cursor routing names is priced, except Auto, and none is a Claude model (CW-272, CW-275)."""

import re
from pathlib import Path

import agent_usage
import cos_models

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
# Auto bills at the list price of the model each request is routed to, so it has no price row by design.
UNPRICED = "auto-smart"


def routed_models():
    """(where, model id) for each Cursor model: agent files, the cos_models.py Cursor routes, and cursor values in skills.

    A bracket suffix on an id (`auto-smart[optimize_for=balanced]`) is dropped.
    """
    found = []
    for f in sorted((ROOT / ".cursor" / "agents").glob("*.md")):
        found += [(f.name, m.split("[")[0]) for m in re.findall(r"^model:\s*(\S+)", f.read_text(), re.M)]
    for role, row in cos_models.MODELS["cursor"].items():
        found += [(f"cos_models.py cursor {role}", v["model"]) for k, v in row.items() if k != "pinned"]
        found += [(f"cos_models.py cursor {role}", m.split("[")[0]) for m in re.findall(r"model: (\S+)", row.get("pinned", ""))]
    for f in sorted(SKILLS.glob("**/*.md")):
        found += [(str(f.relative_to(ROOT)), m) for m in re.findall(r'[iI]nstanceId: "cursor", model: "([^"]+)"', f.read_text())]
    return found


def test_every_cursor_model_is_priced_except_auto_and_none_is_claude():
    found = routed_models()
    assert {m for _, m in found} >= {"auto-smart"}  # the collection found the routing, not nothing
    assert agent_usage.family(UNPRICED) is None  # the day Auto gets a price, drop the exception
    for where, model in found:
        if model != UNPRICED:
            assert agent_usage.family(model) in agent_usage.PRICES, f"{where}: no price for {model}"
        assert "claude" not in model, f"{where}: Claude model {model} on Cursor"
