#!/usr/bin/env python3
"""Which model does a Chief of Staff role run on? Prints the values to pass, from the table for the provider.

Usage:
    ~/.collective-wisdom/scripts/cos_models.py <provider> <role>

Providers: claudeAgent, cursor. Any other provider (Codex, Antigravity, unknown) has no routing.
Roles: chief, ticket-helper, pm, spec, build (build and merge stages), implementer, documenter, compacter,
code-review, security-review.

Output, one line each, compact JSON with the literal values to pass as printed:
    target: {...}          for delegate_task (a role a thread starts as a child or helper)
    modelSelection: {...}  for t3_thread_configure and t3_thread_launch (a switch or a launch)
    pinned: model: <value> in <agent file>   for a subagent; the agent file sets its model, nothing is passed

chief prints modelSelection only (a rotation successor launch). ticket-helper, pm and spec print target only.
build prints both: target at a continuation start, modelSelection for the switch before the spec-approval relay.

Exit 0 when the role is routed. Exit 1 and "cos_models: no <role> routing for <provider>" when it is not.
Exit 2 and a usage line on a wrong number of arguments or an unknown role.

Why, per role (models.md has the full text):
    chief: bookkeeping; the approval gates do not rest on which model relays.
    ticket-helper: runs write-ticket; a wrong Today section costs an Opus spec run.
    pm: reads the tracker and ranks or tidies it; the same tier as the Chief of Staff thread.
    spec: the user approves the spec, so it needs the strongest model.
    build: works from an approved spec; merge stays on this model, so no second switch.
    implementer, documenter, compacter: routine edits and checks on the cheaper tier.
    code-review, security-review: a missed bug costs more than the review.
Cursor routes only to Auto (auto-smart): intelligence where Claude Code uses Opus, balanced elsewhere.
"""

import json
import sys

ROLES = ("chief", "ticket-helper", "pm", "spec", "build", "implementer", "documenter", "compacter", "code-review", "security-review")
AGENT_FILES = {
    "implementer": "implementer.md",
    "documenter": "documenter.md",
    "compacter": "compacter.md",
    "code-review": "code-reviewer.md",
    "security-review": "security-reviewer.md",
}


def _routes(provider, rows):
    """The five thread roles. rows maps chief, helper, pm, spec and build to a model and options."""
    target = {r: {"providerInstanceId": provider, **rows[r]} for r in rows}
    return {
        "chief": {"modelSelection": {"instanceId": provider, **rows["chief"]}},
        "ticket-helper": {"target": target["helper"]},
        "pm": {"target": target["pm"]},
        "spec": {"target": target["spec"]},
        "build": {"target": target["build"], "modelSelection": {"instanceId": provider, **rows["build"]}},
    }


def _pins(folder, models):
    return {r: {"pinned": f"model: {m} in {folder}/agents/{AGENT_FILES[r]}"} for r, m in models.items()}


def _claude(model, effort):
    return {"model": f"claude-{model}-5-5", "options": {"effort": effort}}


def _auto(optimize_for):
    return {"model": "auto-smart", "options": {"optimize_for": optimize_for}}


# MODELS[provider][role] holds the lines to print: "target" and "modelSelection" (dicts) or "pinned" (a string).
MODELS = {
    "claudeAgent": {
        **_routes(
            "claudeAgent",
            {"chief": _claude("sonnet", "medium"), "helper": _claude("sonnet", "high"), "pm": _claude("sonnet", "medium"),
             "spec": _claude("opus", "medium"), "build": _claude("sonnet", "high")},
        ),
        **_pins(".claude", {"implementer": "sonnet", "documenter": "sonnet", "compacter": "sonnet", "code-review": "opus", "security-review": "opus"}),
    },
    "cursor": {
        **_routes(
            "cursor",
            {"chief": _auto("balanced"), "helper": _auto("intelligence"), "pm": _auto("balanced"),
             "spec": _auto("intelligence"), "build": _auto("balanced")},
        ),
        **_pins(
            ".cursor",
            {r: f"auto-smart[optimize_for={'intelligence' if 'review' in r else 'balanced'}]" for r in AGENT_FILES},
        ),
    },
}


def main(argv):
    if argv in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    if len(argv) != 2 or argv[1] not in ROLES:
        print(f"usage: cos_models.py <provider> <{'|'.join(ROLES)}>", file=sys.stderr)
        return 2
    provider, role = argv
    row = MODELS.get(provider, {}).get(role)
    if row is None:
        print(f"cos_models: no {role} routing for {provider}")
        return 1
    for key, value in row.items():
        print(f"{key}: {value if isinstance(value, str) else json.dumps(value, separators=(',', ':'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
