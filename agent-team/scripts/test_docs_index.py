import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("docs_index", Path(__file__).with_name("docs_index.py"))
docs_index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs_index)


def test_table_is_built_from_the_doc_folders(tmp_path, monkeypatch, capsys):
    docs = {
        "specs/2026-11-04-a-design.md": "# A design\n",
        "plans/2026-11-04-a.md": "# A: Implementation Plan\n",
        "as-built/2026-11-04-a.md": "# As-built: A\n",
        "specs/2026-11-02-b-design.md": "# B design\n",
        "specs/notes.md": "# Loose notes\n",
        "plans/2026-11-05-c.md": "no heading\n",
    }
    for rel, text in docs.items():
        (tmp_path / rel).parent.mkdir(exist_ok=True, parents=True)
        (tmp_path / rel).write_text(text)
    monkeypatch.setattr(docs_index, "DOCS", tmp_path)
    docs_index.main()
    out, err = capsys.readouterr()
    assert out.splitlines()[2:] == [
        "| 2026-11-02 | Spec | [B design](specs/2026-11-02-b-design.md) |",
        "| 2026-11-04 | Spec | [A design](specs/2026-11-04-a-design.md) |",
        "| 2026-11-04 | Plan | [A: Implementation Plan](plans/2026-11-04-a.md) |",
        "| 2026-11-04 | As-built | [A](as-built/2026-11-04-a.md) |",
        "| 2026-11-05 | Plan | [2026-11-05-c.md](plans/2026-11-05-c.md) |",
        "|  | Spec | [Loose notes](specs/notes.md) |",
    ]
    assert err == "docs-index: specs/notes.md has no dated name\n"
