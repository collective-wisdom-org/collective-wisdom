import stat

import pytest

import store_secret as ss

STAND_IN = "stand-in-value-not-a-secret"
FAKE = f"""#!/bin/sh
echo "$@" >> "$HOME/security.args"
[ -f "$HOME/item" ] && echo {STAND_IN} && exit 0
exit 44
"""


@pytest.fixture
def keychain(tmp_path, monkeypatch):
    """HOME is a temp folder and `security` on PATH is a fake that logs its arguments; touch tmp_path/item to make it find the item."""
    (tmp_path / "bin").mkdir()
    fake = tmp_path / "bin" / "security"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/usr/bin:/bin")
    return tmp_path


def run(capsys, *argv):
    code = ss.main(list(argv))
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize("name", ["openai-api-key", "a", "A.b_c-9", "x" * 64])
def test_store_prints_the_line_with_no_value(capsys, keychain, name):
    assert run(capsys, "store", name) == (0, f"security add-generic-password -U -s collective-wisdom -a {name} -w\n", "")
    assert not ss.path().exists()


@pytest.mark.parametrize("name", ["a b", "a'b", 'a"b', "a$b", "a`b", "a;b", "a/b", "a\nb", "-a", "_a", ".a", "", "x" * 65])
def test_unsafe_names_print_no_line(capsys, keychain, name):
    for argv in (["store", name], ["record", name, "--note", "n"]):
        code, out, err = run(capsys, *argv)
        assert (code, out) == (2, "")
        assert "is not a safe secret name" in err
    assert not ss.path().exists() and not (keychain / "security.args").exists()


@pytest.mark.parametrize("note", ["a`b", "a|b", "a\nb", "a\x1bb", "x" * 121, "", "  "])
def test_unsafe_notes_write_nothing(capsys, keychain, note):
    (keychain / "item").touch()
    assert run(capsys, "record", "key", "--note", note)[0] == 2
    assert not ss.path().exists()


def test_record_and_list(capsys, keychain):
    assert run(capsys, "record", "one", "--note", "first")[:2] == (1, "")  # not in the keychain yet: no file
    assert not ss.path().exists()
    (keychain / "item").touch()
    assert run(capsys, "record", "one", "--note", "first") == (0, "recorded one\n", "")
    run(capsys, "record", "two", "--note", "second")
    run(capsys, "record", "one", "--note", "changed")
    assert run(capsys, "list") == (0, "one\tchanged\ntwo\tsecond\n", "")
    text = ss.path().read_text()
    assert STAND_IN not in text and text.count("`one`") == 1
    assert stat.S_IMODE(ss.path().stat().st_mode) == 0o600
    calls = (keychain / "security.args").read_text().splitlines()
    assert calls and all("-w" not in c.split() and "-s collective-wisdom -a" in c for c in calls)


def test_list_is_empty_without_a_registry(capsys, keychain):
    assert run(capsys, "list") == (0, "", "")


@pytest.mark.parametrize("row", ["| bare | note |", "| `bad name` | note |", "| `ok` |", "| `ok` | a | b |"])
def test_malformed_row_is_an_error(capsys, keychain, row):
    ss.path().parent.mkdir(parents=True)
    ss.path().write_text(ss.HEADER + row + "\n")
    code, out, err = run(capsys, "list")
    assert (code, out) == (2, "") and f"secrets.md:{ss.HEADER.count(chr(10)) + 1}:" in err


def test_missing_security_is_an_error(capsys, keychain, monkeypatch):
    monkeypatch.setenv("PATH", str(keychain / "empty"))
    assert run(capsys, "record", "key", "--note", "n")[0] == 2
