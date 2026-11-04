import pytest

import cos_brief

OID = "a" * 40
OLD = "c" * 40
NOTE = f"Head moved to {OID} by merging main; PR diff unchanged since {OLD}. Reviews from {OLD} stand."


@pytest.mark.parametrize(
    "who, oid, counts",
    [
        ("sam", OID, True),
        ("me", OID, False),
        ("sam", "b" * 40, False),
    ],
)
def test_moved_line_counts_the_note_only_from_the_given_login(who, oid, counts):
    comments = [{"body": NOTE, "url": "https://x/n", "author": {"login": who}}]
    got = cos_brief.moved_line(oid, comments, "sam")
    assert (got is not None) == counts
    if counts:
        assert "since ccccccc" in got


@pytest.mark.parametrize("set_login, want, asked_gh", [("sam", "sam", False), (None, "owner", True)])
def test_role_author_falls_back_to_the_active_account_not_the_callers_role(monkeypatch, set_login, want, asked_gh):
    seen = []

    def fake_run(cmd, **kw):
        seen.append(kw["env"])
        return type("P", (), {"returncode": 0, "stdout": "owner\n", "stderr": ""})()

    monkeypatch.setenv("AGENT_GH_ROLE", "chief-of-staff")
    monkeypatch.setattr(cos_brief.project_config, "role_login", lambda role: set_login)
    monkeypatch.setattr(cos_brief.subprocess, "run", fake_run)
    assert cos_brief.role_author("builder") == want
    assert bool(seen) == asked_gh
    assert all("AGENT_GH_ROLE" not in env for env in seen)
