# WISE-465: Open the dashboard in the integrated browser from the Chief of Staff thread

**Status:** Draft
**Ticket:** [#465](https://github.com/collective-wisdom-org/collective-wisdom/issues/465)

## Goal

Whenever the Chief of Staff starts the dashboard, and whenever the user asks to see it, the dashboard ends up open and in front in T3 Code's integrated browser, in one tab. When the browser can't be opened, the user still gets the URL and the reason.

## Today

Facts from main at `45ef2d7`.

- `chief-of-staff/startup.md` § Setup step 4 runs `node ~/.collective-wisdom/scripts/dashboard/start.ts --root "<root checkout>" --environment-id "<id>"`. It prints `http://127.0.0.1:<port>/` and exits 0, or prints one error line and exits 1 or 2. It starts a server only when none is healthy for that root, so running it again is safe.
- The same step calls `preview_open` with `reuseExistingTab: false` only when `preview_status` lists no tab at that URL. When a tab exists, nothing brings it forward. When `preview_open` fails, the start report gets a line, but the URL itself is not given.
- `take over`, `resume` and resume mode run "only the dashboard part of Setup step 4" (`rotation.md` § Thread rotation "Take over" step 3.1; `SKILL.md` § Turn start).
- `commands.md` § Commands has no row for seeing the dashboard. Such a message falls to "a message from the user that is not a command", which gets an answer, so the thread can only give the URL.
- `preview_open` takes `url`, `tabId`, `open` (default true: show the tab) and `reuseExistingTab`. Given a `tabId`, it loads `url` in that tab and shows it. `preview_status` lists this thread's tabs with their URLs.

## Design

Markdown only: `agent-team/.claude/skills/chief-of-staff/` and the role doc. No script, server or page change.

### 1. One dashboard section in startup.md

Move the dashboard text out of Setup step 4 into a new `startup.md` § Dashboard, so every caller runs the same steps:

1. Run `start.ts` as today (same `--root` and `--environment-id` rules). If it fails, the report line is the script's line, as today, and the section ends: there is no URL to give.
2. Run `preview_status`. If one of its tabs has a URL on the same origin as the printed URL (`http://127.0.0.1:<port>`, any path), call `preview_open` with that `tabId`, the printed URL and `open: true`. This loads the dashboard in that tab and brings it forward. Otherwise call `preview_open` with the printed URL, `reuseExistingTab: false` and `open: true`.
3. If `preview_status` or `preview_open` errors, or the preview tools are not there, the report line is `Dashboard: <URL>. Not opened in the browser: <error, one line>.` Carry on either way.
4. On success the report says nothing about the dashboard (start and take over), or one line for the command in § 3.

Setup step 4 keeps the thread id, title and `skillCommit` steps and then says "run § Dashboard".

### 2. Callers point at § Dashboard

- `rotation.md` take-over step 3.1: "then startup.md § Dashboard" instead of "only the dashboard part of Setup step 4". Step 4's "the dashboard step's failure line" stays, and now covers the `Not opened in the browser` line too.
- `SKILL.md` § Turn start: "Each also starts the dashboard (startup.md § Dashboard)."
- `kill-switch.md` § Resume already runs the lean take-over pass, so it needs no change.
- `agent-team/docs/agents/chief-of-staff.md`: the dashboard bullet says it starts the dashboard and opens it in the integrated browser, at start, `resume`, `take over` and when the user asks to see it, and gives the URL when the browser can't open.

### 3. A command for seeing the dashboard

New row in `commands.md` § Commands:

| The user says | You do |
|---|---|
| `dashboard`, `show the dashboard`, `open the dashboard`, or any other request to see it | startup.md § Dashboard. Reply `Dashboard open.` on success, or the step 3 line. No tick. |

The row also goes in the `SKILL.md` § Turn start bullet that lists the commands that run no tick, so the request does not run a `status` tick.

Running `start.ts` here also brings back a dashboard server that has stopped, so the user's ask always ends with a live page.

## Tests

None. Every change is skill prose, which `AGENTS.md` § Testing says not to test. `test_agent_files.py` and `test_call_sites.py` still run in the suite and check the links and section names the edits touch.

## Proof

By hand in a Chief of Staff thread on this repo, after install from the branch:

- `start the team` opens one dashboard tab in front.
- With that tab open, `dashboard` brings it forward and `preview_status` still lists one dashboard tab.
- With the tab closed, `dashboard` opens a new one.
- A forced failure (a bad `tabId`, or the server stopped and `start.ts` run with Node older than 24 if one is to hand) shows the URL and the reason line, or the script's line.

## Leaves out

- The dashboard server, page and port handling (WISE-426).
- Opening the dashboard from a ticket child or any thread other than the Chief of Staff.
- Closing extra dashboard tabs the user opened by hand.

## Calls I made

- A tab counts as the dashboard when its URL has the same origin as the printed URL, any path. A tab left on an old port (a server that moved) is not matched, so a new tab opens beside it. Matching by title (`Agent team`) could reuse a tab from another repo's dashboard, which is worse.
- Reusing a tab reloads it at the printed URL rather than only showing it, because `preview_open` needs a URL to target a tab and a reload of the dashboard is harmless.
- The command reply on success is two words, `Dashboard open.`, with no URL, since the ticket asks to stop replying with a link.
- The command runs no tick: seeing the dashboard changes no ticket.
- The steps live in one new `startup.md` § Dashboard section rather than staying inside Setup step 4, so the start, take-over and command paths can't drift apart.
- No test: markdown only.
