import importlib.util
import json
import sqlite3
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


# usage is the Value cell of the user.md subscription row; None leaves the row out.
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
def test_ticket_line(tmp_path, capsys, monkeypatch, user_md, ticket, usage, want):
    user_md("me", usage)
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


def cursor_store(proj, aid, msgs, runs, ref, results=None):
    """Write a Cursor index.db (only the columns agent_usage reads) and transcript for one agent. results (turn number to result text) adds a result column."""
    store = proj / "sdk-agent-store" / aid
    store.mkdir(parents=True)
    db = sqlite3.connect(store / "index.db")
    db.execute("create table agents (agent_id, workspace_ref)")
    db.execute(f"create table runs (agent_id, turn_number, model, usage_json, started_at, created_at{', result' * (results is not None)})")
    db.execute("insert into agents values (?, ?)", (aid, str(ref)))
    for t, m, u, ts in runs:
        row = (aid, t, m, u and json.dumps(u), ts, ts) + ((results.get(t, ""),) if results is not None else ())
        db.execute(f"insert into runs values ({','.join('?' * len(row))})", row)
    db.commit()
    db.close()
    (proj / "agent-transcripts" / aid).mkdir(parents=True)
    wrap = lambda m: {"role": "user", "message": {"content": [{"type": "text", "text": f"<user_query>\n{m}\n</user_query>"}]}}
    (proj / "agent-transcripts" / aid / f"{aid}.jsonl").write_text("\n".join(json.dumps(wrap(m)) for m in msgs))


OPUS, T0, T1 = "claude-opus-5-5", "2026-11-01T10:01:00Z", "2026-11-01T10:31:00Z"
# Opus: 1.5M input less 0.5M of cache is 1M at $4, 40k out at $20, 400k read at $0.20, 100k written at $5 (5 minute rate): $5.38.
PRICED = {"inputTokens": 1_500_000, "cacheReadTokens": 400_000, "cacheWriteTokens": 100_000, "outputTokens": 40_000}
HERE = "Branch: feat/cw-57-foo. Create it yourself."
BOTH = "cost $9.38 API-equivalent (0.40% of the subscription), Cursor $5.38, 2.5M tokens, spec $9.38 / build $0.00 / merge $0.00, 2 child runs, wall 0h 30m"
ONLY_CLAUDE = "cost $4.00 API-equivalent (0.40% of the subscription), 1.0M tokens, spec $4.00 / build $0.00 / merge $0.00, 1 child run, wall 0h 00m"


# Each session is (messages, runs, workspace); claude says whether a Claude Code session ($4.00) ran feat/cw-57-foo too.
@pytest.mark.parametrize(
    "claude, sessions, bad, want",
    [
        # a cancelled run (no usage) adds nothing
        (True, [([HERE], [(1, "default", None, T0), (2, OPUS, PRICED, T1)], "/none")], False, BOTH),
        # an unreadable store may hold this ticket's work: the cost is unknown, not lower
        (True, [([HERE], [(2, OPUS, PRICED, T1)], "/none")], True,
         "cost unknown (cannot read a Cursor store; $9.38 priced), 2.5M tokens, spec $9.38 / build $0.00 / merge $0.00, 2 child runs, wall 0h 30m"),
        # the branch only from git in the workspace
        (True, [(["go"], [(2, OPUS, PRICED, T1)], "git")], False, BOTH),
        # a run with no price, or no model, makes the whole cost unknown but keeps the priced dollars
        (True, [([HERE], [(2, OPUS, PRICED, T1), (3, "gemini-4-argon", {"inputTokens": 100_000}, T1), (4, None, {"inputTokens": 100_000}, T1)], "/none")], False,
         "cost unknown (no price for gemini-4-argon, unknown model; $9.38 priced), 2.7M tokens, spec $9.38 / build $0.00 / merge $0.00, 2 child runs, wall 0h 30m"),
        # each routed Cursor model gives dollars, not cost unknown: 1M input at the input rate, 40k out, 400k read, 100k written at the input rate
        (False, [([HERE], [(1, "grok-4.7", PRICED, T1)], "/none")], False,
         "cost $2.64 API-equivalent (0.00% of the subscription), Cursor $2.64, 1.5M tokens, spec $2.64 / build $0.00 / merge $0.00, 1 child run, wall 0h 00m"),
        (False, [([HERE], [(1, "composer-2.5", PRICED, T1)], "/none")], False,
         "cost $0.73 API-equivalent (0.00% of the subscription), Cursor $0.73, 1.5M tokens, spec $0.73 / build $0.00 / merge $0.00, 1 child run, wall 0h 00m"),
        (True, [(["Branch: feat/cw-570-x"], [(2, OPUS, PRICED, T1)], "/none")], False, ONLY_CLAUDE),
        (False, [(["Branch: feat/cw-570-x"], [(2, OPUS, PRICED, T1)], "/none")], False, 2),
        # an unreadable store does not give a ticket with no session a cost: no_hands relies on exit 2 for it
        (False, [(["Branch: feat/cw-570-x"], [(2, OPUS, PRICED, T1)], "/none")], True, 2),
        # a relay in turn 2 puts turn 1 in spec and turns 2 and 3 in build; 200k input is $0.80 a run
        (False, [([HERE, "CHIEF OF STAFF: the user approved the spec", "go"], [(n, OPUS, {"inputTokens": 200_000}, T1) for n in (1, 2, 3)], "/none")], False,
         "cost $2.40 API-equivalent (0.00% of the subscription), Cursor $2.40, 0.6M tokens, spec $0.80 / build $1.60 / merge $0.00, 1 child run, wall 0h 00m"),
    ],
)
def test_ticket_line_with_cursor(tmp_path, capsys, monkeypatch, user_md, claude, sessions, bad, want):
    user_md("me", "`1000`")
    wt = tmp_path / f"-Users-x--t3-worktrees-{agent_usage.PROJECT}-t3-aaa"
    wt.mkdir()
    if claude:
        (wt / "s1.jsonl").write_text(asst(T0, "feat/cw-57-foo", "r1", 1_000_000))
    ws = tmp_path / "ws"
    subprocess.run(["git", "init", "-q", "-b", "feat/cw-57-foo", str(ws)], check=True)
    cur = tmp_path / "cursor" / wt.name
    for i, (msgs, runs, ref) in enumerate(sessions):
        cursor_store(cur, f"agent-{i}", msgs, runs, ws if ref == "git" else ref)
    if bad:
        (cur / "sdk-agent-store" / "bad").mkdir()
        (cur / "sdk-agent-store" / "bad" / "index.db").write_text("not a database")
    argv = ["agent_usage", "--projects", str(tmp_path), "--cursor-projects", str(tmp_path / "cursor"), "--ticket", "CW-57"]
    monkeypatch.setattr(sys, "argv", argv)
    if want == 2:
        with pytest.raises(SystemExit) as e:
            agent_usage.main()
        assert e.value.code == 2
        return
    agent_usage.main()
    out, err = capsys.readouterr()
    assert out.strip() == want
    assert ("cannot read" in err) == bad


# --cursor-agent: stores hold agent-1 (runs given out of turn order, with results) and agent-2 (no result column); want is the (runs, results) printed, or 2 for an exit 2.
MS0, MS1 = 1_793_527_260_000, 1_793_529_060_000  # T0 and T1 in ms since epoch
@pytest.mark.parametrize(
    "agent, extra, want",
    [
        # turn order, input net of cache, an unpriced or missing model kept, a run without usage left out of runs;
        # results in turn order from every run: turn 3 has a result and no usage (kept), turn 2 has an empty result (left out)
        ("agent-1", None, ([
            {"at": MS0, "model": OPUS, "input": 1_000_000, "output": 40_000, "read": 400_000, "write": 100_000},
            {"at": MS1, "model": None, "input": 100_000, "output": 0, "read": 0, "write": 0},
        ], ["first reply", "third reply"])),
        ("agent-3", None, 2),
        # an unreadable store might hold the agent
        ("agent-3", "bad store", 2),
        # an unreadable store beside the one that has the agent changes nothing; a store without a result column gives no results
        ("agent-2", "bad store", ([{"at": MS0, "model": "gemini-4-argon", "input": 5, "output": 0, "read": 0, "write": 0}], [])),
        ("agent-4", "bad usage", 2),
        ("../agent-1", None, 2),
    ],
)
def test_cursor_agent(tmp_path, capsys, monkeypatch, agent, extra, want):
    cur = tmp_path / "cursor" / "proj"
    cursor_store(cur, "agent-1", ["go"], [(2, None, {"inputTokens": 100_000}, T1), (3, "default", None, T1), (1, OPUS, PRICED, T0)], "/none", {1: "first reply", 2: "", 3: "third reply"})
    cursor_store(tmp_path / "cursor" / "other", "agent-2", ["go"], [(1, "gemini-4-argon", {"inputTokens": 5}, T0)], "/none")
    if extra == "bad store":
        (cur / "sdk-agent-store" / "bad").mkdir()
        (cur / "sdk-agent-store" / "bad" / "index.db").write_text("not a database")
    if extra == "bad usage":
        cursor_store(cur, "agent-4", ["go"], [(1, OPUS, 5, T0)], "/none")
    monkeypatch.setattr(sys, "argv", ["agent_usage", "--cursor-projects", str(tmp_path / "cursor"), "--cursor-agent", agent])
    if want == 2:
        with pytest.raises(SystemExit) as e:
            agent_usage.main()
        assert e.value.code == 2
        assert capsys.readouterr().out == ""
        return
    agent_usage.main()
    assert json.loads(capsys.readouterr().out) == {"runs": want[0], "results": want[1]}
