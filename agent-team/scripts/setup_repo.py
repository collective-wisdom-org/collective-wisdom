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


def unset_rows(text):
    """Names of the required rows that are missing, unset or still hold a template placeholder."""
    rows = project_config._parse(text)

    def get(key):
        found = next(((k, v) for k, v in rows if k == key or k.startswith(key + " (")), None)
        value = found and project_config.setting(found[0], [found])
        return value, not found or value is None or bool(PLACEHOLDER.search(AUTOLINK.sub("", found[1])))

    tracker = (get("Tracker")[0] or "").lower()
    bad = [k for k in REQUIRED if get(k)[1] or (k == "Tracker" and tracker not in project_config.TRACKERS)]
    return bad + (["Linear team name"] if tracker == "linear" and get("Linear team name")[1] else [])


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
    if not isinstance(v, str) or not v.strip() or len(v) > 300 or re.search(r"[\n\r|`]", v):
        raise Fail(2, f"answer '{name}' must be one line of at most 300 characters with no | or backtick")
    return v.strip()


def validate(a):
    unknown = set(a) - ANSWER_KEYS
    if unknown:
        raise Fail(2, f"unknown answers: {', '.join(sorted(unknown))}")
    a = {k: _free(v, k) if k in TEXT_KEYS else v for k, v in a.items()}
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
    s, e = _need_section(lines, title)
    for i in range(s, e):
        lines[i] = re.sub(pattern, repl, lines[i])


def build(text, a, fresh):
    """project.md text rendered from the template (fresh) or `text` with only the rows named in the answers changed."""
    lines = text.splitlines(keepends=True)
    if fresh:
        a = {"target": "main", "host": "github.com", "approver": a.get("login"), **a}
        a["tracker_scope"] = a.get("repo") if a.get("tracker") == "github" else a.get("tracker_scope") or a.get("linear_team")
        missing = [k for k in ("product", "tracker", "prefix", "repo", "test", "approver", "tracker_scope") if not a.get(k)]
        if missing:
            raise Fail(2, f"a first setup needs: {', '.join(missing)}")
    else:
        a = {**a, "tracker_scope": a.get("tracker_scope") or a.get("linear_team")}
    if "product" in a:
        _set(lines, "Product name", a["product"])
        title = next((i for i, line in enumerate(lines) if line.startswith("# Project config (")), None)
        if title is not None:
            lines[title] = f"# Project config ({a['product']})\n"
    if "tracker" in a:
        _token(lines, "Tracker", a["tracker"])
    if a.get("tracker_scope"):
        _set(lines, "Tracker scope", f"`{a['tracker_scope']}`")
        if _find(lines, "Linear team name") and (a.get("tracker") or "linear") == "linear":
            _set(lines, "Linear team name", f"`{a['tracker_scope']}`")
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
        todo = f"TODO({_owner(a)})"
        _set(lines, "Required CI checks", "none (no CI yet)" if a.get("ci", "").lower() == "none" else todo)
    if "rules" in a or fresh:
        s, e = _need_section(lines, "Repo invariants")
        i = max(i for i in range(s, e) if lines[i].startswith("- "))
        eol = lines[i][len(lines[i].rstrip("\r\n")):]
        rules = " ".join(r if r[-1] in ".!?" else r + "." for r in a.get("rules", [])) or "none yet"
        lines[i] = f"- {rules}{eol}"
    if fresh:
        p = a["prefix"].lower()
        _set(lines, "Branch pattern", f"`feat/{p}-N-short-title` (`{p}` is the issue prefix in lower case)")
        for key in ("Lint", "Typecheck"):
            _set(lines, key, f"TODO({_owner(a)})")
        if a["tracker"] == "linear":
            _set(lines, "Linear project", "none (the team is the scope)")
        else:
            _drop(lines, "Linear team name")
            _drop(lines, "Linear project")
        for title in ("Areas and labels", "Product rules", "Security overlays", "Environments and deploy"):
            _fill(lines, title, r"<[^<>]*>", "none yet")
        _fill(lines, "Docs check", r", <add[^<>]*>", "")
        _fill(lines, "Docs check", r"<[^<>]*>", "none")
    return "".join(lines)


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
        raise Fail(1, f"{wt} is not a linked worktree of {root}")
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
    new = build(old if old is not None else (TEMPLATES / "project.md").read_text(), a, old is None)
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
