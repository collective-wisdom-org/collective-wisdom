# Release notes

## 2026-11-14 attach a Cursor ticket helper's session to the ticket it filed (CW-288) (#295)

Merged 2026-11-14 00:06 UTC.

A ticket helper run on Cursor now shows as a card while it runs and, once it files a ticket, its time and cost appear in that ticket's gantt and spend, like a Claude Code helper. A ticket is attached when Cursor has written the helper's final reply by the time its last hook event fires.

## 2026-11-14 record ticket helper support in the agent gantt (CW-290) (#294)

Merged 2026-11-14 00:05 UTC.

The compatibility page now says what a ticket helper gets in the agent gantt on each harness: Claude Code attaches it to the ticket it filed, Cursor shows only a placeholder card until #288 lands, and Codex and Antigravity show nothing.

Context size: pass skipped (no agent files changed)

## 2026-11-13 accept one _suffix in a GitHub login (EMU) (#293)

Merged 2026-11-13 23:50 UTC.

User config now accepts EMU-style GitHub logins with one `_suffix`.

## 2026-11-13 keep Chief of Staff children on its own harness (CW-280) (#291)

Merged 2026-11-13 23:45 UTC.

A Chief of Staff now starts every child, helper and project manager thread on its own harness, using that harness's model table, and flags any child that ends up on a different one. A Chief of Staff on Codex or Antigravity starts no children yet because those harnesses have no routing recorded.

## 2026-11-13 Chief of Staff creates user.md at start when missing (CW-281) (#292)

Merged 2026-11-13 23:44 UTC.

When this machine has no `user.md`, or no row for the repo, the Chief of Staff now asks for your gh login at start, take over and resume, shows what it will write, and writes it after you say yes. A merge approval no longer needs a hand-written file.

## 2026-11-13 show ticket helpers on the Ship loop tab and count their time in the ticket gantt (CW-286) (#289)

Merged 2026-11-13 23:05 UTC.

The dashboard's Ship loop tab now shows a running ticket helper as a card under In progress, and lists open Todo and Backlog tickets in a Not started section. A ticket a helper filed shows the helper's time and cost in its gantt. The Ticket helpers list is gone from the Chief of Staff tab. Update the agent-gantt plugin to get the filed ticket recorded.

Context size: pass skipped (no agent files changed)

## 2026-11-13 show tokens and spend on Cursor gantt rows (CW-284) (#287)

Merged 2026-11-13 22:14 UTC.

A Cursor thread's rows on the local dashboard now show tokens and cost, and the ticket's spend includes them, except the cost of a run on a model with no price. Such a run (Auto, for example) shows a dash for cost, not $0. Nothing to do: rerun `./install.sh` to pick up the change.

## 2026-11-13 install the agent-gantt plugin from install.sh (CW-282) (#285)

Merged 2026-11-13 20:27 UTC.

`./install.sh` now installs the `agent-gantt` Claude Code plugin for you when `claude` is on your PATH. If `claude` is missing or the install fails, the command to run by hand is listed under `TODO:`.

## 2026-11-13 route Cursor to Auto Intelligence and Auto Fast (CW-275) (#283)

Merged 2026-11-13 17:51 UTC.

The Cursor Chief of Staff and its children now run on Cursor's Auto router (Auto Intelligence for specs, reviews and the ticket helper; Auto Fast for the Chief of Staff, build, merge, project manager children and the implementer, documenter and compacter) instead of named Grok and Composer models, because Cursor cannot pick models for everyone. Run `./install.sh` after this merges so `~/.cursor/agents` picks up the new `model:` values. The usage report is expected to show `cost unknown` for Auto runs (unconfirmed until a real Auto run is read), and a No Hands run under a Cursor Chief of Staff then stops on cost unknown. Cursor reviews now run on the Auto router, which pins no model, so a review PASS on Cursor carries less assurance than on Claude Code: keep the approval risk tolerance strict for a Cursor Chief of Staff until the follow-up checks the review model.

## 2026-11-13 record a Cursor Chief of Staff run on the trial repo (CW-256) (#277)

Merged 2026-11-13 17:07 UTC.

The compatibility page now records a Cursor run: a Cursor Chief of Staff can set up a repo and take a ticket to merge, with Claude Code children. A Cursor child thread is still untested, and a follow-up ticket covers it.

## 2026-11-09 route Cursor to Grok 4.7 and Composer 2.5 and price them (CW-272) (#274)

Merged 2026-11-09 04:56 UTC.

On Cursor, the Chief of Staff now starts its children on Grok 4.7 and Composer 2.5 instead of Claude models, and `agent_usage.py` shows a dollar cost for runs on them. Nothing changes on Claude Code.

## 2026-11-09 show ticket helpers on the dashboard Chief of Staff tab (CW-260) (#271)

Merged 2026-11-09 03:55 UTC.

The dashboard's Chief of Staff tab now lists ticket helper threads, running and finished, under the project manager threads. Nothing to do.

## 2026-11-09 produce agent-gantt snapshots from Cursor threads (CW-258) (#270)

Merged 2026-11-09 03:55 UTC.

A Cursor thread on a worktree now shows a gantt row on the local dashboard. Rows show timing and model but no spend, since Cursor does not report tokens. Rerun `./install.sh` to add the hooks to `~/.cursor/hooks.json`.

## 2026-11-09 include Cursor sessions in the usage and cost report (CW-257) (#269)

Merged 2026-11-09 03:51 UTC.

The usage and cost report now counts work done in Cursor, priced like Claude Code work. If a Cursor run used a model with no price in `prices.json`, the ticket's cost shows as unknown, and a No Hands run stops on it and names the ticket.

Context size: 86223 to 86520 characters (+297 from main)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-09 let tag-release.sh cut minor release versions (CW-259) (#268)

Merged 2026-11-09 02:29 UTC.

`./tag-release.sh --minor` now cuts a minor release such as `v0.2.1` between numbered releases, so a small fix can ship without a new `v0.N`. Plain `./tag-release.sh` numbers as before, but it now also refuses to tag a commit that already carries a minor tag. Nothing to do unless you cut releases.

## 2026-11-09 install the Chief of Staff rotation hook for Cursor (CW-253) (#262)

Merged 2026-11-09 02:14 UTC.

On Cursor, the Chief of Staff thread now gets the rotation stop for a skill change. Run `./install.sh` again to add the hook to `~/.cursor/hooks.json`. Size-based rotation is not available on Cursor.

## 2026-11-09 install Cursor-valid copies of the team subagents (CW-255) (#265)

Merged 2026-11-09 02:07 UTC.

On Cursor, the team subagents now install into `~/.cursor/agents` with Cursor's own settings, and the three reviewers are marked read only (not yet run in Cursor). Rerun `./install.sh`. If you already have your own `~/.cursor/agents/implementer.md`, it is kept and wins over the team's.

## 2026-11-09 run the security review on Cursor without review-security (CW-254) (#263)

Merged 2026-11-09 01:53 UTC.

On Cursor, the security review step now runs from files this repo ships, with no Cursor-only skill needed. Nothing to do on your side.

## 2026-11-09 install the Cursor instruction block as a rule file (CW-252) (#261)

Merged 2026-11-09 01:44 UTC.

`./install.sh` now writes the agent team instruction for Cursor to `~/.cursor/rules/collective-wisdom.mdc`, so you no longer paste it into Cursor Settings. Delete any copy you pasted earlier if you want only one.

## 2026-11-08 match the dashboard dark colors to T3 Code dark (CW-248) (#250)

Merged 2026-11-08 23:09 UTC.

The dashboard's dark mode now uses the same black and neutral greys as T3 Code's dark theme instead of GitHub's navy. Light mode is unchanged and nothing needs doing.

## 2026-11-08 add a Chief of Staff tab to the dashboard (CW-247) (#251)

Merged 2026-11-08 23:08 UTC.

The dashboard now has a Chief of Staff tab next to the Ship loop tab. It shows the Chief of Staff and the project manager's ranking and hygiene threads with their gantt charts. Update the agent-gantt mod (`/plugin`) to fill the project manager list; the Chief of Staff card works without it.

## 2026-11-08 close the gap between a merge and the ticket leaving the merge stage (CW-245) (#249)

Merged 2026-11-08 22:40 UTC.

When a merge finishes under a Chief of Staff thread that has rotated, the ticket now leaves the merge stage within about a minute and the next queued merge can start. The dashboard no longer lists a ticket as both merging and merged. Nothing to do; the next `./install.sh` run or checkout of `main` picks it up.

## 2026-11-08 make the dashboard follow the macOS light or dark setting (CW-242) (#246)

Merged 2026-11-08 22:20 UTC.

The dashboard now opens in dark or light to match the macOS setting, including in a new or reopened T3 preview tab and after the server restarts. Nothing to do; on other systems it behaves as before.

## 2026-11-08 redesign the dashboard Details section, render markdown, pick details by stage (CW-240) (#244)

Merged 2026-11-08 21:52 UTC.

The dashboard's Details section is easier to scan, shows the spec and PR text as formatted markdown, and adds a Spec link next to the PR link. Merged tickets now have a Details section too. Nothing to do on your side.

## 2026-11-08 back up the dashboard spend ledger and gantt history (CW-238) (#243)

Merged 2026-11-08 21:50 UTC.

The dashboard now backs up its spend ledger and gantt history to `~/.agent-team-backups/` every time it starts and once a day, keeping the last 14. If the files are lost, stop the dashboard and run `node ~/.collective-wisdom/scripts/dashboard/backup.ts restore --root <root checkout>`.

## 2026-11-08 restart the dashboard server when its code changes (CW-239) (#241)

Merged 2026-11-08 21:33 UTC.

The local dashboard now restarts itself on the new code after a merge, so there is no manual stop and rerun. If the new code fails to load, the old server keeps running and the page says so. The server running before this ships needs one `start the team`, `resume` or `take over` to be replaced.

## 2026-11-08 label gantt task rows by stage and helper role (CW-233) (#237)

Merged 2026-11-08 21:04 UTC.

On a ticket's Agents chart, each child thread's row now starts with its stage (`Spec CW-N: ...`, `Build CW-N: ...`, `Merge CW-N: ...`), and the ticket helper, backlog ranking and hygiene children show their role. Run `/plugin update agent-gantt@collective-wisdom` to get it; rows already recorded keep their old names.

Context size: pass skipped (no agent files changed)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-08 expandable Details section on each dashboard ticket (CW-227) (#231)

Merged 2026-11-08 20:47 UTC.

Each ticket on the dashboard has a new `Details` section. For a ticket waiting on build approval it shows what the spec says, and for one waiting on merge approval it shows what the PR changes, with the review verdicts. No setup needed.

## 2026-11-08 gantt tooltips show on hover in the dashboard (CW-232) (#236)

Merged 2026-11-08 20:40 UTC.

Hovering a bar or a row in the dashboard's gantt chart now shows its tooltip, including bars of tasks that are still running. A running bar's tooltip no longer shows its length so far; the row's duration column still does.

## 2026-11-08 reload the open dashboard page when its files change (CW-230) (#234)

Merged 2026-11-08 20:23 UTC.

An open dashboard tab now reloads itself within about 5 seconds when the page files change. A tab opened before this ships needs one hard refresh; restarting the server after a server-side change is still manual.

Context size: pass skipped (no agent files changed)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-08 T3 Code harness columns in the compatibility matrix (CW-226) (#229)

Merged 2026-11-08 20:13 UTC.

The compatibility page now lists four harness columns, each running in T3 Code: Claude Code, Codex, Cursor and Antigravity, and gains an Azure DevOps column for trackers. Every cell starts with a colored circle so the page reads at a glance. Nothing to do; Cursor, Antigravity and Azure DevOps cells are `untested`, `partial` or `not supported` until someone runs them; every Azure DevOps cell is `not supported` because there is no adapter.

Context size: pass skipped (no agent files changed)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-08 gantt task rows show only their own work, bars get tooltips (CW-225) (#228)

Merged 2026-11-08 20:06 UTC.

On the dashboard gantt, a task's row now shows only the time the task itself worked, not the time it waited on its subagents. Hovering a bar shows its name, start and end, length and model.

## 2026-11-08 compatibility matrix for harnesses and trackers (CW-223) (#224)

Merged 2026-11-08 19:56 UTC.

The repo now has a compatibility page, `docs/compatibility.md`, that lists which team features work on which harness (Claude Code, Codex, Cursor, T3 Code) and ticket tracker (GitHub Issues, Linear, Jira). Nothing to do.

## 2026-11-08 match prices.json to the published rates and Claude Code's session cost (CW-220) (#222)

Merged 2026-11-08 19:33 UTC.

The cost the agent gantt and the dashboard show for a session now matches Claude Code's own figure to within a cent in most cases. Sonnet cache reads and subagent cache writes were overpriced before. Sessions recorded earlier keep their old costs, and the dashboard says so.

## 2026-11-08 name gantt tasks by what the work is (CW-219) (#221)

Merged 2026-11-08 18:34 UTC.

Gantt task rows now say what the work was, such as `CW-216 build` or `CW-216 merge PR #218`, instead of a Chief of Staff relay line or the delegated-task preamble. Run `/plugin update agent-gantt@collective-wisdom` to get it; rows already recorded keep their old names.

## 2026-11-08 redesign the agent gantt as a waterfall by task, active time only (CW-216) (#218)

Merged 2026-11-08 18:14 UTC.

The Agents chart in the dashboard is now one waterfall per ticket, with a row per task showing how long the agent actually worked and what it cost. Time spent waiting on your approvals no longer counts. Restart the dashboard and the agent-gantt mod to see it.

## 2026-11-08 remove leftovers of dropped features (CW-212) (#217)

Merged 2026-11-08 18:12 UTC.

A leftover Chief of Staff heartbeat task from the old design is no longer cleaned up automatically; delete one by hand if you still have it. The merge gate now needs the `## Release note` section in the PR body, and a dated release note file no longer stands in for it. `install.sh` now refuses any argument except `--dry-run`, with the same message that names the removal command.

## 2026-11-08 No Hands mode that works the Backlog with no approvals (CW-159) (#215)

Merged 2026-11-08 17:42 UTC.

You can turn on a No Hands run: set the three new `project.md` rows (off by default), then say `no hands` in the Chief of Staff thread. The team approves specs and merges itself, except changes to the files that decide approvals, migrations and flagged changes (money, auth, user email), which still wait for you. It stops at 10 tickets or $200 by default, and posts a summary when it ends. `stop everything` always ends it.

## 2026-11-08 show the agent gantt on merged PRs in the dashboard (CW-213) (#214)

Merged 2026-11-08 17:42 UTC.

A merged PR in the dashboard now has an "Agents" section that opens to the same agent gantt a ticket card has. It shows only tickets that ran while the dashboard was running; nothing is needed from you.

## 2026-11-08 show agent spend on merged PRs in the dashboard (CW-209) (#211)

Merged 2026-11-08 08:39 UTC.

The dashboard's merged list now shows what the agents spent on each ticket, as cost and tokens. It only covers PRs that merge while the dashboard is running after this update; older ones show nothing. The dashboard now writes `.agent-team/spend.json` in the root checkout.

## 2026-11-08 send a conflict found at MERGE READY to the merge lane (CW-206) (#210)

Merged 2026-11-08 08:38 UTC.

A conflict found when a ticket reaches `MERGE READY` now goes to the merge lane when the setting `Review after conflict resolution` is `off`, so the reviews stand and it no longer goes back to build. You need to do nothing.

## 2026-11-08 read the dashboard tracker from the Tracker row (CW-205) (#208)

Merged 2026-11-08 08:18 UTC.

The dashboard shows GitHub issue links only for repos whose `Tracker` row is `github`. Repos on Linear or Jira that still carry the template's tracker text no longer get wrong issue links. Nothing to do.

## 2026-11-08 compact skills and role docs, add cos_route, cos_restart, cos_todo (CW-197) (#207)

Merged 2026-11-08 08:13 UTC.

The Chief of Staff skill and the role docs are about 18 thousand characters smaller. Three new scripts (`cos_route.py`, `cos_restart.py`, `cos_todo.py`) now work out the lane for a relay, the stuck-child restart and the Todo start order, so the Chief of Staff runs them instead of working it out. Rules, gates and commands are unchanged, with the two small exceptions under Behaviour changes. Nothing for you to do after `./install.sh`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-08 collapsible dashboard status sections (CW-200) (#204)

Merged 2026-11-08 07:15 UTC.

Each section on the dashboard can be collapsed from its heading, and the dashboard remembers which ones you closed. Nothing to do.

## 2026-11-08 overhaul the dashboard layout so it is easy to read (CW-195) (#203)

Merged 2026-11-08 07:05 UTC.

The dashboard page is reorganised: tickets waiting on your approval come first in a red or amber band, in-progress work follows, and queued and merged items are short rows. The Gantt is one compact row per agent, with its details on a muted line under the name and the same data as before. Nothing to do on your side.

## 2026-11-08 run the docs check once after the code and security reviews pass (CW-199) (#202)

Merged 2026-11-08 07:04 UTC.

The documenter now runs once per PR, after the code and security reviews pass, and a docs-file-only fix after that no longer sends the PR back through the reviews. You don't need to do anything.

Context size: 75003 to 74970 characters (-33 from main)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-08 sort dashboard sections by last updated (CW-198) (#201)

Merged 2026-11-08 06:40 UTC.

On GitHub-issue boards, dashboard sections now list the most recently updated ticket first. The two queued sections keep their start order. Nothing to do.

## 2026-11-08 cos_tick.py plans a Chief of Staff turn (CW-60) (#196)

Merged 2026-11-08 06:38 UTC.

The Chief of Staff now gets the order of each turn from a script (`cos_tick.py`) instead of working it out from the skill text, so its turns follow the same steps every time. You need do nothing.

## 2026-11-08 split the Gantt main row into task chunks, show model and harness, leave out waiting time (CW-191) (#194)

Merged 2026-11-08 05:58 UTC.

The agent chart on each dashboard card now splits the main agent into one row per task, shows the model and harness on every row, and draws bars only for the time an agent was working. The Kids count is gone. A session that was running when the `agent-gantt` mod updates starts its rows fresh at the next event.

## 2026-11-08 move skill logic into scripts (CW-115) (#190)

Merged 2026-11-08 05:45 UTC.

Four more checks the agents did by reading prose are now scripts: the review check before `MERGE READY`, the head check before a merge approval, the project manager's hygiene rules and its Dry ranking test. The Chief of Staff, ship-loop, project-manager and merge-pr skills are about 4 KB smaller. Nothing to do on your side; behavior is the same, with the small differences listed in the as-built.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-08 run CI on pull requests only (CW-103) (#193)

Merged 2026-11-08 05:42 UTC.

CI no longer runs again on `main` after a merge, so `main` is tested only through its pull requests. A merge can still leave `main` red when another PR merged first, and nothing reports that today.

## 2026-11-08 dashboard header badges and tighter heading (CW-188) (#192)

Merged 2026-11-08 05:38 UTC.

The dashboard header now has badges at the top right: threads awaiting merge approval (red), threads awaiting build approval (yellow) and the build queue size. The `Status` sub header is gone and there is less space under the heading. Nothing to do.

## 2026-11-08 replace the dashboard Agents pane with a paginated Merged list (CW-187) (#189)

Merged 2026-11-08 05:32 UTC.

The local dashboard's Agents list is replaced by a Merged list: merged tickets, newest first, ten per page, with Newer and Older buttons. Agent charts still appear inside each ticket's card. Agent sessions that belong to no card are no longer listed.

Context size: pass skipped (no agent files changed)

## 2026-11-08 rename awaiting-spec to awaiting-build and SPEC READY to BUILD READY (CW-177) (#186)

Merged 2026-11-08 05:24 UTC.

The Chief of Staff's waiting stage is now `awaiting-build` and a child's spec report is now `BUILD READY`. State files and children started before this change still work. Nothing to do.

Context size: 178690 to 178835 characters (+145 from main)

## 2026-11-08 show spec-stage tickets in a Speccing dashboard group (CW-182) (#185)

Merged 2026-11-08 05:19 UTC.

Tickets whose spec is still being written now show under "Speccing" in the dashboard, the status pane and the `status` answer, instead of "Other".

## 2026-11-08 list subagent threads under each Running child (CW-94) (#180)

Merged 2026-11-08 05:09 UTC.

The Chief of Staff's `Running` list now shows the subagent threads (implementer, docs check, code review and others) under each running ticket, so you can open them from the report. Nothing to do on your side.

## 2026-11-08 nest each agent Gantt chart under its status card (CW-181) (#184)

Merged 2026-11-08 05:08 UTC.

The local dashboard now shows each agent's Gantt chart inside the status card of its ticket, collapsed until you open it. Sessions that don't belong to a card stay in the Agents list.

Context size: pass skipped (no agent files changed)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-08 show dashboard Gantt charts only for worktree sessions (CW-178) (#183)

Merged 2026-11-08 05:06 UTC.

The dashboard's Agents view now shows Gantt charts only for sessions running in a worktree, so the Chief of Staff thread and other root-checkout sessions no longer get a chart. Nothing to do.

## 2026-11-08 delete the old-shape CW-55 and CW-51 closeout files (CW-69) (#179)

Merged 2026-11-08 04:58 UTC.

The CW-55 release note no longer prints twice, and the unused `docs/superpowers/index/` folder is gone. Nothing to do.

## 2026-11-08 fit the dashboard to a narrow side pane and show a title on every row (CW-175) (#176)

Merged 2026-11-08 01:09 UTC.

The local dashboard now fits a narrow side pane and shows a title on each ticket row, reading a missing one from GitHub issues. A new `start` state op needs a title, so a rebuilt or adopted ticket never has a blank one.

Context size: 99026 to 99293 characters (+267 from main)

## 2026-11-08 show the status pane and agent Gantt in a local dashboard (CW-173) (#174)

Merged 2026-11-08 00:32 UTC.

`start the team` now also starts a local dashboard and opens it in T3's browser pane. It shows the Chief of Staff status and each session's agents as a Gantt chart, with links to issues and PRs. It needs Node 24 or newer; without it you get one line in the start report and everything else works as before.

## 2026-11-07 read the agent-gantt price table from the machine install (CW-171) (#172)

Merged 2026-11-07 23:28 UTC.

The agent-gantt cost column now reads the price table from `~/.collective-wisdom/scripts/prices.json`, so it shows dollar amounts in any repo once `./install.sh` has run. Update the mod with `claude plugin update agent-gantt`.

Context size: pass skipped (no agent files changed)

## 2026-11-07 remove the root links and rely on the machine install (CW-169) (#170)

Merged 2026-11-07 23:18 UTC.

This repo no longer links its files from the root into `agent-team/`. Run `./install.sh` once on the machine and the Chief of Staff here reads everything from `~/.collective-wisdom`, as an app does.

## 2026-11-07 ask setup questions before the Chief of Staff starts in a new repo (CW-163) (#168)

Merged 2026-11-07 22:46 UTC.

Saying `set up this repo` (or `start the team` in a repo whose `docs/agents/project.md` is missing or still holds template placeholders) now asks a few setup questions and opens a PR with `docs/agents/project.md` and the `.agent-team/` line in `.gitignore`. Merge that PR, pull, and say `start the team`. It asks before it creates the branch, commits, pushes or opens the PR, and never pushes to the merge target.

## 2026-11-07 choose the GitHub account per repo from the user install (CW-162) (#167)

Merged 2026-11-07 21:35 UTC.

The GitHub account for a repo now comes from `~/.config/collective-wisdom/user.md`, not from `project.md`. Before your next merge, add a row for each repo (and your subscription figure if you want cost percentages); see `github-auth.md` § Account per repo.

## 2026-11-07 leave only project.md from the team in a consuming repo (CW-161) (#166)

Merged 2026-11-07 20:24 UTC.

An app now commits only `docs/agents/project.md` from the team; skills, scripts and role docs come from the machine install. If an app still carries the old copied team, run `~/.collective-wisdom/scripts/remove_app_copies.py` in it and commit the removal as a PR. `install.sh <app>` no longer works.

Context size: 227377 to 227915 characters (+538 from main)

## 2026-11-06 install the agent team once per machine (CW-160) (#164)

Merged 2026-11-06 22:17 UTC.

Install the agent team once per machine with `./install.sh` from a clone of collective-wisdom (no target path). Every repo with a `docs/agents/project.md` then runs that clone's skills and scripts; update by checking out a newer release in the clone and running `./install.sh` again. Apps keep their copied files until the follow-on change removes them, but from this release on the copied skills call `~/.collective-wisdom/scripts/`, so an app updated the old way also needs the machine install on each machine.

Context size: 284185 to 288628 characters (+4443 from main, all from the `~/.collective-wisdom/` path prefix on script calls)

## 2026-11-06 reject an empty Backlog ranking when the Backlog has tickets (CW-150) (#158)

Merged 2026-11-06 20:58 UTC.

A Backlog ranking that comes back empty while the Backlog has tickets is now rejected instead of saved, so the Chief of Staff keeps the old ranking and tries again on a later turn. Nothing to do: it takes effect with the next tagged release.

## 2026-11-06 context compacter agent in the build (CW-72) (#154)

Merged 2026-11-06 04:50 UTC.

When a build adds text to a skill or role doc, a compacter subagent now tightens the added text before the PR opens, and the PR body shows the size change. The pass runs only in collective-wisdom itself; apps get the new files with the next install update and see no change.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-06 add the status pane to the plugin marketplace (CW-156) (#157)

Merged 2026-11-06 04:49 UTC.

The status pane can now be installed on a machine with `/plugin install status-pane@collective-wisdom`, after adding this repo as a plugin marketplace.

## 2026-11-06 run shellcheck and pytest in one CI job (CW-100) (#155)

Merged 2026-11-06 04:41 UTC.

CI now runs shellcheck and pytest in one job named `checks`, which saves one billed job minute per run. If you require CI on `main`, add `checks` as the required status check after this merges (see the spec).

## 2026-11-06 cancel superseded CI runs on the same PR (CW-101) (#153)

Merged 2026-11-06 04:20 UTC.

CI on this repo now cancels the run for an older commit when a newer push arrives on the same PR. Runs on `main` are not cancelled.

## 2026-11-06 show the ticket title in the status pane rows (CW-151) (#152)

Merged 2026-11-06 04:19 UTC.

The status pane now shows each ticket's title between its ID and its risk. Tickets the Chief of Staff started before this change show the ID alone until it sets a title. The pane's thread links and the `environmentId` option are gone.

## 2026-11-06 detect tickets in flight that Chief of Staff state doesn't know (CW-133) (#147)

Merged 2026-11-06 03:39 UTC.

The Chief of Staff now tells you about your own tickets that are in flight but missing from its state, for example after a rotation or on another machine. Say `adopt N` to add one to its state when its child thread is on this machine. It keeps listing the ticket until you do or label it `agent-skip`.

## 2026-11-06 live Gantt and cost pane for agents as a Claude Code mod (CW-96) (#149)

Merged 2026-11-06 03:38 UTC.

A new optional Claude Code mod, `agent-gantt`, shows this session's agents as a live Gantt chart with tokens, cost and child counts. Install it once per machine with `/plugin install agent-gantt --marketplace collective-wisdom-org/collective-wisdom`. Apps need no update to install it, but its cost column shows only once an app has taken the release that adds `scripts/prices.json`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-06 status pane that shows the Chief of Staff status report (CW-144) (#146)

Merged 2026-11-06 03:33 UTC.

A new `status-pane` mod shows the Chief of Staff status in a pane beside the chat, with links to each child thread and each subagent. After `install.sh --update`, load the mod in Claude Code, open it with `/status-pane` and set your T3 environment ID in the mod's options (see `docs/agents/status-pane.md`).

## 2026-11-06 install.sh fits repos with their own agent setup, adoption steps (CW-130) (#148)

Merged 2026-11-06 03:11 UTC.

`install.sh` now tells you what to merge by hand when your repo already has its own `AGENTS.md`, `.agents/skills` or `.claude/settings.json`, and the README has a step-by-step "Adopt in a repo" checklist. Nothing is changed in those files for you.

## 2026-11-06 write thread links as markdown links (CW-134) (#145)

Merged 2026-11-06 03:01 UTC.

The Chief of Staff now writes thread links as titled markdown links so they show as a name you can click instead of a raw `t3-thread://` string. Apps pick it up on the next install update.

## 2026-11-06 merge target branch setting (CW-125) (#132)

Merged 2026-11-06 02:55 UTC.

An app can now merge its PRs into a branch other than `main`, such as `dev`, by setting the `Merge target branch` row in `docs/agents/project.md`. Apps without the row keep merging into `main`; add the row only if you want a different branch.

## 2026-11-06 show subscription share next to ticket cost (CW-135) (#143)

Merged 2026-11-06 02:50 UTC.

When you type your Claude plan's API-equivalent dollars into `project.md`, a ticket's cost line also shows what share of that plan it used, for example `$14.20 API-equivalent (0.12% of the subscription)`. Leave the row at `none` and nothing changes.

## 2026-11-06 awaiting-review stage for PRs waiting on a teammate's review (CW-128) (#141)

Merged 2026-11-06 02:47 UTC.

A PR that waits for a teammate's GitHub review no longer needs anyone to watch it. The Chief of Staff holds the ticket in a new `awaiting-review` stage, tells you when a teammate approves, and sends the child back to build when a teammate asks for changes. You can reply `approve N` early; it is held until the teammate approves that head. Repos that don't use reviews see no change.

## 2026-11-06 resolve merge conflicts in the merge lane without a review restart (CW-138) (#142)

Merged 2026-11-06 01:01 UTC.

When a PR you approved for merge conflicts with `main`, the team now resolves it in the merge lane and merges it, without a second review or approval. Set `Review after conflict resolution` to `on` in `project.md` to review the resolution again. Apps without the row behave as `off`.

## 2026-11-06 Publish release notes setting (CW-129) (#139)

Merged 2026-11-06 00:30 UTC.

A repo can now turn release notes off with a `Publish release notes` row in `docs/agents/project.md` § Docs. New installs start with `off`; existing apps have no row, so they keep notes on and nothing changes for them.

## 2026-11-06 review mode setting that uses CI review instead of the agent reviewers (CW-126) (#137)

Merged 2026-11-06 00:26 UTC.

Repos whose CI already runs a review bot can set `Review mode` to `ci` in `docs/agents/project.md` (§ Review, with the bot's login). The team then answers and resolves the bot's review threads instead of running its own code and security reviewers, and merge waits for green checks and no unresolved bot thread. Nothing changes for repos without the row; add the section from the template to turn it on.

## 2026-11-06 let codeowners merge past a missing review through the Chief of Staff (#140)

Merged 2026-11-06 00:05 UTC.

Codeowners can now merge their own PRs through the Chief of Staff when the only blocker is a review required from another codeowner.

## 2026-11-06 require teammate approval and GitHub's required reviews before merge (CW-127) (#136)

Merged 2026-11-06 00:00 UTC.

A repo can now set `Require teammate approval` to `on` in `project.md`, and the merge gate then waits for a teammate's GitHub approval on the current head as well as your `approve N`. Whatever the setting, a PR that GitHub still holds for a required review now stops with the reviewers' names. `MERGE READY` lists the reviewers still requested.

## 2026-11-05 make team mode the only mode in the shipped skills (CW-58) (#131)

Merged 2026-11-05 23:35 UTC.

A hand-run `/ship-loop` now follows the same rules as a Chief of Staff child: it writes the spec without asking you questions first (choices go under `## Calls I made`), stops at `SPEC READY` for your approval, always commits and pushes, uses the `security-reviewer` subagent instead of the built-in `/security-review`, and no longer offers worktree cleanup after the merge. A merge approval counts only when you send it after the `MERGE READY` report, so "merge if reviewed" sent earlier no longer merges. Tasks that name a `Chief of Staff thread:` behave as before.

## 2026-11-05 approval risk tolerance setting (CW-108) (#119)

Merged 2026-11-05 21:02 UTC.

You can now choose how much the agent team asks you to approve. Commit an `Approval risk tolerance` row to `docs/agents/project.md` on `main`: `balanced` skips your reply for Low risk tickets and `permissive` also skips it for Medium. High risk tickets, tickets the team files for itself from its own observation, and changes to the team's own scripts, skills, agents, role docs under `docs/agents/` or `project.md`, still wait for you, and without the row nothing changes.

## 2026-11-05 reject a negated approval in cos_user_check (NH-35) (#124)

Merged 2026-11-05 19:28 UTC.

The Chief of Staff no longer treats a message such as "don't approve 30 yet" or "approve 30, no rush" as an approval. Send a plain `approve N` to approve; `cancel N` and `resume` need the same plain form. `stop everything` still stops even when negated, because stopping is the safe direction.

## 2026-11-05 keep the merge approval human-only after CW-110 (NH-29) (#123)

Merged 2026-11-05 16:24 UTC.

A push after a merge approval now stops the merge: the merge child reports `BLOCKED: head moved after approval` and you reply `approve N` again. The merge script also refuses to run unless gh is signed in as the owner, and `cos_approve_pr.py` shows the words it verified. After you update the agent team, rotate the Chief of Staff thread.

## 2026-11-05 Chief of Staff files agent-team tickets from repeated failures (CW-39) (#117)

Merged 2026-11-05 03:32 UTC.

The Chief of Staff now files an agent-team improvement ticket on its own when it sees the same kind of process failure repeat in a week (a lost notice or a stalled child on two tickets, say), or notices another problem worth fixing. The ticket goes to the Backlog marked as filed from its own observation, and the project manager ranks it like any other. Specs and merges still need your approval.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-05 open-source readiness sweep (CW-104) (#120)

Merged 2026-11-05 03:05 UTC.

The repo now carries a LICENSE (MIT), a SECURITY.md and a CONTRIBUTING.md, and the README no longer assumes the repo is private. Nothing to do in your app.

## 2026-11-05 skip pytest and shellcheck on docs-only changes (CW-102) (#121)

Merged 2026-11-05 02:44 UTC.

CI skips the pytest steps on PRs that change only Markdown files in `README.md` or under `docs/` (not `docs/agents/`). It skips the shellcheck step on any PR that changes no `.sh` file, no `.shellcheckrc` and nothing under `.github/`. Both checks still appear and finish green. Skill and role-doc edits still run pytest.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-05 require a Proof section in every PR (CW-107) (#109)

Merged 2026-11-05 02:03 UTC.

Every PR now carries a `## Proof` section showing evidence for each Acceptance item and a `Not proven` list. The merge script refuses a PR without them, so an open PR needs the section added before it can merge.

## 2026-11-05 point repo paths at collective-wisdom-org (#118)

Merged 2026-11-05 02:02 UTC.

The default clone URL for \`agent-team-update.sh\`, the README links, and the tracker scope now use \`collective-wisdom-org/collective-wisdom\`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-05 add noahstotland to CODEOWNERS (CW-113) (#114)

Merged 2026-11-05 01:46 UTC.

PRs will now request review from both David and Noah. Nothing to do on your side.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-05 remove the per-agent GitHub users, thread approval is the merge proof (CW-110) (#111)

Merged 2026-11-05 01:41 UTC.

The agent team no longer uses separate GitHub accounts per role: every PR, comment and ticket comes from the account running `gh`. A merge is approved by your `approve N` in the Chief of Staff thread alone; no GitHub review is posted or required. Remove the four login rows from your app's `docs/agents/project.md` on the next update, and drop any branch rule that requires a Code Owners review.

## 2026-11-04 author and push ticket branch commits as the builder user (CW-92) (#99)

Merged 2026-11-04 22:59 UTC.

Ticket branch commits from the builder child now show the builder user instead of a hostname email. To get it in an app, update the agent team; set `git config --global user.email` to an address on your own GitHub account so your hand commits link to you.

## 2026-11-04 skip the security review on docs-only diffs, merge the passes on small ones (CW-54) (#93)

Merged 2026-11-04 22:58 UTC.

Reviews now scale with the diff. A PR that only changes markdown under `docs/` (not `docs/agents/`, hidden folders, or agent config files such as `CLAUDE.md` and `AGENTS.md`) or the top `README.md` gets its code review and a short "skipped" security review comment. A PR of 200 changed lines or fewer gets both reviews from one run. Larger PRs are reviewed as before.

## 2026-11-04 let wait-for-ci.sh pass when project.md says there is no CI (CW-105) (#106)

Merged 2026-11-04 22:53 UTC.

`wait-for-ci.sh` now passes with `no CI declared` when `project.md` says there is no CI.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 accept a repository ruleset as the merge gate protection (CW-88) (#95)

Merged 2026-11-04 17:05 UTC.

The merge gate now accepts a repository ruleset that requires an approving review on `main`, not only classic branch protection. If the gate can't read either, it says so instead of claiming there is no protection.

## 2026-11-04 publish all release notes to a release-notes branch after each merge (CW-71) (#85)

Merged 2026-11-04 09:23 UTC.

After each team merge, all release notes are published as `RELEASE_NOTES.md` on the `release-notes` branch of the repo. Read it on GitHub instead of running `scripts/release_notes.py`. Nothing to do; the first merge after you update creates the branch.

## 2026-11-04 post the owner's approving review when the user approves a merge (CW-87) (#89)

Merged 2026-11-04 09:22 UTC.

When you reply `approve N` on a merge in the Chief of Staff thread, the Chief of Staff now posts your approving review on the PR for you, after checking that the message is yours. You no longer approve on GitHub first, though doing so by hand still works. You need to install the new release in each app.

## 2026-11-04 post a status line while the Chief of Staff takes over (CW-82) (#90)

Merged 2026-11-04 09:15 UTC.

A new Chief of Staff thread now posts a "Taking over" line as soon as the hand-off checks pass, then a "Take-over done" summary at the end.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 sort release notes by merge time (CW-41) (#83)

Merged 2026-11-04 08:53 UTC.

`python3 scripts/release_notes.py` now lists release notes by when their PR merged, newest first, and shows the merge time under each note it can date.

## 2026-11-04 require an owner approval on GitHub to merge (CW-52) (#84)

Merged 2026-11-04 08:42 UTC.

Merging now needs your approving review on the PR in GitHub, and `main` needs branch protection (setup steps in `docs/agents/github-auth.md`). Replying `approve N` in the Chief of Staff thread alone no longer lets a merge through.

## 2026-11-04 put the cost of each ticket in the merge brief (CW-57) (#81)

Merged 2026-11-04 08:41 UTC.

The merge request for each ticket now shows what the ticket cost to build, and the report after a merge repeats it. `status` shows the cost so far per ticket. Apps get it with the next `agent-team-update`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 set the security reviewer GitHub login (CW-77) (#80)

Merged 2026-11-04 07:10 UTC.

Security review comments on PRs now show `collective-wisdom-sentinel` instead of David. A PR that already has a passing security review by David needs `main` merged in and the review run again before it can merge.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 rotate the Chief of Staff thread less often (CW-53) (#79)

Merged 2026-11-04 07:09 UTC.

The Chief of Staff thread no longer rotates every time its own skill changes. A skill change waits for a quiet turn and at most one rotation an hour; threads no longer rotate just for being old. The size cap of 220k still rotates at once. Nothing to do on your side.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 move tracker hygiene into a one-shot project manager child (CW-56) (#78)

Merged 2026-11-04 07:00 UTC.

The Chief of Staff no longer scans the tracker on every message. Tidying (priorities, labels, stale tickets, duplicates) runs in a separate child at start-up, on `backlog`, and at most once a day, and ready tickets now go from the Backlog straight into work instead of through Todo. Apps pick this up with the next update.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 install from a pinned tag, one-command app update (CW-59) (#70)

Merged 2026-11-04 06:36 UTC.

Run `scripts/agent-team-update.sh v0.N` in an app to move its agent team to a release tag, with no clone of this repo. The maintainer tags releases with `./tag-release.sh` after a batch of merges. Apps get the new script on their next install.

## 2026-11-04 list running children in idle check reports (CW-68) (#74)

Merged 2026-11-04 06:26 UTC.

When the Chief of Staff reports after an idle check, the message now includes a `Running` list of the children still working, each with its ticket title and a link to its thread.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 set the code reviewer GitHub login (CW-75) (#76)

Merged 2026-11-04 06:18 UTC.

Code review comments in this repo now show the `collective-wisdom-reviewer` user instead of David. Nothing to do in your app. Open PRs that already have a code review from David need `main` merged in and the review run again before they can merge.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## 2026-11-04 shrink the files agents load without changing behaviour (CW-23) (#73)

Merged 2026-11-04 06:15 UTC.

The Chief of Staff skill now loads about 40% less text on every turn; rotation, cross-repo requests, the kill switch, the ticket helper and similar sections load only when needed. Nothing changes in how the team works. After the next install PR, an app's Chief of Staff thread starts smaller.

## 2026-11-04 CW-65: Builder PRs come from collective-wisdom-builder

Merged 2026-11-04 05:39 UTC.

Ship-loop pull requests, notes and ticket moves in this repo now show the `collective-wisdom-builder` user instead of David. Nothing to do in your app.

## 2026-11-04 lighten the closeout docs per ticket (CW-55) (#66)

Merged 2026-11-04 05:31 UTC.

The closeout is lighter: the as-built is one line in the spec unless the build differs, the release note is a section in the PR body, and the index is generated by `scripts/docs_index.py`. After you re-run `install.sh --update` in an app, copy `docs/superpowers/README.md` over by hand (the installer only adds it when missing); the app's old `index/` files can be deleted.

## 2026-11-04 CW-51: Chief of Staff trusts its state file

Merged 2026-11-04 05:17 UTC.

The Chief of Staff no longer re-reads T3 to double-check what its state file says about retirement, parent threads and wake tasks, so turns cost fewer tool calls. Pull the change into your app; old state files keep working.

## 2026-11-03 CW-42: Update and check an installed agent team

Merged 2026-11-04 04:55 UTC.

`install.sh --update <app>` now moves an app to the newest `origin/main` commit and reports what changed, and `install.sh --check <app>` says whether the app's copied files still match the commit in `installed-from.txt`. An update refuses when you have edited a copied file, unless you pass `--force`, and it never deletes old files; it lists them for you. Scripts now find the app from the repo you run them in.

## 2026-11-03 CW-38: Agent roles can act as their own GitHub users

Merged 2026-11-04 04:28 UTC.

Each agent role can now post as its own GitHub user, with a short persona, instead of as you. Nothing changes until you create the accounts and fill in the four login rows in `project.md`; `github-auth.md` § Agent users has the steps. Merges still run as you.

## 2026-11-03 CW-49: Child thread link under the ticket in status

Merged 2026-11-04 04:24 UTC.

In the Chief of Staff's `status` table, the link to a ticket's child thread now sits in the Ticket cell under the ID and title, not at the end of Next. Nothing to do on your side beyond pulling the change into your app.

## 2026-11-03 CW-40: More tests for the Chief of Staff's wait check

Merged 2026-11-04 04:21 UTC.

Nothing changes for you. The check that tells a waiting child from a stalled one now has tests for the output shapes it had no coverage for.

## 2026-11-03 CW-21: Children waiting on CI are no longer restarted

Merged 2026-11-04 02:47 UTC.

The Chief of Staff now checks whether a finished child run is only waiting on a background command, such as CI, before it calls the child stuck. Waiting children are left alone. After this lands, re-run `install.sh` in each app to pick it up.

## 2026-11-03 CW-17: Cross-repo Chief of Staff requests

Merged 2026-11-04 02:42 UTC.

A Chief of Staff can now pass your request for a ticket in another repo to that repo's Chief of Staff. It checks that you wrote the request and files it as a Backlog ticket, and the ticket link comes back to the thread where you asked. Both repos need the install.

## 2026-11-03 CW-35: Plan for one release notes file on GitHub

Merged 2026-11-04 02:41 UTC.

The options for a single release notes file you can read on GitHub are compared on issue #35. The pick is to publish it to a separate `release-notes` branch after each merge. Nothing changes yet; a follow-up ticket builds it.

## 2026-11-03 CW-16: Warning when a relay may finish unannounced

Merged 2026-11-04 02:39 UTC.

The Chief of Staff now adds a line under Moving when it sends work to a child it won't hear back from: `I may not hear when this run ends; say status to check.` No timer, scheduled wake or new Stop hook was added; apps get the line the next time `install.sh` runs.

## 2026-11-03 CW-14: Continuation children for more relays

Merged 2026-11-04 02:35 UTC.

After a Chief of Staff handoff, a restart, an answer to a blocked ticket, `resume` or a rate-limit continue now starts a new child that reports to the current Chief of Staff, as long as the old child left nothing unpushed. If it did, the relay goes to the old child as before. Apps get this the next time `install.sh` runs; nothing else to do.

## 2026-11-03 CW-12: Grouped status and a risk level on every approval

Merged 2026-11-04 02:00 UTC.

`status` now answers with tickets grouped by what each one waits on, and every ticket and approval request shows a risk level (Low, Medium or High) with a short reason. The level only informs you; every ticket still needs your `approve N`. Apps get this the next time `install.sh` runs.

## 2026-11-03 CW-15: Chief of Staff rules reviewed, none changed

Merged 2026-11-04 01:59 UTC.

The idle check, rotation chain walk, approval gates, lane limits and models were reviewed one by one and all five stay as they are. The reasons are on issue #15; nothing for you to do.

## 2026-11-03 Tests for the Chief of Staff ready check

Merged 2026-11-04 01:47 UTC.

Nothing changes for you. The ready check that finds a lost `MERGE READY` or `SPEC READY` notice now has tests for its real GitHub call and for running from a symlinked root, so a break there is caught before it reaches a Chief of Staff pass.

## 2026-11-03 CW-11: More reliable Chief of Staff relays

Merged 2026-11-04 01:34 UTC.

A Chief of Staff now finds a child that finished without its notice reaching it, through one new command (`scripts/cos_sweep.py`) that the skill runs on every turn. Continuation children start with a `HANDOFF` block of the branch, spec, PR, head and reviews. Apps get both the next time `install.sh` runs; nothing else to do.

## 2026-11-03 CW-13: Release notes in the closeout docs

Merged 2026-11-04 01:18 UTC.

Every PR now adds a short release note under `docs/superpowers/release-notes/`, and `merge_pr.py` refuses to merge without one. Run `python3 scripts/release_notes.py` to read all the notes in one place, newest first.

## 2026-11-03 GUY-330: Parity with the IHAG team files and install version pin

`install.sh` now records the installed commit in `docs/agents/installed-from.txt`, refuses a dirty or non-git checkout, and warns about old skill copies it no longer ships (it never deletes them). A change to a shared team file now ships as a collective-wisdom PR plus an install PR in the app. The Chief of Staff also no longer limits how many specs can wait for review.

## 2026-11-03 GUY-316: Docs check and documenter subagent

The ship loop now runs a docs check before code review: a documenter subagent compares the PR against the living docs and reports stale ones, and the review comment carries a `Docs checked:` line. After you re-run `install.sh` in an app, fill in the new Docs check section of its `project.md`.

## 2026-11-03 CW-28: Publish the agent team

The agent team (Chief of Staff, project manager pass, ship loop, PR and security reviews) now lives in this repo and installs into any app with `./install.sh /path/to/app`. After installing, fill in the app's `docs/agents/project.md` and `AGENTS.md`. Re-running the script updates the app.

## 2026-11-03 CW-27: Choose Linear, GitHub Issues or Jira as the tracker

Set the `Tracker` row in `docs/agents/project.md` to `linear` (the default), `github` or `jira`, and the skills use that tracker's adapter. The Jira adapter has not been run against a real Jira site, so work through the checklist in `docs/agents/trackers/jira.md` before relying on it.

## 2026-11-03 CW-25: Backfill release notes

`python3 scripts/release_notes.py` now also lists the five PRs merged before release notes existed, so it shows the whole history of the agent team.

## 2026-11-03 CW-9: Chief of Staff for collective-wisdom itself

You can now run a Chief of Staff from this repo's root, so changes to the agent team go through the same ship loop as an app. Tickets are GitHub issues with the `CW` prefix, and this repo's `project.md` stays local and is never shipped to apps.
