"""`cos_head_check.py --next`: the last line has its `next:` text (send-or-queue.md § Send or queue, head check); the relay has none."""

import json
import re
from pathlib import Path

import pytest

import cos_head_check

OLD, NEW = "a" * 40, "b" * 40
# live head, mergeable, rule, extra flags, last line, words in the next: text
CASES = [
    (OLD, "MERGEABLE", "off", [], "head-check: ok", ["Go on"]),
    (NEW, "MERGEABLE", "off", [], "head-check: moved aaaaaaa bbbbbbb", ["Approval withdrawn at <time>: the PR head moved.", "(caller `head-moved`)", "drop it if it was queued"]),
    (OLD, "CONFLICTING", "off", [], "head-check: conflict keep", ["Keep the approval", "`conflict-keep`"]),
    (OLD, "CONFLICTING", "off", ["--no-approval"], "head-check: conflict stand", ["reviews stand", "`conflict-stand`"]),
    (OLD, "CONFLICTING", "on", [], "head-check: conflict withdraw", ["Approval withdrawn at <time>: the PR conflicts with <target>.", "`conflict-withdraw`"]),
    ("junk", "MERGEABLE", "off", [], "head-check: cannot read the PR", ["Don't send", "Needs you"]),
]


def call(tmp_path, monkeypatch, capsys, live, mergeable, rule, flags):
    monkeypatch.setattr(cos_head_check.project_config, "review_after_conflict", lambda: rule)
    monkeypatch.setattr(cos_head_check.project_config, "target_branch", lambda: "main")
    state, prs = Path(tmp_path / "state.json"), Path(tmp_path / "prs.json")
    state.write_text(json.dumps({"tickets": {"ABC-1": {"stage": "awaiting-merge", "pr": 5, "headSha": OLD}}}))
    prs.write_text(json.dumps({"5": {"headRefOid": live, "mergeable": mergeable}}))
    code = cos_head_check.main(["ABC-1", "--file", str(state), "--prs", str(prs), *flags])
    return code, capsys.readouterr().out.splitlines()


@pytest.mark.parametrize("live, mergeable, rule, flags, last, has", CASES)
def test_the_last_line_has_its_next_and_the_relay_has_none(tmp_path, monkeypatch, capsys, live, mergeable, rule, flags, last, has):
    code, out = call(tmp_path, monkeypatch, capsys, live, mergeable, rule, [*flags, "--next"])
    nexts = [i for i, x in enumerate(out) if x.startswith("next: ")]
    assert nexts == [len(out) - 1] and out[-2] == last
    assert all(x in out[-1] for x in has)
    assert not re.search(r"\{[a-z]+\}", out[-1])
    # without the flag: the same lines, no next
    _, plain = call(tmp_path, monkeypatch, capsys, live, mergeable, rule, flags)
    assert plain == out[:-1] and code == (2 if "cannot" in last else 0)
