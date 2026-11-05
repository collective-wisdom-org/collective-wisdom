"""Point the scripts at a fixture project.md so the suite needs no consumer config."""

import os
import tempfile
from pathlib import Path

FIXTURE = """| Key | Value |
|---|---|
| Issue identifier prefix (`<PREFIX>`) | `ABC` |
| Repo (`<owner>/<repo>`) | `example/app` |
| Branch pattern | `feat/<prefix>-N-short-title` |
| Migrations directory | none |
| Owner login (trusted review-comment author) | `me` |
"""

_dir = tempfile.mkdtemp(prefix="agent-team-tests-")
_md = Path(_dir) / "project.md"
_md.write_text(FIXTURE)
os.environ["PROJECT_MD"] = str(_md)
