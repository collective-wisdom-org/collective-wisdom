import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "agent_usage", Path(__file__).with_name("agent_usage.py")
)
agent_usage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent_usage)


def line(rid, ts, inp, cache_read, out=100):
    usage = {
        "input_tokens": inp,
        "cache_read_input_tokens": cache_read,
        "output_tokens": out,
    }
    return json.dumps(
        {
            "type": "assistant",
            "requestId": rid,
            "timestamp": ts,
            "message": {"model": "claude-opus-5-5", "usage": usage},
        }
    )


IN = "2026-11-01T10:00:00Z"


@pytest.mark.parametrize(
    "root_reqs, sub_ctx, want_n, want_ctx, want_avg",
    [
        # r1 appears twice (deduped); the subagent's 900k context must not count.
        (
            [("r1", IN, 10, 20_000), ("r1", IN, 10, 20_000), ("r2", IN, 10, 60_000)],
            900_000,
            2,
            "60k",
            0.010,
        ),
        # r2 is before --since: it counts toward neither requests nor max context.
        (
            [("r1", IN, 5, 5_000), ("r2", "2026-10-30T10:00:00Z", 5, 500_000)],
            900_000,
            1,
            "5k",
            0.003,
        ),
    ],
)
def test_turns_report_ignores_subagents(
    tmp_path, capsys, monkeypatch, root_reqs, sub_ctx, want_n, want_ctx, want_avg
):
    proj = tmp_path / f"-Users-x-Documents-{agent_usage.PROJECT}"
    (proj / "sess1" / "subagents").mkdir(parents=True)
    (proj / "sess1.jsonl").write_text(
        "\n".join(line(r, ts, i, c) for r, ts, i, c in root_reqs)
    )
    (proj / "sess1" / "subagents" / "agent-1.jsonl").write_text(
        line("s1", IN, 10, sub_ctx)
    )
    argv = ["agent_usage", "--projects", str(tmp_path), "--turns"]
    argv += ["--since", "2026-11-01T00:00:00Z", "--until", "2026-11-02T00:00:00Z"]
    monkeypatch.setattr(sys, "argv", argv)
    agent_usage.main()
    out = capsys.readouterr().out
    row = next(
        ln for ln in out.split("root sessions (turns)")[1].splitlines() if "root " in ln
    )
    cols = row.split()
    assert (int(cols[-4]), cols[-3], float(cols[-2])) == (
        want_n,
        want_ctx,
        pytest.approx(want_avg, abs=1e-3),
    )


def user(ts, content="hello"):
    msg = {"role": "user", "content": content}
    return json.dumps({"type": "user", "timestamp": ts, "message": msg})


SID = "aaaaaaaa-0000-4000-8000-000000000001"


@pytest.mark.parametrize(
    "mode, sid, want",
    [
        ("--context", SID, "context=120030 started=2026-11-01T10:01:00Z"),
        ("--context", None, 2),
        ("--context", "missing", 2),
        ("--context", "../" + SID, 2),
        # Stops at the second human message; the tool result does not end the turn.
        ("--turns", SID, "80k"),
    ],
)
def test_context_and_start_ctx(tmp_path, capsys, monkeypatch, mode, sid, want):
    proj = tmp_path / f"-Users-x-Documents-{agent_usage.PROJECT}"
    (proj / SID / "subagents").mkdir(parents=True)
    result = [{"type": "tool_result", "content": "ok"}]
    (proj / f"{SID}.jsonl").write_text(
        "\n".join(
            [
                user("2026-11-01T10:00:00Z"),
                line("r1", "2026-11-01T10:01:00Z", 10, 10_000),
                line("r2", "2026-11-01T10:02:00Z", 10, 50_000),
                user("2026-11-01T10:03:00Z", result),
                line("r3", "2026-11-01T10:04:00Z", 10, 80_000),
                user("2026-11-01T10:05:00Z"),
                line("r4", "2026-11-01T10:06:00Z", 30, 120_000),
            ]
        )
    )
    (proj / SID / "subagents" / "agent-1.jsonl").write_text(
        line("s1", "2026-11-01T10:07:00Z", 10, 900_000)
    )
    if sid:
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", sid)
    else:
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    argv = ["agent_usage", "--projects", str(tmp_path), mode]
    argv += ["--since", "2026-11-01T00:00:00Z", "--until", "2026-11-02T00:00:00Z"]
    monkeypatch.setattr(sys, "argv", argv)
    if want == 2:
        with pytest.raises(SystemExit) as e:
            agent_usage.main()
        assert e.value.code == 2
        return
    agent_usage.main()
    out = capsys.readouterr().out
    if mode == "--context":
        assert out.strip() == want
    else:
        table = out.split("root sessions (turns)")[1]
        row = next(ln for ln in table.splitlines() if "root " in ln)
        assert row.split()[-1] == want


@pytest.mark.parametrize("mode", ["main", "worktree", "no-git"])
def test_project_name_is_main_checkout_dir(tmp_path, mode):
    root = tmp_path / "myapp"
    (root / "scripts").mkdir(parents=True)
    script = root / "scripts" / "agent_usage.py"
    script.touch()
    if mode != "no-git":
        git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    if mode == "worktree":
        wt = tmp_path / "t3-ae642d70"
        subprocess.run([*git, "worktree", "add", "-q", str(wt)], check=True)
        (wt / "scripts").mkdir()
        script = wt / "scripts" / "agent_usage.py"
        script.touch()
    assert agent_usage.project_name(script.parent.parent) == "myapp"


def ev(ts, branch, **kw):
    # Compact separators, like Claude Code's transcripts; the --ticket pre-filter reads raw text.
    return json.dumps({"timestamp": ts, "gitBranch": branch, **kw}, separators=(",", ":"))


def asst(ts, branch, rid, tokens):
    usage = {"input_tokens": tokens}
    msg = {"model": "claude-opus-5-5", "usage": usage}
    return ev(ts, branch, type="assistant", requestId=rid, message=msg)


def human(ts, branch, content):
    return ev(ts, branch, type="user", message={"role": "user", "content": content})


# Opus input is $4 per million tokens, so 1_000_000 tokens cost $4.00.
TICKET_LINE = (
    "cost $19.20 API-equivalent, 4.8M tokens, spec $4.00 / build $14.00 / merge $1.20, "
    "2 child runs, wall 2h 03m"
)


def shared(pct):
    return TICKET_LINE.replace("API-equivalent,", f"API-equivalent ({pct} of the subscription),")


# usage is the Value cell of the project.md subscription row; None leaves the row out.
@pytest.mark.parametrize(
    "ticket, usage, want",
    [
        ("CW-57", None, TICKET_LINE),
        ("cw-57", None, TICKET_LINE),
        ("CW-57", "`12000`", shared("0.16%")),  # $19.20 of $12000
        ("CW-57", "`1000000`", shared("<0.01%")),
        ("CW-57", "`none`", TICKET_LINE),
        ("CW-57", "`0`", TICKET_LINE),
        ("CW-57", "`-5`", TICKET_LINE),
        ("CW-57", "`abc`", TICKET_LINE),
        ("CW-57", "`12,000`", TICKET_LINE),
        ("CW-99", None, 2),  # no sessions
        ("CW57", None, 2),  # not an ID
    ],
)
def test_ticket_line(tmp_path, capsys, monkeypatch, ticket, usage, want):
    cfg = tmp_path / "project.md"
    cfg.write_text("| Key | Value |\n|---|---|\n" + (f"| Claude subscription API-equivalent usage (dollars) | {usage} |\n" if usage else ""))
    monkeypatch.setenv("PROJECT_MD", str(cfg))
    t3, b = "t3/abc", "feat/cw-57-foo"
    wt = tmp_path / f"-Users-x--t3-worktrees-{agent_usage.PROJECT}-t3-aaa"
    (wt / "s1" / "subagents").mkdir(parents=True)
    # Spec on the t3 branch, approval relay, build on the feature branch, a subagent in build.
    (wt / "s1.jsonl").write_text("\n".join([
        human("2026-11-01T10:00:00Z", t3, "Run /ship-loop for CW-57"),
        asst("2026-11-01T10:01:00Z", t3, "r1", 1_000_000),
        human("2026-11-01T10:10:00Z", b, "CHIEF OF STAFF: the user approved the spec"),
        asst("2026-11-01T10:11:00Z", b, "r2", 2_000_000),
    ]))
    (wt / "s1" / "subagents" / "agent-1.jsonl").write_text(
        asst("2026-11-01T10:12:00Z", b, "s1", 500_000)
    )
    # A continuation child starts in build, then the merge approval moves it to merge.
    (wt / "s2.jsonl").write_text("\n".join([
        human("2026-11-01T11:00:00Z", "feat/cw-57", "Act as the implementation sub-agent for this task. TEAM MODE. CONTINUE. Run /ship-loop. Do the build stage."),
        asst("2026-11-01T11:01:00Z", "feat/cw-57", "r3", 1_000_000),
        human("2026-11-01T12:00:00Z", "feat/cw-57", "CHIEF OF STAFF: the user approved the merge"),
        asst("2026-11-01T12:03:00Z", "feat/cw-57", "r4", 300_000),
    ]))
    # Neither of these belongs to CW-57: a longer number, and the root checkout.
    (wt / "s3.jsonl").write_text(asst("2026-11-01T10:00:00Z", "feat/cw-570-x", "r5", 9_000_000))
    root = tmp_path / f"-Users-x-Documents-{agent_usage.PROJECT}"
    root.mkdir()
    (root / "s4.jsonl").write_text(asst("2026-11-01T10:00:00Z", b, "r6", 9_000_000))
    monkeypatch.setattr(sys, "argv", ["agent_usage", "--projects", str(tmp_path), "--ticket", ticket])
    if want == 2:
        with pytest.raises(SystemExit) as e:
            agent_usage.main()
        assert e.value.code == 2
        assert capsys.readouterr().out == ""
        return
    agent_usage.main()
    assert capsys.readouterr().out.strip() == want


@pytest.mark.parametrize(
    "model, want",
    [
        # 1M tokens of each kind, with the cache writes split 1h and 5m: the dollars the old in-code table gave.
        ("claude-opus-5-5", 4 + 20 + 0.20 + 8 + 5),
        ("claude-sonnet-5-5", 2 + 10 + 0.20 + 4 + 2.5),
        ("claude-haiku-5", 0.10 + 0.50 + 0.01 + 0.20 + 0.125),
        ("claude-fable-1", 10 + 50 + 0.25 + 20 + 12.5),
    ],
)
def test_prices_json_prices_a_usage_as_before(model, want):
    m = 1_000_000
    usage = {
        "input_tokens": m,
        "output_tokens": m,
        "cache_read_input_tokens": m,
        "cache_creation": {"ephemeral_1h_input_tokens": m, "ephemeral_5m_input_tokens": m},
    }
    assert sum(agent_usage.costs(model, usage).values()) == pytest.approx(want)
