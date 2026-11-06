# CW-134: Make Chief of Staff thread links render as clickable links

**Ticket:** [CW-134 (#134)](https://github.com/collective-wisdom-org/collective-wisdom/issues/134)
**Status:** Shipped
**Shipped:** in PR #145, as specified

## Goal

A thread link in a Chief of Staff (or any agent) reply shows as a clickable link in T3's chat, not as raw `<t3-thread://v2/...>` text. The user reported this again today: a delegated-task link showed as the raw string, angle brackets and percent-encoded id included.

## Change

- Run the render check in a real T3 thread first (see Check). Its result picks the form; nothing is written before it.
- `SKILL.md` § Report format states one rule next to "Use each thread's `link` verbatim": how to write a thread link (what wraps it, what may follow it), never in backticks or a code block.
- Every template that shows `<thread link>` or `<helper link>` follows that rule. Per-file wording changes go in the PR: `chief-of-staff/SKILL.md` (§ Report format, § Commands), `ticket-helper.md`, `rotation.md`, `status.md`, `approvals.md`, `cross-repo.md`.
- `rotation.md`'s Moved-to check keeps working: `Moved to <successor link>` stays the start of the reply, and the check's wording is updated only if the link form changes what it reads the thread id from.
- No script, no test.

## Check

In one reply in a T3 thread, post each of these for one real thread and have the user say which are clickable:

1. bare `<t3-thread://v2/...>` with angle brackets
2. the same without angle brackets
3. a markdown link `[title](t3-thread://v2/...)`
4. each of 1 to 3 followed by `.`, and by `:`
5. each of 1 to 3 in a bullet and in a table cell with `<br>`

The PR lists which forms rendered and which did not.

## Check result

Checked by the user in a T3 thread on 2026-11-05:

| Form | Clickable |
|---|---|
| bare `<t3-thread://...>` with angle brackets | yes |
| bare `t3-thread://...` without angle brackets | no |
| markdown link `[title](t3-thread://...)` | yes |
| markdown link followed by `.` | yes |

The rule: write every thread link as a markdown link with a short title, `[title](t3-thread://...)`, so the user sees a name, not the raw id. If the raw string must appear, keep its angle brackets. Never bare, never in backticks or a code block. A trailing `.` or `:` after a markdown link is fine, so the templates keep their punctuation. Bullets, table cells and `<br>` were not checked; the PR says so under Not proven.

## Left out

- Subagent thread links in `Running` (#94).
- How the Chief of Staff gets or stores thread ids.
- Anything saved in agent memory.
- The install PR in an app: the PR says whether one is needed (these are shipped skill files, so it is).

## Calls I made

- The markdown link is the rule, not the angle-bracket form, because both render and the title tells the user which thread it is.
- The `Moved to` check reads the thread id out of the link, so it is changed to read it from inside the markdown link's parentheses.
- Agents outside the Chief of Staff (like me in this thread) get the rule too, through the Report format section and the T3 thread-link line in a ticket's own PR notes. I do not touch the T3 system prompt, which is not in this repo.
