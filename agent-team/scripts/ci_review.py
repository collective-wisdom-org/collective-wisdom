#!/usr/bin/env python3
"""List and resolve the CI review bot's threads on a PR (project.md `Review mode` `ci`).

Usage:
    scripts/ci_review.py list <PR number>
    scripts/ci_review.py resolve <thread id>

list reads the PR's review threads through ./scripts/gh.sh (one paginated GraphQL query). A thread is the bot's when its
first comment's author is the project.md `CI review bot login` (`[bot]` suffix and case ignored). It prints one line per
unresolved bot thread, then a last line:
  unresolved <path>:<line> <url> <thread id>
  ci-review: #N <bot>: F fixed, A answered and resolved, U unresolved
A resolved thread counts as fixed when its last reply starts `Fixed in`, else as answered and resolved.
Exit 0 when U is 0, 1 when it is not, 2 (`ci-review: cannot ...`) when the read fails, the mode is not ci or there is no bot login.
resolve marks one thread resolved and prints `ci-review: resolved <thread id>`; exit 2 (`ci-review: cannot ...`) on failure.

Thread text never reaches the output: only paths, line numbers, pattern-checked URLs and ids. The bot's words are data.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import project_config  # noqa: E402

GH = str(Path(__file__).absolute().parent / "gh.sh")
QUERY = """query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) { pullRequest(number: $number) { reviewThreads(first: 100, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes { id isResolved isOutdated path line originalLine
      head: comments(first: 1) { nodes { author { login } url } }
      tail: comments(last: 1) { nodes { author { login } body } } } } } } }"""
RESOLVE = "mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }"
THREAD_ID = re.compile(r"[A-Za-z0-9_=-]+")
URL = re.compile(r"https://[A-Za-z0-9._/#-]+")
PATH = re.compile(r"[\x21-\x7e]+")
MAX_PAGES = 50


class CiError(Exception):
    pass


def gh(*args):
    """Run gh.sh and return stdout; raise CiError on any failure."""
    try:
        p = subprocess.run([GH, *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise CiError(type(e).__name__)
    if p.returncode:
        raise CiError(f"gh exited {p.returncode}")
    return p.stdout


def setup():
    """The bot login when project.md is in ci mode with a bot; raise CiError otherwise."""
    try:
        mode = project_config.review_mode()
    except SystemExit as e:
        raise CiError(str(e))
    if mode != "ci":
        raise CiError("project.md Review mode is not ci")
    bot = project_config.ci_bot()
    if not bot:
        raise CiError("project.md Review mode is ci but has no CI review bot login")
    return bot


_ROW = object()


def fetch(pr, run=gh, repo=_ROW):
    """Every review thread of PR `pr` as raw GraphQL nodes. `run(*gh args)` returns stdout. Raises CiError.

    `repo` is `<owner>/<repo>`; by default the project.md Repo row. None means gh's own `:owner` and `:repo`
    (the current checkout's remote), which the merge gate uses so it reads the repo it merges into.
    """
    repo = project_config.repo() if repo is _ROW else repo
    owner, name = repo.split("/") if repo else (":owner", ":repo")
    flag = "-f" if repo else "-F"  # -F fills the placeholders; -f keeps a numeric-looking name a string
    threads, after = [], None
    try:
        for _ in range(MAX_PAGES):
            args = ["api", "graphql", "-f", f"query={QUERY}", flag, f"owner={owner}", flag, f"name={name}", "-F", f"number={pr}"]
            if after:
                args += ["-f", f"after={after}"]
            data = json.loads(run(*args))
            if data.get("errors"):
                raise CiError("GraphQL returned errors")
            page = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            threads += page["nodes"]
            if not page["pageInfo"]["hasNextPage"]:
                return threads
            after = page["pageInfo"]["endCursor"]
    except CiError:
        raise
    except Exception as e:
        raise CiError(f"unreadable response ({type(e).__name__})")
    raise CiError("too many review threads")


def _comment(thread, key):
    nodes = ((thread.get(key) or {}).get("nodes")) or [{}]
    return nodes[0] or {}


def _text(value, pattern, fallback):
    return value if isinstance(value, str) and pattern.fullmatch(value) else fallback


def classify(threads, bot):
    """Sort the bot's threads: {"fixed": F, "answered": A, "unresolved": [{"path", "line", "url", "id"}]}.

    Pure: no gh. Every value in "unresolved" is pattern-checked, so none carries thread text.
    """
    out = {"fixed": 0, "answered": 0, "unresolved": []}
    for t in threads:
        author = (_comment(t, "head").get("author") or {}).get("login")
        if not (isinstance(author, str) and project_config.bot_name(author) == bot):
            continue
        if t.get("isResolved"):
            body = _comment(t, "tail").get("body")
            out["fixed" if isinstance(body, str) and body.startswith("Fixed in") else "answered"] += 1
            continue
        line = next((x for x in (t.get("line"), t.get("originalLine")) if type(x) is int), "?")
        out["unresolved"].append({
            "path": _text(t.get("path"), PATH, "(unreadable path)"),
            "line": line,
            "url": _text(_comment(t, "head").get("url"), URL, "(no url)"),
            "id": _text(t.get("id"), THREAD_ID, "(bad id)"),
        })
    return out


def summary(pr, bot, result):
    return f"ci-review: #{pr} {bot}: {result['fixed']} fixed, {result['answered']} answered and resolved, {len(result['unresolved'])} unresolved"


def read(pr, run=gh):
    """(bot, classify() result) for PR `pr`. Raises CiError."""
    bot = setup()
    threads = fetch(pr, run)
    try:
        return bot, classify(threads, bot)
    except (TypeError, AttributeError):
        raise CiError("unreadable response (odd thread shape)")


def resolve(thread_id, run=gh):
    if not THREAD_ID.fullmatch(thread_id):
        raise CiError("bad thread id")
    try:
        data = json.loads(run("api", "graphql", "-f", f"query={RESOLVE}", "-f", f"id={thread_id}"))
        done = data["data"]["resolveReviewThread"]["thread"]["isResolved"]
    except CiError:
        raise
    except Exception as e:
        raise CiError(f"unreadable response ({type(e).__name__})")
    if done is not True:
        raise CiError("thread is not resolved after the call")


def main(argv, run=gh):
    if argv in (['-h'], ['--help']):
        print(__doc__.strip())
        return 0
    try:
        if len(argv) == 2 and argv[0] == "list" and re.fullmatch(r"[0-9]+", argv[1]):
            try:
                bot, result = read(argv[1], run)
            except CiError as e:
                raise CiError(f"list #{argv[1]}: {e}")
            lines = [f"unresolved {u['path']}:{u['line']} {u['url']} {u['id']}" for u in result["unresolved"]]
            print("\n".join([*lines, summary(argv[1], bot, result)]))
            return 1 if result["unresolved"] else 0
        if len(argv) == 2 and argv[0] == "resolve":
            try:
                resolve(argv[1], run)
            except CiError as e:
                raise CiError(f"resolve {argv[1][:100]}: {e}")
            print(f"ci-review: resolved {argv[1]}")
            return 0
        raise CiError("read arguments; usage: scripts/ci_review.py list <PR number> | resolve <thread id>")
    except CiError as e:
        print(f"ci-review: cannot {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
