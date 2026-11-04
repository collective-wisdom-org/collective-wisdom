import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "release_notes", Path(__file__).with_name("release_notes.py")
)
release_notes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_notes)


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
