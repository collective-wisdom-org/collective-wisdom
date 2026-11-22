import pytest

import ci_review
import cos_brief

OID = "a" * 40
OLD = "c" * 40
URL = "https://x/c"
SURL = "https://x/s"


def review(heading, verdict, url):
    return {"body": f"## {heading} review (pass 1)\n\nVerdict: {verdict}\n", "url": url, "author": {"login": "me"}, "createdAt": "2026-11-20T10:00:00Z"}


CODE, SEC = review("Code", "PASS", URL), review("Security", "PASS", SURL)
MERGE = f"Head moved to {OID} by merging main; PR diff unchanged since {OLD}. Reviews from {OLD} stand."
DOCS = f"Head moved to {OID}; PR diff changed only in docs files since {OLD}: ['README.md']. Reviews from {OLD} stand."
LIVING = f"Head moved to {OID} by the docs check fix commit; PR diff changed only in living docs since {OLD}: ['AGENTS.md']. Reviews from {OLD} stand."


def note(body):
    return {"body": body, "url": "https://x/n", "author": {"login": "me"}}


def run(monkeypatch, capsys, comments, files, lines=True, mode="agents", rollup=None, ci=None):
    pr = {"url": "u", "title": "t", "headRefOid": OID, "headRefName": "x", "files": [{"path": f} for f in files],
          "statusCheckRollup": rollup or [], "comments": comments, "mergeable": "MERGEABLE"}
    monkeypatch.setattr(cos_brief, "gh_json", lambda *a: pr)
    monkeypatch.setattr(cos_brief, "own_login", lambda: "me")
    monkeypatch.setattr(cos_brief, "cost_line", lambda b: "cost: unknown")
    monkeypatch.setattr(cos_brief.project_config, "review_mode", lambda: mode)
    monkeypatch.setattr(cos_brief.project_config, "target_branch", lambda: "main")
    monkeypatch.setattr(ci_review, "read", lambda n, run: ("bot", ci or {"fixed": 0, "answered": 0, "unresolved": []}))
    cos_brief.cmd_pr(type("A", (), {"number": 7, "head": None, "lines": lines})())
    return capsys.readouterr().out.splitlines()


@pytest.mark.parametrize(
    "comments, want",
    [
        ([CODE, SEC], f"reviews: code review PASS {URL}, security PASS {SURL}"),
        ([CODE], f"reviews: code review PASS {URL}, security not posted"),
        ([], "reviews: code review not posted, security not posted"),
        ([CODE, SEC, note(MERGE)], f"reviews: code review PASS {URL}, security PASS {SURL} (head moved by a main merge only since ccccccc; PR diff unchanged)"),
        ([CODE, SEC, note(DOCS)], f"reviews: code review PASS {URL}, security PASS {SURL} (head moved by docs-file changes only since ccccccc)"),
        ([CODE, SEC, note(LIVING)],
         f"reviews: code review PASS {URL}, security PASS {SURL} (head moved by the docs check fix commit only since ccccccc; PR diff changed only in living docs)"),
        ([CODE, SEC, note(MERGE.replace(OID, "b" * 40))], f"reviews: code review PASS {URL}, security PASS {SURL}"),  # a note for another head
    ],
)
def test_reviews_line_has_both_verdicts_and_the_head_moved_suffix(monkeypatch, capsys, comments, want):
    assert want in run(monkeypatch, capsys, comments, ["a.md"])


@pytest.mark.parametrize(
    "rollup, ci, want",
    [
        ([{"status": "COMPLETED", "conclusion": "SUCCESS", "name": "t"}], {"fixed": 2, "answered": 1, "unresolved": []}, "reviews: CI green at aaaaaaa, CI review 2 fixed, 1 answered and resolved, 0 unresolved"),
        ([{"status": "COMPLETED", "conclusion": "FAILURE", "name": "t"}], {"fixed": 0, "answered": 0, "unresolved": ["t1", "t2"]}, "reviews: CI not green at aaaaaaa, CI review 0 fixed, 0 answered and resolved, 2 unresolved"),
    ],
)
def test_reviews_line_in_ci_mode_names_ci_and_the_ci_review_counts(monkeypatch, capsys, rollup, ci, want):
    out = run(monkeypatch, capsys, [], ["a.md"], mode="ci", rollup=rollup, ci=ci)
    assert want in out and not any(l.startswith(("code review:", "reviews: code")) for l in out)


@pytest.mark.parametrize("count, size", [(0, "small"), (1, "small"), (5, "small"), (6, "large"), (40, "large")])
def test_size_is_small_up_to_five_files(monkeypatch, capsys, count, size):
    assert f"size: {size}" in run(monkeypatch, capsys, [CODE, SEC], [f"d/{i}.md" for i in range(count)])


@pytest.mark.parametrize("mode", ["agents", "ci"])
def test_the_new_lines_come_last_and_only_with_the_flag(monkeypatch, capsys, mode):
    base = run(monkeypatch, capsys, [CODE, SEC, note(MERGE)], ["a.md"], lines=False, mode=mode)
    more = run(monkeypatch, capsys, [CODE, SEC, note(MERGE)], ["a.md"], lines=True, mode=mode)
    assert not any(l.startswith(("reviews:", "size:")) for l in base)
    assert more[:len(base)] == base and [l.split(":")[0] for l in more[len(base):]] == ["reviews", "size"]
