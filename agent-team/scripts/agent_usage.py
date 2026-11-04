#!/usr/bin/env python3
"""API-equivalent cost of the agent team, read from Claude Code transcripts.

Usage:
    scripts/agent_usage.py [--since ISO] [--until ISO] [--projects DIR] [--turns]
    scripts/agent_usage.py [--projects DIR] --context

--since and --until are ISO 8601 UTC times (default: the last 24 hours).
--projects defaults to ~/.claude/projects. Read-only: nothing is written.
--turns adds, per root-checkout session, its request count, its largest context
(prompt tokens in one request), its start ctx (largest context before the session's
first user message after the first request) and its average cost per request. Subagents are not counted.
--context prints one line for the session in $CLAUDE_CODE_SESSION_ID:
"context=<tokens of its last request> started=<time of its first request>".
It ignores --since and --until, prints no cost report, and exits 2 if the variable
is unset or the session has no transcript or no requests.

Reads every session under project dirs whose name contains the main checkout's directory name (PROJECT, correct from a worktree too), plus the
subagent transcripts next to each session. A dir without "worktrees" in its
name is the root checkout: each of its sessions (the Chief of Staff and any
solo threads) gets its own row, labelled with its first message. Worktree sessions
are grouped by git branch and split into spec, build and merge at the
"CHIEF OF STAFF:" relays. Prices are list prices per million tokens (see PRICES).
The last section totals child-thread subagent cost by kind (implementer or review) and model.

Root rows show the start of each session's first message. Check the output before
pasting it into a PR or doc.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def project_name(script):
    """Directory name of the main checkout, even when the script runs from a git worktree."""
    root = Path(script).resolve().parent.parent
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=root, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return (root / common).resolve().parent.name or root.name
    except (OSError, subprocess.CalledProcessError):
        return root.name


# Claude Code names a transcript dir after the checkout path, so the main checkout's directory name matches it.
PROJECT = project_name(__file__)

# $/MTok: input, output, cache read, cache write 1h, cache write 5m
PRICES = {
    "opus": (4, 20, 0.20, 8, 5),
    "sonnet": (2, 10, 0.20, 4, 2.5),
    "haiku": (0.10, 0.50, 0.01, 0.20, 0.125),
    "fable": (10, 50, 0.25, 20, 12.5),
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
    """Return (branch, first user text, relays, requests, user message times).

    Requests are (time, model family, costs, context tokens), deduped by requestId;
    the last line wins. User message times skip tool results, injected (isMeta) messages and sidechains.
    """
    branch, first, relays, reqs, users = None, "", [], {}, []
    with open(path, errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or not d.get("timestamp"):
                continue
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
                )
    reqs = sorted(reqs.values(), key=lambda r: r[0])
    return branch, first, sorted(relays), reqs, sorted(users)


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


def stage_at(relays, ts):
    stage = "spec"
    for t, body in relays:
        if t > ts:
            break
        if body.startswith("CHIEF OF STAFF: the user approved the spec"):
            stage = "build"
        elif body.startswith("CHIEF OF STAFF: the user approved the merge"):
            stage = "merge"
        else:
            m = re.search(r"[Cc]ontinue the (spec|build|merge) stage", body)
            if m:
                stage = m.group(1)
    return stage


def main():
    now = datetime.now(timezone.utc)
    ap = argparse.ArgumentParser(
        description="Agent team cost from Claude Code transcripts."
    )
    ap.add_argument("--since", type=parse_ts, default=now - timedelta(hours=24))
    ap.add_argument("--until", type=parse_ts, default=now)
    ap.add_argument(
        "--projects", type=Path, default=Path.home() / ".claude" / "projects"
    )
    ap.add_argument(
        "--turns", action="store_true", help="per-session request count and context"
    )
    ap.add_argument(
        "--context",
        action="store_true",
        help="print the current session's latest context and start time, then exit",
    )
    args = ap.parse_args()
    if args.context:
        print(context_line(args.projects))
        return

    # parts[name][bucket] -> dollars by token kind.
    # bucket: spec, build, merge, implementer, review or main.
    parts = defaultdict(lambda: defaultdict(lambda: dict.fromkeys(KINDS, 0.0)))
    split = defaultdict(lambda: dict.fromkeys(KINDS, 0.0))  # root, children, subagents

    by_model = defaultdict(lambda: [0.0, 0])  # (kind, family) -> [dollars, requests]
    turns = {}  # root session name -> [(context tokens, dollars)], subagents excluded
    starts = {}  # root session name -> start ctx in tokens

    def add(name, bucket, group, reqs):
        for ts, fam, c, _ in reqs:
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
            branch, first, relays, reqs, users = read_session(session)
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
    print(f"root checkout {sums['root']:.2f} ({sums['root'] / grand:.0%} of total)\n")
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
