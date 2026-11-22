"""`cos_rotation_check.py --next`: every line the check can print has its `next:` text (rotation.md § Thread rotation) or is judgement-only."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from test_cos_rotation_check import CLAUDE, GANTT, NEW, NOW, OLD, QUEUED, ago, crc

# (state, context tokens, commit, branch, line printed, words in the next: text, words it must not hold)
CASES = [
    ({}, 40_000, OLD, "main", "ok context=40k", ["Nothing."], []),
    ({}, None, OLD, "main", "ok (size unknown on Cursor)", ["Nothing."], []),
    ({}, 231_000, OLD, "main", "rotate: size 231k >= 220k; mode reset", ["gantt_plugin.py", "agent-gantt plugin: <text>", "rotation.md § Thread rotation"], []),
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
