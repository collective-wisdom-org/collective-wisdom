"""`cos_restart.py --next`: each action line has its `next:` text (SKILL.md § Child path, Stuck check); the text to send has none."""

import pytest

from test_cos_restart import run

ACTION = ("cancel:", "set:", "moving:", "cleanup:", "restart:")

# kwargs for test_cos_restart.run: one per kind of output
SCENARIOS = [
    {"run": "failed"},                                                              # send
    {"run": "running", "updated-at": "2026-11-08T11:00:00Z"},                       # send cancel, with a cancel: line
    {"parent": "old"},                                                              # continuation
    {"run": "completed", "wait": "2twice"},                                         # send with a cleanup: line
    {"restarts": {"build": 1}},                                                     # blocked
    {"restarts": {"build": 1}, "run": "running", "updated-at": "2026-11-08T11:00:00Z"},  # blocked after a cancel: line
    {"restarts": {"build": 1}, "run": "completed", "wait": "2twice"},               # unreadable, with a cleanup: line
    {"run": "completed", "marker": True},                                           # not-stuck
]


def split(out):
    """(line, next text or None) per output line outside the text to send, and the lines of that text."""
    rows, text, inside = [], [], False
    for i, line in enumerate(out):
        if line.startswith("next: "):
            continue
        if line == "---":
            inside = not inside
        elif inside:
            text.append(line)
        else:
            rows.append((line, out[i + 1][6:] if i + 1 < len(out) and out[i + 1].startswith("next: ") else None))
    return rows, text


@pytest.mark.parametrize("kw", SCENARIOS)
def test_every_action_line_has_its_next_and_nothing_else_does(tmp_path, capsys, monkeypatch, kw):
    code, out = run(tmp_path, capsys, monkeypatch, **kw, next=True)
    rows, text = split(out)
    assert code == 0 and rows
    for line, nxt in rows:
        if line == "---":
            assert nxt is None
        else:
            assert line.startswith(ACTION) and nxt, line
    assert not any(x.startswith("next: ") for x in text)


@pytest.mark.parametrize("kw", SCENARIOS)
def test_without_the_flag_the_output_is_unchanged(tmp_path, capsys, monkeypatch, kw):
    _, plain = run(tmp_path, capsys, monkeypatch, **kw)
    _, flagged = run(tmp_path, capsys, monkeypatch, **kw, next=True)
    assert [x for x in flagged if not x.startswith("next: ")] == plain


@pytest.mark.parametrize(
    "kw, last, has",
    [
        ({"run": "failed"}, "restart: send build", ["`t3_thread_send` the message between the two `---` lines", "start the run wait"]),
        ({"run": "running", "updated-at": "2026-11-08T11:00:00Z"}, "restart: send build cancel", ["`task_cancel(firstTaskId)` first"]),
        ({"parent": "old"}, "restart: continuation build", ["continuation.md § Continuation child", "in place of the send"]),
        ({"restarts": {"build": 1}}, "restart: blocked restarted already; last run failed", ["`stage` op to `blocked`", "no-hands.md § What drains or stops a run"]),
        ({"restarts": {"build": 1}, "run": "completed", "wait": "2twice"}, "restart: unreadable", ["Not blocked"]),
        ({"run": "completed", "marker": True}, "restart: not-stuck", ["no report line"]),
    ],
)
def test_next_text_of_the_last_line(tmp_path, capsys, monkeypatch, kw, last, has):
    _, out = run(tmp_path, capsys, monkeypatch, **kw, next=True)
    rows, _ = split(out)
    assert rows[-1][0] == last and all(x in rows[-1][1] for x in has)


def test_a_bad_call_prints_cannot_and_no_next(tmp_path, capsys, monkeypatch):
    code, out = run(tmp_path, capsys, monkeypatch, stage="build", run="completed", next=True)  # no --wait on a completed run
    assert code == 2 and out == ["restart: cannot judge a completed run with no marker without --wait"]
