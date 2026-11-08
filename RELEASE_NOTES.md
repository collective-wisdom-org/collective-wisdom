# Release notes

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

## 2026-11-04 CW-55: Lighter closeout docs

Merged 2026-11-04 05:31 UTC.

A ticket that ships as specified now needs only its spec (with a `**Shipped:** in PR #N, as specified` line) and a `## Release note` section in the PR body; an as-built file is written only when the build differs. `scripts/docs_index.py` builds the index from the docs, `scripts/release_notes.py` also reads merged PR bodies, and `merge_pr.py` accepts both the new and the old shape. After `install.sh --update`, copy `docs/superpowers/README.md` over by hand and delete the app's old `index/` files.

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
