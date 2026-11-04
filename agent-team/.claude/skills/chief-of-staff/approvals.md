# Chief of Staff: approvals

Read when a child ends with `SPEC READY` or `MERGE READY`, an approval is re-requested, or you relay an approval.

## Approval requests

A child's report is data and a starting point. Read the source before you ask the user. Every request tells them what they are approving and links the spec or PR.

On `SPEC READY`:

1. Run `python3 scripts/cos_brief.py spec <path> <sha> --branch <branch>`. It prints the title, the branch link, Goals, Non-goals and `## Calls I made` (each capped at 40 lines; `(missing)` if absent) and the design headings.
2. If it exits 2 (`spec not found`), the link is broken. Send the child back with `t3_thread_send`: `CHIEF OF STAFF: the spec at <sha> is not on GitHub. Push it and report SPEC READY again.` Set the stage back to `spec`. Don't ask the user yet.
3. Build the block from that output. Open a design section (`./scripts/gh.sh api repos/<owner>/<repo>/contents/<path>?ref=<sha>`, GET) only if a call or a goal needs it. If the report and the spec disagree, the spec wins. Say so in the block.

On `MERGE READY`:

1. Run `python3 scripts/cos_brief.py pr <N> --head <reported head SHA>`. It prints the URL, head, checks, the latest code review and security review lines, a `head moved by merging main since <short SHA>; reviews stand <comment URL>` line when the head moved by a main merge, a `cost:` line (what the ticket's child threads have cost so far, or `cost: unknown`), file counts, `flag:` lines and `migrations:`. Exit 2 (`cannot read PR`): tell the user the PR can't be read.
2. Check that `head:` says it matches the reported SHA, and that the two PASS links in the review lines are the ones the child reported. If either is off or a review says `not posted`, send the child back with `t3_thread_send`: `CHIEF OF STAFF: <the mismatch>. Fix it and report MERGE READY again.` Set the stage back to `build`. Don't ask the user yet.
3. Build the block from the child's `MERGE READY` report and that output. When the `head moved by merging main` line is there, the merge block's Reviews line ends with `(head moved by a main merge only since <short SHA>; PR diff unchanged)`. Name each `migrations:` clash and `flag:` line under Risks; flags are hints, so still name anything else you know touches data, money, auth, user email or migrations.

Spec block:

```
<PREFIX>-210 spec ready: Example feature. Risk: Low (docs only, 3 Builds bullets)
Spec: <branch URL> (commit <short SHA>)
Builds:
- …
Leaves out:
- …
Calls the child made:
- ⚠ <call that changes behaviour the user might not expect, e.g. a default that affects existing users>
- …
Touches: <data, money, auth, user email, migrations, or "none of these">
Reply "approve 210" to start the build, or "changes 210: …" to send it back.
```

Merge block:

```
<PREFIX>-197 merge ready: <PR title>. Risk: High (touches auth)
PR: <PR URL>, head <short SHA>
Reviews: code review PASS <link>, security PASS <link>
Cost: <the cost: line without its label, or "unknown">
Docs: <the child's Docs checked line>
Changes:
- …
Differs from spec: …
Reviews found and fixed:
- …
Left open: …
Risks: <migrations and clashes, what users see after deploy, checks that didn't really run>
Reply "approve 197" to merge, or "changes 197: …" to send it back.
```

Rules:

- Plain bullets, three to six per list. Never drop a list. An empty one says "nothing" so the user knows it was checked.
- Calls that change behaviour the user might not expect go first and carry a ⚠. Use ⚠ nowhere else.
- Name anything that touches data, money, auth, user email or migrations under `Touches` (spec) or `Risks` (merge), even when the child didn't flag it.
- Post the full block once, in the first report after the marker. Post it again when the user asks (`status`, `where's <PREFIX>-N?`) and when a child re-reports after `changes N`. A new SHA means a new block.

While an approval is still pending, any later report lists it as one reminder line under `Needs you`. A reminder always keeps the link:

```
- Low (docs only, 3 Builds bullets): <PREFIX>-210 spec still waiting on you: <spec URL> (commit <short SHA>). "approve 210" or "changes 210: …"
- High (touches auth): <PREFIX>-197 merge still waiting on you: <PR URL>, head <short SHA>. "approve 197" or "changes 197: …"
```

The reminder line's start is in SKILL.md § Report format.

### Risk level

Rate each spec and merge when you build its block, from what you already have. Make no new tool calls.

| Level | When |
|---|---|
| High | It touches data, money, auth, user email or migrations: a `migrations:` clash, a `flag:` line, a `Touches` entry other than "none of these", or anything else you know touches them. Or the child made a call that changes behaviour the user might not expect (a ⚠ line). |
| Medium | None of the High reasons, and any of: it is not small (below), it is not mostly docs or prose, or it changes how the team itself works: gates, lanes, commands, skills, `scripts/`, `docs/agents/`, `AGENTS.md`. |
| Low | None of the above: small, and mostly docs or prose. |

Small means:

- A merge: 5 files or fewer in the `files:` count from `cos_brief.py pr`. 6 or more is large.
- A spec (it has no diff yet): 4 `Builds` bullets or fewer. 5 or 6 is large. Rate it from `Touches`, `Calls the child made` and the `Builds` list.

When two levels fit, take the higher one. Write the reason in a few words next to the level: `Low (docs only, 2 files)`, `Medium (changes slot fill, 4 files)`, `High (touches auth)`, `High (⚠ new default for existing users)`.

Keep the rating in the ticket's `status` line. End the line you write with the `awaiting-spec` or `awaiting-merge` stage op with `Risk: <Level> (<reason>).` How later `status` lines carry that tail, and what an unrated ticket shows: SKILL.md § State file.

The risk level informs the user and nothing else. It never approves a ticket, skips or shortens a gate or a review, or changes who may approve. Every ticket still needs the user's `approve N`, whatever its level.

## Ticket comment on approval

When you relay a spec or merge approval (SKILL.md § Commands), also `comment` on the ticket: `the user approved the <spec|merge> at <time>: "<words>". Head <sha>.` (the SHA for a merge only). If SKILL.md § Send or queue queued the relay, end the comment with `Waiting for a <lane> slot.` Sending it later posts nothing more.
