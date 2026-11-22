"""`cos_tick.py --next`: every plan line has its `next:` text (SKILL.md § Tick), and without the flag the plan is unchanged."""

import re

import pytest

import cos_tick
from test_cos_tick import AUTO_MERGE, AUTO_SPEC, BUILD, CHANGES, FRESH, NH, SPEC1, USER_MERGE, USER_SPEC, chief_of, queued, run, tk

ON_NOTICE = "notice:zz"
HELD_UP = {"rateLimitedAt": "2026-11-08T11:00:00Z"}
PAST, SOON = "2026-11-08T11:30:00Z", "2026-11-08T13:00:00Z"
FULL = {"ABC-1": BUILD, "ABC-2": tk("build", "c2"), "ABC-3": SPEC1, "ABC-4": tk("spec", "c4")}

# state, trigger, flags: one plan per line kind the tick can print
SCENARIOS = [
    ({"chiefThreadId": "new", "tickets": {}}, "user", []),
    ({"paused": True, "tickets": {}}, "user", ["--after-reads"]),
    ({"tickets": {"ABC-1": BUILD, "ABC-3": SPEC1}}, "user", []),
    ({"tickets": {"ABC-1": BUILD, "ABC-3": SPEC1}}, "notice:c1", []),
    ({"tickets": {"ABC-1": BUILD}}, "notice:thread:other", []),
    ({"tickets": {"ABC-1": BUILD}}, "status", []),
    ({"tickets": {}}, "start", []),
    ({"tickets": {"ABC-1": BUILD}}, "start", []),
    ({"tickets": {"ABC-1": BUILD}, "wakeTaskId": "w1"}, "wake", []),
    ({"tickets": {"ABC-1": {**BUILD, "provider": "claudeAgent"}}, **chief_of("cursor")}, "user", []),
    ({"tickets": {"ABC-1": BUILD}, "chiefProvider": {"threadId": "other", "provider": "x"}}, "user", []),
    ({"tickets": {"ABC-1": BUILD}, "takeover": {"startedAt": "2026-11-08T11:00:00Z", "mode": "take-over"}}, "user", []),
    # the act plan
    ({"tickets": {}}, "user", ["--after-reads"]),
    ({"tickets": {}, **FRESH}, "status", ["--after-reads"]),
    ({"tickets": FULL, **FRESH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": BUILD}, **FRESH, "noHands": NH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": BUILD}, **FRESH, "noHands": {**NH, "drain": "blocked ABC-1"}}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {}, **HELD_UP, "wakeTaskId": "w1", "wakeAt": PAST}, "wake", ["--after-reads"]),
    ({"tickets": {}, **HELD_UP, "wakeAt": PAST}, "wake", ["--after-reads"]),
    ({"tickets": {}, **HELD_UP, "wakeAt": SOON}, "user", ["--after-reads"]),
    # queued relays: every send, check, switch, wait and rebuild line
    ({"tickets": {"ABC-1": queued("build-queued", USER_SPEC, "1", approvalItemId="it1"), **FULL, "ABC-9": SPEC1}, **FRESH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": queued("build-queued", AUTO_SPEC, "1")}, **FRESH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": queued("merge-queued", USER_MERGE, "1", pr=5, headSha="a" * 40)}, **FRESH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": queued("merge-queued", AUTO_MERGE, "1", pr=5, headSha="b" * 40)}, **FRESH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": queued("build-queued", USER_SPEC, "1", approvalItemId="it1", parentThreadId="old")}, **FRESH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": {**tk("build-queued", "q1"), "queuedAt": "2026-11-08T01:00:00Z"}}, **FRESH}, ON_NOTICE, ["--after-reads"]),
    ({"tickets": {"ABC-1": queued("build-queued", CHANGES, "1", parentThreadId=None)}, **FRESH}, ON_NOTICE, ["--after-reads"]),
]
# Printed by no plan today: the generic `run` text is only the fallback for a script the table does not know.
NOT_PRINTED = {"run"}


def plan_and_next(tmp_path, capsys, state, trigger, flags):
    out = run(tmp_path, capsys, state, trigger, *flags, "--next")
    pairs, last = [], None
    for line in out:
        if line.startswith("next: "):
            pairs.append((last, line[6:]))
            last = None
        elif not line.startswith("filling-stopped: "):
            assert last is None, f"{last!r} has no next: line"
            last = line
    assert last is None, f"{last!r} has no next: line"
    return out, pairs


def test_every_plan_line_has_a_next_text_and_every_table_row_is_used(tmp_path, capsys):
    seen = set()
    for state, trigger, flags in SCENARIOS:
        _, pairs = plan_and_next(tmp_path, capsys, state, trigger, flags)
        assert pairs
        for line, text in pairs:
            seen.add(cos_tick.next_key(line))
            assert text and not re.search(r"\{[a-z_]+\}", text), (line, text)  # no format field left unfilled
    assert not set(cos_tick.NEXT) - seen - NOT_PRINTED


@pytest.mark.parametrize("state, trigger, flags", SCENARIOS)
def test_without_the_flag_the_plan_is_unchanged(tmp_path, capsys, state, trigger, flags):
    plain = run(tmp_path, capsys, state, trigger, *flags)
    flagged = run(tmp_path, capsys, state, trigger, *flags, "--next")
    assert [x.removesuffix(" --next") for x in flagged if not x.startswith(("next: ", "filling-stopped: "))] == plain
    assert not any(x.startswith(("next: ", "filling-stopped: ")) for x in plain)


@pytest.mark.parametrize(
    "line, has",
    [
        ("stop not-chief", ["State names <id> as Chief of Staff", "only when the user wrote", "gets no reply"]),
        ("stop paused", ["answer commands only"]),
        ("harness-mismatch ABC-5 child=claudeAgent chief=cursor", ["`ABC-5: <short title> runs on claudeAgent, not this thread's cursor. Say cancel 5 to stop it.`"]),
        ("child-read ABC-1 c1 afterPosition=7", ["cos_child_read.py ABC-1 c1 --after 7", "fallbacks.md § Child read"]),
        ("pending c1", ["t3_pending_request", "Never answer the request yourself"]),
        ("run python3 ~/.collective-wisdom/scripts/cos_idle_check.py --store", ["fallbacks.md § Idle check", "takes no stdin"]),
        ("run python3 ~/.collective-wisdom/scripts/no_hands.py check", ["`action:` line", "the `start-todo` lines below are not run"]),
        ("run python3 ~/.collective-wisdom/scripts/cos_rotation_check.py", ["last Bash call of every turn"]),
        ("head-check ABC-1 pr=5 head=aaa", ["cos_head_check.py ABC-1 --next"]),
        ('user-check ABC-1 th9 it1 words="x"', ["cos_user_check.py item th9 it1", "Exit 1", "Exit 2", "User check script unavailable"]),
        ("configure q1 build", ["`t3_thread_configure` on q1", "`build` role's `modelSelection`"]),
        ("send ABC-1 build \"x\"", ["stage` op to `build`", "I may not hear when this run ends"]),
        ("merge-wait ABC-1", ["cos_merge_wait.py ABC-1 --next", "unmatched", "On Cursor skip it"]),
        ("run-wait ABC-1", ["cos_run_wait.py ABC-1 --next", "timeout: 7200000"]),
        ("rebuild-relay ABC-1", ["startup.md § State rebuild"]),
        ("continuation ABC-1 build", ["continuation.md § Continuation child", "no \"I may not hear\""]),
    ],
)
def test_next_texts_carry_the_rule_with_the_line_filled_in(line, has):
    text = cos_tick.next_text(line)
    assert text and all(x in text for x in has)
