"""Read repo-specific facts from docs/agents/project.md so the agent-team scripts hardcode none.

project.md holds markdown tables of `| Key | Value |` rows. A value is the first backticked token in
the Value cell. `none`, an empty cell and `TODO(...)` text have no backticked token, so they read as unset.
Set PROJECT_MD to read another file (tests do).
"""

import os
import re
from pathlib import Path

DEFAULT = Path(__file__).absolute().parent.parent / "docs" / "agents" / "project.md"
FALLBACK_BRANCH_HEAD = "feat/"


def _rows():
    path = Path(os.environ.get("PROJECT_MD") or DEFAULT)
    try:
        text = path.read_text()
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 2:
            rows.append((cells[0], cells[1]))
    return rows


def value(key_prefix):
    """First backticked token in the Value cell of the row whose Key starts with key_prefix, or None."""
    for key, val in _rows():
        if key.startswith(key_prefix):
            m = re.search(r"`([^`]+)`", val)
            return m.group(1) if m else None
    return None


def prefix():
    """Issue identifier prefix, e.g. GORP. Raises if project.md doesn't give one."""
    p = value("Issue identifier prefix")
    if not p or not re.fullmatch(r"[A-Z][A-Z0-9]*", p):
        raise SystemExit("project.md: 'Issue identifier prefix' row has no usable `PREFIX` value")
    return p


def ticket_re(anchored=False):
    body = re.escape(prefix()) + r"-\d+"
    return re.compile(f"^{body}$" if anchored else body)


def repo():
    """`<owner>/<repo>` from project.md, or None."""
    r = value("Repo")
    return r if r and re.fullmatch(r"[\w.-]+/[\w.-]+", r) else None


def branch_head():
    """Text before `<prefix>` in the branch pattern (e.g. `feat/`)."""
    pat = value("Branch pattern") or ""
    head = pat.split("<prefix>")[0] if "<prefix>" in pat else ""
    return head or FALLBACK_BRANCH_HEAD


def migrations_dir():
    """Migrations directory without a trailing slash, or None when the repo has none."""
    d = value("Migrations directory")
    return d.strip("/") if d else None


TRACKERS = ("linear", "github", "jira")


def tracker():
    """Ticket tracker named in the `Tracker` row: linear, github or jira. Unset reads as linear."""
    t = "linear"
    for key, val in _rows():
        if key == "Tracker" or key.startswith("Tracker ("):  # not the `Tracker scope` row
            m = re.search(r"`([^`]+)`", val)
            t = m.group(1).lower() if m else "linear"
            break
    if t not in TRACKERS:
        raise SystemExit(f"project.md: 'Tracker' row must be one of {', '.join(TRACKERS)}, got `{t}`")
    return t


ROLE_ROWS = {
    "chief-of-staff": "Chief of Staff login",
    "builder": "Builder login",
    "code-reviewer": "Code reviewer login",
    "security-reviewer": "Security reviewer login",
}
LOGIN_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?")


def role_login(role):
    """GitHub login for an agent role, or None when its row is missing, empty, `none` or TODO.

    None means the role keeps using the account running gh. Raises SystemExit for an unknown role or a
    value that is not a GitHub login.
    """
    if role not in ROLE_ROWS:
        raise SystemExit(f"unknown role {role!r}; expected one of {', '.join(ROLE_ROWS)}")
    login = value(ROLE_ROWS[role])
    if login is None:
        cell = next((v for k, v in _rows() if k.startswith(ROLE_ROWS[role])), "")
        if cell and not re.match(r"(?i)none(\s|\(|$)|TODO\(", cell):  # text, but no `login`: don't fall back to the owner
            raise SystemExit(f"project.md: '{ROLE_ROWS[role]}' row has no backticked `login`")
        return None
    if login.lower() == "none":
        return None
    if not LOGIN_RE.fullmatch(login):
        raise SystemExit(f"project.md: '{ROLE_ROWS[role]}' row has no usable `login` value")
    return login


if __name__ == "__main__":
    import sys

    try:
        if len(sys.argv) != 3 or sys.argv[1] != "login":
            raise SystemExit("usage: project_config.py login <role>")
        found = role_login(sys.argv[2])
    except SystemExit as e:
        print(e, file=sys.stderr)
        sys.exit(2)
    if found:
        print(found)
