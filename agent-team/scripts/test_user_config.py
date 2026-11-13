import subprocess

import pytest

import user_config as uc


@pytest.fixture(autouse=True)
def app_user():  # these tests use the real repo_key
    pass


def repo(path, remote):
    path.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    if remote:
        subprocess.run(["git", "remote", "add", "origin", remote], cwd=path, check=True)
    return path


@pytest.mark.parametrize(
    "remote, key",
    [
        ("https://github.com/Foo/Bar", "github.com/foo/bar"),
        ("https://me@github.com/foo/bar.git/", "github.com/foo/bar"),
        ("git@github.com:foo/bar.git", "github.com/foo/bar"),
        ("ssh://git@ghe.example.com:2222/foo/bar.git", "ghe.example.com/foo/bar"),
        ("https://ghe.example.com:8443/foo/bar", "ghe.example.com/foo/bar"),
        ("http://github.com/foo/bar", None),
        ("https://github.com/foo", None),
        ("/srv/git/bar", None),
        (None, None),
    ],
)
def test_repo_key(tmp_path, remote, key):
    assert uc.repo_key(repo(tmp_path / "r", remote)) == key


def row(repo_cell, login_cell):
    return f"| {repo_cell} | {login_cell} |\n"


OWN = "`github.com/foo/bar`"
ERR = "err:"
LOGIN_ROWS = [
    (row(OWN, "`alice`"), "alice"),
    (row("`GitHub.com/FOO/bar`", "`Alice-1`"), "Alice-1"),
    (None, None),  # no file
    (row("`github.com/foo/other`", "`alice`"), None),
    (row("`github.com/foo/other`", "`-bad`"), None),  # a bad row for another repo is not an error
    (row(OWN, "`alice`") + row(OWN.upper(), "`bob`"), ERR + "lines 1 and 2 both map github.com/foo/bar"),
    ("\n" + row(OWN, "`-alice`"), ERR + ":2:"),
    (row(OWN, "`a--b`"), ERR + ":1:"),
    (row(OWN, "`" + "a" * 40 + "`"), ERR + ":1:"),
    (row(OWN, "`Jane-Doe_corp`"), "Jane-Doe_corp"),  # EMU login: one _suffix
    (row(OWN, "`_x`"), ERR + ":1:"),
    (row(OWN, "`a_`"), ERR + ":1:"),
    (row(OWN, "`a__b`"), ERR + ":1:"),
    (row(OWN, "`a_b_c`"), ERR + ":1:"),
    (row(OWN, "`a_-b`"), ERR + ":1:"),
    (row(OWN, "`a-_b`"), ERR + ":1:"),
    (row(OWN, "alice"), ERR + ":1:"),
]


@pytest.mark.parametrize("text, want", LOGIN_ROWS)
def test_login(tmp_path, monkeypatch, text, want):
    monkeypatch.setenv("HOME", str(tmp_path))
    if text is not None:
        uc.path().parent.mkdir(parents=True)
        uc.path().write_text(text)
    app = repo(tmp_path / "app", "https://github.com/Foo/Bar")
    if want and want.startswith(ERR):
        with pytest.raises(uc.UserConfigError, match=want[len(ERR):]):
            uc.login(app)
    else:
        assert uc.login(app) == want


USAGE_ROWS = [("`0.5`", 0.5), ("`none`", None), ("`nan`", None), ("`inf`", None), ("12000", None), (None, None)]


@pytest.mark.parametrize("cell, want", USAGE_ROWS)
def test_subscription_usage(user_md, cell, want):
    user_md("me", cell)
    assert uc.subscription_usage("Claude") == want
    assert uc.subscription_usage("Codex") is None
