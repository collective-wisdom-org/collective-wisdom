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
    monkeypatch.setattr(release_notes, "file_merge_times", lambda: {})


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


LOG = (
    "\0" + "2026-11-04T08:00:00+02:00\n\ndocs/superpowers/release-notes/cw-2.md\ndocs/other.md\n"
    "\0" + "2026-11-03T19:30:00-06:00\n\ndocs/superpowers/release-notes/cw-2.md\ndocs/superpowers/release-notes/cw-1.md\n"
)


def test_parse_added_newest_add_wins_in_utc_inside_folder():
    got = release_notes.parse_added(LOG)
    assert {k: v.isoformat() for k, v in got.items()} == {
        "cw-2.md": "2026-11-04T06:00:00+00:00",
        "cw-1.md": "2026-11-04T01:30:00+00:00",
    }


def fail(*a, **k):
    raise OSError("no git")


@pytest.mark.parametrize("run", [fail, lambda *a, **k: type("P", (), {"returncode": 128, "stdout": "fatal"})])
def test_file_merge_times_is_empty_when_git_fails(monkeypatch, run):
    monkeypatch.setattr(release_notes.subprocess, "run", run)
    assert release_notes.file_merge_times() == {}


def file(n, day):
    return f"# {day} CW-{n}: f{n}\n\nbody\n"


@pytest.mark.parametrize(
    "files, times, prs, expected",
    [
        (  # merge time beats file name order
            {"cw-1.md": file(1, "2026-11-04"), "cw-2.md": file(2, "2026-11-04")},
            {"cw-1.md": "2026-11-04T09:00:00+00:00", "cw-2.md": "2026-11-04T08:00:00+00:00"},
            [],
            ["## 2026-11-04 CW-1: f1", "Merged 2026-11-04 09:00 UTC.", "## 2026-11-04 CW-2: f2", "Merged 2026-11-04 08:00 UTC."],
        ),
        (  # PR and file note on one day, ordered by time; the file's merge day wins over its heading day
            {"cw-1.md": file(1, "2026-11-03")},
            {"cw-1.md": "2026-11-04T09:00:00+00:00"},
            [pr(5, "fix: a", NOTE, "2026-11-04T10:15:00Z"), pr(6, "fix: b", NOTE, "2026-11-04T08:59:00Z")],
            [
                "## 2026-11-04 a (#5)", "Merged 2026-11-04 10:15 UTC.",
                "## 2026-11-03 CW-1: f1", "Merged 2026-11-04 09:00 UTC.",
                "## 2026-11-04 b (#6)", "Merged 2026-11-04 08:59 UTC.",
            ],
        ),
        (  # a file note without a merge time comes after timed notes of its day, with no Merged line
            {"cw-1.md": file(1, "2026-11-04"), "cw-2.md": file(2, "2026-11-04")},
            {"cw-1.md": "2026-11-04T01:00:00+00:00"},
            [pr(5, "fix: a", NOTE, "2026-11-04T00:30:00Z")],
            ["## 2026-11-04 CW-1: f1", "Merged 2026-11-04 01:00 UTC.", "## 2026-11-04 a (#5)", "Merged 2026-11-04 00:30 UTC.", "## 2026-11-04 CW-2: f2"],
        ),
    ],
)
def test_order_and_merged_line(tmp_path, monkeypatch, capsys, files, times, prs, expected):
    notes = tmp_path / "release-notes"
    notes.mkdir()
    for name, text in files.items():
        (notes / name).write_text(text)
    monkeypatch.setattr(release_notes, "NOTES", notes)
    monkeypatch.setattr(release_notes, "merged_prs", lambda: prs)
    monkeypatch.setattr(release_notes, "file_merge_times", lambda: {k: release_notes.utc(v) for k, v in times.items()})
    assert release_notes.main() == 0
    out = capsys.readouterr().out
    assert [l for l in out.splitlines() if l.startswith(("## ", "Merged "))] == expected
