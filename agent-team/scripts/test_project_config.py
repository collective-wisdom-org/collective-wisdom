import project_config

TABLE = """| Key | Value |
|---|---|
| Issue identifier prefix (`<PREFIX>`) | `ABC` |
| Repo (`<owner>/<repo>`) | `me/thing` (<https://github.com/me/thing>) |
| Branch pattern | `work/<prefix>-N-short-title` |
| Migrations directory | none (TODO(david): set a path) |
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
