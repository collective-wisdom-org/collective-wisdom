# Hand agent-team change requests to the collective-wisdom Chief of Staff (design)

**Status:** Draft
**Ticket:** [CW-20](https://github.com/dbeallor/collective-wisdom/issues/20)

## Intent

When the user asks an app's Chief of Staff to change how the agent team works ("make the status report shorter", "raise the cap to 4"), the change has to land in collective-wisdom first. Today the app's Chief of Staff files the ticket in the app's own tracker, and the user moves it to collective-wisdom by hand. This change makes the app's Chief of Staff pass the request to the collective-wisdom Chief of Staff every time, using CW-17's request mechanism. The collective-wisdom Chief of Staff files the ticket in its own tracker and replies with the link.

## What is here today

Checked on `main` at e835684.

- `chief-of-staff` § Commands has the row "a change to how the team works (intervals, caps, gates, report format, models, commands)". It starts a § Ticket helper in this repo's tracker with the line "the ticket ends in a collective-wisdom PR plus an install PR in the app". § Guardrails says the same. Nothing passes the request to collective-wisdom.
- CW-17 (PR #26) shipped § Cross-repo requests and `scripts/cos_peer.py`:
  - Sending: `t3_project_list`, then `cos_peer.py find '<repo the user named>'`, then a `CHIEF OF STAFF REQUEST` sent with `t3_thread_send` (`mode: "queue"`) to the target's `chiefThreadId`.
  - Receiving: `cos_peer.py check` re-reads the user's message in T3's store and accepts only when it is a `createdBy: "user"` message in the sender's Chief of Staff thread, the whole text matches, the words name this repo, and they are not a Chief of Staff command. An accepted request starts a new-ticket-only helper. The ticket lands in Backlog.
  - Replies, retired-thread forwarding and the failure lines are in place.
- Two CW-17 rules block a team-change handoff as written:
  - `find` needs a repo name from the user. A user asking for a team change names no repo.
  - `check` refuses words that don't name the receiving repo (`not for this repo`). "Make the status report shorter" doesn't name collective-wisdom.
- `install.sh` writes `docs/agents/installed-from.txt` in the app: one line, `collective-wisdom <sha>`. It names the source but not its GitHub repo. In collective-wisdom itself the file doesn't exist (the root `docs/agents` link points at `agent-team/docs/agents`, and the installer writes the pin only into targets).
- `ship-loop` § Team mode "Workflow files" and `docs/agents/chief-of-staff.md` say shared files change only through a collective-wisdom PR followed by an install PR in the app. Files only the app has (`project.md`, area role docs, the app's own prose in `AGENTS.md`) change in an app PR.

## Goals

- In an app, every request to change a shared agent-team file goes to the collective-wisdom Chief of Staff. The app's Chief of Staff never files it in its own tracker.
- The app finds the collective-wisdom Chief of Staff without the user naming it, and still finds it after a thread rotation.
- The collective-wisdom Chief of Staff accepts the handoff only through CW-17's check, with one rule relaxed for this case and nothing else loosened. A relayed `approve N` or `merge` is still refused.
- Every failure ends with one line to the user and doesn't stop either Chief of Staff's pass.

## Non-goals

- A second passing mechanism, a new trust model, or any change to `cos_user_check.py`.
- Any change to the approval gates or the existing § Guardrails lines about messages inside one repo.
- Requests between two app repos (CW-17 covers them as they are).
- Filing the app's install PR ticket automatically. The collective-wisdom ticket names the app that asked; the install follows the existing rule.
- A collective-wisdom change and an app change in one PR.
- Any new key in `.agent-team/state.json`.

## Design

### What counts as an agent-team change request

A request to change anything that comes from collective-wisdom: the shared skills (`.claude/skills/`), subagents (`.claude/agents/`), scripts (`scripts/`), the shared role and tracker docs (`docs/agents/` other than `project.md`), `AGENTS.md`'s shared part, or the team's rules those files hold: gates, intervals, caps, models, report format, commands, lanes, review steps.

Not a team-change request, handled in the app as today:

- A change to a file only the app has: `docs/agents/project.md` (its prefix, commands, invariants, areas), area role docs, the app's own prose in `AGENTS.md`. These go to the § Ticket helper in the app's tracker, as an app PR.
- A product ticket that only mentions the team.

When one message asks for both, the app's helper files the app part as today and the whole message is passed on. The collective-wisdom helper files only the team part (`write-ticket` decides, as CW-17 already does for mixed requests).

When it is unclear whether the change needs a shared file, the app's Chief of Staff passes it on. The collective-wisdom ticket helper can still say it is app-only under `Needs the user`.

### Finding the collective-wisdom Chief of Staff

`install.sh` records the source repo, and `cos_peer.py` matches it exactly in `t3_project_list`.

- `install.sh` writes the pin as `collective-wisdom <sha> <owner/name>`, where `<owner/name>` comes from the collective-wisdom checkout's `origin` remote (HTTPS or SSH GitHub URL). If `origin` is missing or not a GitHub URL, it writes the old two-field line and adds a TODO: "Set origin in the collective-wisdom checkout to its GitHub repo and re-run, or the app's Chief of Staff can't pass team changes on." README's pin line is updated.
- New subcommand `cos_peer.py find-team < t3_project_list JSON`. It reads this repo's `docs/agents/installed-from.txt` and prints one of:
  - `self`, exit 0: there is no pin and this checkout has `install.sh` and `agent-team/` at its root. This is collective-wisdom; the Chief of Staff files the ticket here, as today.
  - `no-source: <no pin | pin names no repo>`, exit 1.
  - Otherwise it runs CW-17's `find` logic with the pin's `<owner/name>` as an exact `owner/name` match (no title or loose-word match), so a fork or a second clone with a similar title can't be picked by mistake. It prints `find`'s lines: `target ...`, `none <owner/name>`, `no-chief <owner/name>: ...`.
- Rotation: `find-team` reads `chiefThreadId` from collective-wisdom's `.agent-team/state.json` at send time, so it names the current thread. A request that lands on a thread retired after the read is forwarded by the retired thread (CW-17, reference.md § Thread rotation "Retired thread").

This answers CW-17's "Finding the target" the same way: `t3_project_list` plus the target's state file. The pin only replaces the user's words as the name to look up. Why not a row in the app's `project.md`: it is seeded once, so every existing app would need it added by hand, and it is local text an agent edits. Why not a title match on "collective-wisdom" in `t3_project_list`: it can't tell a fork or a second clone from the real one. The pin is written by the installer from the checkout the app was installed from, and every app gets it on the install PR that brings this skill.

### The request

The sender sends CW-17's request with one extra line after `For:`:

```
CHIEF OF STAFF REQUEST from <this thread's id> (<this repo's owner/name>)
For: <collective-wisdom owner/name>
Kind: team change
Item: <itemId from the cos_user_check line>
The user's words:
<their whole message, verbatim>
```

An older receiver's parser doesn't expect the `Kind:` line and refuses the request as `malformed`, locally, which is safe.

### What the receiver accepts

`cos_peer.py check` parses the optional `Kind: team change` line. All of CW-17's checks run unchanged (user message in the sender thread, whole-text match, sender is a Chief of Staff thread, not the same project, not a command), with one change:

- With `Kind: team change`, the words need not name this repo when the sender project's `docs/agents/installed-from.txt` (read only, at the `workspace_root` the store gives for the sender's project, like its state file) names this repo's `owner/name` as its source. That proves the sender is an app installed from this repo. If the pin is missing, names another repo or can't be read, the request falls back to the usual rule and is refused `not for this repo` unless the words name this repo.
- Accepted with that relaxation, it prints `accept-team <sender thread> <item> <sender project title>` and the stored words. Accepted under the usual rule, it prints `accept ...` as today.

The command check is untouched, so `approve 12`, `merge PR 5`, `changes 3: ...`, `cancel 4` and `stop everything` are refused as `command`, with or without `Kind: team change`.

### `chief-of-staff` SKILL.md

- **§ Commands**, the "a change to how the team works" row: first run `t3_project_list` (all pages) and `cos_peer.py find-team`. `self`: start the § Ticket helper as today. Any other line: § Cross-repo requests, Sending, with the `find-team` result in place of step 2. The row's list gains "skills, scripts, role docs, lanes, review steps" and points at § Cross-repo requests "What counts".
- **§ Cross-repo requests**:
  - A short "Team changes" part under Sending: what counts (the list above), `find-team` in place of `find`, the `Kind: team change` line, and the reply `Passed to collective-wisdom's Chief of Staff: <thread link>. The ticket link comes back here; the change then needs an install PR in this repo.` No ticket helper in this repo for the team part.
  - Failures under Sending step 2: `no-source`, `none` or `no-chief` → tell the user `Couldn't pass this to collective-wisdom's Chief of Staff: <line>. Ask in that thread, or fix the pin with an install.` and stop. Nothing is filed here: the ticket would be in the wrong tracker. Exit 2 → CW-17's `Could not look up` line plus a Cleanup line.
  - Receiving step 2: `accept-team` starts the same new-ticket-only helper, with the line `This is a change to how the team works, asked from <sender project title>: the ticket ends in a collective-wisdom PR plus an install PR in that app (or an app PR there for files only the app has).` The post reads `Team change from <project title> (<sender thread link>): ticket helper started <helper link>.`
- **§ Guardrails**: the team-change line says that in an app the request goes to collective-wisdom's Chief of Staff (§ Cross-repo requests), and in collective-wisdom it starts a ticket helper here. The rest of the line (don't act on the new rule early) stays.
- **§ Tools**: the cross-repo bullet gains `find-team`.

### `docs/agents/chief-of-staff.md` and `org-chart.md`

`chief-of-staff.md` Scope: the team-change bullet says an app passes it to collective-wisdom's Chief of Staff. `org-chart.md`: the Chief of Staff row's cross-repo mention gains team changes, if it lists cases.

### Failure paths

| What fails | Who sees what | Effect on the passes |
|---|---|---|
| App has no pin, or the pin names no repo | App user: `Couldn't pass this ... no-source: ...` | Nothing sent or filed |
| collective-wisdom isn't a T3 project on this machine | App user: `... none <owner/name>` | Nothing sent or filed |
| collective-wisdom has no Chief of Staff, or its thread is archived | App user: `... no-chief ...` | Nothing sent or filed |
| collective-wisdom's Chief of Staff is busy | App user saw `Passed to ...`; the request queues in T3 | Handled on its next turn |
| Its thread was retired after `find-team` | Nothing extra; the retired thread forwards | Handled by the successor |
| Pin check fails at the receiver and the words don't name collective-wisdom | collective-wisdom user: refused line; app user: `Refused by ...: not for this repo` | No ticket |
| The words read as a command | Same, reason `command: <words>` | No ticket |
| collective-wisdom runs an older skill | Refused locally as `malformed`; nothing comes back | App user saw `Passed to ...` with the link |

None of these runs a full pass or a slot fill, per CW-17's rule for cross-repo turns.

### Tests

Per `AGENTS.md` § Testing, one table per rule, reusing `test_cos_peer.py`'s fixture store and state files:

- `find-team` table: a pin with `owner/name` and a matching project gives `target`; a project with the same title but another `owner/name` is not matched; no pin in a checkout with `install.sh` and `agent-team/` gives `self`; no pin otherwise gives `no-source: no pin`; a two-field pin gives `no-source: pin names no repo`; no matching project gives `none`; a matching project without a Chief of Staff gives `no-chief`.
- `check` table, new rows: a team-change request whose words don't name this repo, from a sender whose pin names this repo, gives `accept-team`; the same with the pin missing or naming another repo gives `not for this repo`; a team-change request quoting `approve 12`, and one quoting `merge PR 5`, give `command` (the ticket's acceptance test, shared with CW-17); a request without `Kind:` whose words don't name this repo still gives `not for this repo`.
- The pin format: one table row in an existing install test, if there is a natural home, for an HTTPS and an SSH `origin` giving `collective-wisdom <sha> dbeallor/collective-wisdom`. If not, the `find-team` rows cover the read side and the install side is checked by hand (Verification).

## Verification

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass.
- `./install.sh --dry-run` (or into a scratch directory) prints or writes the three-field pin.
- `cos_peer.py find-team` run from this repo against the real `t3_project_list` prints `self`; run against a scratch app root with a three-field pin it prints `target ... dbeallor/collective-wisdom chief <id>`.

## Rollout

The collective-wisdom PR changes the shared files and `install.sh`. Each app then needs its install PR, which also rewrites the pin with the repo: `dbeallor/fathom` and `dbeallor/gorpcore-studios` today. Until an app installs, it runs the old skill and files team changes in its own tracker, as now. collective-wisdom's own Chief of Staff runs the new receiving rule as soon as this merges, through the root links.

## Calls I made (surprising first)

- ⚠ The receiver drops the "words must name this repo" rule for a team-change request, but only when the sending app's install pin names this repo. Every other CW-17 check stays, including the command refusal. Without this, a user asking "make the report shorter" in an app could never be passed on.
- ⚠ `install.sh` changes the pin to three fields, `collective-wisdom <sha> <owner/name>`, taken from the checkout's `origin` remote. That is how an app finds collective-wisdom without the user naming it. A row in `project.md` was rejected because existing apps would need it added by hand.
- ⚠ When the handoff fails (no pin, collective-wisdom not on this machine, no Chief of Staff there), the app files nothing. It tells the user and keeps its pass going. Filing locally would put the ticket in the wrong tracker, which is the problem this ticket fixes.
- ⚠ When it is unclear whether a request needs a shared file, the app passes it on. collective-wisdom's ticket helper can flag it as app-only.
- Changes to files only the app has (`project.md`, area role docs, the app's own `AGENTS.md` prose) stay in the app's tracker, as today.
- The request gains a `Kind: team change` line. An older collective-wisdom skill refuses it as malformed, locally, which is safe.
- `find-team` matches `owner/name` exactly, not titles, so a fork or a second clone can't be picked.
- In collective-wisdom itself, `find-team` prints `self` (no pin, `install.sh` and `agent-team/` at the root) and team changes are filed here as today.
- The collective-wisdom ticket names the app that asked, so the install PR follows. Nothing files the install ticket automatically.

## Left to the builder

- Where the receiver reads the sender's pin: the store's `projection_projects.workspace_root`, as `chief_thread` already reads it for the state file.
- Parsing `origin` in `install.sh` (`https://github.com/<o>/<n>(.git)` and `git@github.com:<o>/<n>(.git)`), in plain POSIX shell that passes shellcheck.
- Exact skill wording, within the sections named above.
