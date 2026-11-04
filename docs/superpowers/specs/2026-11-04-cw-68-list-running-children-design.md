# CW-68: List the running children, with thread links, whenever the idle check runs

**Ticket:** [CW-68](https://github.com/dbeallor/collective-wisdom/issues/68)
**Status:** Shipped
**Shipped:** in PR #74, as specified

## Goal

When the Chief of Staff's idle check runs and the turn posts a message, the message ends with a short list of the children that are still running, each with a link to its thread. Today only `status` and `where's <PREFIX>-N?` show thread links, so a routine report leaves the user with no way to open a running child.

## Non-goals

- Listing children that are not running (queued, `awaiting-*`, `blocked`, or a `full` line from the idle check).
- Changing when the idle check runs, or what makes a child `full`.
- Changing `cos_idle_check.py` or its test.
- Changing the `status` and `where's` layout.

## Design

### Where the link comes from

The idle check already does one `t3_thread_read` per active child (`limit: 1`, `maxCharsPerItem: 1`, `runLimit: 1`). That response carries the child's `thread.link`, the exact string T3 wants in replies (checked against a live read: `"link": "<t3-thread://v2/…/mcp:…>"`). The skill keeps that link from the same read. No extra call, and no link built by hand from `childThreadId`.

So the script doesn't change. Its `ok <PREFIX>-N (running, updated HH:MM)` lines say which children are running; the skill pairs each with the link from its read. Changing the script would mean a new input field, a new output shape, a test change and an install PR in each app, for a value the skill already holds.

### Titles

Each line shows `<PREFIX>-N title`. State has no ticket titles, so the title comes from one `list-tickets` call (label `agent`, fields `id, title`), the same call the status layout uses. It runs only when the turn posts and the idle check printed at least one `ok` line, and once per turn even if the status layout or another step already needs it. If the call fails, the line shows the ID alone.

### The rule, in `SKILL.md` § Lean turns

Add to the Idle check bullet: keep each child's `link` from its read. When the turn posts anything, end the message with a `Running` section: one line per `ok` line, in the script's order. A turn that posts nothing posts nothing for the list either: the list never makes a turn post.

### The format, in `SKILL.md` § Report format

Add a `Running` section to the report example, after `Moving` and before `Done since last report`:

```
Running
- <PREFIX>-199 Background jobs: <thread link>
- <PREFIX>-240 Example feature: <thread link>
```

And one rule line under the example:

- The `Running` section lists the idle check's `ok` children, with the link from its read. It shows on every report that runs the check, not only when it changed, so it is exempt from the "only lines that changed" rule in § Lean turns Reports. A `status` or `where's` answer doesn't add it: the status layout already has a row and a link for each of those children.

### `status` and `where's`

Both already run the idle check and already show every active child, with its link, in the table. They don't get a `Running` section, so no child shows twice. The status layout text doesn't change.

### How this fits with CW-23

CW-23 (blocked, branch `feat/cw-23-shrink-agent-files`, no PR yet) splits the Chief of Staff skill into `SKILL.md` plus reference files. On that branch:

- § Lean turns stays in `SKILL.md`, and the Idle check bullet is word for word today's text.
- § Report format stays in `SKILL.md` with its example; only the status layout moves to `status.md`.

This ticket edits only those two sections and leaves the status layout alone, so the edits land in sections CW-23 keeps in place. Whichever merges second carries the other's text: if CW-68 merges first, CW-23's rebase keeps the new Idle check sentence and the `Running` section and rule line in `SKILL.md`; if CW-23 merges first, this branch makes the same edits in the same two `SKILL.md` sections. The additions are a few lines and go toward CW-23's size budget, so they stay short.

## Testing

No script changes, so no new tests. The change is prose in a skill (AGENTS.md § Testing: don't test prose). `python3 -I -m pytest -q agent-team/scripts` and `shellcheck` still run before the PR.

## Calls I made

- **Script stays as it is.** The link comes from the read the idle check already makes, not from the script and not from `childThreadId`. The ticket allowed either; this one needs no install PR and no test change.
- **One extra tracker call for titles.** `list-tickets` once per posting turn that has running children. The cheaper option, the child thread's T3 title, is not the ticket title.
- **The list repeats on every report.** It is exempt from "report only lines that changed", since its job is to give the user a link to every running child each time.
- **Its own `Running` section**, after `Moving`, rather than links added to the `Moving` lines. `Moving` lists what changed; many running children have no `Moving` line.
- **Full-pass turns don't get the list.** A turn whose full pass read every active child skips the idle check today, and the ticket ties the list to the idle check. Adding it to full passes is a small follow-up if wanted.
- **`full` children are left out**, including `full <PREFIX>-N idle 50m`, which is still running. Each one gets a full read and its own report line.
