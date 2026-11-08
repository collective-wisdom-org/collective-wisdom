# CW-94: subagent thread links in the Running section

**Status:** Shipped
**Shipped:** in PR #180, as specified
**Ticket:** [#94](https://github.com/collective-wisdom-org/collective-wisdom/issues/94)

## Goal

When a Chief of Staff report shows the `Running` section, each running child's line is followed by links to the subagent threads that child started (implementer, docs check, code review, security review and others), so the user can open them from the report.

## Today

- `agent-team/.claude/skills/chief-of-staff/SKILL.md` § Lean turns "Idle check" builds `Running` from the idle check's `ok` lines: one line per child, `[<PREFIX>-N title](<thread link>)`. § Report format shows the example and a paragraph on when the section appears.
- A child's native subagents (the `Agent` tool) show up in T3 as their own threads. `t3_thread_list` with `includeSubagents: true` returns them with `parentThreadId` set to the child's thread ID, `relationshipToParent: "subagent"`, a `title` taken from the subagent's description (for example `Docs check for PR 155`, `Implement CW-100 CI merge`) and a `link`. Checked in a real thread on 2026-11-05.
- `t3_thread_list` has no parent filter. It lists threads newest first, up to 100 per page.
- § Lean turns "Reads" says `t3_thread_list` is used only for the state rebuild. The untracked check in § Sweep already uses it too, so the line is already out of date.
- State holds each ticket's `childThreadId`.

## Builds

All edits in `agent-team/.claude/skills/chief-of-staff/SKILL.md`. No script and no test: the change is skill prose.

- § Lean turns "Idle check": when the turn posts and the check printed at least one `ok` line, make one `t3_thread_list` call (`includeSubagents: true`, `limit: 100`). Keep the threads whose `parentThreadId` is the `childThreadId` of a ticket on a `Running` line. Under that ticket's line, list up to 5 of them, newest first, one per line: `[<thread title>](<thread link>)`. A child with none gets no extra lines. If the call fails, show the `Running` lines without sub-lines and add nothing else. The call is skipped when the turn posts nothing, so the list never makes a turn post.
- § Lean turns "Reads": the `t3_thread_list` line names its three uses (state rebuild, untracked check, the `Running` subagent list) and keeps "Never as a look around."
- § Report format: the `Running` example gets indented sub-lines under one child, and the paragraph after it says where they come from and that `status` and `where's` don't add them.

## Leaves out

- Subagents of children not on a `Running` line (queued, `awaiting-*`, `blocked`).
- Subagents of subagents, and the old child of a continuation (only the current `childThreadId` counts).
- Any change to `status`, `where's <PREFIX>-N?`, the idle check script, when the idle check runs, or what makes a child `full`.
- The subagent's status (running or finished). The title and link only.
- The install PR in an app. That follows the release as for any shared-file change.

## Calls I made (surprising first)

- **Overlap with CW-60.** CW-60 (the `cos_tick.py` spec, awaiting approval on `feat/cw-60-cos-tick-script`) would rewrite § Lean turns "Idle check" and § Report format. This change is kept to a few sentences in those two places plus one line in "Reads", so whichever merges second has a small rebase. If CW-60 merges first, this rule moves into its new text as is.
- **At most 5 subagents per child, newest first.** A long build can start ten or more (implementer, docs check, code review and security review passes). Five keeps a report short and shows what the child is doing now. Older ones stay reachable from the child's own thread.
- **One `t3_thread_list` call per posting turn, 100 threads.** There is no parent filter, so the call pages the whole project. 100 newest threads covers the subagents of every running child in normal use. A child whose subagents are all older than that shows none, which is harmless: its own link is still there.
- **The label is the subagent thread's title**, which is the description the child gave the `Agent` call. No agent type is added: T3 doesn't return one.
- **A failed list call drops the sub-lines silently.** The section is a convenience, and an error line on every report would be noise.
- **The out-of-date "only for the state rebuild" line is fixed in the same edit**, since this change adds a third use.

## Touches

none of these
