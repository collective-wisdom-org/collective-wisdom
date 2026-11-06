import subprocess

import pytest

import project_config

TABLE = """| Key | Value |
|---|---|
| Issue identifier prefix (`<PREFIX>`) | `ABC` |
| Repo (`<owner>/<repo>`) | `me/thing` (<https://github.com/me/thing>) |
| Branch pattern | `work/<prefix>-N-short-title` |
| Migrations directory | none (TODO(owner): set a path) |
"""


def test_reads_values_and_treats_none_as_unset(tmp_path, monkeypatch):
    md = tmp_path / "project.md"
    md.write_text(TABLE)
    monkeypatch.setenv("PROJECT_MD", str(md))
    assert project_config.prefix() == "ABC"
    assert project_config.repo() == "me/thing"
    assert project_config.branch_head() == "work/"
    assert project_config.migrations_dir() is None
    assert project_config.ticket_re(anchored=True).match("ABC-12")
    assert not project_config.ticket_re(anchored=True).match("XYZ-12")


@pytest.mark.parametrize(
    "cell, expect",
    [("`on`", "on"), ("`on` (default)", "on"), ("on", "on"), ("  yes ", "yes"), ("", None), ("TODO(owner)", None)],
)
def test_setting_reads_a_cell_with_or_without_backticks(cell, expect):
    rows = project_config._parse(f"| Key | Value |\n|---|---|\n| Flag (on or off) | {cell} |\n")
    assert project_config.setting("Flag", rows) == expect
    assert project_config.setting("Missing", rows) is None


def _tracker(tmp_path, monkeypatch, row):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n" + row)
    monkeypatch.setenv("PROJECT_MD", str(md))
    return project_config.tracker()


def test_tracker_defaults_to_linear(tmp_path, monkeypatch):
    assert _tracker(tmp_path, monkeypatch, "| Repo | `me/thing` |\n") == "linear"
    assert _tracker(tmp_path, monkeypatch, "| Tracker (`linear`, `github` or `jira`) | |\n") == "linear"
    assert _tracker(tmp_path, monkeypatch, "| Tracker (`linear`, `github` or `jira`) | TODO(owner) |\n") == "linear"


def test_tracker_reads_value_lowercased(tmp_path, monkeypatch):
    row = "| Tracker (`linear`, `github` or `jira`) | `{}` |\n"
    assert _tracker(tmp_path, monkeypatch, row.format("github")) == "github"
    assert _tracker(tmp_path, monkeypatch, row.format("GitHub")) == "github"
    assert _tracker(tmp_path, monkeypatch, row.format("jira")) == "jira"


def test_tracker_ignores_scope_row(tmp_path, monkeypatch):
    scope = "| Tracker scope (<TEAM>) | `engineering` |\n"
    assert _tracker(tmp_path, monkeypatch, scope) == "linear"
    row = "| Tracker (`linear`, `github` or `jira`) | `github` |\n"
    assert _tracker(tmp_path, monkeypatch, scope + row) == "github"


def test_tracker_rejects_unknown_value(tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as e:
        _tracker(tmp_path, monkeypatch, "| Tracker (`linear`, `github` or `jira`) | `trello` |\n")
    assert "linear" in str(e.value)


def test_tracker_missing_file_is_linear(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_MD", str(tmp_path / "nope.md"))
    assert project_config.tracker() == "linear"


def test_approval_setting_ignores_a_local_branch_named_origin_main(tmp_path, monkeypatch):
    def git(*args, cwd=tmp_path / "work"):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True, capture_output=True)

    def commit(tolerance, msg):
        (tmp_path / "work" / "docs" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "work" / "docs" / "agents" / "project.md").write_text(f"| Approval risk tolerance | `{tolerance}` |\n")
        git("add", "-A")
        git("commit", "-m", msg)

    git("init", "--bare", "-b", "main", str(tmp_path / "origin.git"), cwd=tmp_path)
    git("init", "-b", "main", str(tmp_path / "work"), cwd=tmp_path)
    git("remote", "add", "origin", str(tmp_path / "origin.git"))
    commit("strict", "strict")
    git("push", "origin", "main")
    git("checkout", "-b", "origin/main")  # a local branch that shadows the remote-tracking ref
    commit("permissive", "permissive")
    monkeypatch.setattr(project_config, "root", lambda: tmp_path / "work")
    assert project_config.approval_setting() == ("strict", "")


def _set_project_md(tmp_path, monkeypatch, row):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n| Branch pattern | `feat/<prefix>-N-x` |\n" + row)
    monkeypatch.setenv("PROJECT_MD", str(md))


@pytest.mark.parametrize("row,want", [
    ("", "main"),
    ("| Merge target branch | none |\n", "main"),
    ("| Merge target branch | |\n", "main"),
    ("| Merge target branch | TODO(owner): pick one |\n", "main"),
    ("| Merge target branch | `dev` |\n", "dev"),
    ("| Merge target branch | `release/next` |\n", "release/next"),
    ("| Merge target branch | `-x` |\n", None),
    ("| Merge target branch | `a..b` |\n", None),
    ("| Merge target branch | `dev.lock` |\n", None),
    ("| Merge target branch | `a b` |\n", None),
    ("| Merge target branch | `feat//x` |\n", None),
    ("| Merge target branch | `dev/` |\n", None),
    ("| Merge target branch | `.dev` |\n", None),
])
def test_target_branch(tmp_path, monkeypatch, row, want):
    _set_project_md(tmp_path, monkeypatch, row)
    if want is None:
        with pytest.raises(SystemExit, match="Merge target branch"):
            project_config.target_branch()
    else:
        assert project_config.target_branch() == want


def _file(target, tolerance="permissive"):
    row = f"| Merge target branch | `{target}` |\n" if target else ""
    return f"{row}| Approval risk tolerance | `{tolerance}` |\n"


# target: what the root checkout's project.md names. tree: what the current worktree's project.md names (None: the same).
@pytest.mark.parametrize("target,committed,want,tree", [
    ("dev", _file("dev"), ("permissive", ""), None),
    ("main", _file(None, "balanced"), ("balanced", ""), None),
    ("feat/next", _file("feat/next"), "strict", None),
    ("dev", _file("main"), "strict", None),
    ("dev", _file(None), "strict", None),
    ("main", _file("dev"), "strict", None),
    ("dev", _file("-x"), "strict", None),
    ("-x", _file("-x"), "strict", None),
    # a worktree that names another target changes nothing: the root's row decides
    ("main", _file("x"), "strict", "x"),
    ("dev", _file("dev"), ("permissive", ""), "main"),
    ("feat/next", _file("dev"), "strict", "dev"),
])
def test_approval_setting_follows_the_target(tmp_path, monkeypatch, target, committed, want, tree):
    _set_project_md(tmp_path, monkeypatch, f"| Merge target branch | `{tree or target}` |\n")
    root = tmp_path / "root" / "docs" / "agents"
    root.mkdir(parents=True)
    (root / "project.md").write_text(f"| Branch pattern | `feat/<prefix>-N-x` |\n| Merge target branch | `{target}` |\n")
    calls = []

    def fake(cmd):
        calls.append(cmd)
        if cmd[1] == "worktree":
            return f"worktree {tmp_path / 'root'}\nHEAD x\n\nworktree {tmp_path}\nHEAD y\n"
        return committed

    got = project_config.approval_setting(fake)
    assert (got if isinstance(want, tuple) else got[0]) == want
    listing = ["git", "worktree", "list", "--porcelain"]
    if want != "strict":
        assert calls == [
            listing,
            ["git", "fetch", "origin", target],
            ["git", "show", f"refs/remotes/origin/{target}:docs/agents/project.md"],
        ]
    if target.startswith(("feat/", "-")):
        assert calls == [listing]


@pytest.mark.parametrize(
    "rows, mode, bot",
    [
        ("| Repo | `me/thing` |\n", "agents", None),
        ("| Review mode (`agents` or `ci`) | TODO(owner) |\n", "agents", None),
        ("| Review mode (`agents` or `ci`) | `agents`. `ci` uses the bot |\n", "agents", None),
        ("| Review mode (`agents` or `ci`) | `CI` |\n| CI review bot login (`ci` mode only) | `Some-Bot[bot]` |\n", "ci", "some-bot"),
        ("| Review mode | `ci` |\n| CI review bot login | none (or the login in backticks) |\n", "ci", None),
        ("| Review mode | `ci,agents` |\n", SystemExit, None),
    ],
)
def test_review_mode_and_bot(tmp_path, monkeypatch, rows, mode, bot):
    md = tmp_path / "project.md"
    md.write_text("| Key | Value |\n|---|---|\n" + rows)
    monkeypatch.setenv("PROJECT_MD", str(md))
    assert project_config.ci_bot() == bot
    if mode is SystemExit:
        with pytest.raises(SystemExit, match="Review mode"):
            project_config.review_mode()
    else:
        assert project_config.review_mode() == mode
