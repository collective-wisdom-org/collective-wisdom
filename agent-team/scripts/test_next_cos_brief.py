"""`cos_brief.py --next`: the step after the spec and pr output (approvals.md § Approval requests); without the flag nothing is added."""

import base64

import pytest

import cos_brief

OID = "a" * 40
SPEC = "# Title\n\n## Goals\n\n- one\n"


def spec_args(nxt, sha="b" * 40):
    return type("A", (), {"path": "docs/superpowers/specs/x.md", "sha": sha, "branch": None, "nxt": nxt})()


def pr_args(nxt):
    return type("A", (), {"number": 7, "head": None, "lines": True, "nxt": nxt})()


def fake_pr(monkeypatch, mergeable):
    pr = {"url": "u", "title": "t", "headRefOid": OID, "headRefName": "x", "files": [{"path": "a.md"}], "statusCheckRollup": [],
          "comments": [], "mergeable": mergeable}
    monkeypatch.setattr(cos_brief, "gh_json", lambda *a: pr)
    monkeypatch.setattr(cos_brief, "own_login", lambda: "me")
    monkeypatch.setattr(cos_brief, "cost_line", lambda b: "cost: unknown")
    monkeypatch.setattr(cos_brief.project_config, "review_mode", lambda: "agents")
    monkeypatch.setattr(cos_brief.project_config, "target_branch", lambda: "main")


@pytest.mark.parametrize("mergeable, key, has", [
    ("MERGEABLE", "block", ["`reviews:` as printed", "`size:`", "`migrations:` clash"]),
    ("CONFLICTING", "conflict", ["ask no approval", "cos_head_check.py <PREFIX>-N --no-approval", "`conflict-withdraw`"]),
])
def test_pr_ends_with_one_next_line(monkeypatch, capsys, mergeable, key, has):
    fake_pr(monkeypatch, mergeable)
    cos_brief.cmd_pr(pr_args(False))
    plain = capsys.readouterr().out.splitlines()
    cos_brief.cmd_pr(pr_args(True))
    out = capsys.readouterr().out.splitlines()
    assert out[:-1] == plain and out[-1] == f"next: {cos_brief.NEXT_PR[key]}"
    assert all(x in out[-1] for x in has)


def test_spec_has_its_next_and_not_found_has_the_send_back(monkeypatch, capsys):
    data = {"encoding": "base64", "content": base64.b64encode(SPEC.encode()).decode()}
    monkeypatch.setattr(cos_brief, "gh_json", lambda *a: data)
    cos_brief.cmd_spec(spec_args(False))
    plain = capsys.readouterr().out.splitlines()
    cos_brief.cmd_spec(spec_args(True))
    out = capsys.readouterr().out.splitlines()
    assert out[:-1] == plain and out[-1].startswith("next: Build the spec block") and "The spec wins over the report" in out[-1]
    for nxt in (False, True):
        with pytest.raises(SystemExit) as e:
            cos_brief.cmd_spec(spec_args(nxt, sha="zz"))
        assert e.value.code == 2
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "cos_brief: spec not found at zz"
        assert (len(lines) == 2 and "CHIEF OF STAFF: the spec at <sha> is not on GitHub" in lines[1]) == nxt and (len(lines) == 1) == (not nxt)
