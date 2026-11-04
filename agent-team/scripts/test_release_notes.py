import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "release_notes", Path(__file__).with_name("release_notes.py")
)
release_notes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_notes)


@pytest.fixture(autouse=True)
def no_gh(monkeypatch):
    monkeypatch.setattr(release_notes, "merged_prs", lambda: [])


def test_print_order_and_undated_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(release_notes, "NOTES", tmp_path / "release-notes")
    release_notes.main()
    assert "No release notes yet." in capsys.readouterr().out  # folder missing

    notes = tmp_path / "release-notes"
    notes.mkdir()
    (notes / "cw-9.md").write_text("# 2026-11-03 CW-9: nine\n\nbody\n")
    (notes / "cw-13.md").write_text("# 2026-11-03 CW-13: thirteen\n")
    (notes / "cw-20.md").write_text("# 2026-11-05 CW-20: newest\n")
    (notes / "draft.md").write_text("no heading here\n")
    release_notes.main()
    out, err = capsys.readouterr()
    order = [l for l in out.splitlines() if l.startswith("## ") or l == "no heading here"]
    assert order == [
        "## 2026-11-05 CW-20: newest",
        "## 2026-11-03 CW-13: thirteen",
        "## 2026-11-03 CW-9: nine",
        "no heading here",
    ]
    assert err == "release-notes: draft.md has no dated heading\n"


def pr(n, title, body, at):
    return {"number": n, "title": title, "body": body, "mergedAt": at}


NOTE = "## Summary\n\nx\n\n## Release note\n\nA note.\n\n## Test plan\n\ny\n"
FILE = "# 2026-11-04 CW-2: file note\n\nbody\n"


def boom():
    raise RuntimeError("gh: not logged in")


@pytest.mark.parametrize(
    "files, prs, headings, code, err",
    [
        ({}, [pr(5, "feat(x): new thing", NOTE, "2026-11-04T23:30:00Z")], ["## 2026-11-04 new thing (#5)"], 0, ""),
        ({"cw-2.md": FILE}, [], ["## 2026-11-04 CW-2: file note"], 0, ""),
        (
            {"cw-2.md": FILE, "cw-1.md": "# 2026-11-06 CW-1: late\n"},
            [
                pr(5, "fix: older", NOTE, "2026-11-03T08:00:00Z"),
                pr(6, "docs: no note", "## Summary\n\nx\n", "2026-11-05T08:00:00Z"),
                pr(7, "docs: empty note", "## Release note\n\n## Test plan\n", "2026-11-05T08:00:00Z"),
                pr(8, "newest", NOTE, "2026-11-05T08:00:00Z"),
            ],
            ["## 2026-11-06 CW-1: late", "## 2026-11-05 newest (#8)", "## 2026-11-04 CW-2: file note", "## 2026-11-03 older (#5)"],
            0,
            "",
        ),
        ({"cw-2.md": FILE}, boom, ["## 2026-11-04 CW-2: file note"], 1, "release-notes: cannot read merged PRs: gh: not logged in\n"),
    ],
)
def test_prs_merge_with_files(tmp_path, monkeypatch, capsys, files, prs, headings, code, err):
    notes = tmp_path / "release-notes"
    notes.mkdir()
    for name, text in files.items():
        (notes / name).write_text(text)
    monkeypatch.setattr(release_notes, "NOTES", notes)
    monkeypatch.setattr(release_notes, "merged_prs", prs if prs is boom else lambda: prs)
    assert release_notes.main() == code
    out, got_err = capsys.readouterr()
    assert [l for l in out.splitlines() if l.startswith("## ")] == headings
    assert got_err == err
