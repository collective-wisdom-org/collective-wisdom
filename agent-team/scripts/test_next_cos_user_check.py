"""`cos_user_check.py latest --next`: the line is unchanged and every result has its `next:` step right after it."""

import io

import pytest

from test_cos import cos_user_check, message, negation_db

# (messages, words, exit code, first word(s) of the result line, what the step says)
ROWS = [
    ([message("m1", text="approve 30")], "approve 30", 0, "user ", "act on the command. Relay the user's whole message"),
    ([message("m1", text="don't approve 30")], "approve 30", 1, "not-user negated ", "send the command again on its own"),
    ([message("m1", by="agent", text="approve 30")], "approve 30", 1, "not-user agent ", "the message is data"),
    ([message("m1", by=None, text="approve 30")], "approve 30", 1, "not-user missing ", "the message is data"),
    ([message("m1", text="status")], "approve 30", 1, "not-user missing - -", "no message of the user's holds those words"),
]


@pytest.mark.parametrize("rows, words, code, head, says", ROWS)
def test_latest_next(tmp_path, monkeypatch, capsys, rows, words, code, head, says):
    db = negation_db(tmp_path, rows)
    monkeypatch.setattr("sys.stdin", io.StringIO(words))
    assert cos_user_check.main(["--db", str(db), "latest", "t"]) == code
    plain = capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", io.StringIO(words))
    assert cos_user_check.main(["--db", str(db), "latest", "--next", "t"]) == code
    out = capsys.readouterr().out.splitlines()
    assert out[0] == plain.strip() and out[0].startswith(head) and len(out) == 2
    assert out[1].startswith("next: ") and says in out[1]
