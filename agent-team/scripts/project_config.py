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


def release_notes_enabled():
    """False only when the `Publish release notes` row says `off` (any case). A missing row or any other value is True."""
    return (value("Publish release notes") or "").lower() != "off"


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


def branch_heads(rows=None):
    """Heads before `<prefix>` in the branch pattern, in row order: `{feat,infra}/<prefix>-N` gives ("feat/", "infra/").

    A plain head (`work/<prefix>-N`) gives that one head. No row, no `<prefix>` or a brace list that does not parse gives ("feat/",).
    """
    pat = value("Branch pattern", rows) or ""
    head = pat.split("<prefix>")[0] if "<prefix>" in pat else ""
    m = re.fullmatch(r"\{([a-z0-9-]+(?:,[a-z0-9-]+)*)\}/", head)
    if m:
        return tuple(f"{name}/" for name in m.group(1).split(","))
    return (head,) if head and not re.search(r"[{},]", head) else (FALLBACK_BRANCH_HEAD,)


def branch_head(rows=None):
    """The first head of the branch pattern, the one a new branch uses (e.g. `feat/`)."""
    return branch_heads(rows)[0]


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


REVIEW_MODES = ("agents", "ci")


def review_mode():
    """`agents` or `ci` from the `Review mode` row. A missing or unset row reads as agents.

    Any other value raises SystemExit, so a typo cannot quietly drop a review gate. Callers treat that as a failed read.
    """
    v = value("Review mode")
    if v is None:
        return "agents"
    if v.lower() not in REVIEW_MODES:
        raise SystemExit(f"project.md: 'Review mode' row must be one of {', '.join(REVIEW_MODES)}, got `{v}`")
    return v.lower()


def bot_name(login):
    """A GitHub login without a `[bot]` suffix, lower case."""
    return re.sub(r"\[bot\]$", "", login.strip(), flags=re.I).lower()


def ci_bot():
    """The `CI review bot login` row as bot_name() gives it, or None when unset."""
    v = value("CI review bot login")
    return (bot_name(v) or None) if v else None


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


def _committed_rows(run):
    """(rows, why): project.md as committed on origin/<target>; rows is None and why says so on any failure.

    <target> is the `Merge target branch` row of the root checkout's project.md (the first entry of `git worktree list`,
    so a feature worktree's own edit of that row changes nothing), read as refs/remotes/origin/<target>. Never read from a
    working tree. A target that starts with a branch pattern head (from the root checkout's project.md too; an agent can
    push such a branch) or a committed project.md that names another target is a failure too.
    """
    try:
        rows = _root_rows(run)
        target = _plain_branch(value("Merge target branch", rows) or DEFAULT_TARGET)
    except OSError as e:
        return None, f"could not read project.md in the root checkout: {e}"
    except SystemExit as e:
        return None, str(e)
    if target.startswith(branch_heads(rows)):
        return None, f"merge target branch `{target}` is a ticket branch"
    try:
        run(["git", "fetch", "origin", target])
        text = run(["git", "show", f"refs/remotes/origin/{target}:docs/agents/project.md"])
        committed = _plain_branch(value("Merge target branch", _parse(text)) or DEFAULT_TARGET)
    except OSError as e:
        return None, f"could not read project.md on origin/{target}: {e}"
    except SystemExit as e:
        return None, str(e)
    if committed != target:
        return None, f"project.md on origin/{target} names merge target branch `{committed}`, not `{target}`"
    return _parse(text), ""


def approval_setting(run=_git):
    """(tolerance, note) from the `Approval risk tolerance` row of project.md as committed on origin/<target>.

    Every failure to read (`_committed_rows`) and every unknown value gives ("strict", why). note is "" when the row set the level.
    """
    rows, why = _committed_rows(run)
    if rows is None:
        return "strict", why
    v = value("Approval risk tolerance", rows)
    if v is None:
        return "strict", "no Approval risk tolerance value on the merge target branch"
    if v.lower() not in TOLERANCES:
        return "strict", f"unknown Approval risk tolerance `{v}`"
    return v.lower(), ""


def approval_tolerance(run=_git):
    """`strict`, `balanced` or `permissive`; `strict` for anything missing, unknown or unreadable."""
    return approval_setting(run)[0]


def no_hands_setting(run=_git):
    """(on, ticket_cap, cost_cap, note) from the three No Hands rows of project.md as committed on origin/<target>.

    on is True only when the `No Hands` row says `on` and both caps (`No Hands ticket cap`, `No Hands cost cap`) are positive
    whole numbers. A missing row, an unknown value, a bad cap and every failure to read (`_committed_rows`) give
    (False, 0, 0, why). note is "" when the rows are fine.
    """
    rows, why = _committed_rows(run)
    if rows is None:
        return False, 0, 0, why
    cell = next((v for k, v in rows if k == "No Hands" or k.startswith("No Hands (")), "")
    mode = (re.search(r"`([^`]+)`", cell) or [None, None])[1]
    if (mode or "").lower() not in ("off", "on"):
        return False, 0, 0, "no usable No Hands value on the merge target branch" if mode is None else f"unknown No Hands value `{mode}`"
    caps = [value(k, rows) for k in ("No Hands ticket cap", "No Hands cost cap")]
    if not all(c and re.fullmatch(r"[0-9]+", c) and int(c) > 0 for c in caps):
        return False, 0, 0, "No Hands ticket cap and cost cap must be positive whole numbers"
    return mode.lower() == "on", int(caps[0]), int(caps[1]), ""


def review_after_conflict(run=_git):
    """`off` or `on` from the `Review after conflict resolution` row of project.md as committed on origin/<target>.

    A missing row is `off`. An unknown value, and any failure to read (`_committed_rows`), is `on`: the safe side is to review.
    """
    rows, _ = _committed_rows(run)
    if rows is None:
        return "on"
    if not any(k.startswith("Review after conflict resolution") for k, _ in rows):
        return "off"
    v = (value("Review after conflict resolution", rows) or "").lower()
    return v if v in ("off", "on") else "on"


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
