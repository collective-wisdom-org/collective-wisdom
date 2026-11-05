# As-built: Approval risk tolerance

**Shipped:** in PR #119
**Ticket:** CW-108
**Spec:** [2026-11-04-cw-108-approval-risk-tolerance-design.md](../specs/2026-11-04-cw-108-approval-risk-tolerance-design.md)

## Differs from the spec

- The spec does not cover queued relays. Queue and continuation code recognised approvals only by the prefix `CHIEF OF STAFF: the user approved`, so `continuation.md`, `state-keys.md` and the queue wording in chief-of-staff `SKILL.md` now handle `auto-approved` relays too. A queued auto relay stores no `approvalItemId`, and the auto check runs again just before it is sent.
- `agent_usage.py` files the cost of `CHIEF OF STAFF: auto-approved the merge` under the merge stage.
- `cos_approve_pr.py --auto` stops when the PR has 100 or more files, because `gh` returns at most 100 and the approval-path and flag checks could not cover the rest.
- `approval_policy.py` accepts `-h` and `--help` (exit 0).
- `project_config.py` also has `approval_setting()`, which returns the level and the reason for a fallback to `strict`.
- The `Risk:` tail needs a valid level followed by a parenthesised reason. A status line with more than one `Risk: ` reads as not rated, so a title or reason cannot carry a second rating.
- The setting is read as `refs/remotes/origin/main:docs/agents/project.md`, so a local branch or tag named `origin/main` cannot win.
- A ticket queued with an auto-approved relay (`build-queued` for a spec, `merge-queued` for a merge) is re-checked by `approval_policy.py auto` and `cos_approve_pr.py --auto` just before the relay is sent.
- `cos_approve_pr.py --auto` stops when any PR file is renamed, because `gh` gives only the new path.
- For `CHIEF OF STAFF: auto-approved the spec`, the ship-loop child also reads the Chief of Staff thread and needs an assistant notice for the ticket saying `Auto-approved under <tolerance>`, else `BLOCKED:`.
- `agent_usage.py` also files the cost after `CHIEF OF STAFF: auto-approved the spec` under build.
- `approval_policy.py check` ends with `approval: auto spec under <tolerance> (Risk: <Level>)` or `approval: ask (<why>)`; the spec gave no format.
- The approval path is all of `docs/agents/` (trackers included), not just `project.md` and the two review docs. It also covers dot-directories and dot-files at the root (`.claude`, `.github`, `.agents`, `.cursor`, `.codex`, `.vscode`, `.mcp.json`, `.gitignore` and the like) and agent instruction files at any depth (`AGENTS.md`, `CLAUDE.md`, `AGENTS.override.md`, `CLAUDE.local.md`). Paths are compared in lower case, and the bare name of the `scripts` root link matches too.
- A queued auto spec relay always gets a one-line `Auto-approved under <tolerance>` notice in the sending thread just before it is sent. The notice says `the build starts when a slot frees` when the ticket is queued. A ship-loop child in a `TEAM MODE. CONTINUE` task needs that notice to be the newest Chief of Staff thread message about the ticket before its task started; the child that ran the spec needs it after its latest `SPEC READY`.
