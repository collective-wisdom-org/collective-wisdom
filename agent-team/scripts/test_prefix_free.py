import ast
import importlib.util
import io
import json
import re
import sys
import tokenize
from pathlib import Path

import pytest

import project_config

REPO = Path(__file__).absolute().parents[2]
BASE = "| Key | Value |\n|---|---|\n| Repo | `example/app` |\n| Branch pattern | `{feat,infra}/<prefix>-N-short-title` |\n| Tracker | `github` |\n"


def use_project(monkeypatch, tmp_path, prefix, retired=None):
    rows = f"| Issue identifier prefix | `{prefix}` |\n" + (f"| Retired issue prefixes | `{retired}` |\n" if retired else "")
    md = tmp_path / "project.md"
    md.write_text(BASE + rows)
    monkeypatch.setenv("PROJECT_MD", str(md))


def test_two_prefixes_split_at_the_cutover(monkeypatch, tmp_path, capsys):
    use_project(monkeypatch, tmp_path, "ZZ", "YY<10")
    pc = project_config
    assert [pc.ticket_id(5), pc.ticket_id(10)] == ["YY-5", "ZZ-10"]
    assert [bool(pc.ticket_re(anchored=True).match(t)) for t in ("YY-5", "ZZ-10", "CW-5", "ZZ-")] == [True, True, False, False]
    assert [pc.ticket_number(t) for t in ("YY-5", "ZZ-10", "CW-5")] == [5, 10, None]
    branch = re.compile(pc.branch_ticket_re())
    assert [branch.match(b).groups() if branch.match(b) else None for b in ("feat/yy-5-x", "infra/zz-10-x", "feat/cw-5-x")] == [
        ("yy", "5"), ("zz", "10"), None,
    ]
    assert pc.chief_thread_title() == "ZZ - Chief of Staff"

    # an open issue 5 is already in state as YY-5, so the untracked check reports nothing
    spec = importlib.util.spec_from_file_location("cos_untracked_check", Path(__file__).with_name("cos_untracked_check.py"))
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    files = {"state.json": {"tickets": {"YY-5": {}}, "merged": {}},
             "issues.json": [{"number": 5, "labels": [{"name": "agent"}, {"name": "status:in-review"}], "author": {"login": "bot"}}],
             "prs.json": [{"number": 7, "headRefName": "feat/yy-5-x", "author": {"login": "bot"}}]}
    for name, data in files.items():
        (tmp_path / name).write_text(json.dumps(data))
    argv = ["x", "--login", "bot"] + [a for k, f in (("--file", "state"), ("--issues", "issues"), ("--open-prs", "prs")) for a in (k, str(tmp_path / f"{f}.json"))]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as e:
        check.main()
    assert (e.value.code, capsys.readouterr().out.splitlines()) == (0, ["untracked-check: 0 not in state"])


@pytest.mark.parametrize("row", ["YY<x", "ZZ<10", "YY<10,XX<10", "YY<10,YY<20", "yy<10", "YY"])
def test_bad_retired_row_stops_the_script(monkeypatch, tmp_path, row):
    use_project(monkeypatch, tmp_path, "ZZ", row)
    with pytest.raises(SystemExit, match="'Retired issue prefixes' row"):
        project_config.retired_prefixes()


def repo_prefixes():
    """The current and retired prefixes of this repo's own project.md, whatever PROJECT_MD says."""
    rows = project_config._parse((REPO / "docs" / "agents" / "project.md").read_text())
    return [project_config.value("Issue identifier prefix", rows), *(p for p, _ in project_config.retired_prefixes(rows))]


HIT = re.compile("|".join(rf"\b{p}\b|\b{p.lower()}-\d" for p in repo_prefixes()))


def python_hits(path):
    text = path.read_text()
    tree = ast.parse(text)
    docs = [
        (n.body[0].lineno, n.body[0].end_lineno)
        for n in ast.walk(tree)
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and n.body and isinstance(n.body[0], ast.Expr) and isinstance(getattr(n.body[0].value, "value", None), str)
    ]
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT or any(a <= tok.start[0] <= b for a, b in docs):
            continue
        if HIT.search(tok.string):
            yield tok.start[0], tok.line.strip()


def text_hits(path):
    in_block = False
    for n, line in enumerate(path.read_text().splitlines(), 1):
        code = ""
        rest = line
        while rest:
            if in_block:
                end = rest.find("*/")
                rest, in_block = (rest[end + 2:], False) if end >= 0 else ("", True)
            else:
                start = rest.find("/*") if path.suffix != ".sh" else -1
                code += rest[:start] if start >= 0 else rest
                rest, in_block = (rest[start + 2:], True) if start >= 0 else ("", False)
        code = re.sub(r"(?<!:)//.*" if path.suffix != ".sh" else r"(^|\s)#.*", "", code)
        if HIT.search(code):
            yield n, line.strip()


def test_no_ticket_prefix_in_code():
    files = [
        p
        for pattern in ("agent-team/scripts/**/*", "mods/**/*", "install.sh")
        for p in REPO.glob(pattern)
        if p.suffix in (".py", ".ts", ".tsx", ".js", ".sh")
        and "node_modules" not in p.parts
        and not re.search(r"(^test_|\.test\.|^conftest)", p.name)
    ]
    hits = [
        f"{p.relative_to(REPO)}:{n}: {line}"
        for p in files
        for n, line in (python_hits(p) if p.suffix == ".py" else text_hits(p))
    ]
    assert not hits, "a ticket prefix is hardcoded in code; read it from project.md:\n" + "\n".join(hits)
