"""`cos_rotation_check.py --next`: every line the check can print has its `next:` text (rotation.md § Thread rotation) or is judgement-only."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from test_cos_rotation_check import CLAUDE, GANTT, NEW, NOW, OLD, QUEUED, ago, crc

# (state, context tokens, commit, branch, line printed, words in the next: text, words it must not hold)
CASES = [
    ({}, 40_000, OLD, "main", "ok context=40k", ["Nothing."], []),
    ({}, None, OLD, "main", "ok (size unknown on Cursor)", ["Nothing."], []),
    ({}, 231_000, OLD, "main", "rotate: size 231k >= 220k; mode reset", ["gantt_plugin.py", "agent-gantt plugin: <text>", "0. Write `.agent-team/chief-notes.md`"], []),
    ({}, 40_000, NEW, "main", "rotate: skill changed aaaaaaa..bbbbbbb; mode reset", ["gantt_plugin.py"], []),
    ({"paused": True}, 231_000, OLD, "main", "ok (held: paused)", ["Never reset in the middle of a command"], ["gantt_plugin.py"]),
    ({"reset": {"id": "0a1b2c3d", "startedAt": ago(1)}}, 231_000, OLD, "main", "ok (held: reset)", ["Never reset in the middle of a command"], []),
    ({"takeover": {"startedAt": ago(7), "mode": "take-over"}}, 40_000, OLD, "main", "finish: take over unfinished since 7m; mode take-over",
     ["rotation.md § Thread rotation: Finish take over", "message that woke this turn"], []),
    ({"skillCommit": None}, 40_000, NEW, "main", f"ok; set skillCommit {NEW}", ["Save that sha as `skillCommit`", "Don't reset"], []),
    ({"skillCommit": "8ddace1"}, 40_000, NEW, "main", f"ok; skillCommit is not a full sha; set skillCommit {NEW}", ["Save that sha as `skillCommit`"], []),
    (QUEUED, 40_000, NEW, "main", "ok (skill change waits: queued CW-9)", ["the first quiet turn resets"], []),
    ({**GANTT, **QUEUED}, 40_000, OLD, "main", "ok (plugin change waits: queued CW-9)", ["the first quiet turn resets"], []),
    ({"takeoverContext": {"threadId": "T1", "tokens": 230_000}}, 230_000, OLD, "main", "ok (size trigger off: take-over ended at 230k)", ["Nothing"], []),
]
SUFFIXES = [
    ("; take-over context=150k", ["Take-over context is 150k", "`Take-over context 150k.`"], ["Reset did not shrink"]),
    ("; take-over context=230k", ["Reset did not shrink the context"], []),
    ("; take-over context=230k (turn 4)", ["Take-over context is 230k", "Reset did not shrink the context"], []),
    ("; take-over context pending (turn 4)", ["`Take-over context pending.`", "`take-over context=<K>k (turn 4)`"], []),
]


def decide(state, context, commit, branch):
    state = {"skillCommit": OLD, "chiefThreadId": "T1", "chiefProvider": CLAUDE, **state}
    plugin = state.pop("plugin", None)
    return crc.decide(state, context, NOW, commit, branch, plugin=plugin)


@pytest.mark.parametrize("state, context, commit, branch, line, has, lacks", CASES)
def test_each_line_the_check_prints_has_its_next(state, context, commit, branch, line, has, lacks):
    got = decide(state, context, commit, branch)
    assert got == line
    text = crc.next_text(got)
    assert text and all(x in text for x in has) and not any(x in text for x in lacks)


@pytest.mark.parametrize("suffix, has, lacks", SUFFIXES)
def test_a_take_over_suffix_adds_its_step_to_the_line_text(suffix, has, lacks):
    base = "ok (size trigger off: take-over ended at 230k)"
    text = crc.next_text(base + suffix)
    assert text.startswith(crc.next_text(base)) and all(x in text for x in has) and not any(x in text for x in lacks)


@pytest.mark.parametrize("line", ["rotation-check: cannot read context", "ok context=40k; takeoverContext not saved"])
def test_judgement_only_lines_have_no_next(line):
    assert crc.next_text(line) is None


@pytest.mark.parametrize("flags", [[], ["--record-takeover"]])
def test_main_prints_next_after_the_line_and_nothing_else_changes(monkeypatch, capsys, tmp_path, flags):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"chiefThreadId": "T1", "chiefSessionId": "S9", "skillCommit": OLD, "tickets": {}, "chiefProvider": CLAUDE}))
    monkeypatch.setenv("COS_STATE_FILE", str(path))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "S9")
    monkeypatch.setattr(crc, "read_context", lambda sid=None, cursor=False: (231_000, datetime.now(timezone.utc) - timedelta(hours=1)))
    monkeypatch.setattr(crc, "skill_commit", lambda: OLD)
    monkeypatch.setattr(crc, "branch", lambda: "main")
    assert crc.main(flags) == 0
    plain = capsys.readouterr().out.splitlines()
    path.write_text(json.dumps({"chiefThreadId": "T1", "chiefSessionId": "S9", "skillCommit": OLD, "tickets": {}, "chiefProvider": CLAUDE}))
    assert crc.main([*flags, "--next"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[:-1] == plain and len(plain) == 1 and out[-1].startswith("next: ")
    # exit 2 prints its line and no next
    monkeypatch.setattr(crc, "read_context", lambda sid=None, cursor=False: (_ for _ in ()).throw(crc.Unreadable("context")))
    assert crc.main(["--next"]) == 2
    assert capsys.readouterr().out.splitlines() == ["rotation-check: cannot read context"]


# The reset steps in the `rotate:` text, by mode (rotation.md § Thread rotation points here)
RESETS = [
    ("rotate: size 231k >= 220k; mode reset", ["`t3_thread_send` to your own thread ID with `freshContext: true`", '"reason": "size 231k >= 220k"}', "`Resetting my context (size 231k >= 220k).`"], ["compact", "schedule_task"]),
    ("rotate: skill changed aaaaaaa..bbbbbbb; mode reset-scheduled; reset never confirmed", ["one-shot `schedule_task`", "`freshSession`", '"reason": "skill changed aaaaaaa..bbbbbbb"}'], ["t3_thread_send"]),
    ("rotate: agent-gantt plugin 0.1.12 -> 0.1.13; mode compact", ['"mode": "compact"', "`/compact`", "CHIEF OF STAFF RESET <id>. Run /chief-of-staff take over."], ["freshContext: true`"]),
]


@pytest.mark.parametrize("line, has, lacks", RESETS)
def test_the_rotate_text_holds_the_reset_steps_for_its_mode(line, has, lacks):
    text = crc.next_text(line)
    assert all(x in text for x in has) and not any(x in text for x in lacks)
    assert all(x in text for x in ["0. Write `.agent-team/chief-notes.md`", "`Reset refused: <error>.", "`rotation-failed` sighting"])


@pytest.mark.parametrize(
    "line, report, has",
    [
        ("ok context=40k; take-over context=40k", "take-over", ["`Take-over done. <N> tickets in flight.`", "`Take-over context 40k.`", "`Notes: <first line of chief-notes.md>.`", "`Filling stopped: <reason>.`"]),
        ("ok context=40k", "resume", ["`Resumed. <N> tickets in flight.`", "still under an older thread", "failure line from startup.md § Dashboard"]),
        ("ok context=40k; takeoverContext not saved", "take-over", ["`Take-over done. <N> tickets in flight.`"]),
    ],
)
def test_a_pass_adds_its_one_line_report(line, report, has):
    text = crc.next_text(line, report)
    assert text and all(x in text for x in has)
    assert "Take-over done" not in (crc.next_text(line) or "") and "Resumed." not in (crc.next_text(line) or "")


def test_reset_steps_flag_prints_the_reset_for_each_mode(capsys):
    """The exit-2 item-count fallback runs `--reset-steps <mode>`: gantt first, then the mode's reset, exit 0."""
    from cos_rotation_check import main
    for mode, send in (("reset", "freshContext: true"), ("reset-scheduled", "schedule_task"), ("compact", "/compact")):
        assert main(["--reset-steps", mode]) == 0
        out = capsys.readouterr().out
        assert "gantt_plugin.py" in out and "0. Write" in out and send in out
