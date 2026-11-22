"""`cos_peer.py --next`: every result of find, check and reply has its `next:` step, and without the lines the output is the old output."""

import io
import json

import pytest

from test_cos_peer import CHECK, FIND, GOOD, HEAD, REPLY, SRC, TICKET, check_env, cos_peer, make_store, project, request, write_state


def split(out):
    """(result lines, next lines): a `next:` line and the indented lines after it belong to the step."""
    lines = out.splitlines()
    nxt = [i for i, x in enumerate(lines) if x.startswith("next: ")]
    assert len(nxt) <= 1
    step = []
    if nxt:
        step = [lines[nxt[0]]] + [x for x in lines[nxt[0] + 1:] if x.startswith("  ")]
    return [x for x in lines if x not in step], step


@pytest.mark.parametrize("name, code, out", FIND)
def test_find_next(tmp_path, monkeypatch, capsys, name, code, out):
    roots = {n: tmp_path / n for n in ("mail", "app", "api", "ui", "nostate", "nullchief", "elsewhere", "archived")}
    for n, chief in (("mail", "c1"), ("app", "c0"), ("api", "c2"), ("ui", "c3"), ("nullchief", None), ("elsewhere", "c1"), ("archived", "c6")):
        write_state(roots[n], chiefThreadId=chief)
    projects = [project("p1", "Acme Mail", "acme/mail", roots["mail"]), project("p0", "Example", "example/app", roots["app"]),
                project("p2", "Widget Shop", "acme/widget-api", roots["api"]), project("p3", "Widget Studio", "acme/widget-ui", roots["ui"]),
                project("p4", "No State", "acme/nostate", roots["nostate"]), project("p5", "Null Chief", "acme/nullchief", roots["nullchief"]),
                project("p6", "Elsewhere", "acme/elsewhere", roots["elsewhere"]), project("p7", "Archived", "acme/archived", roots["archived"])]
    db = make_store(tmp_path, [("c1", "p1", None, None), ("c0", "p0", None, None), ("c2", "p2", None, None), ("c3", "p3", None, None), ("c6", "p7", "2026-11-01", None)], [])
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"projects": projects})))
    assert cos_peer.main(["--db", str(db), "find", "--next", name]) == code
    result, step = split(capsys.readouterr().out)
    assert result == [out] and step
    if out.startswith("target"):
        assert "to thread c1" in step[0] and "CHIEF OF STAFF REQUEST from <this thread's id> (example/app)" in step[1] and "For: acme/mail" in step[2]
    if out.startswith("ambiguous"):
        assert "ask which repo" in step[0]


@pytest.mark.parametrize("sender, item, words, code, out", CHECK)
def test_check_next(tmp_path, capsys, sender, item, words, code, out):
    db = check_env(tmp_path, [("req", "me", request(sender, item, words) if words else "hello")])
    assert cos_peer.main(["--db", str(db), "check", "--next", "--thread", "me", "--item", "req"]) == code
    result, step = split(capsys.readouterr().out)
    assert step and "\n".join(result) == out
    if out.startswith("accept"):
        assert step[0].startswith("next: start a ticket-helper.md § Ticket helper")
    else:  # a refusal replies to the sender only when the sender was verified
        reason = out.removeprefix("refuse: ")
        assert ("send the sender one message" in step[0]) == (reason in ("same repo", "not for this repo") or reason.startswith("command:"))


def test_accept_puts_the_step_before_the_stored_words(tmp_path, capsys):
    db = check_env(tmp_path, [("req", "me", request("cs", "u1", GOOD))])
    assert cos_peer.main(["--db", str(db), "check", "--next", "--thread", "me", "--item", "req"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "accept cs u1 Sender" and lines[1].startswith("next: ") and lines[-1] == GOOD


@pytest.mark.parametrize("text, code, out", REPLY)
def test_reply_next(tmp_path, capsys, text, code, out):
    root = write_state(tmp_path / "receiver", chiefThreadId="r1")
    db = make_store(tmp_path, [("r1", "pr", None, None), ("child", "pr", None, None), ("n1", "pn", None, None)],
                    [("pr", "Receiver", root), ("pn", "Stateless", str(tmp_path / "no-state"))], [("rep", "me", "agent", text)])
    assert cos_peer.main(["--db", str(db), "reply", "--next", "--thread", "me", "--item", "rep"]) == code
    result, step = split(capsys.readouterr().out)
    assert "\n".join(result) == out and len(step) == 1
    assert ("had nothing usable" in step[0]) == (code == 1) and ("Receiver" in step[0]) == (code == 0)


def test_same_repo_refusal_replies_to_the_sender(tmp_path, capsys):
    db = check_env(tmp_path, [("req", "sib", request("cs", "u1", GOOD))])
    assert cos_peer.main(["--db", str(db), "check", "--next", "--thread", "sib", "--item", "req"]) == 1
    result, step = split(capsys.readouterr().out)
    assert result == ["refuse: same repo"] and "`Item: u1`, `Refused: same repo`" in step[0]
