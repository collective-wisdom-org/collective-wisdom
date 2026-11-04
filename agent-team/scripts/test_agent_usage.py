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
    assert agent_usage.project_name(script) == "myapp"
