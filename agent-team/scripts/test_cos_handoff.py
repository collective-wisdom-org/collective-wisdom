import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("cos_handoff", Path(__file__).with_name("cos_handoff.py"))
cos_handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cos_handoff)

def run(argv):
    try:
        return cos_handoff.main(argv)
    except SystemExit as e:  # fail() exits 2
        return e.code


HEAD = "a1b2c3d4e5f6" + "0" * 28
SPEC_PATH = "docs/superpowers/specs/2026-11-03-x-design.md"
PR = {
    "url": "https://github.com/example/app/pull/14",
    "headRefOid": HEAD,
    "statusCheckRollup": [{"name": "t", "status": "COMPLETED", "conclusion": "SUCCESS"}],
    "comments": [
        {"body": f"## {k} review (pass {n})\n\nVerdict: PASS", "url": f"https://x/{k}", "createdAt": "2026-11-03T21:02:00Z"}
        for k, n in (("Code", 2), ("Security", 1))
    ],
}
MERGE = {
    "stage": "awaiting-merge", "branch": "feat/abc-1-x", "specPath": SPEC_PATH, "specSha": "1a2b3c4d",
    "pr": 14, "headSha": HEAD, "status": "awaiting-merge since 21:25:\nPR #14 head 1a2b3c4.",
}
SPEC_ONLY = {**MERGE, "stage": "awaiting-spec", "pr": None, "headSha": None}


@pytest.mark.parametrize(
    "ticket, pr, want, code",
    [
        (MERGE, PR, ["Ticket: ABC-1, stage awaiting-merge", "Branch: feat/abc-1-x", f"Spec: {SPEC_PATH} at 1a2b3c4",
                     "PR: #14 https://github.com/example/app/pull/14", f"Head: {HEAD} (same as the head in state)",
                     "checks: 1 pass, 0 fail, 0 pending, 0 skipped", "code review: pass 2 PASS https://x/Code (21:02)",
                     "security review: pass 1 PASS https://x/Security (21:02)",
                     'Last status: "awaiting-merge since 21:25: PR #14 head 1a2b3c4."'], 0),
        (SPEC_ONLY, None, ["PR: none yet"], 0),
        ({**MERGE, "headSha": "9" * 40}, PR, ["(moved from 9999999)"], 0),
        ({**MERGE, "headSha": None}, PR, ["(no head in state)"], 0),
        ({**MERGE, "branch": "feat/abc-11-x"}, PR, ["reject: branch feat/abc-11-x"], 1),
        ({**MERGE, "branch": "feat/abc-1-x\nreject: evil"}, PR, ["reject: branch feat/abc-1-x reject: evil"], 1),
        ({**MERGE, "specPath": "docs/../etc/passwd.md"}, PR, ["reject: specPath docs/../etc/passwd.md"], 1),
        ({**MERGE, "specSha": "main"}, PR, ["reject: specSha main"], 1),
        (MERGE, "not json", ["cos_handoff: cannot read PR #14"], 2),
    ],
)
def test_handoff_block(tmp_path, capsys, ticket, pr, want, code):
    (tmp_path / "state.json").write_text(json.dumps({"tickets": {"ABC-1": ticket}}))
    argv = ["ABC-1", "--file", str(tmp_path / "state.json")]
    if pr is not None:
        (tmp_path / "pr.json").write_text(pr if isinstance(pr, str) else json.dumps(pr))
        argv += ["--pr", str(tmp_path / "pr.json")]
    assert run(argv) == code
    out = capsys.readouterr().out.splitlines()
    for line in want:
        assert any(line in o for o in out), line
    if code:
        assert len(out) == 1
    if pr is None:
        assert not any(o.startswith(("Head:", "checks:", "code review:")) for o in out)


def test_missing_ticket_or_state_exits_2(tmp_path, capsys):
    (tmp_path / "state.json").write_text(json.dumps({"tickets": {}}))
    assert run(["ABC-1", "--file", str(tmp_path / "state.json")]) == 2
    assert run(["ABC-1", "--file", str(tmp_path / "none.json")]) == 2
    assert capsys.readouterr().out.count("cos_handoff:") == 2
