"""Find the app the scripts serve: the git repo of the current directory.

The scripts are copied into an app, so they can't assume where their own file sits.
Every documented call runs from the repo top (or a worktree top), where this returns that checkout.
Outside any git repo it returns the current directory.
"""

import functools
import subprocess
from pathlib import Path


@functools.cache
def root():
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        top = ""
    return Path(top) if top else Path.cwd()
