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


def lane_row(key, value):
    return f"| {key} | {value} |\n"


CAP, SPEC, BUILD = "Active children cap (spec and build together)", "Spec lane limit", "Build lane limit"
DEFAULTS = {"cap": 4, "spec": 2, "build": 2}
LANE_ROWS = [
    (None, DEFAULTS),  # no file
    ("", DEFAULTS),
    (lane_row(CAP, "`none`") + lane_row(SPEC, "`none`") + lane_row(BUILD, "`none`"), DEFAULTS),
    (lane_row(CAP, "`3`") + lane_row(SPEC, "`1`") + lane_row(BUILD, "`3`"), {"cap": 3, "spec": 1, "build": 3}),
    (lane_row(CAP, "`9`"), {"cap": 9, "spec": 2, "build": 2}),  # a cap above spec + build changes nothing downstream
    (lane_row(BUILD, "`3`"), {"cap": 5, "spec": 2, "build": 3}),  # lane rows only: the cap follows the sum
    (lane_row(CAP, "`999`"), {"cap": 999, "spec": 2, "build": 2}),
    *[(lane_row(CAP, v) + lane_row(SPEC, v) + lane_row(BUILD, v), DEFAULTS) for v in ("`0`", "`-1`", "`+3`", "`2.5`", "`03`", "`1000`", "`many`", "3")],
    (lane_row("Merge lane limit", "`3`"), DEFAULTS),  # merge is never read
]


@pytest.mark.parametrize("text, want", LANE_ROWS)
def test_lane_limits(tmp_path, monkeypatch, text, want):
    monkeypatch.setenv("HOME", str(tmp_path))
    uc.path().parent.mkdir(parents=True)
    if text is not None:
        uc.path().write_text(text)
    assert uc.lane_limits() == want


def test_lane_limits_with_an_unreadable_file_are_the_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    uc.path().parent.mkdir(parents=True)
    uc.path().write_bytes(b"\xff\xfe| Spec lane limit | `1` |\n")  # not UTF-8
    assert uc.lane_limits() == DEFAULTS
