"""Read repo-specific facts from docs/agents/project.md so the agent-team scripts hardcode none.

project.md holds markdown tables of `| Key | Value |` rows. A value is the first backticked token in
the Value cell. `none`, an empty cell and `TODO(...)` text have no backticked token, so they read as unset.
Set PROJECT_MD to read another file (tests do).
"""

import os
import re
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "docs" / "agents" / "project.md"
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
