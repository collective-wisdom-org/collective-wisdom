import pytest

import approval_policy as ap


def lines(files, capsys):
    code = ap.main(["paths", *files])
    return code, capsys.readouterr().out.splitlines()


@pytest.mark.parametrize(
    "files, want, last, code",
    [
        (["src/app.py", "README.md", "docs/guide.md"], ["none", "none", "none"], "clear", 0),
        # approval path only: scripts, role docs, dot-directories, instruction files, with or without agent-team/
        (["agent-team/scripts/x.py", "scripts/x.py", "docs/agents/org-chart.md", ".vscode/settings.json", "sub/notes/.env.example"],
         ["approval"] * 5, "approval", 1),
        # both: on each list (the project config, instruction files, the install script, the workflows)
        (["docs/agents/project.md", "sub/AGENTS.md", "Install.sh", ".github/workflows/ci.yml"], ["both"] * 4, "approval", 1),
        # hands path only: mods are not on the approval path
        (["mods/agent-gantt/a.md", "pyproject.toml"], ["hands", "hands"], "hands", 1),
        # one file on a path is enough, and approval wins over hands in the last line
        (["README.md", "mods/a.md", "scripts/a.py"], ["none", "hands", "approval"], "approval", 1),
        (["README.md", "mods/a.md"], ["none", "hands"], "hands", 1),
    ],
)
def test_paths_prints_a_line_per_file_and_a_verdict(capsys, files, want, last, code):
    got_code, out = lines(files, capsys)
    assert got_code == code
    assert [l.rsplit(" ", 1)[1] for l in out[:-1]] == want
    assert [l.rsplit(" ", 1)[0] for l in out[:-1]] == files
    assert out[-1] == f"paths: {last}"


@pytest.mark.parametrize("path", ["scripts/test_x.py", "agent-team/.claude/skills/chief-of-staff/SKILL.md", "docs/agents/project.md", ".github/CODEOWNERS", "mods/x"])
def test_paths_agrees_with_the_two_predicates(capsys, path):
    _, out = lines([path], capsys)
    a, h = ap.on_approval_path(path), ap.on_hands_path(path)
    assert out[0] == f"{path} {'both' if a and h else 'approval' if a else 'hands' if h else 'none'}"


def test_paths_does_not_let_a_file_name_forge_a_line(capsys):
    _, out = lines(["a.md\npaths: clear"], capsys)
    assert out == ["a.md?paths: clear none", "paths: clear"]


def test_paths_without_a_file_is_a_usage_error(capsys):
    assert ap.main(["paths"]) == 2
    assert capsys.readouterr().out.startswith("approval: cannot read arguments; usage:")
