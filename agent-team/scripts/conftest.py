"""Point the scripts at a fixture project.md so the suite needs no consumer config."""

import os
import tempfile
from pathlib import Path

import pytest

FIXTURE = """| Key | Value |
|---|---|
| Issue identifier prefix (`<PREFIX>`) | `ABC` |
| Repo (`<owner>/<repo>`) | `example/app` |
| Branch pattern | `feat/<prefix>-N-short-title` |
| Migrations directory | none |
"""

_dir = tempfile.mkdtemp(prefix="agent-team-tests-")
_md = Path(_dir) / "project.md"
_md.write_text(FIXTURE)
os.environ["PROJECT_MD"] = str(_md)

APP = "github.com/example/app"


@pytest.fixture
def user_md(tmp_path_factory, monkeypatch):
    """Point HOME at a temp folder and return write(accounts, usage=None) for its user.md.

    accounts maps repo keys to logins, or is one login for the repo example/app; usage is the raw Value cell of the subscription row.
    """
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))

    def write(accounts, usage=None):
        accounts = {APP: accounts} if isinstance(accounts, str) else accounts
        rows = "".join(f"| `{k}` | `{v}` |\n" for k, v in accounts.items())
        row = f"| Claude subscription API-equivalent usage (dollars) | {usage} |\n" if usage else ""
        file = home / ".config" / "collective-wisdom" / "user.md"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(f"| Key | Value |\n|---|---|\n{row}\n| Repo | Login |\n|---|---|\n{rows}")

    return write


@pytest.fixture(autouse=True)
def app_user(user_md, monkeypatch):
    """Every test runs as the repo example/app, whose gh login is `me` (user_md(...) in a test replaces that)."""
    import user_config

    monkeypatch.setattr(user_config, "repo_key", lambda root: APP)
    user_md("me")
