import json
import re
import subprocess

import pytest

import setup_repo as sr
import user_config as uc

TEMPLATE = (sr.TEMPLATES / "project.md").read_text()
FILLED = """| Key | Value |
|---|---|
| Tracker (`linear`, `github` or `jira`) | `github` |
| Tracker scope (`<TEAM>`) | `a/b` |
| Issue identifier prefix (`<PREFIX>`) | `AB` |
| Repo (`<owner>/<repo>`) | `a/b` (<https://github.com/a/b>) |
| Test | `pytest` |
| Lint | TODO(me) |
"""
TEAM = "| Linear team name (Linear only) | `Acme` |\n"
GITHUB = dict(product="My App", tracker="github", prefix="MA", repo="Foo/my-app", test="pytest", approver="David Q", login="dq")
LINEAR = {**GITHUB, "tracker": "linear", "tracker_scope": "Acme"}

STATUS = [
    (FILLED, "set"),
    (FILLED.replace("`pytest`", "TODO(me)"), "placeholders: Test"),
    (FILLED.replace("`AB`", "`<PREFIX>`"), "placeholders: Issue identifier prefix"),
    (FILLED.replace("`a/b` (", "`<owner>/<repo>` ("), "placeholders: Repo"),
    (FILLED.replace("| Test | `pytest` |\n", ""), "placeholders: Test"),
    (FILLED.replace("`github`", "`linear`"), "placeholders: Linear team name"),
    (FILLED.replace("`github`", "`linear`") + TEAM, "set"),
    (FILLED.replace("| Tracker (`linear`, `github` or `jira`) | `github` |\n", "") + TEAM, "set"),
    (FILLED.replace("| Tracker (`linear`, `github` or `jira`) | `github` |\n| Tracker scope (`<TEAM>`) | `a/b` |\n", "") + TEAM, "set"),
    (FILLED.replace("| Tracker (`linear`, `github` or `jira`) | `github` |\n", ""), "placeholders: Linear team name"),
    (TEMPLATE, "placeholders: Tracker scope, Issue identifier prefix, Repo, Test, Linear team name"),
]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(sr, "_gh_logins", lambda host: [])


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    for k in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{k}_NAME", "t")
        monkeypatch.setenv(f"GIT_{k}_EMAIL", "t@t")
    root, wt = tmp_path / "root", tmp_path / "wt"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "commit", "-q", "--allow-empty", "-m", "i")
    git(root, "worktree", "add", "-q", "-b", "agent-team-setup", str(wt))
    return root, wt


def run(capsys, *argv):
    code = sr.main([str(a) for a in argv])
    out = capsys.readouterr()
    return code, out.out, out.err


def write(capsys, repo, answers, wt=None):
    return run(capsys, "write", "--root", repo[0], "--dir", wt or repo[1], "--answers", json.dumps(answers))


def md(wt):
    return (wt / "docs" / "agents" / "project.md").read_text()


@pytest.mark.parametrize("text, want", STATUS)
def test_status(tmp_path, capsys, text, want):
    (tmp_path / "docs" / "agents").mkdir(parents=True)
    (tmp_path / "docs" / "agents" / "project.md").write_text(text)
    code, out, _ = run(capsys, "status", "--root", tmp_path)
    assert (code, out.splitlines()[0]) == (0, want)
    assert {"prefix_guess", "test_guess", "has_workflows"} <= set(json.loads(out.splitlines()[1]))


def test_status_missing_and_unreadable(tmp_path, capsys):
    assert run(capsys, "status", "--root", tmp_path)[1].splitlines()[0] == "missing"
    (tmp_path / "docs" / "agents" / "project.md").mkdir(parents=True)
    code, _, err = run(capsys, "status", "--root", tmp_path)
    assert code == 2 and "cannot read" in err


def test_status_facts(tmp_path, capsys):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
    (tmp_path / "pyproject.toml").write_text("")
    facts = json.loads(run(capsys, "status", "--root", tmp_path)[1].splitlines()[1])
    assert (facts["has_workflows"], facts["test_guess"], facts["target"]) == (True, "pytest", "main")


GUESS = [
    ({"package.json": '{"scripts": {"test": "jest"}}'}, "npm test"),
    ({"package.json": '{"scripts": {"test": "jest"}}', "pnpm-lock.yaml": ""}, "pnpm test"),
    ({"package.json": '{"scripts": {"test": "jest"}}', "yarn.lock": ""}, "yarn test"),
    ({"package.json": '{"scripts": {"test": "jest"}}', "pyproject.toml": ""}, "npm test"),
    ({"package.json": '{"scripts": {}}', "go.mod": ""}, "go test ./..."),
    ({"package.json": "{not json", "pytest.ini": ""}, "pytest"),
    ({"package.json": "[]", "Cargo.toml": ""}, "cargo test"),
    ({"pyproject.toml": ""}, "pytest"),
    ({}, None),
]


@pytest.mark.parametrize("files, want", GUESS)
def test_guess_test(tmp_path, files, want):
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    assert sr.guess_test(tmp_path) == want


@pytest.mark.parametrize("name, want", [("collective-wisdom", "CW"), ("my_cool.app", "MCA"), ("a-b-c-d-e", "ABCD"), ("billing", "BIL"), ("x", None), ("-", None)])
def test_guess_prefix(name, want):
    assert sr.guess_prefix(name) == want


@pytest.mark.parametrize("answers, has, lacks", [
    (GITHUB, ["`Foo/my-app` (<https://github.com/Foo/my-app>)", "| Branch pattern | `feat/<prefix>-N-short-title` (`<prefix>` is", "TODO(dq)"], ["Linear team name", "Linear project"]),
    ({**GITHUB, "ci": "none", "rules": ["Never delete data/"]}, ["none (no CI yet)", "- Repo rules: Never delete data/."], ["TODO(dq) |\n| Agent"]),
    ({**GITHUB, "approver": "dq."}, ["| Approver | dq. Approves specs and merges only |"], ["dq.."]),
    (LINEAR, ["| Linear team name (Linear only) | `Acme` |", "none (the team is the scope)", "| Tracker scope (`<TEAM>`) | `Acme` |"], []),
    ({**GITHUB, "tracker": "jira", "tracker_scope": "KEY"}, ["| Tracker scope (`<TEAM>`) | `KEY` |"], ["Linear team name"]),
])
def test_write_fresh(repo, capsys, answers, has, lacks):
    code, out, _ = write(capsys, repo, answers)
    text = md(repo[1])
    assert code == 0 and out.count("\n") == 2
    assert run(capsys, "status", "--root", repo[1])[1].splitlines()[0] == "set"
    assert "Owner login" not in text and "Subscription" not in text
    assert all(h in text for h in has) and not any(x in text for x in lacks)
    assert "| Tracker scope (`<TEAM>`) |" in text and "(`<PREFIX>`)" in text
    assert (repo[1] / ".gitignore").read_text() == ".agent-team/\n"


def test_write_rerun_changes_only_given_rows(repo, capsys):
    write(capsys, repo, GITHUB)
    before = md(repo[1]).splitlines()
    code, out, _ = write(capsys, repo, {"test": "npm test", "prefix": "ZZ"})
    after = md(repo[1]).splitlines()
    changed = [(a, b) for a, b in zip(before, after) if a != b]
    assert code == 0 and len(before) == len(after) and len(changed) == 2
    assert {b.split(" | ")[0] for _, b in changed} == {"| Test", "| Issue identifier prefix (`<PREFIX>`)"}
    assert out.count("unchanged: ") == 1
    assert write(capsys, repo, {"test": "npm test"})[1].count("unchanged: ") == 2


def test_write_rerun_missing_row_is_an_error(repo, capsys):
    write(capsys, repo, GITHUB)
    path = repo[1] / "docs" / "agents" / "project.md"
    path.write_text(re.sub(r"\| Required CI checks.*\n", "", path.read_text()))
    code, _, err = write(capsys, repo, {"ci": "none"})
    assert code == 2 and "'Required CI checks'" in err


@pytest.mark.parametrize("had, want", [
    (None, ".agent-team/\n"),
    ("node_modules\n", "node_modules\n.agent-team/\n"),
    ("node_modules", "node_modules\n.agent-team/\n"),
    (".agent-team/\n", ".agent-team/\n"),
    ("a\n /.agent-team/ \nb\n", "a\n /.agent-team/ \nb\n"),
    ("/.agent-team\n", "/.agent-team\n"),
])
def test_write_gitignore(repo, capsys, had, want):
    if had is not None:
        (repo[1] / ".gitignore").write_text(had)
    write(capsys, repo, GITHUB)
    assert (repo[1] / ".gitignore").read_text() == want


def refusal(tmp_path, repo):
    root, wt = repo
    git(wt, "checkout", "-q", "--detach")
    other = tmp_path / "other"
    git(root, "worktree", "add", "-q", "-b", "feat/x", str(other))
    return {
        "root checkout": (root, {}, "is not a linked worktree"), "not a worktree": (tmp_path, {}, f"{tmp_path.resolve()} is not a linked worktree of the repo at {root}"),
        "detached": (wt, {}, "detached HEAD"), "branch is the target": (other, {"target": "feat/x"}, "merge target"),
    }


@pytest.mark.parametrize("case", ["root checkout", "not a worktree", "detached", "branch is the target"])
def test_write_refuses(repo, capsys, tmp_path, case):
    wt, extra, message = refusal(tmp_path, repo)[case]
    code, _, err = write(capsys, repo, {**GITHUB, **extra}, wt=wt)
    assert code == 1 and message in err
    assert not (wt / "docs").exists() and not (wt / ".gitignore").exists()


def test_write_refuses_symlink_out_of_worktree(repo, capsys, tmp_path):
    outside = tmp_path / "outside"
    (outside / "agents").mkdir(parents=True)
    (repo[1] / "docs").symlink_to(outside)
    code, _, err = write(capsys, repo, GITHUB)
    assert code == 1 and "outside" in err
    assert list((outside / "agents").iterdir()) == [] and not (repo[1] / ".gitignore").exists()


BAD = [
    {"prefix": "ab"}, {"prefix": "A-B"}, {"repo": "a b"}, {"repo": "solo"}, {"login": "-x"}, {"tracker": "trello"},
    {"target": "../x"}, {"test": "pytest `x`"}, {"test": "a | b"}, {"product": "a\nb"}, {"product": "x" * 301},
    {"rules": ["ok", "bad `x`"]}, {"rules": "no"}, {"nope": "x"},
    {"test": "make test ARGS=<all>"}, {"product": "a>b"}, {"tracker_scope": "T<1"}, {"linear_team": "<x>"},
]


@pytest.mark.parametrize("bad", BAD)
def test_write_rejects_bad_answers_and_writes_nothing(repo, capsys, bad):
    code, _, err = write(capsys, repo, {**GITHUB, **bad})
    assert code == 2 and err
    assert not (repo[1] / "docs").exists() and not (repo[1] / ".gitignore").exists()


def test_write_fresh_needs_every_answer(repo, capsys):
    code, _, err = write(capsys, repo, {k: v for k, v in GITHUB.items() if k != "test"})
    assert code == 2 and "test" in err and not (repo[1] / "docs").exists()


def rerun(capsys, repo, start, answers):
    """Write `start` fresh, then re-run `answers`; returns (code, err, project.md text, status line)."""
    write(capsys, repo, start)
    code, _, err = write(capsys, repo, answers)
    return code, err, md(repo[1]), run(capsys, "status", "--root", repo[1])[1].splitlines()[0]


@pytest.mark.parametrize("start, answers, code, has, lacks", [
    (GITHUB, {"tracker": "linear", "tracker_scope": "Acme"}, 0, ["| Tracker scope (`<TEAM>`) | `Acme` |", "| Linear team name (Linear only) | `Acme` |", "| Linear project (Linear only) | none (the team is the scope) |", "| Tracker (`linear`, `github` or `jira`) | `linear` |"], []),
    (GITHUB, {"tracker": "linear"}, 2, [], []),
    (LINEAR, {"tracker": "github"}, 0, ["| Tracker scope (`<TEAM>`) | `Foo/my-app` |"], ["Linear team name", "Linear project", "Acme"]),
    (GITHUB, {"tracker": "jira", "tracker_scope": "KEY", "login": "dq"}, 0, ["| Tracker scope (`<TEAM>`) | `KEY` |", "| Jira site | TODO(dq) |", "| Jira status: Canceled | TODO(dq) |"], []),
])
def test_write_rerun_tracker_change(repo, capsys, start, answers, code, has, lacks):
    got, err, text, status = rerun(capsys, repo, start, answers)
    assert got == code and (status == "set" or code == 2)
    assert all(h in text for h in has) and not any(x in text for x in lacks)
    assert not (code == 0 and "TODO(dq)" not in text and "jira" in answers.values())


def test_write_rerun_rules_replace_only_the_rules_bullet(repo, capsys):
    def bullets():
        text = md(repo[1])
        return [x for x in text.split("## Repo invariants")[1].split("## Areas")[0].splitlines() if x.startswith("- ")][3:]

    write(capsys, repo, GITHUB)
    assert bullets() == ["- none yet"]
    for rules, want in ((["A"], ["- Repo rules: A."]), (["B", "C"], ["- Repo rules: B. C."])):
        write(capsys, repo, {"rules": rules})
        assert bullets() == want
    path = repo[1] / "docs" / "agents" / "project.md"
    path.write_text(path.read_text().replace("- Repo rules: B. C.", "- Mine."))
    assert write(capsys, repo, {"rules": ["D"]})[0] == 0
    assert bullets() == ["- Mine.", "- Repo rules: D."]
    write(capsys, repo, {"rules": ["E"]})
    assert bullets() == ["- Mine.", "- Repo rules: E."]


def commit(repo, text):
    (repo[1] / "docs" / "agents").mkdir(parents=True, exist_ok=True)
    (repo[1] / "docs" / "agents" / "project.md").write_text(text)


def drop_rows(text, *keys):
    return "".join(line for line in text.splitlines(keepends=True) if not any(line.startswith(f"| {k}") for k in keys))


@pytest.mark.parametrize("answers, has, lacks", [
    (GITHUB, ["| Tracker scope (`<TEAM>`) | `Foo/my-app` |", "| Product name | My App |", "# Project config (My App)", "| Lint | TODO(dq) |", "- none yet"], ["Linear team name", "<product name"]),
    ({**LINEAR, "rules": ["No x"]}, ["| Linear team name (Linear only) | `Acme` |", "- Repo rules: No x."], ["<Name the local"]),
])
def test_write_on_the_committed_template_ends_set(repo, capsys, answers, has, lacks):
    commit(repo, TEMPLATE)
    assert run(capsys, "status", "--root", repo[1])[1].startswith("placeholders")
    assert write(capsys, repo, answers)[0] == 0
    text = md(repo[1])
    assert run(capsys, "status", "--root", repo[1])[1].splitlines()[0] == "set"
    assert all(h in text for h in has) and not any(x in text for x in lacks)


@pytest.mark.parametrize("drop, answers, has", [
    (("Tracker (",), {"test": "npm test"}, ["| Test | `npm test` |"]),
    (("Tracker (", "Test |"), {"test": "pytest"}, ["| Test | `pytest` |"]),
    (("Tracker (", "Linear project"), {"tracker": "github"}, ["| Tracker (`linear`, `github` or `jira`) | `github` |", "| Tracker scope (`<TEAM>`) | `Foo/my-app` |"]),
])
def test_write_when_the_tracker_row_is_missing_it_reads_as_linear(repo, capsys, drop, answers, has):
    write(capsys, repo, LINEAR)
    commit(repo, drop_rows(md(repo[1]), *drop))
    code, _, err = write(capsys, repo, answers)
    assert code == 0, err
    assert run(capsys, "status", "--root", repo[1])[1].splitlines()[0] == "set"
    assert all(h in md(repo[1]) for h in has)


OLD = {**LINEAR, "product": "Old App", "approver": "al", "prefix": "AB", "target": "develop", "repo": "Old/app", "tracker_scope": "Acme"}
BARE = dict(GITHUB, product="my-app", approver="dq", target="main", host="github.com", rules=["x"])


@pytest.mark.parametrize("drop, edit", [
    ((), lambda t: t),
    (("Publish release notes",), lambda t: t),
    (("Tracker scope",), lambda t: t.replace("| Linear team name (Linear only) | `Acme` |", "| Linear team name (Linear only) | Acme (key `AB`, <https://linear.app/w/team/AB/overview>) |")),
])
def test_repair_of_a_one_gap_file_changes_only_the_gap(repo, capsys, drop, edit):
    write(capsys, repo, OLD)
    old = edit(drop_rows(md(repo[1]), *drop)).replace("| Test | `pytest` |", "| Test | TODO(alice) |")
    commit(repo, old)
    assert run(capsys, "status", "--root", repo[1])[1].splitlines()[0] == "placeholders: Test"
    assert write(capsys, repo, BARE)[0] == 0
    new = md(repo[1])
    assert run(capsys, "status", "--root", repo[1])[1].splitlines()[0] == "set"
    want = old.replace("| Test | TODO(alice) |", "| Test | `pytest` |")
    if "Tracker scope" in drop:
        want = want.replace("| Linear team name", "| Tracker scope (`<TEAM>`) | `Acme` |\n| Linear team name", 1)
    assert new == want


def run_user(capsys, *args, key="github.com/Example/App"):
    return run(capsys, "user", "--repo-key", key, *args)


def rows(text):
    return re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|$", text, re.M)


def test_user_creates_file_from_template(capsys):
    uc.path().unlink()
    assert run_user(capsys, "--login", "dq", "--subscription", "20")[0] == 0
    text = uc.path().read_text()
    assert rows(text) == [("github.com/example/app", "dq")]
    assert uc.subscription_usage("Claude") == 20 and "example-login" not in text and "## Settings" in text
    assert uc.path().stat().st_mode & 0o777 == 0o600


def test_user_keeps_template_subscription_none_without_flag(capsys):
    uc.path().unlink()
    run_user(capsys, "--login", "dq")
    assert uc.subscription_usage("Claude") is None and "`none`" in uc.path().read_text()


def test_user_adds_and_replaces_rows_and_keeps_the_rest(capsys):
    uc.path().unlink()
    run_user(capsys, "--login", "bob", "--subscription", "15", key="github.com/other/repo")
    before = uc.path().read_text()
    run_user(capsys, "--login", "dq", "--subscription", "99")
    added = uc.path().read_text()
    assert rows(added) == [("github.com/other/repo", "bob"), ("github.com/example/app", "dq")]
    run_user(capsys, "--login", "alice", key="GitHub.com/Example/App")
    assert uc.path().read_text() == added.replace("`dq`", "`alice`")
    assert added.replace("| `github.com/example/app` | `dq` |\n", "") == before and uc.subscription_usage("Claude") == 15


def test_user_replaces_the_row_of_a_file_without_headings(capsys):
    assert run_user(capsys, "--login", "dq")[0] == 0
    assert rows(uc.path().read_text()) == [("github.com/example/app", "dq")]


def test_user_writes_through_a_link(user_md, capsys, tmp_path):
    user_md("me")
    real = tmp_path / "real.md"
    real.write_text(uc.path().read_text())
    uc.path().unlink()
    uc.path().symlink_to(real)
    run_user(capsys, "--login", "dq")
    assert uc.path().is_symlink() and ("github.com/example/app", "dq") in rows(real.read_text())


@pytest.mark.parametrize("args", [["--login=-x"], ["--login", "a b"], *[["--login", "dq", "--subscription", s] for s in ("0", "-5", "nan", "inf", "abc", "1_0")]])
def test_user_rejects_bad_input(capsys, args):
    before = uc.path().read_text()
    assert run_user(capsys, *args)[0] == 2
    assert uc.path().read_text() == before


def test_user_needs_a_repo_key(capsys, monkeypatch):
    monkeypatch.setattr(uc, "repo_key", lambda root: None)
    assert run(capsys, "user", "--login", "dq")[0] == 2
