#!/usr/bin/env python3
"""API-equivalent cost of the agent team, read from Claude Code transcripts and Cursor's run store.

Usage:
    ~/.collective-wisdom/scripts/agent_usage.py [--since ISO] [--until ISO] [--projects DIR] [--cursor-projects DIR] [--turns]
    ~/.collective-wisdom/scripts/agent_usage.py [--projects DIR] --context
    ~/.collective-wisdom/scripts/agent_usage.py [--projects DIR] [--cursor-projects DIR] --ticket <PREFIX>-N
    ~/.collective-wisdom/scripts/agent_usage.py [--cursor-projects DIR] --cursor-agent <agent id>

--since and --until are ISO 8601 UTC times (default: the last 24 hours).
--projects defaults to ~/.claude/projects, --cursor-projects to ~/.cursor/projects (a missing dir means no
Cursor runs). Read-only: the report writes nothing, and each Cursor sdk-agent-store/*/index.db opens read-only (SQLite may add empty -shm and -wal files beside it).
Cursor runs are priced from prices.json by model family: input minus cache tokens, output, cache read and the
5 minute cache write rate. A Cursor run on a model with no price is unpriced: its tokens count, its dollars do not.
--turns adds, per root-checkout session, its request count, its largest context
(prompt tokens in one request), its start ctx (largest context before the session's
first user message after the first request) and its average cost per request. Subagents are not counted.
--context prints one line for the session in $CLAUDE_CODE_SESSION_ID:
"context=<tokens of its last request> started=<time of its first request>".
It ignores --since and --until, prints no cost report, and exits 2 if the variable
is unset or the session has no transcript or no requests.
--ticket prints one line for that ticket's child threads: "cost $X API-equivalent,
N.NM tokens, spec $a / build $b / merge $c, K child runs, wall Hh MMm". It reads only
worktree sessions with a git branch <head><prefix>-N or <head><prefix>-N-..., where <head> is a head of the Branch pattern row,, plus their
subagents, ignores --since and --until, and exits 2 when no Claude Code or Cursor session ran the ticket.
A Cursor session's branch is the "Branch:" line of its first message, else the git branch of its workspace.
When the user's user.md sets a positive "Claude subscription API-equivalent usage", the cost reads "cost $X
API-equivalent (P% of the subscription), ..." with the share of the Claude Code dollars only. When the ticket
has Cursor runs the cost part adds ", Cursor $Y". When any Cursor run on the ticket is unpriced, or a Cursor
store cannot be read (once the ticket has a session) or a run of the ticket's session cannot be parsed, the line is "cost unknown (no price for <models>[; cannot read a Cursor store]; $X priced),
N.NM tokens, spec ..." and still exits 0.
--cursor-agent prints one Cursor agent's runs with usage as JSON, {"runs": [{"at": <ms since epoch>, "model": <str or null>,
"input": n, "output": n, "read": n, "write": n}, ...], "results": ["<final reply>", ...]}, in turn order, for the Cursor gantt hook.
"results" holds the non-empty "result" text of every run of the agent, with or without usage ([] when a store has no
"result" column). It looks through every project's stores, ignores the other options, and exits 2 when the id is not [A-Za-z0-9_-]{1,80}, no store has the agent
(an unreadable store counts as one that might), or a run of the agent cannot be parsed.

Reads every session under project dirs whose name contains the main checkout's directory name (PROJECT, correct from a worktree too), plus the
subagent transcripts next to each session. A dir without "worktrees" in its
name is the root checkout: each of its sessions (the Chief of Staff and any
solo threads) gets its own row, labelled with its first message. Worktree sessions
are grouped by git branch and split into spec, build and merge at the
"CHIEF OF STAFF:" relays. Prices are list prices per million tokens (see PRICES).
The last section totals child-thread subagent cost by kind (implementer or review) and model.
Cursor worktree sessions join the child rows by branch and Cursor root sessions get a "root cursor" row;
unpriced Cursor runs add "not priced: <model> N runs, M.M tokens" lines. --turns and --context read Claude Code only.

Root rows show the start of each session's first message. Check the output before
pasting it into a PR or doc.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).absolute().parent))
import app_root  # noqa: E402
import project_config  # noqa: E402
import user_config  # noqa: E402


def project_name(root=None):
    """Directory name of the main checkout, even when run from a git worktree. Defaults to the current repo."""
    root = Path(root) if root else app_root.root()
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return (root / common).resolve().parent.name or root.name
    except (OSError, subprocess.CalledProcessError):
        return root.name


# Claude Code names a transcript dir after the checkout path, so the main checkout's directory name matches it.
PROJECT = project_name()

# $/MTok: input, output, cache read, cache write 1h, cache write 5m. The numbers live in prices.json,
# which the agent-gantt mod reads too.
_RATES = ("input", "output", "read", "write_1h", "write_5m")
PRICES = {
    fam: tuple(rates[k] for k in _RATES)
    for fam, rates in json.loads(Path(__file__).with_name("prices.json").read_text()).items()
}
KINDS = ("input", "output", "read", "write")
ROOT = "root "  # prefix of root-checkout session rows


def parse_ts(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def family(model):
    return next((k for k in PRICES if k in (model or "")), None)


def costs(model, u):
    """Dollars by token kind for one request."""
    p = PRICES[family(model)]
    cc = u.get("cache_creation") or {}
    w1 = cc.get("ephemeral_1h_input_tokens", 0)
    w5 = cc.get("ephemeral_5m_input_tokens", 0)
    if not cc:
        w5 = u.get("cache_creation_input_tokens", 0)
    return {
        "input": u.get("input_tokens", 0) * p[0] / 1e6,
        "output": u.get("output_tokens", 0) * p[1] / 1e6,
        "read": u.get("cache_read_input_tokens", 0) * p[2] / 1e6,
        "write": (w1 * p[3] + w5 * p[4]) / 1e6,
    }


def cursor_tokens(u):
    """The billed token kinds of one Cursor usage record. inputTokens includes the cache tokens, so input is net of them."""
    cr, cw = u.get("cacheReadTokens", 0), u.get("cacheWriteTokens", 0)
    return {
        "input": max(u.get("inputTokens", 0) - cr - cw, 0),
        "output": u.get("outputTokens", 0),
        "read": cr,
        "write": cw,
    }


def cursor_costs(fam, u):
    """(dollars by token kind, billed tokens) for one Cursor usage record; dollars are None without a price.

    Cache writes are priced at the 5 minute rate.
    """
    t = cursor_tokens(u)
    p = PRICES.get(fam)
    paid = p and {"input": t["input"] * p[0] / 1e6, "output": t["output"] * p[1] / 1e6, "read": t["read"] * p[2] / 1e6, "write": t["write"] * p[4] / 1e6}
    return paid or None, sum(t.values())


def text(message):
    c = message.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(
            b.get("text", "")
            for b in c
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def read_session(path):
    """Return (branch, first user text, relays, requests, user message times, (first, last event time)).

    Requests are (time, model family, costs, context tokens, all billed tokens), deduped by
    requestId; the last line wins. User message times skip tool results, injected (isMeta) messages and sidechains.
    """
    branch, first, relays, reqs, users = None, "", [], {}, []
    span = [None, None]
    with open(path, errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or not d.get("timestamp"):
                continue
            try:
                ts = parse_ts(d["timestamp"])
                span = [min(span[0] or ts, ts), max(span[1] or ts, ts)]
            except (TypeError, ValueError):
                pass
            branch = d.get("gitBranch") or branch
            m = d.get("message")
            if not isinstance(m, dict):
                continue
            if d.get("type") == "user" and not d.get("isSidechain"):
                t = text(m)
                c = m.get("content")
                if not d.get("isMeta") and not (
                    isinstance(c, list)
                    and any(
                        isinstance(b, dict) and b.get("type") == "tool_result"
                        for b in c
                    )
                ):
                    users.append(parse_ts(d["timestamp"]))
                if not first and t.strip() and not t.startswith("<"):
                    first = " ".join(t.split())
                if t.startswith("CHIEF OF STAFF:"):
                    relays.append((parse_ts(d["timestamp"]), t))
            elif m.get("usage") and family(m.get("model")):
                reqs[d.get("requestId") or d.get("uuid")] = (
                    parse_ts(d["timestamp"]),
                    family(m["model"]),
                    costs(m["model"], m["usage"]),
                    sum(
                        m["usage"].get(k, 0)
                        for k in (
                            "input_tokens",
                            "cache_read_input_tokens",
                            "cache_creation_input_tokens",
                        )
                    ),
                    sum(
                        m["usage"].get(k, 0)
                        for k in (
                            "input_tokens",
                            "output_tokens",
                            "cache_read_input_tokens",
                            "cache_creation_input_tokens",
                        )
                    ),
                )
    reqs = sorted(reqs.values(), key=lambda r: r[0])
    return branch, first, sorted(relays), reqs, sorted(users), tuple(span)


def cursor_messages(path):
    """A Cursor transcript's user messages in turn order, without the <user_query> wrapper."""
    out = []
    try:
        with open(path, errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    m = d["message"] if d["role"] == "user" else None
                except (ValueError, KeyError, TypeError):
                    continue
                if isinstance(m, dict):
                    t = text(m)
                    q = re.search(r"<user_query>\s*(.*?)\s*</user_query>", t, re.S)
                    out.append((q.group(1) if q else t).strip())
    except OSError:
        pass
    return out


def git_branch(workspace):
    try:
        r = subprocess.run(["git", "-C", workspace, "branch", "--show-current"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None


def read_store(db):
    """(agents, runs) of one Cursor index.db, opened read-only; raises sqlite3.Error when it cannot be read.

    agents are (agent_id, workspace_ref); runs are (agent_id, turn number, model, usage_json, time) with usage, by turn.
    """
    con = sqlite3.connect(f"{db.absolute().as_uri()}?mode=ro", uri=True)
    try:
        agents = con.execute("select agent_id, workspace_ref from agents").fetchall()
        rows = con.execute(
            "select agent_id, turn_number, model, usage_json, coalesce(started_at, created_at) "
            "from runs where usage_json is not null order by turn_number"
        ).fetchall()
    finally:
        con.close()
    return agents, rows


def read_cursor(proj, failed=None):
    """Cursor sessions of one project dir, one per agent with usage: dicts with id, branch, first, relays, runs.

    Runs are (time, model, family, costs, tokens, turn number); costs is None when the model has no price.
    A run without usage_json is skipped. A store that cannot be read is reported on stderr, skipped and appended
    to failed. A run whose usage cannot be parsed is reported on stderr and marks its session bad. Relays are
    (turn number, text) of the user messages that start "CHIEF OF STAFF:".
    The branch is only looked for in worktree dirs.
    """
    sessions = []
    for db in sorted(proj.glob("sdk-agent-store/*/index.db")):
        try:
            agents, rows = read_store(db)
        except sqlite3.Error:
            print(f"agent_usage: cannot read {db}", file=sys.stderr)
            if failed is not None:
                failed.append(db)
            continue
        for aid, ref in agents:
            runs, bad = [], False
            for a, turn, model, usage, ts in rows:
                if a != aid:
                    continue
                try:
                    u = json.loads(usage)
                    fam = family(model)
                    paid, n = cursor_costs(fam, u)
                    runs.append((parse_ts(ts), model, fam, paid, n, turn))
                except (TypeError, ValueError, AttributeError):
                    print(f"agent_usage: cannot read a run of {db}", file=sys.stderr)
                    bad = True
            if not runs and not bad:
                continue
            msgs = cursor_messages(proj / "agent-transcripts" / aid / f"{aid}.jsonl")
            branch = None
            if "worktrees" in proj.name:
                m = re.search(rf"^Branch:\s*({project_config.branch_heads_re()}[A-Za-z0-9_/-]+)", msgs[0] if msgs else "", re.M)
                branch = m.group(1) if m else git_branch(ref)
            sessions.append({
                "id": aid,
                "branch": branch,
                "first": " ".join(msgs[0].split()) if msgs else "",
                "relays": [(n, t) for n, t in enumerate(msgs, 1) if t.startswith("CHIEF OF STAFF:")],
                "runs": runs,
                "bad": bad,
            })
    return sessions


def read_results(db, agent):
    """The non-empty result text of every run of one agent in an index.db, by turn; [] when the store has no result column."""
    con = sqlite3.connect(f"{db.absolute().as_uri()}?mode=ro", uri=True)
    try:
        rows = con.execute("select result from runs where agent_id = ? order by turn_number", (agent,)).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()
    return [r[0] for r in rows if isinstance(r[0], str) and r[0].strip()]


def cursor_agent_runs(projects, agent):
    """(runs, results) of one Cursor agent, in turn order. runs are the runs with usage, as dicts with at (ms since epoch),
    model and the billed kinds; results are the non-empty result texts of all its runs.

    Looks through every project's stores. Raises LookupError when no readable store has the agent (or a store that
    could hold it cannot be read) or when one of its runs cannot be parsed.
    """
    failed = []
    for db in sorted(projects.glob("*/sdk-agent-store/*/index.db")):
        try:
            _, rows = read_store(db)
        except sqlite3.Error:
            failed.append(db)
            continue
        mine = [r for r in rows if r[0] == agent]
        if not mine:
            continue
        runs = []
        for _, _, model, usage, ts in mine:
            try:
                at = int(parse_ts(ts).timestamp() * 1000)
                runs.append({"at": at, "model": model, **cursor_tokens(json.loads(usage))})
            except (TypeError, ValueError, AttributeError):
                raise LookupError(f"cannot read a run of {db}")
        try:
            results = read_results(db, agent)
        except sqlite3.Error:
            results = []
        return runs, results
    raise LookupError(f"cannot read {failed[0]}" if failed else f"no Cursor store has agent {agent}")


def start_stage(first):
    """A continuation child's task names the stage it starts in."""
    m = re.search(r"\bTEAM MODE\. CONTINUE\b", first) and re.search(r"Do the (spec|build|merge) stage", first)
    return m.group(1) if m else "spec"


def start_ctx(reqs, users):
    """Largest context before the first user message that follows the first request."""
    end = next((u for u in users if reqs and u > reqs[0][0]), None)
    return max((r[3] for r in reqs if end is None or r[0] < end), default=0)


def context_line(projects):
    """The --context line for $CLAUDE_CODE_SESSION_ID, or exit 2 with a reason."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid or not re.fullmatch(r"[0-9a-f-]{36}", sid):
        print("CLAUDE_CODE_SESSION_ID is not set or not a session id", file=sys.stderr)
        raise SystemExit(2)
    path = next(iter(sorted(projects.glob(f"*{PROJECT}*/{sid}.jsonl"))), None)
    reqs = read_session(path)[3] if path else []
    if not reqs:
        print(f"no requests found for session {sid}", file=sys.stderr)
        raise SystemExit(2)
    started = reqs[0][0].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"context={reqs[-1][3]} started={started}"


def stage_at(relays, ts, stage="spec"):
    for t, body in relays:
        if t > ts:
            break
        if body.startswith(("CHIEF OF STAFF: the user approved the spec", "CHIEF OF STAFF: auto-approved the spec")):
            stage = "build"
        elif body.startswith(("CHIEF OF STAFF: the user approved the merge", "CHIEF OF STAFF: auto-approved the merge")):
            stage = "merge"
        else:
            m = re.search(r"[Cc]ontinue the (spec|build|merge) stage", body)
            if m:
                stage = m.group(1)
    return stage


def share(cost, usage):
    """` (P% of the subscription)` for a cost against the subscription's API-equivalent usage, or "" when usage is unset."""
    if not usage:
        return ""
    pct = cost / usage * 100
    return f" ({'<0.01' if 0 < pct < 0.005 else f'{pct:.2f}'}% of the subscription)"


def ticket_line(projects, ticket, usage=None, cursor=None):
    """The --ticket line for a ticket like CW-57, or None when no Claude Code or Cursor worktree session ran its branch.

    usage is the subscription's API-equivalent dollars; when set, the cost part also shows the share of the Claude Code part.
    cursor is the Cursor projects dir.
    """
    heads = project_config.branch_heads_re()
    own = re.compile(r'"gitBranch":"' + heads + re.escape(ticket.lower()) + r'[-"]')
    mine = re.compile(heads + re.escape(ticket.lower()) + r"(-.*)?", re.I)
    spent = dict.fromkeys(("spec", "build", "merge"), 0.0)
    tokens, runs, times, cursor_runs, cursor_spent, unpriced, failed = 0, 0, [], 0, 0.0, set(), []
    unreadable = False
    for proj in sorted(projects.glob(f"*{PROJECT}*")):
        if "worktrees" not in proj.name:
            continue
        for session in proj.glob("*.jsonl"):
            try:
                if not own.search(session.read_text(errors="replace")):
                    continue
            except OSError:
                continue
            _, first, relays, reqs, _, span = read_session(session)
            runs += 1
            times += span
            start = start_stage(first)
            for sub in (proj / session.stem / "subagents").glob("agent-*.jsonl"):
                _, _, _, sreqs, _, sspan = read_session(sub)
                reqs, times = reqs + sreqs, times + list(sspan)
            for ts, _, c, _, n in reqs:
                spent[stage_at(relays, ts, start)] += sum(c.values())
                tokens += n
    for proj in sorted(cursor.glob(f"*{PROJECT}*")) if cursor else []:
        if "worktrees" not in proj.name:
            continue
        for s in read_cursor(proj, failed):
            if not (s["branch"] and mine.fullmatch(s["branch"])):
                continue
            runs += 1
            cursor_runs += 1
            unreadable = unreadable or s["bad"]
            for at, model, _, paid, n, turn in s["runs"]:
                times.append(at)
                tokens += n
                if paid is None:
                    unpriced.add(model or "unknown model")
                else:
                    spent[stage_at(s["relays"], turn, start_stage(s["first"]))] += sum(paid.values())
                    cursor_spent += sum(paid.values())
    if not runs:
        return None
    times = [t for t in times if t]
    wall = int((max(times) - min(times)).total_seconds() // 60) if times else 0
    total = sum(spent.values())
    unreadable = unreadable or bool(failed)
    if unpriced or unreadable:
        why = ([f"no price for {', '.join(sorted(unpriced))}"] if unpriced else []) + (["cannot read a Cursor store"] if unreadable else [])
        cost = f"cost unknown ({'; '.join(why)}; ${total:.2f} priced)"
    else:
        cost = f"cost ${total:.2f} API-equivalent{share(total - cursor_spent, usage)}"
        cost += f", Cursor ${cursor_spent:.2f}" * bool(cursor_runs)
    return (
        f"{cost}, {tokens / 1e6:.1f}M tokens, "
        f"spec ${spent['spec']:.2f} / build ${spent['build']:.2f} / merge ${spent['merge']:.2f}, "
        f"{runs} child run{'s' * (runs != 1)}, wall {wall // 60}h {wall % 60:02d}m"
    )


def ticket_id(s):
    if not re.fullmatch(r"[A-Za-z]+-[0-9]+", s):
        raise argparse.ArgumentTypeError(f"{s!r} is not like CW-57")
    return s


def agent_id(s):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", s):
        raise argparse.ArgumentTypeError(f"{s!r} is not a Cursor agent id")
    return s


def main():
    now = datetime.now(timezone.utc)
    ap = argparse.ArgumentParser(
        description="Agent team cost from Claude Code transcripts and Cursor runs."
    )
    ap.add_argument("--since", type=parse_ts, default=now - timedelta(hours=24))
    ap.add_argument("--until", type=parse_ts, default=now)
    ap.add_argument(
        "--projects", type=Path, default=Path.home() / ".claude" / "projects"
    )
    ap.add_argument(
        "--cursor-projects", type=Path, default=Path.home() / ".cursor" / "projects"
    )
    ap.add_argument(
        "--turns", action="store_true", help="per-session request count and context"
    )
    ap.add_argument(
        "--context",
        action="store_true",
        help="print the current session's latest context and start time, then exit",
    )
    ap.add_argument(
        "--ticket",
        type=ticket_id,
        help="print one cost line for a ticket's child threads (all time), then exit",
    )
    ap.add_argument(
        "--cursor-agent",
        type=agent_id,
        help="print one Cursor agent's runs as JSON, then exit",
    )
    args = ap.parse_args()
    if args.cursor_agent:
        try:
            runs, results = cursor_agent_runs(args.cursor_projects, args.cursor_agent)
            print(json.dumps({"runs": runs, "results": results}))
        except LookupError as e:
            print(f"agent_usage: {e}", file=sys.stderr)
            raise SystemExit(2)
        return
    if args.context:
        print(context_line(args.projects))
        return
    if args.ticket:
        try:
            usage = user_config.subscription_usage("Claude")
        except Exception:  # an unreadable user.md reads as unset
            usage = None
        found = ticket_line(args.projects, args.ticket, usage, args.cursor_projects)
        if not found:
            print(f"agent_usage: no transcripts for {args.ticket}", file=sys.stderr)
            raise SystemExit(2)
        print(found)
        return

    # parts[name][bucket] -> dollars by token kind.
    # bucket: spec, build, merge, implementer, review or main.
    parts = defaultdict(lambda: defaultdict(lambda: dict.fromkeys(KINDS, 0.0)))
    split = defaultdict(lambda: dict.fromkeys(KINDS, 0.0))  # root, children, subagents

    by_model = defaultdict(lambda: [0.0, 0])  # (kind, family) -> [dollars, requests]
    turns = {}  # root session name -> [(context tokens, dollars)], subagents excluded
    starts = {}  # root session name -> start ctx in tokens

    def add(name, bucket, group, reqs):
        for ts, fam, c, *_ in reqs:
            if args.since <= ts <= args.until:
                for k in KINDS:
                    parts[name][bucket][k] += c[k]
                    split[group][k] += c[k]
                if group == "subagents" and not name.startswith(ROOT):
                    by_model[bucket, fam][0] += sum(c.values())
                    by_model[bucket, fam][1] += 1

    for proj in sorted(args.projects.glob(f"*{PROJECT}*")):
        is_root = "worktrees" not in proj.name
        for session in proj.glob("*.jsonl"):
            branch, first, relays, reqs, users, _ = read_session(session)
            name = (
                f"{ROOT}{session.stem[:8]} {first[:28]}"
                if is_root
                else (branch or session.stem[:8])
            )
            if is_root:
                add(name, "main", "root", reqs)
                turns[name] = [
                    (r[3], sum(r[2].values()))
                    for r in reqs
                    if args.since <= r[0] <= args.until
                ]
                starts[name] = start_ctx(reqs, users)
            else:
                for r in reqs:
                    add(name, stage_at(relays, r[0]), "children", [r])
            for sub in (proj / session.stem / "subagents").glob("agent-*.jsonl"):
                sreqs = read_session(sub)[3]
                try:
                    kind = json.loads(sub.with_suffix(".meta.json").read_text()).get(
                        "agentType"
                    )
                except (OSError, ValueError):
                    kind = None
                add(
                    name,
                    "implementer" if kind == "implementer" else "review",
                    "subagents",
                    sreqs,
                )

    unpriced = defaultdict(lambda: [0, 0])  # Cursor model with no price -> [runs, tokens]
    for proj in sorted(args.cursor_projects.glob(f"*{PROJECT}*")):
        is_root = "worktrees" not in proj.name
        for s in read_cursor(proj):
            sid = s["id"].removeprefix("agent-")[:8]
            name = f"{ROOT}cursor {sid} {s['first'][:20]}" if is_root else (s["branch"] or sid)
            for at, model, fam, paid, n, turn in s["runs"]:
                if not args.since <= at <= args.until:
                    continue
                if paid is None:
                    unpriced[model or "unknown model"][0] += 1
                    unpriced[model or "unknown model"][1] += n
                elif is_root:
                    add(name, "main", "root", [(at, fam, paid)])
                else:
                    add(name, stage_at(s["relays"], turn, start_stage(s["first"])), "children", [(at, fam, paid)])

    def total(b):
        return sum(b.values())

    cols = ("spec", "build", "merge", "implementer", "review")
    print(
        f"Window {args.since:%Y-%m-%d %H:%M}Z to {args.until:%Y-%m-%d %H:%M}Z (API-equivalent $)\n"
    )
    print(f"{'thread':46}" + "".join(f"{c:>12}" for c in cols) + f"{'total':>10}")
    sums = defaultdict(float)
    children = sorted(n for n in parts if not n.startswith(ROOT))
    roots = sorted(n for n in parts if n.startswith(ROOT))
    for name in children + roots:
        is_root = name.startswith(ROOT)
        row = {c: total(parts[name][c]) for c in cols}
        row["main"] = total(parts[name]["main"])
        t = sum(row.values())
        if t < 0.005:
            continue
        for k, v in row.items():
            sums["root" if is_root else k] += v
        if is_root:
            note = f"main {row['main']:.2f}, subagents {t - row['main']:.2f}"
            shown = f"{note:>{12 * len(cols)}}"
        else:
            shown = "".join(f"{row[c]:12.2f}" for c in cols)
        print(f"{name[:45]:46}{shown}{t:10.2f}")
    grand = sum(sums.values()) or 1.0
    print(
        f"\n{'totals':46}"
        + "".join(f"{sums[c]:12.2f}" for c in cols)
        + f"{grand:10.2f}"
    )
    print(f"{'share':46}" + "".join(f"{sums[c] / grand:12.0%}" for c in cols))
    print(f"root checkout {sums['root']:.2f} ({sums['root'] / grand:.0%} of total)")
    for model, (n, tok) in sorted(unpriced.items()):
        print(f"not priced: {model} {n} runs, {tok / 1e6:.1f}M tokens")
    print()
    print(
        f"{'token types (share of $)':26}"
        + "".join(f"{k:>12}" for k in KINDS)
        + f"{'total $':>10}"
    )
    for g in ("root", "children", "subagents"):
        t = sum(split[g].values())
        if t:
            print(
                f"{g:26}"
                + "".join(f"{split[g][k] / t:12.0%}" for k in KINDS)
                + f"{t:10.2f}"
            )
    print("\nsubagents by kind and model")
    for (kind, fam), (dollars, n) in sorted(by_model.items()):
        print(f"{kind + ' ' + fam:26}{dollars:10.2f}{n:8} requests")
    if args.turns:
        print(
            f"\n{'root sessions (turns)':46}{'requests':>10}{'max ctx':>10}{'avg $/req':>11}{'start ctx':>11}"
        )
        for name, rs in sorted(turns.items()):
            if rs:
                ctx = max(c for c, _ in rs) / 1000
                avg = sum(d for _, d in rs) / len(rs)
                print(
                    f"{name[:45]:46}{len(rs):10}{ctx:9.0f}k{avg:11.3f}{starts[name] / 1000:10.0f}k"
                )


if __name__ == "__main__":
    main()
