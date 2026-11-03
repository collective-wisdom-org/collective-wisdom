"""Keep the tracker adapters and the skills in step.

1. Each adapter doc has a `### `op`` heading for every operation in trackers/README.md.
2. Skills, role docs and templates name no tracker-specific tool.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TRACKERS = ROOT / "docs" / "agents" / "trackers"
ADAPTERS = ["linear.md", "github.md", "jira.md"]

FORBIDDEN = [
    "save_issue",
    "list_issues",
    "get_issue",
    "save_comment",
    "list_comments",
    "list_issue_labels",
    "create_issue_label",
    "searchJiraIssuesUsingJql",
    "getJiraIssue",
    "editJiraIssue",
    "createJiraIssue",
    "transitionJiraIssue",
    "listJiraIssueTransitions",
    "listJiraIssueComments",
    "addOrEditJiraIssueComment",
    "listJiraIssueLinkTypes",
    "createJiraIssueLink",
    "mcp__linear",
    "mcp__atlassian",
]


def operations():
    ops = []
    text = (TRACKERS / "README.md").read_text()
    section = text.split("\n## Operations\n", 1)[1].split("\n## ", 1)[0]
    for line in section.splitlines():
        m = re.match(r"\|\s*((?:`[a-z-]+`(?:,\s*)?)+)\s*\|", line)
        if m:
            ops += re.findall(r"`([a-z-]+)`", m.group(1))
    return ops


def test_readme_lists_the_operations():
    ops = operations()
    assert len(ops) == len(set(ops))
    assert {"list-tickets", "set-state", "comment", "ensure-labels"} <= set(ops)


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_adapter_covers_every_operation(adapter):
    text = (TRACKERS / adapter).read_text()
    headings = set(re.findall(r"^### `([a-z-]+)`", text, re.M))
    missing = [op for op in operations() if op not in headings]
    assert not missing, f"{adapter} has no section for: {', '.join(missing)}"


def scanned_files():
    files = list((ROOT / ".claude" / "skills").rglob("*.md"))
    files += (ROOT / "docs" / "agents").glob("*.md")
    files += (ROOT / "templates").glob("*")
    return sorted(f for f in files if f.is_file())


def test_skills_and_docs_name_no_tracker_tool():
    hits = []
    for f in scanned_files():
        for n, line in enumerate(f.read_text().splitlines(), 1):
            for name in FORBIDDEN:
                if name in line:
                    hits.append(f"{f.relative_to(ROOT)}:{n}: {name}")
    assert not hits, "tracker tool names outside trackers/:\n" + "\n".join(hits)


UNSAFE_FLAG = re.compile(
    r"(?:--(?:body|title|search|description)(?:\s+|=)|\s-[btS]\s+)\""
)


def command_lines(text):
    """Lines inside fenced blocks, plus inline-code spans that hold a command."""
    lines = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif in_fence:
            lines.append(line)
        else:
            lines += [s for s in re.findall(r"`([^`]+)`", line) if "gh.sh" in s]
    return lines


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_adapter_puts_no_free_text_in_double_quotes(adapter):
    text = (TRACKERS / adapter).read_text()
    hits = []
    for line in command_lines(text):
        if UNSAFE_FLAG.search(line):
            hits.append(line.strip())
        for quoted in re.findall(r'"[^"]*"', line):
            if "$(" in quoted or "`" in quoted:
                hits.append(line.strip())
    assert not hits, f"{adapter}: free text in double quotes:\n" + "\n".join(hits)


@pytest.mark.parametrize(
    "line",
    [
        'gh issue create --body "x"',
        'gh issue create --body="x"',
        'gh issue create --title="x"',
        'gh issue create --title "x"',
        'gh issue create -b "x"',
        'gh issue create -t "x"',
        'gh issue list -S "x"',
        'gh issue list --search "x"',
        'gh issue list --search="x"',
    ],
)
def test_unsafe_flag_catches_double_quoted_forms(line):
    assert UNSAFE_FLAG.search(line)


@pytest.mark.parametrize(
    "line",
    [
        "gh issue create --title 'x' --body-file -",
        "gh issue list -S 'x'",
        "gh issue list --label \"x\"",
    ],
)
def test_unsafe_flag_allows_safe_forms(line):
    assert not UNSAFE_FLAG.search(line)


def test_readme_states_the_shell_safety_rule():
    text = (TRACKERS / "README.md").read_text()
    assert "## Shell safety" in text
    section = text.split("## Shell safety", 1)[1].split("\n## ", 1)[0]
    assert "untrusted" in section.lower()
    assert "--body-file -" in section
    assert "heredoc" in section
    assert "single quotes" in section
    assert "double-quoted" in section
