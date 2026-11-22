import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("review_gate", Path(__file__).with_name("review_gate.py"))
review_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_gate)

HEAD, OLD = "a" * 40, "c" * 40
CODE, SEC = "https://github.com/o/r/pull/7#issuecomment-1", "https://github.com/o/r/pull/7#issuecomment-2"
DOCS_URL = "https://github.com/o/r/pull/7#issuecomment-9"
PASS = f"review-gate: pass head {HEAD} code {CODE} security {SEC}"


def comment(body, at, url="u", who="me"):
    return {"author": {"login": who}, "body": body, "createdAt": at, "url": url}


def review(title, url):
    return comment(f"{title}\n\nbody\n\n**Verdict:** PASS\n", "2026-11-02T10:00:00Z", url)


def pr(extra=(), requests=(), late=False):
    """Both reviews PASS, newer than the head commit unless late (then the head came after them)."""
    return {
        "headRefOid": HEAD,
        "comments": [review("## Code review (pass 2)", CODE), review("## Security review", SEC), *extra],
        "commits": [{"oid": OLD, "committedDate": "2026-11-02T08:00:00Z"}, {"oid": HEAD, "committedDate": "2026-11-02T10:30:00Z" if late else "2026-11-02T09:00:00Z"}],
        "reviewRequests": list(requests),
    }


def docs(url, at, who="me"):
    return comment("## Docs check\n\nDOCS CHECK: ok\nDocs checked: nothing stale at abc1234\nRejected: none", at, url, who)


ALICE = {"__typename": "User", "login": "alice"}
TEAM = {"__typename": "Team", "slug": "acme/core"}


def run_gate(tmp_path, monkeypatch, capsys, argv, facts, mode="agents", delta=None):
    md = tmp_path / "project.md"
    md.write_text(f"| Key | Value |\n|---|---|\n| Review mode | `{mode}` |\n")
    monkeypatch.setenv("PROJECT_MD", str(md))
    calls = []

    def run(cmd, input=None):
        calls.append(" ".join(cmd))
        return json.dumps(facts) if "pr view" in " ".join(cmd) else "me\n"

    code = review_gate.main(argv, run, delta or (lambda f, reviewed: ("same", [])))
    return code, capsys.readouterr().out.splitlines(), calls


@pytest.mark.parametrize(
    "facts, mode, want",
    [
        # pass: who GitHub waits on, and whether the docs check ran (the newest comment of the gh user counts)
        (pr(), "agents", ["reviews-needed: none", "docs-check: run", PASS]),
        (pr([docs("old", "2026-11-02T10:05:00Z"), docs(DOCS_URL, "2026-11-02T10:20:00Z")], [ALICE, TEAM]), "agents",
         ["reviews-needed: alice, @acme/core", f"docs-check: done {DOCS_URL}", PASS]),
        (pr([docs("theirs", "2026-11-02T10:05:00Z", who="someone")], [TEAM]), "agents", ["reviews-needed: @acme/core", "docs-check: run", PASS]),
        # nothing is added to any other last line
        (pr(late=True), "agents", ["Head moved to {h} by merging main; PR diff unchanged since {o}. Reviews from {o} stand.".format(h=HEAD, o=OLD), f"review-gate: note head {HEAD} reviewed {OLD}"]),
        (pr(extra=[comment("## Code review\n\nx\n\n**Verdict:** CHANGES NEEDED\n", "2026-11-02T10:10:00Z")]), "agents",
         ["review-gate: rerun code: latest Code review does not end in Verdict: PASS"]),
        (pr(), "ci", ["review-gate: ci"]),
    ],
)
def test_lines(tmp_path, monkeypatch, capsys, facts, mode, want):
    code, out, calls = run_gate(tmp_path, monkeypatch, capsys, ["7", "--lines"], facts, mode)
    assert code == 0 and out == want
    assert all("reviewRequests" in c for c in calls if "pr view" in c)


@pytest.mark.parametrize("facts", [pr(), pr([docs(DOCS_URL, "2026-11-02T10:20:00Z")], [ALICE]), pr(late=True)])
def test_without_the_flag_the_output_and_the_read_are_unchanged(tmp_path, monkeypatch, capsys, facts):
    code, plain, calls = run_gate(tmp_path, monkeypatch, capsys, ["7"], facts)
    _, with_lines, _ = run_gate(tmp_path, monkeypatch, capsys, ["7", "--lines"], facts)
    assert code == 0
    assert "reviewRequests" not in calls[0]
    assert [l for l in with_lines if not l.startswith(("reviews-needed: ", "docs-check: "))] == plain
