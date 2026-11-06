"""Read repo-specific facts from docs/agents/project.md so the agent-team scripts hardcode none.

project.md holds markdown tables of `| Key | Value |` rows. A value is the first backticked token in
the Value cell. `none`, an empty cell and `TODO(...)` text have no backticked token, so they read as unset.
Set PROJECT_MD to read another file (tests do).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
from app_root import root  # noqa: E402

DEFAULT = root() / "docs" / "agents" / "project.md"
FALLBACK_BRANCH_HEAD = "feat/"


def _rows():
    path = Path(os.environ.get("PROJECT_MD") or DEFAULT)
    try:
        text = path.read_text()
    except OSError:
        return []
    return _parse(text)


def _parse(text):
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 2:
            rows.append((cells[0], cells[1]))
    return rows


def value(key_prefix, rows=None):
    """First backticked token in the Value cell of the row whose Key starts with key_prefix, or None."""
    for key, val in _rows() if rows is None else rows:
        if key.startswith(key_prefix):
            m = re.search(r"`([^`]+)`", val)
            return m.group(1) if m else None
    return None


def setting(key_prefix, rows=None):
    """Like value, but a Value cell without backticks reads as its bare text: `on` and "on" both give "on".

    None when the row is missing, the cell is empty or the cell starts with TODO(.
    """
    for key, val in _rows() if rows is None else rows:
        if key.startswith(key_prefix):
            m = re.search(r"`([^`]+)`", val)
            if m:
                return m.group(1)
            return None if not val or val.startswith("TODO(") else val
    return None


def no_ci():
    """True when the `Required CI checks` row declares no CI: the cell starts with `none`, in backticks or not."""
    cell = next((v for k, v in _rows() if k.startswith("Required CI checks")), "")
    return bool(re.match(r"`?none\b", cell, re.I))


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


def branch_head(rows=None):
    """Text before `<prefix>` in the branch pattern (e.g. `feat/`)."""
    pat = value("Branch pattern", rows) or ""
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


DEFAULT_TARGET = "main"


def _plain_branch(t):
    """t when it is a plain branch name; SystemExit for anything else."""
    bad = (
        not re.fullmatch(r"[A-Za-z0-9._/-]+", t)
        or t[0] in "-/."
        or t[-1] in "/."
        or t.endswith(".lock")
        or ".." in t
        or "//" in t
    )
    if bad:
        raise SystemExit(f"project.md: 'Merge target branch' row has no usable branch name, got `{t}`")
    return t


def target_branch():
    """The branch every PR merges into: the `Merge target branch` row, `main` when unset."""
    return _plain_branch(value("Merge target branch") or DEFAULT_TARGET)


def target_ref():
    """The merge target branch as a full remote-tracking ref name, so a tag named origin/<branch> cannot win."""
    return f"refs/remotes/origin/{target_branch()}"


TOLERANCES = ("strict", "balanced", "permissive")


def _git(cmd):
    """Run a git command in the app's checkout and return stdout; raise OSError on any failure."""
    try:
        p = subprocess.run(cmd, cwd=root(), capture_output=True, text=True, timeout=60)
    except subprocess.SubprocessError as e:
        raise OSError(type(e).__name__)
    if p.returncode:
        raise OSError((p.stderr or p.stdout).strip() or f"exit {p.returncode}")
    return p.stdout


def _root_rows(run):
    """Rows of project.md in the root checkout, the first entry of `git worktree list`. Raises OSError."""
    first = run(["git", "worktree", "list", "--porcelain"]).strip().split("\n\n")[0].splitlines()
    if not first or not first[0].startswith("worktree "):
        raise OSError("no root checkout in git worktree list")
    try:
        return _parse((Path(first[0].removeprefix("worktree ")) / "docs" / "agents" / "project.md").read_text())
    except ValueError as e:  # undecodable bytes
        raise OSError(type(e).__name__)


def approval_setting(run=_git):
    """(tolerance, note) from the `Approval risk tolerance` row of project.md as committed on origin/<target>.

    <target> is the `Merge target branch` row of the root checkout's project.md (the first entry of `git worktree list`,
    so a feature worktree's own edit of that row changes nothing), read as refs/remotes/origin/<target>. The level is
    never read from a working tree. Every failure to read (git, file, row) and every unknown value gives ("strict", why),
    and so does a target that starts with the branch pattern head (from the root checkout's project.md too; an agent can
    push such a branch) or a committed project.md that names another target. note is "" when the row set the level.
    """
    try:
        rows = _root_rows(run)
        target = _plain_branch(value("Merge target branch", rows) or DEFAULT_TARGET)
    except OSError as e:
        return "strict", f"could not read project.md in the root checkout: {e}"
    except SystemExit as e:
        return "strict", str(e)
    if target.startswith(branch_head(rows)):
        return "strict", f"merge target branch `{target}` is a ticket branch"
    try:
        run(["git", "fetch", "origin", target])
        text = run(["git", "show", f"refs/remotes/origin/{target}:docs/agents/project.md"])
        committed = _plain_branch(value("Merge target branch", _parse(text)) or DEFAULT_TARGET)
    except OSError as e:
        return "strict", f"could not read project.md on origin/{target}: {e}"
    except SystemExit as e:
        return "strict", str(e)
    if committed != target:
        return "strict", f"project.md on origin/{target} names merge target branch `{committed}`, not `{target}`"
    v = value("Approval risk tolerance", _parse(text))
    if v is None:
        return "strict", f"no Approval risk tolerance value on origin/{target}"
    if v.lower() not in TOLERANCES:
        return "strict", f"unknown Approval risk tolerance `{v}`"
    return v.lower(), ""


def approval_tolerance(run=_git):
    """`strict`, `balanced` or `permissive`; `strict` for anything missing, unknown or unreadable."""
    return approval_setting(run)[0]


if __name__ == "__main__":
    import sys

    try:
        if sys.argv[1:] == ["no-ci"]:
            print("yes" if no_ci() else "no")
        else:
            raise SystemExit("usage: project_config.py no-ci")
    except SystemExit as e:
        print(e, file=sys.stderr)
        sys.exit(2)
