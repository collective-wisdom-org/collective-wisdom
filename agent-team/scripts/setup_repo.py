"""Set up the agent team in a repo: read what is set, write the user's account row, render project.md.

    setup_repo.py status [--root DIR]    line 1 `missing`, `set` or `placeholders: <rows>`, line 2 the facts as JSON; writes nothing
    setup_repo.py user --login L [--subscription N|none] [--repo-key K]
                                         add or replace this repo's row in ~/.config/collective-wisdom/user.md
    setup_repo.py write --dir WT --answers JSON|@file [--root DIR]
                                         render or update WT/docs/agents/project.md and add `.agent-team/` to WT/.gitignore

Exit 0 on success, 1 when `write` refuses (WT is not a linked worktree of the repo, or sits on the merge target), 2 on bad input.
`write` touches no file outside WT. user.md never holds tokens.
"""

import argparse
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import app_root  # noqa: E402
import project_config  # noqa: E402
import user_config  # noqa: E402

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
REQUIRED = ("Tracker", "Tracker scope", "Issue identifier prefix", "Repo", "Test")
PLACEHOLDER = re.compile(r"<[^>]+>")
AUTOLINK = re.compile(r"<https?://[^<>\s]+>")
PROSE = r"<(?!https?://)[^<>]*>"
READ_AS_ON = ("Publish release notes",)  # a missing row already reads as on; the template's `off` would change that
RULES = "Repo rules: "
RULE_BULLET = re.compile(r"- <[^<>]*>")
JIRA = ("Jira site", "Jira project key", *(f"Jira status: {s}" for s in ("Backlog", "Todo", "In Progress", "In Review", "Done", "Canceled")))
TRACKER_ROWS = ("Tracker", "Tracker scope", "Linear team name")
ANSWER_ROWS = {  # the rows an answer fills; on a repair it applies only while one of them is unset
    "product": ("Product name",), "approver": ("Approver",), "target": ("Merge target branch",), "ci": ("Required CI checks",),
    "tracker": TRACKER_ROWS, "tracker_scope": TRACKER_ROWS, "prefix": ("Issue identifier prefix",), "repo": ("Repo",), "host": ("Repo",), "test": ("Test",),
}
NO_ANGLE = ("test", "product", "tracker_scope", "linear_team")
IGNORED = {".agent-team", ".agent-team/", "/.agent-team", "/.agent-team/"}
TEXT_KEYS = ("product", "tracker_scope", "linear_team", "test", "approver", "ci")
ANSWER_KEYS = set(TEXT_KEYS) | {"tracker", "prefix", "repo", "host", "target", "login", "rules"}
REPO = re.compile(r"[\w.-]+/[\w.-]+")
HOST = re.compile(r"[A-Za-z0-9][\w.-]*")
KEY = re.compile(r"[\w.-]+/[\w.-]+/[\w.-]+")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def _git(args, cwd, timeout=15):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        p = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=timeout, env=env, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def _branch(name):
    try:
        return project_config._plain_branch(name)
    except SystemExit:
        raise Fail(2, f"not a plain branch name: {name}")


def _read(path):
    return path.read_bytes().decode("utf-8", "surrogateescape")


def _write(path, text, mode):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".setup_repo-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(text.encode("utf-8", "surrogateescape"))
        os.chmod(tmp, path.stat().st_mode & 0o777 if path.exists() else mode)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _find(lines, key):
    """(index, cells) of the table row whose key cell is `key` or starts with `key (`; None when absent."""
    for i, line in enumerate(lines):
        c = _cells(line)
        if line.lstrip().startswith("|") and len(c) >= 2 and (c[0] == key or c[0].startswith(key + " (")):
            return i, c
    return None


def _row(lines, key):
    found = _find(lines, key)
    if not found:
        raise Fail(2, f"no '{key}' row to change")
    return found


def _set(lines, key, cell):
    i, c = _row(lines, key)
    eol = lines[i][len(lines[i].rstrip("\r\n")):]
    lines[i] = f"| {c[0]} | {cell} |{eol}"


def _token(lines, key, new):
    """Put `new` in the first backticked token of the row's value, or give the cell just `new` in backticks."""
    cell = _row(lines, key)[1][1]
    _set(lines, key, re.sub(r"`[^`]+`", lambda m: f"`{new}`", cell, count=1) if "`" in cell else f"`{new}`")


def _drop(lines, key):
    found = _find(lines, key)
    if found:
        del lines[found[0]]


def _section(lines, title):
    start = next((i for i, line in enumerate(lines) if line.rstrip() == f"## {title}"), None)
    if start is None:
        return None
    return start, next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))


def _need_section(lines, title):
    found = _section(lines, title)
    if not found:
        raise Fail(2, f"no '## {title}' section")
    return found


def guess_test(d):
    try:
        data = json.loads((d / "package.json").read_text())
        scripts = data.get("scripts") if isinstance(data, dict) else None
        if isinstance(scripts, dict) and scripts.get("test"):
            return "pnpm test" if (d / "pnpm-lock.yaml").exists() else "yarn test" if (d / "yarn.lock").exists() else "npm test"
    except (OSError, ValueError):
        pass
    for marker, cmd in (("pyproject.toml", "pytest"), ("pytest.ini", "pytest"), ("go.mod", "go test ./..."), ("Cargo.toml", "cargo test")):
        if (d / marker).exists():
            return cmd
    return None


def guess_prefix(name):
    words = [w for w in re.split(r"[-_.]+", name or "") if w]
    letters = "".join(w[0] for w in words if w[0].isalnum()).upper()
    if len(letters) < 2:
        letters = re.sub(r"[^A-Za-z0-9]", "", name or "")[:3].upper()
    letters = letters[:4]
    return letters if len(letters) >= 2 and re.fullmatch(r"[A-Z][A-Z0-9]*", letters) else None


def _ph(cell):
    return bool(PLACEHOLDER.search(AUTOLINK.sub("", cell)))


def _get(rows, key):
    """(value, unset) of the row `key`: unset when it is missing, empty, a TODO or still holds a template placeholder."""
    found = next(((k, v) for k, v in rows if k == key or k.startswith(key + " (")), None)
    value = found and project_config.setting(found[0], [found])
    return value, not found or value is None or _ph(found[1])


def unset_rows(text):
    """Names of the required rows that are unset or hold a template placeholder. A missing `Tracker` row reads as linear."""
    rows = project_config._parse(text)
    tracker = (_get(rows, "Tracker")[0] or "linear").lower()
    team_unset = _get(rows, "Linear team name")[1]
    bad = [
        k for k in REQUIRED
        if (tracker not in project_config.TRACKERS if k == "Tracker" else _get(rows, k)[1] and not (k == "Tracker scope" and tracker == "linear" and not team_unset))
    ]
    return bad + (["Linear team name"] if tracker == "linear" and team_unset else [])


def _known(text):
    """The answers a project.md already holds in its set rows."""
    rows = project_config._parse(text)

    def val(key):
        value, unset = _get(rows, key)
        return None if unset else value

    tracker = (val("Tracker") or "linear").lower()
    team = next((v for k, v in rows if k.startswith("Linear team name")), "").split(" (key")[0].strip()
    team = team if team and "`" not in team and not _ph(team) else val("Linear team name")
    out = {
        "product": val("Product name"), "tracker": tracker if tracker in project_config.TRACKERS else None, "prefix": val("Issue identifier prefix"),
        "tracker_scope": val("Tracker scope") or team, "repo": val("Repo"), "test": val("Test"),
        "approver": (val("Approver") or "").split(". Approves")[0],
    }
    return {k: v for k, v in out.items() if v}


def _gh_logins(host):
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN", "GH_TOKEN")}
    try:
        p = subprocess.run(["gh", "auth", "status", "--hostname", host], capture_output=True, text=True, timeout=15, env=env, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return []
    found = re.findall(rf"Logged in to {re.escape(host)} account (\S+)", p.stdout + p.stderr)
    return list(dict.fromkeys(f for f in found if user_config.LOGIN.fullmatch(f)))


def facts(d):
    url = _git(["remote", "get-url", "origin"], d) or ""
    m = user_config.URL.fullmatch(url) or user_config.SCP.fullmatch(url)
    host, repo = (m["host"], m["repo"]) if m else (None, None)
    refs = _git(["ls-remote", "--symref", "origin", "HEAD"], d) or ""
    t = re.search(r"^ref: refs/heads/(\S+)\tHEAD$", refs, re.M)
    try:
        target = _branch(t[1]) if t else "main"
    except Fail:
        target = "main"
    out = {"host": host, "repo": repo, "repo_key": user_config.repo_key(d), "target": target}
    out["gh_logins"] = _gh_logins(host or "github.com")
    try:
        out["mapped_login"] = user_config.login(d)
    except user_config.UserConfigError as e:
        out["mapped_login"], out["user_md_error"] = None, str(e)
    name = repo.split("/")[1] if repo else d.resolve().name
    pinned = _git(["cat-file", "-e", f"refs/remotes/origin/{target}:docs/agents/installed-from.txt"], d)
    workflows = d / ".github" / "workflows"
    out.update(
        user_md_exists=user_config.path().exists(),
        pinned=pinned is not None,
        has_workflows=workflows.is_dir() and any(workflows.iterdir()),
        test_guess=guess_test(d),
        prefix_guess=guess_prefix(name),
        product_guess=name,
    )
    return out


def cmd_status(args):
    d = Path(args.root) if args.root else app_root.root()
    try:
        text = _read(d / "docs" / "agents" / "project.md")
        bad = unset_rows(text)
        state = f"placeholders: {', '.join(bad)}" if bad else "set"
    except (FileNotFoundError, NotADirectoryError):
        state = "missing"
    except OSError as e:
        raise Fail(2, f"cannot read project.md: {type(e).__name__}")
    print(state)
    print(json.dumps(facts(d)))
    return 0


def _example_free(lines, s, e):
    return [line for i, line in enumerate(lines) if not (s < i < e and line.lstrip().startswith("|") and "`example-login`" in line)]


def cmd_user(args):
    key = (args.repo_key or user_config.repo_key(app_root.root()) or "").lower()
    if not KEY.fullmatch(key):
        raise Fail(2, "no repo key: the origin remote is not a recognised URL, pass --repo-key")
    if not user_config.LOGIN.fullmatch(args.login):
        raise Fail(2, f"not a GitHub login: {args.login}")
    sub = args.subscription
    if sub not in (None, "none") and not (NUMBER.fullmatch(sub) and float(sub) > 0 and math.isfinite(float(sub))):
        raise Fail(2, "--subscription is `none` or a positive number")
    file = user_config.path().resolve()
    try:
        lines = _read(file).splitlines(keepends=True)
    except FileNotFoundError:
        lines = (TEMPLATES / "user.md").read_text().splitlines(keepends=True)
        if _section(lines, "GitHub accounts"):
            lines = _example_free(lines, *_section(lines, "GitHub accounts"))
        if sub not in (None, "none"):
            _token(lines, "Claude subscription API-equivalent usage", sub)
    row = f"| `{key}` | `{args.login}` |\n"
    same = [i for i, line in enumerate(lines) if line.lstrip().startswith("|") and (m := re.search(r"`([^`]+)`", _cells(line)[0])) and m[1].lower() == key]
    found = _section(lines, "GitHub accounts")
    if same:
        lines[same[0]] = row
        for i in reversed(same[1:]):
            del lines[i]
    elif not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines += ["\n", "## GitHub accounts\n", "\n", "| Repo | Login |\n", "|---|---|\n", row]
    else:
        s, e = found
        rows = [i for i in range(s + 1, e) if lines[i].lstrip().startswith("|")]
        at = rows[-1] + 1 if rows else e
        if not lines[at - 1].endswith("\n"):
            lines[at - 1] += "\n"
        lines[at:at] = [row] if rows else ["\n", "| Repo | Login |\n", "|---|---|\n", row]
    file.parent.mkdir(parents=True, exist_ok=True)
    _write(file, "".join(lines), 0o600)
    print(file)
    return 0


def _free(v, name):
    bad = r"[\n\r|`<>]" if name in NO_ANGLE else r"[\n\r|`]"
    if not isinstance(v, str) or not v.strip() or len(v) > 300 or re.search(bad, v):
        raise Fail(2, f"answer '{name}' must be one line of at most 300 characters with no | or backtick" + (" and no < or >" if name in NO_ANGLE else ""))
    return v.strip()


def validate(a):
    unknown = set(a) - ANSWER_KEYS
    if unknown:
        raise Fail(2, f"unknown answers: {', '.join(sorted(unknown))}")
    a = {k: _free(v, k) if k in TEXT_KEYS else v for k, v in a.items()}
    if "linear_team" in a:
        a.setdefault("tracker_scope", a.pop("linear_team"))
    if "approver" in a:
        a["approver"] = a["approver"].rstrip(".")
    if "rules" in a:
        if not isinstance(a["rules"], list):
            raise Fail(2, "answer 'rules' must be a list")
        a["rules"] = [_free(r, "rules") for r in a["rules"] if not isinstance(r, str) or r.strip()]
    checks = {
        "tracker": lambda v: v in project_config.TRACKERS,
        "prefix": lambda v: isinstance(v, str) and re.fullmatch(r"[A-Z][A-Z0-9]*", v),
        "repo": lambda v: isinstance(v, str) and REPO.fullmatch(v),
        "host": lambda v: isinstance(v, str) and HOST.fullmatch(v),
        "login": lambda v: isinstance(v, str) and user_config.LOGIN.fullmatch(v),
    }
    for k, ok in checks.items():
        if k in a and not ok(a[k]):
            raise Fail(2, f"bad answer '{k}': {a[k]!r}")
    if "target" in a:
        _branch(a["target"] if isinstance(a["target"], str) else "")
    return a


def _owner(a):
    word = re.search(r"[\w.-]+", a.get("approver", ""))
    return a.get("login") or (word and word[0]) or "owner"


def _fill(lines, title, pattern, repl):
    found = _section(lines, title)
    for i in range(*found) if found else ():
        lines[i] = re.sub(pattern, repl, lines[i])


def _prose(lines):
    for title in ("Areas and labels", "Product rules", "Security overlays", "Environments and deploy"):
        _fill(lines, title, PROSE, "none yet")
    _fill(lines, "Docs check", r", <add[^<>]*>", "")
    _fill(lines, "Docs check", PROSE, "none")


def _put(lines, key, cell, *after, overwrite=True):
    """Set the row `key` (its whole key cell) to `cell`; add it after the first of the `after` rows that exists when it is missing."""
    base = key.split(" (")[0]
    if _find(lines, base):
        if overwrite:
            _set(lines, base, cell)
        return
    anchor = next((f for f in (_find(lines, k) for k in after) if f), None)
    if not anchor:
        raise Fail(2, f"no '{after[0]}' row to add '{base}' after")
    if not lines[anchor[0]].endswith("\n"):
        lines[anchor[0]] += "\n"
    lines.insert(anchor[0] + 1, f"| {key} | {cell} |\n")


def _tracker(lines, a, owner, fresh):
    """Set the `Tracker` row and what hangs on it: the scope, the Linear rows, the Jira rows."""
    t = a.get("tracker")
    if t and _find(lines, "Tracker"):
        _token(lines, "Tracker", t)
    elif t:
        _put(lines, "Tracker (`linear`, `github` or `jira`)", f"`{t}`", "Product name", "Tracker scope", "Issue identifier prefix")
    scope = a.get("tracker_scope")
    if scope:
        _put(lines, "Tracker scope (`<TEAM>`)", f"`{scope}`", "Tracker", "Product name", "Issue identifier prefix")
    now = t or (_get(project_config._parse("".join(lines)), "Tracker")[0] or "linear").lower()
    if now == "linear":
        if scope:
            _put(lines, "Linear team name (Linear only)", f"`{scope}`", "Tracker scope")
        elif t and not _find(lines, "Linear team name"):
            raise Fail(2, "switching to linear needs tracker_scope, the Linear team name")
        if t:
            _put(lines, "Linear project (Linear only)", "none (the team is the scope)", "Issue identifier prefix", overwrite=fresh)
    elif t:
        _drop(lines, "Linear team name")
        _drop(lines, "Linear project")
    if t == "jira":
        prev = "Issue identifier prefix"
        for key in JIRA:
            _put(lines, key, f"TODO({owner})", prev, overwrite=False)
            prev = key
    elif t:
        for key in JIRA:
            _drop(lines, key)


def _rules(lines, rules, ph_only=False):
    """Write the repo rules bullet over the one setup wrote, else `none yet`, else the template bullet; else after the last bullet.

    With ph_only, change only the template bullet and only when there is one.
    """
    found = _section(lines, "Repo invariants") if ph_only else _need_section(lines, "Repo invariants")
    if not found:
        return
    s, e = found
    bullets = [i for i in range(s, e) if lines[i].startswith("- ")]
    tests = [lambda t: t.startswith("- " + RULES), lambda t: t == "- none yet", lambda t: bool(RULE_BULLET.fullmatch(t))]
    at = next((i for f in tests[2 * ph_only:] for i in bullets if f(lines[i].rstrip())), None)
    if ph_only and at is None:
        return
    text = "- " + RULES + " ".join(r if r[-1] in ".!?" else r + "." for r in rules) if rules else "- none yet"
    if at is not None:
        lines[at] = text + lines[at][len(lines[at].rstrip("\r\n")):]
        return
    last = bullets[-1] if bullets else s
    if not lines[last].endswith("\n"):
        lines[last] += "\n"
    lines[last + 1:last + 1] = ([] if bullets else ["\n"]) + [text + "\n"]


def build(text, a, fresh):
    """project.md text rendered from the template (fresh) or `text` with only the rows named in the answers changed."""
    lines = text.splitlines(keepends=True)
    if fresh:
        a = {"target": "main", "host": "github.com", "approver": a.get("login"), **a}
        a["tracker_scope"] = a.get("repo") if a.get("tracker") == "github" else a.get("tracker_scope")
        missing = [k for k in ("product", "tracker", "prefix", "repo", "test", "approver", "tracker_scope") if not a.get(k)]
        if missing:
            raise Fail(2, f"a first setup needs: {', '.join(missing)}")
    elif a.get("tracker") == "github":
        a = {**a, "tracker_scope": a.get("repo") or _get(project_config._parse(text), "Repo")[0]}
    owner = _owner(a)
    if "product" in a:
        _set(lines, "Product name", a["product"])
        title = next((i for i, line in enumerate(lines) if line.startswith("# Project config (")), None)
        if title is not None:
            lines[title] = f"# Project config ({a['product']})\n"
    if "tracker" in a or a.get("tracker_scope"):
        _tracker(lines, a, owner, fresh)
    if "prefix" in a:
        _token(lines, "Issue identifier prefix", a["prefix"])
    if "approver" in a:
        _set(lines, "Approver", f"{a['approver']}. Approves specs and merges only")
    if "target" in a:
        _token(lines, "Merge target branch", a["target"])
    if "repo" in a:
        _set(lines, "Repo", f"`{a['repo']}` (<https://{a.get('host', 'github.com')}/{a['repo']}>)")
    if "test" in a:
        _token(lines, "Test", a["test"])
    if "ci" in a or fresh:
        _set(lines, "Required CI checks", "none (no CI yet)" if a.get("ci", "").lower() == "none" else f"TODO({owner})")
    if "rules" in a or fresh:
        _rules(lines, a.get("rules", []))
    if fresh:
        for key in ("Lint", "Typecheck"):
            _set(lines, key, f"TODO({owner})")
        _prose(lines)
    return "".join(lines)


def _rowkey(line):
    c = _cells(line)
    return c[0].split(" (")[0] if line.lstrip().startswith("|") and len(c) >= 2 and c[0] not in ("Key", "") and not c[0].startswith("-") else None


def _table_end(lines, i):
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        i += 1
    return i


def _anchor(lines, new, j):
    """Where in `lines` to put row new[j]: after the nearest preceding row of its table that `lines` has, else at the end of the table of the nearest following one."""
    for rng, end in ((range(j - 1, -1, -1), False), (range(j + 1, len(new)), True)):
        for k in rng:
            if not new[k].lstrip().startswith("|"):
                break
            found = (key := _rowkey(new[k])) and _find(lines, key)
            if found:
                return _table_end(lines, found[0]) if end else found[0] + 1


def _merge(lines, new):
    """Take the fresh render's row for each row of `lines` that holds a placeholder it fills, and add the rows `lines` lacks."""
    title = lambda ls: next((i for i, line in enumerate(ls) if line.startswith("# Project config (")), None)
    ot, nt = title(lines), title(new)
    if None not in (ot, nt) and _ph(lines[ot]) and not _ph(new[nt]):
        lines[ot] = new[nt]
    for j, line in enumerate(new):
        key = _rowkey(line)
        if not key:
            continue
        found = _find(lines, key)
        if found:
            if _ph(found[1][1]) and not _ph(_cells(line)[1]):
                lines[found[0]] = line
        elif key not in READ_AS_ON and (at := _anchor(lines, new, j)) is not None:
            if not lines[at - 1].endswith("\n"):
                lines[at - 1] += "\n"
            lines.insert(at, line if line.endswith("\n") else line + "\n")


def repair(old, a):
    """`old` with every unset row and template bullet filled in as a first setup would write them. An answer applies only to an unset row; a set row keeps its value."""
    unset = set(unset_rows(old)) | {k for k in ("Product name", "Approver", "Merge target branch", "Required CI checks") if _get(project_config._parse(old), k)[1]}
    a = {k: v for k, v in a.items() if k not in ANSWER_ROWS or unset & set(ANSWER_ROWS[k])}
    rules = a.pop("rules", [])
    known = _known(old)
    if a.get("tracker", known.get("tracker")) != known.get("tracker"):
        known.pop("tracker_scope", None)
    fresh = build((TEMPLATES / "project.md").read_text(), {**known, **a}, True)
    lines = old.splitlines(keepends=True)
    _merge(lines, fresh.splitlines(keepends=True))
    _prose(lines)
    _rules(lines, rules, ph_only=True)
    return build("".join(lines), a, False)


def _inside(path, wt):
    try:
        path.resolve().relative_to(wt)
    except ValueError:
        raise Fail(1, f"{path} resolves outside {wt}")


def _check_worktree(root, wt, a):
    listed = _git(["worktree", "list", "--porcelain"], root)
    if listed is None:
        raise Fail(2, f"git worktree list failed in {root}")
    trees = [Path(line[9:]).resolve() for line in listed.splitlines() if line.startswith("worktree ")]
    if wt not in trees[1:]:
        raise Fail(1, f"{wt} is not a linked worktree of the repo at {root}")
    branch = _git(["symbolic-ref", "--short", "-q", "HEAD"], wt)
    if not branch:
        raise Fail(1, f"{wt} has a detached HEAD")
    target = a.get("target")
    if not target:
        try:
            target = project_config.value("Merge target branch", project_config._parse(_read(wt / "docs" / "agents" / "project.md"))) or "main"
        except OSError:
            target = "main"
        target = _branch(target)
    if branch in (target, "main", "master"):
        raise Fail(1, f"{wt} is on {branch}, which is the merge target or a default branch; use a setup branch")


def cmd_write(args):
    try:
        a = json.loads(Path(args.answers[1:]).read_text() if args.answers.startswith("@") else args.answers)
    except (OSError, ValueError) as e:
        raise Fail(2, f"cannot read --answers: {type(e).__name__}")
    if not isinstance(a, dict):
        raise Fail(2, "--answers must be a JSON object")
    a = validate(a)
    wt = Path(args.dir).resolve()
    _check_worktree(Path(args.root) if args.root else app_root.root(), wt, a)
    agents, md, ignore = wt / "docs" / "agents", wt / "docs" / "agents" / "project.md", wt / ".gitignore"
    for p in (wt / "docs", agents, md, ignore):
        _inside(p, wt)
    try:
        old = _read(md)
    except FileNotFoundError:
        old = None
    if old is None:
        new = build((TEMPLATES / "project.md").read_text(), a, True)
    else:
        new = repair(old, a) if unset_rows(old) else build(old, a, False)
    ignored = _read(ignore) if ignore.exists() else ""
    if not any(line.strip() in IGNORED for line in ignored.splitlines()):
        ignored += ("" if not ignored or ignored.endswith("\n") else "\n") + ".agent-team/\n"
    agents.mkdir(parents=True, exist_ok=True)
    for path, text, was in ((md, new, old), (ignore, ignored, _read(ignore) if ignore.exists() else None)):
        if text == was:
            print(f"unchanged: {path}")
        else:
            _write(path, text, 0o644)
            print(path)
    return 0


def main(argv):
    p = argparse.ArgumentParser(prog="setup_repo.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--root")
    u = sub.add_parser("user")
    u.add_argument("--login", required=True)
    u.add_argument("--subscription")
    u.add_argument("--repo-key")
    w = sub.add_parser("write")
    w.add_argument("--dir", required=True)
    w.add_argument("--answers", required=True)
    w.add_argument("--root")
    args = p.parse_args(argv)
    try:
        return {"status": cmd_status, "user": cmd_user, "write": cmd_write}[args.cmd](args)
    except Fail as e:
        print(f"setup_repo: {e}", file=sys.stderr)
        return e.code
    except OSError as e:
        print(f"setup_repo: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
