import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("review_gate", Path(__file__).with_name("review_gate.py"))
review_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_gate)

HEAD, MID, OLD, SIDE = "a" * 40, "b" * 40, "c" * 40, "d" * 40
CODE, SEC = "https://github.com/o/r/pull/7#issuecomment-1", "https://github.com/o/r/pull/7#issuecomment-2"
NOTE = "Head moved to {h} by merging main; PR diff unchanged since {o}. Reviews from {o} stand."
RESOLVED = "Head moved to {h} by resolving conflicts with main; reviews from {o} stand."


def comment(body, at, url="u", who="me"):
    return {"author": {"login": who}, "body": body, "createdAt": at, "url": url}


def review(title, at="2026-11-02T10:00:00Z", verdict="PASS", url="u"):
    return comment(f"{title}\n\nbody\n\n**Verdict:** {verdict}\n", at, url)


def pr(**kw):
    """A PR whose head was committed after both reviews, on top of OLD."""
    p = {
        "headRefOid": HEAD,
        "comments": [review("## Code review (pass 2)", url=CODE), review("## Security review", url=SEC)],
        "commits": [{"oid": OLD, "committedDate": "2026-11-02T08:00:00Z"}, {"oid": HEAD, "committedDate": "2026-11-02T10:30:00Z"}],
    }
    p.update(kw)
    return p


def fresh(p):
    p["commits"][-1]["committedDate"] = "2026-11-02T09:00:00Z"
    return p


def noted(p):
    p["comments"].append(comment(NOTE.format(h=HEAD, o=OLD), "2026-11-02T10:40:00Z"))
    return p


PASS = f"review-gate: pass head {HEAD} code {CODE} security {SEC}"


@pytest.mark.parametrize(
    "mode, prs, delta, code, out",
    [
        ("agents", fresh(pr()), None, 0, [PASS]),
        ("agents", fresh(pr(comments=[review("## Code review", url=CODE)])), None, 0, ["review-gate: rerun security: no Security review comment by me"]),
        ("agents", fresh(pr(comments=[review("## Code review"), review("## Security review", verdict="CHANGES NEEDED")])), None, 0,
         ["review-gate: rerun security: latest Security review does not end in Verdict: PASS"]),
        ("agents", pr(comments=[]), None, 0, ["review-gate: rerun both: code: no Code review comment by me; security: no Security review comment by me"]),
        # Pushed after the reviews: the diff decides.
        ("agents", pr(), ("same", []), 0, [NOTE.format(h=HEAD, o=OLD), f"review-gate: note head {HEAD} reviewed {OLD}"]),
        ("agents", pr(), ("changed", ["a.py", "b.py"]), 0, ["review-gate: rerun both: diff changed since ccccccc: 'a.py', 'b.py'"]),
        ("agents", pr(), "boom", 0, ["review-gate: rerun both: cannot compare diff since ccccccc: boom"]),
        # The note is posted: the same script now passes, with the same rule the merge gate runs.
        ("agents", noted(pr()), ("same", []), 0, [PASS]),
        ("agents", noted(pr()), ("changed", ["a.py"]), 0, ["review-gate: rerun both: code: latest Code review is older than head commit aaaaaaa; diff changed since ccccccc: 'a.py'; security: latest Security review is older than head commit aaaaaaa; diff changed since ccccccc: 'a.py'"]),
        # Reviews on different heads cannot share one note.
        ("agents", pr(commits=[{"oid": OLD, "committedDate": "2026-11-02T08:00:00Z"}, {"oid": MID, "committedDate": "2026-11-02T09:00:00Z"},
                               {"oid": HEAD, "committedDate": "2026-11-02T10:30:00Z"}],
                      comments=[review("## Code review", at="2026-11-02T08:30:00Z"), review("## Security review", at="2026-11-02T10:00:00Z")]),
         ("same", []), 0, ["review-gate: rerun both: the reviews were posted on different heads"]),
        ("ci", pr(comments=[]), None, 0, ["review-gate: ci"]),
        ("agents", None, None, 2, ["review-gate: cannot read PR #7: CmdError gh failed"]),
        ("bogus", pr(), None, 2, ["review-gate: cannot read PR #7: SystemExit project.md: 'Review mode' row must be one of agents, ci, got `bogus`"]),
    ],
)
def test_review_gate(tmp_path, monkeypatch, capsys, mode, prs, delta, code, out):
    md = tmp_path / "project.md"
    md.write_text(f"| Key | Value |\n|---|---|\n| Review mode | `{mode}` |\n")
    monkeypatch.setenv("PROJECT_MD", str(md))

    def run(cmd, input=None):
        if prs is None:
            raise review_gate.merge_pr.CmdError("gh failed")
        return json.dumps(prs) if "pr view" in " ".join(cmd) else "me\n"

    def stub_delta(f, reviewed):
        assert reviewed == OLD
        if delta == "boom":
            raise review_gate.merge_pr.CmdError("boom")
        return delta

    assert review_gate.main(["7"], run, stub_delta) == code
    assert capsys.readouterr().out.splitlines() == out


def test_a_head_resolved_for_conflicts_passes_without_a_diff_compare(tmp_path, monkeypatch, capsys):
    """open-pr's off setting: the merge gate accepts this head, so the check must too."""
    monkeypatch.setenv("PROJECT_MD", str(tmp_path / "missing.md"))
    monkeypatch.setattr(review_gate.project_config, "review_after_conflict", lambda: "off")
    monkeypatch.setattr(review_gate.merge_pr.pr_diff_delta, "fetch", lambda *a: None)
    p = pr()
    p["comments"].append(comment(RESOLVED.format(h=HEAD, o=OLD), "2026-11-02T10:40:00Z"))

    def run(cmd, input=None):
        text = " ".join(cmd)
        if "pr view" in text:
            return json.dumps(p)
        if "--parents" in text:
            return f"{HEAD} {OLD} {SIDE}"
        return HEAD if "rev-list" in text else "me\n"

    def no_delta(f, reviewed):
        raise AssertionError("a resolved head is not compared by diff")

    assert review_gate.main(["7"], run, no_delta) == 0
    assert capsys.readouterr().out.splitlines() == [PASS]

