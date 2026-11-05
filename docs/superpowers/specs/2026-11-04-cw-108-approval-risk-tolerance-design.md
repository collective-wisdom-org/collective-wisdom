# CW-108: Let users set how much the agent team asks them to approve

**Ticket:** [CW-108](https://github.com/collective-wisdom-org/collective-wisdom/issues/108)
**Status:** Shipped
**Shipped:** in PR #119, with differences: [as-built](../as-built/2026-11-04-cw-108-approval-risk-tolerance.md)

## Goals

- A new `project.md` row, `Approval risk tolerance`, lets the user pick `strict`, `balanced` or `permissive`.
- `strict` is today's behaviour, and a missing row or an unknown value reads as `strict`.
- Under `balanced`, a Low ticket is approved without a reply. Under `permissive`, a Low or Medium ticket is. A High ticket always waits for the user's `approve N`.
- An auto-approval is checked by a script before the Chief of Staff relays it, just like a user approval is today. The relay and the ticket comment say it was auto-approved and under which setting.
- CI, the code review PASS, the security review PASS and every other `merge_pr.py` gate still apply at every level.
- No ticket, comment, PR or child can raise the setting or approve itself through it.

## Non-goals

- Changing how the Chief of Staff rates risk (approvals.md § Risk level keeps its table).
- Per-ticket or per-area levels.
- Removing or softening any review gate.
- Changing `scripts/merge_pr.py`. It has no user-approval check left to satisfy (below).

## Today

Facts from `main` at `b6b2692`, checked 2026-11-04.

- The ticket's "Today" section is out of date. CW-110 (#111) removed `owner_approval()` from `merge_pr.py`. The user's merge approval is now proven in the Chief of Staff thread: `scripts/cos_approve_pr.py <PREFIX>-N` checks the user's own `approve N` in T3's message store, that gh is signed in as the owner, and that the PR is open, not a draft, based on `main` and at the head in state. Only when it exits 0 does the Chief of Staff relay the merge (`github-auth.md` § Merge gate). `merge_pr.py` then checks CI, both review PASS comments, closeout docs and the head, and merges at that head.
- A spec approval is proven by the child itself: before it builds, it reads the Chief of Staff thread and needs a `createdBy: "user"` message approving the spec (ship-loop § Team mode, **Relays**).
- `approvals.md` § Risk level rates each spec and merge Low, Medium or High and stores it as the `Risk: <Level> (<reason>).` tail of the ticket's `awaiting-spec` or `awaiting-merge` status line. Line 90: "The risk level informs the user and nothing else. It never approves a ticket ..."
- `cos_brief.py pr` prints `flag:` lines (paths that look like auth, user email, money or migrations) and a `migrations:` line.
- `project_config.py` reads `project.md` from the working tree of the current checkout (`PROJECT_MD` overrides it in tests).
- `install.sh` seeds `docs/agents/project.md` from `agent-team/templates/project.md` only when the app has none, so `--update` never adds the new row to an existing app.

## Design

### The setting

A new row in the Identity table of `agent-team/templates/project.md` and of this repo's `docs/agents/project.md`, under `Approver`:

```
| Approval risk tolerance (`strict`, `balanced` or `permissive`) | `strict`. Which approvals the team takes without asking: `strict` none, `balanced` Low risk only, `permissive` Low and Medium. High always waits for you |
```

It is read from `main` as committed on `origin`, never from a working tree: `git fetch origin main`, then `git show origin/main:docs/agents/project.md`. So a feature branch can't change it for its own approval, and an uncommitted edit doesn't count. To change it, the user commits to `main` by hand or merges a PR, and a PR that touches `project.md` always waits for the user (§ The approval path).

`project_config.py` gets `approval_tolerance()`. It runs the fetch and the `git show`, parses the text with the same row reader the other values use, and returns `strict`, `balanced` or `permissive`. A missing row, a missing file, an unknown value or a failed git call returns `strict`, with the reason, so every read failure fails closed.

### The decision rule

New `agent-team/scripts/approval_policy.py`, one pure function and a small CLI.

| Tolerance | Low | Medium | High | Not rated |
|---|---|---|---|---|
| `strict` | ask | ask | ask | ask |
| `balanced` | auto | ask | ask | ask |
| `permissive` | auto | auto | ask | ask |

The same rule applies to a spec and to a merge. Each decision reads the setting again, so a change on `main` between spec and merge counts at the merge.

### The approval path

Under any setting, a merge is never auto-approved if the PR adds, edits or deletes a file on the approval path. The script holds the list, matched with or without a leading `agent-team/` and ignoring case:

- everything under `docs/agents/` (`project.md`, the review rules and every other role doc, trackers included), and `templates/project.md`
- dot-directories and dot-files at any depth (`.claude`, `.github`, `.agents`, `.cursor`, `.codex`, `.vscode`, `.mcp.json`, `.gitignore` and the like)
- everything under `scripts/`, and the bare name of that root link
- `templates/AGENTS.md`, and any file at any depth named `AGENTS.md` or `CLAUDE.md` or like `AGENTS.override.md` and `CLAUDE.local.md`

Without this, `permissive` would let a Medium PR (Medium covers "changes how the team itself works") rewrite the gate that let it through. A spec has no diff yet, so approvals.md adds the same rule in prose: the Chief of Staff doesn't auto-approve a spec whose Builds change a file on this list. If it gets that wrong, the merge check still stops the PR.

### Spec auto-approval

On `SPEC READY`, the Chief of Staff rates the spec as today and writes the `awaiting-spec` status line with its `Risk:` tail. Then, from the root checkout:

```
python3 scripts/approval_policy.py auto <PREFIX>-N spec
```

It reads the ticket from the state file (stage must be `awaiting-spec`), takes the level from the `Risk:` tail of its status line, reads the setting and applies the rule. Last line:

- exit 0: `approval: auto spec <PREFIX>-N under <tolerance> (Risk: <Level>)`
- exit 1: `approval: ask <PREFIX>-N (<why>)`, for example `strict`, `High`, `not rated`
- exit 2: `approval: cannot <what>`. Treated as ask.

On exit 0, the Chief of Staff posts the full spec block as a notice, with this last line in place of the reply line: `Auto-approved under <tolerance>; the build has started. Reply "cancel N" to stop it.` (`the build starts when a slot frees` when the relay is queued) Then it runs § Send or queue as for `approve N` (Models switch included) with this relay:

```
CHIEF OF STAFF: auto-approved the spec under `<tolerance>` (Risk: <Level> (<reason>)). Continue to the build stage.
```

It comments on the ticket: `auto-approved the spec at <time> under <tolerance> (Risk: <Level> (<reason>)).` On exit 1 or 2, it asks the user as today.

The child can't read the Chief of Staff's state, so ship-loop § Relays gets a second accepted form. For a relay that starts `CHIEF OF STAFF: auto-approved the spec`, the child runs `python3 scripts/approval_policy.py check <Level>` from its worktree. That reads the setting from `origin/main` and applies the rule to the relayed level. On exit 0 it builds. Otherwise it stops with `BLOCKED:` and the script's last line. It also stops with `BLOCKED:` if its own spec changes a file on the approval path. The proof is the setting on `main`.

### Merge auto-approval

On `MERGE READY`, the Chief of Staff rates the merge, writes `awaiting-merge` with its `Risk:` tail, and runs:

```
python3 scripts/cos_approve_pr.py <PREFIX>-N --auto
```

`--auto` runs every gate the script runs today, in the same order, except the user's message: root checkout, state (`awaiting-merge`, PR, full head SHA), gh login is the owner, PR open, not a draft, not a fork, base `main`, head matches state. In place of the message check it needs all of these:

1. The rule says auto for the `Risk:` tail in state and the setting on `origin/main`.
2. No PR file is on the approval path.
3. `cos_brief.py`'s `flags_for` and migration check give no `flag:` line and no migration file. These already make a merge High, and checking them here means a mis-rated merge still waits.

Exit 0 last line: `cos-approve: auto-approved #<N> at <SHA> under <tolerance> (Risk: <Level>)`. Exit 1: `cos-approve: stop <PREFIX>-N: <reason>`, and the Chief of Staff asks the user as today. Exit 2 as today. Without `--auto` the script is unchanged.

On exit 0, the Chief of Staff posts the merge block as a notice ending `Auto-approved under <tolerance>; merging now. Reply "cancel N" to stop it.`, comments `auto-approved the merge at <time> under <tolerance> (Risk: <Level> (<reason>)). Head <sha>.`, runs the head check and § Send or queue, and relays:

```
CHIEF OF STAFF: auto-approved the merge of PR #X at head <short SHA> under `<tolerance>` (Risk: <Level> (<reason>)).
```

merge-pr § Team mode accepts that relay like a user approval: its proof is that `cos_approve_pr.py --auto` passed, and `merge_pr.py` still merges only at the named head. A push after `MERGE READY` means a new `MERGE READY` and a new decision, as today.

### Doc changes

- `approvals.md`: replace line 90 with the rule table, the approval-path rule for specs, the notice block endings and the auto-approval ticket comments. Add the `auto` call to § Approval requests after the rating.
- `chief-of-staff/SKILL.md`: § Tools lists `approval_policy.py`; § Send or queue and § Commands take the auto relays; the Models table row on who proves approvals names the setting.
- `ship-loop/SKILL.md` § Team mode **Relays**: the auto spec relay and its `check`.
- `merge-pr/SKILL.md` § Team mode: the auto merge relay.
- `github-auth.md` § Merge gate: one paragraph on `--auto`.
- `README.md`: one paragraph on the setting, its levels and the `strict` default.
- `install.sh`: the project.md seed note also says to pick an `Approval risk tolerance` (`strict` if left as is). An existing app's `project.md` isn't touched, so it stays `strict` until the user adds the row.

### Tests

- `test_approval_policy.py`: one table over tolerance (each level, missing row, unknown value, failed read) and risk (each level, not rated) giving auto or ask; one table over PR paths giving on or off the approval path, with and without the `agent-team/` prefix; one table for reading the level from a status line's `Risk:` tail.
- `test_cos_approve_pr.py`: one table for `--auto` with fake state, gh and setting: Medium under `permissive` passes; High, `strict`, a file on the approval path, and a `flag:` path each stop it, no user message is read, and the other gates still stop it.

## Acceptance

- With no row, or `strict`, every spec and merge waits for the user's `approve N`, as today.
- With `permissive` on `main`, a Low or Medium ticket goes from `SPEC READY` to build, and from `MERGE READY` to merge, with no user reply. A High one waits.
- A PR touching a file on the approval path waits for the user at every level.
- The setting read from a feature branch or an uncommitted edit has no effect.
- `merge_pr.py` gates are unchanged.
- The tests above pass.

## Calls I made

- ⚠ Under `permissive`, most agent-team changes are Medium and would merge without you. I carved out the approval path: any PR touching `project.md`, any role doc under `docs/agents/`, any script, any dot-directory or dot-file at any depth, the root `install.sh` or `tag-release.sh`, or any `AGENTS.md` or `CLAUDE.md` file always waits for you, at every level.
- ⚠ This repo's own row is set to `strict`, so nothing changes here until you change it.
- The setting counts only as committed on `origin/main`. An edit in the root checkout that isn't committed and pushed does nothing.
- Spec and merge use the same rule. There is no "auto-approve specs but always ask before merge" mode.
- For an auto-approved spec, the child checks the setting itself but trusts the Chief of Staff's risk level, because only the Chief of Staff keeps it. The merge check is stricter: it re-checks flags, migrations and the approval path from the PR's files, so a spec rated too low still stops at merge if it touched those.
- An auto-approval still posts the full block to you as a notice, so you see what went through, and `cancel N` stops it.
- An unknown or misspelled value, a missing row and any read failure all count as `strict`.
- An unrated ticket always waits.
- The ticket asked how an auto-approved merge satisfies `merge_pr.py`'s owner-review check. That check is gone since CW-110, so `merge_pr.py` stays as it is and the new route is `cos_approve_pr.py --auto`.
