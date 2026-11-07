import os
import subprocess
from pathlib import Path

import pytest

GH_SH = Path(__file__).with_name("gh.sh")
# Logs every call (token variables and args) to $FAKE_LOG, answers `auth token --hostname H --user U` from $FAKE_KEYRING/H/U.
FAKE = """#!/usr/bin/env bash
line="GH_TOKEN=${GH_TOKEN-unset} GITHUB_TOKEN=${GITHUB_TOKEN-unset} GH_ENTERPRISE_TOKEN=${GH_ENTERPRISE_TOKEN-unset} ARGS=$*"
echo "$line" >> "${FAKE_LOG:-/dev/null}"
if [ "$1 $2 $3 $5" = "auth token --hostname --user" ]; then cat "$FAKE_KEYRING/$4/$6"; else echo "$line"; fi
"""


def call(args, gh="unset", ent="unset"):
    return f"GH_TOKEN={gh} GITHUB_TOKEN=unset GH_ENTERPRISE_TOKEN={ent} ARGS={args}"


def token(host, user):
    return call(f"auth token --hostname {host} --user {user}")


API = "api user"
REMOTES = {"a": "https://github.com/org/a", "b": "git@github.com:org/b.git", "c": "https://ghe.example.com/org/c",
           "d": "https://github.com/org/d", "e": "https://github.com/org/e", "free": "https://github.com/org/free", "bare": None}
USER_MD = """| `github.com/org/a` | `alice` |
| `github.com/org/b` | `bob` |
| `ghe.example.com/org/c` | `carol` |
| `github.com/org/d` | `dave` |
| `github.com/org/e` | `eve` |
| `github.com/org/e` | `eve` |
"""
KEYRING = {"github.com/alice": "tokA", "github.com/bob": "tokB", "ghe.example.com/carol": "tokC"}
# repo, via a link to gh.sh, exit code, calls gh sees, part of stderr
ROWS = [
    ("a", False, 0, [token("github.com", "alice"), call(API, "tokA")], ""),
    ("b", False, 0, [token("github.com", "bob"), call(API, "tokB")], ""),
    ("a", True, 0, [token("github.com", "alice"), call(API, "tokA")], ""),
    ("c", False, 0, [token("ghe.example.com", "carol"), call(API, ent="tokC")], ""),
    ("free", False, 0, [call(API)], ""),  # no row: as before
    ("bare", False, 0, [call(API)], ""),  # no origin
    ("d", False, 2, [token("github.com", "dave")], "no gh login dave on github.com; run gh auth login -h github.com"),
    ("e", False, 2, [], "user_config: "),  # two rows for one repo
]


@pytest.mark.parametrize("name, link, code, want, err", ROWS)
def test_gh_sh_account_per_repo(tmp_path, name, link, code, want, err):
    bin_dir, home, log = tmp_path / "bin", tmp_path / "home", tmp_path / "log"
    bin_dir.mkdir()
    (bin_dir / "gh").write_text(FAKE)
    (bin_dir / "gh").chmod(0o755)
    for k, v in KEYRING.items():
        (tmp_path / "keyring" / k).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "keyring" / k).write_text(v)
    (home / ".config" / "collective-wisdom").mkdir(parents=True)
    (home / ".config" / "collective-wisdom" / "user.md").write_text(USER_MD)
    app = tmp_path / name
    app.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=app, check=True)
    if REMOTES[name]:
        subprocess.run(["git", "remote", "add", "origin", REMOTES[name]], cwd=app, check=True)
    script = GH_SH
    if link:
        (tmp_path / "elsewhere").mkdir()
        script = tmp_path / "elsewhere" / "gh.sh"
        script.symlink_to(GH_SH)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "HOME": str(home), "FAKE_LOG": str(log),
           "FAKE_KEYRING": str(tmp_path / "keyring"), "GITHUB_TOKEN": "pat", "GH_TOKEN": "pat"}
    p = subprocess.run([str(script), *API.split()], cwd=app, env=env, capture_output=True, text=True)
    assert p.returncode == code
    assert (log.read_text().splitlines() if log.exists() else []) == want
    assert err in p.stderr
    assert "tok" not in p.stderr
