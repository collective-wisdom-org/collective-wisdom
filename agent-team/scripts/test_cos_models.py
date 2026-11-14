import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_models", Path(__file__).with_name("cos_models.py"))
cos_models = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_models)


def claude(model, effort, key="providerInstanceId"):
    return f'{{"{key}":"claudeAgent","model":"claude-{model}-5-5","options":{{"effort":"{effort}"}}}}'


def auto(optimize_for, key="providerInstanceId"):
    return f'{{"{key}":"cursor","model":"auto-smart","options":{{"optimize_for":"{optimize_for}"}}}}'


def pins(provider_dir, models):
    names = ["implementer", "documenter", "compacter", "code-reviewer", "security-reviewer"]
    return [f"pinned: model: {m} in {provider_dir}/agents/{n}.md" for m, n in zip(models, names)]


SHEET = [
    ("claudeAgent", "chief", ["modelSelection: " + claude("sonnet", "medium", "instanceId")]),
    ("claudeAgent", "ticket-helper", ["target: " + claude("sonnet", "high")]),
    ("claudeAgent", "pm", ["target: " + claude("sonnet", "medium")]),
    ("claudeAgent", "spec", ["target: " + claude("opus", "medium")]),
    ("claudeAgent", "build", ["target: " + claude("sonnet", "high"), "modelSelection: " + claude("sonnet", "high", "instanceId")]),
    ("cursor", "chief", ["modelSelection: " + auto("balanced", "instanceId")]),
    ("cursor", "ticket-helper", ["target: " + auto("intelligence")]),
    ("cursor", "pm", ["target: " + auto("balanced")]),
    ("cursor", "spec", ["target: " + auto("intelligence")]),
    ("cursor", "build", ["target: " + auto("balanced"), "modelSelection: " + auto("balanced", "instanceId")]),
]
SHEET += [("claudeAgent", r, [p]) for r, p in zip(["implementer", "documenter", "compacter", "code-review", "security-review"], pins(".claude", ["sonnet"] * 3 + ["opus"] * 2))]
SHEET += [("cursor", r, [p]) for r, p in zip(["implementer", "documenter", "compacter", "code-review", "security-review"], pins(".cursor", [f"auto-smart[optimize_for={o}]" for o in ["balanced"] * 3 + ["intelligence"] * 2]))]
SHEET += [("codex", "spec", ["cos_models: no spec routing for codex"]), ("nope", "implementer", ["cos_models: no implementer routing for nope"])]


@pytest.mark.parametrize("provider, role, lines", SHEET)
def test_routing_prints_the_table_values_and_an_unrouted_provider_exits_1(provider, role, lines, capsys):
    code = cos_models.main([provider, role])
    assert capsys.readouterr().out.splitlines() == lines
    assert code == (0 if provider in ("claudeAgent", "cursor") else 1)


def test_usage_errors_exit_2(capsys):
    assert [cos_models.main(a) for a in ([], ["cursor"], ["cursor", "boss"], ["a", "spec", "x"])] == [2, 2, 2, 2]
