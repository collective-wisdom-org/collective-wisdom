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


def test_tracker_rejects_unknown_value(tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as e:
        _tracker(tmp_path, monkeypatch, "| Tracker (`linear`, `github` or `jira`) | `trello` |\n")
    assert "linear" in str(e.value)


def test_tracker_missing_file_is_linear(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_MD", str(tmp_path / "nope.md"))
    assert project_config.tracker() == "linear"
