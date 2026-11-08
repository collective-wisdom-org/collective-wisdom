import importlib.util
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


review_gate, merge_pr = load("review_gate"), load("merge_pr")


@pytest.mark.parametrize(
    "fix_path, outcome",
    [
        ("docs/superpowers/specs/x.md", "note"),
        ("docs/superpowers/specs/it's.md", "note"),
        ("agent-team/.claude/skills/x/SKILL.md", "rerun"),
        ("docs/agents/x.md", "rerun"),
        ("a.py", "rerun"),
    ],
)
def test_review_gate_and_merge_gate_agree_on_a_fix_after_the_reviews(tmp_path, monkeypatch, fix_path, outcome):
    monkeypatch.setenv("PROJECT_MD", str(tmp_path / "missing.md"))

    def git(*args):
        env = ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        return subprocess.run(["git", *env, *args], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()

    def commit(path, text):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text)
        git("add", "-A")
        git("commit", "-m", "c")
        return git("rev-parse", "HEAD")

    git("init", "-b", "main")
    commit("base.txt", "x\n")
    git("update-ref", "refs/remotes/origin/main", "main")
    git("checkout", "-b", "pr")
    h = commit("a.py", "1\n")
    f = commit(fix_path, "fix\n")

    def delta(facts, reviewed):
        return merge_pr.pr_diff_delta.delta(reviewed, facts["headRefOid"], lambda cmd: git(*cmd[1:]))

    def comment(body, at):
        return {"author": {"login": "me"}, "body": body, "createdAt": at, "url": "u"}

    facts = {
        "login": "me",
        "headRefOid": f,
        "commits": [{"oid": h, "committedDate": "2026-11-02T08:00:00Z"}, {"oid": f, "committedDate": "2026-11-02T10:00:00Z"}],
        "comments": [comment(f"{t}\n\n**Verdict:** PASS\n", "2026-11-02T09:00:00Z") for t in review_gate.TITLES.values()],
    }

    def both():
        problems = [merge_pr.review(facts, t, delta)[1] for t in review_gate.TITLES.values()]
        return review_gate.verdict(facts, delta), problems

    (last, note), problems = both()
    assert all(problems)  # without a note, the merge gate stops both reviews
    if outcome == "rerun":
        assert last.startswith("review-gate: rerun both:")
        return
    assert last == f"review-gate: note head {f} reviewed {h}"
    facts["comments"].append(comment(note, "2026-11-02T10:10:00Z"))
    (last, _), problems = both()
    assert last.startswith(f"review-gate: pass head {f}") and problems == [None, None]
