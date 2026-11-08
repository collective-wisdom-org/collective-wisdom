"""Read the per-user settings of this machine from ~/.config/collective-wisdom/user.md.

user.md holds markdown tables like project.md; a value is the first backticked token in its cell.
A `## GitHub accounts` row maps a repo (`<host>/<owner>/<repo>` of its origin remote) to the gh login that acts there.
The `Claude subscription API-equivalent usage` row holds one dollar figure. It never holds tokens.

    user_config.py account   print `<host> <login>` for the current repo, nothing when it has no login
    user_config.py path      print the file's path
"""

import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import app_root  # noqa: E402

LOGIN = re.compile(r"(?!.{40})[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
NAME = r"[\w.-]+"
URL = re.compile(rf"(?:https|ssh)://(?:[^@/\s]+@)?(?P<host>[A-Za-z0-9][\w.-]*)(?::\d+)?/(?P<repo>{NAME}/{NAME}?)(?:\.git)?/?")
SCP = re.compile(rf"(?:[^@/\s]+@)?(?P<host>[A-Za-z0-9][\w.-]*):(?P<repo>{NAME}/{NAME}?)(?:\.git)?/?")


class UserConfigError(Exception):
    pass


def path():
    return Path.home() / ".config" / "collective-wisdom" / "user.md"


def repo_key(root):
    """`<host>/<owner>/<repo>` in lower case from the origin remote of the repo at root, or None."""
    try:
        p = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    url = p.stdout.strip()
    m = p.returncode == 0 and (URL.fullmatch(url) or SCP.fullmatch(url))
    return f"{m['host']}/{m['repo']}".lower() if m else None


def _rows(file):
    """(line number, first backticked token of cell 1 or None, raw cell 1, cell 2) per table row; [] with no file."""
    try:
        lines = file.read_text().splitlines()
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as e:
        raise UserConfigError(f"cannot read {file}: {type(e).__name__}")
    rows = []
    for n, line in enumerate(lines, 1):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 2:
            m = re.search(r"`([^`]+)`", cells[0])
            rows.append((n, m and m[1], cells[0], cells[1]))
    return rows


def login(root):
    """The gh login user.md maps to the repo at root, or None. Raises UserConfigError on a duplicate or malformed row."""
    key, file = repo_key(root), path()
    found = [(n, cell) for n, token, _, cell in _rows(file) if key and token and token.lower() == key]
    if len(found) > 1:
        raise UserConfigError(f"{file}: lines {found[0][0]} and {found[1][0]} both map {key}")
    if not found:
        return None
    n, cell = found[0]
    m = re.search(r"`([^`]+)`", cell)
    if not m or not LOGIN.fullmatch(m[1]):
        raise UserConfigError(f"{file}:{n}: the login for {key} is not a GitHub login")
    return m[1]


def subscription_usage(provider):
    """API-equivalent dollars of a provider's subscription from its `<provider> subscription API-equivalent usage` row.

    A positive finite number, else None: no file, no row, `none`, 0, a negative, `12,000` and text all read as None.
    """
    for _, _, key, cell in _rows(path()):
        if key.startswith(f"{provider} subscription API-equivalent usage"):
            m = re.search(r"`([^`]+)`", cell)
            try:
                n = float(m[1]) if m else None
            except ValueError:
                return None
            return n if n is not None and math.isfinite(n) and n > 0 else None
    return None


def main(argv):
    if argv == ["path"]:
        print(path())
    elif argv == ["account"]:
        try:
            key, who = repo_key(app_root.root()), login(app_root.root())
        except UserConfigError as e:
            print(f"user_config: {e}", file=sys.stderr)
            return 2
        if who:
            print(f"{key.split('/')[0]} {who}")
    else:
        print("usage: user_config.py account|path", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
