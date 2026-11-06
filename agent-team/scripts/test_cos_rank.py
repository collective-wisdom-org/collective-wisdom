import importlib.util
import io
import json
from pathlib import Path

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cos_rank = load("cos_rank")

STARTED = "2026-11-02T10:00:00Z"
STATE = {"tickets": {"ABC-7": {"stage": "build"}}, "merged": {}, "retiredThreads": [], "pm": {"rankedAt": "old"}}


def entry(n=1, readiness="ready", **kw):
    return {"id": f"ABC-{n}", "title": "t", "reason": "r", "readiness": readiness,
            "priority": "High", "createdAt": "2026-10-30T10:00:00Z", **kw}


def run(tmp_path, monkeypatch, body, started=STARTED, extra=()):
    path = tmp_path / "state.json"
    path.write_text(json.dumps(STATE))
    before = path.read_bytes()
    monkeypatch.setattr("sys.stdin", io.StringIO(body))
    code = cos_rank.main(["--file", str(path), "--started", started, *extra])
    return code, before, path


@pytest.mark.parametrize("body,started,code", [
    (json.dumps([entry(n) for n in range(1, 6)] + [entry(n, "held: PR #9") for n in range(10, 15)]), STARTED, 0),
    ("noise\n```json\n[]\n```\nmore\n```json\n" + json.dumps([entry()]) + "\n```\n", STARTED, 0),
    ("not json", STARTED, 2),
    ('{"id": "ABC-1"}', STARTED, 2),
    (json.dumps([{k: v for k, v in entry().items() if k != "reason"}]), STARTED, 2),
    (json.dumps([entry(extra=1)]), STARTED, 2),
    (json.dumps([entry(id="abc-1")]), STARTED, 2),
    (json.dumps([entry(1), entry(1)]), STARTED, 2),
    (json.dumps([entry(7)]), STARTED, 2),
    (json.dumps([entry(reason="a\nb")]), STARTED, 2),
    (json.dumps([entry(readiness="maybe")]), STARTED, 2),
    (json.dumps([entry(readiness="needs: ")]), STARTED, 2),
    (json.dumps([entry(priority="Critical")]), STARTED, 2),
    (json.dumps([entry(createdAt="yesterday")]), STARTED, 2),
    (json.dumps([entry(n) for n in range(1, 7)]), STARTED, 2),
    (json.dumps([entry(n, "held: x") for n in range(1, 7)]), STARTED, 2),
    ("[]", "2026-11-02", 2),
    ("[]", "2999-01-01T00:00:00Z", 2),
])
def test_ranking_shape_check(tmp_path, monkeypatch, capsys, body, started, code):
    got, before, path = run(tmp_path, monkeypatch, body, started)
    assert got == code
    if code:
        assert capsys.readouterr().out.startswith("cos_rank: ")
        assert path.read_bytes() == before
    else:
        pm = json.loads(path.read_text())["pm"]
        assert pm["rankedAt"] == STARTED
        assert pm["ranked"] == json.loads(cos_rank.FENCE.findall(body)[-1] if "```" in body else body)


@pytest.mark.parametrize("body,extra,code,msg", [
    ("[]", [], 3, "cos_rank: empty ranking, count the Backlog"),
    ("[]", ["--backlog-count", "0"], 0, ""),
    ("[]", ["--backlog-count", "3"], 2, "3 rankable tickets"),
    (json.dumps([entry()]), ["--backlog-count", "0"], 0, ""),
    ("[]", ["--backlog-count", "-1"], 2, "cos_rank: bad --backlog-count"),
    ("[]", ["--backlog-count", "abc"], 2, "cos_rank: bad --backlog-count"),
])
def test_empty_ranking_needs_backlog_count(tmp_path, monkeypatch, capsys, body, extra, code, msg):
    got, before, path = run(tmp_path, monkeypatch, body, extra=extra)
    assert got == code
    out = capsys.readouterr().out
    if code:
        assert msg in out
        assert path.read_bytes() == before
    else:
        pm = json.loads(path.read_text())["pm"]
        assert pm["rankedAt"] == STARTED
        assert pm["ranked"] == json.loads(body)
        assert pm["rankedReady"] is bool(json.loads(body))


def test_ranked_ready_comes_from_entries(tmp_path, monkeypatch):
    for ranked, ready in (([entry(1, "needs: why"), entry(2, "held: PR #9")], False), ([entry(1, "needs: why"), entry(2)], True)):
        _, _, path = run(tmp_path, monkeypatch, json.dumps(ranked))
        assert json.loads(path.read_text())["pm"]["rankedReady"] is ready
