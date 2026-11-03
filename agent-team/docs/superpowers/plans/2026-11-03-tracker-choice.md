# Tracker choice plan

**Spec:** [2026-11-03-tracker-choice-design.md](../specs/2026-11-03-tracker-choice-design.md)
**Branch:** `feat/tracker-choice`, worktree `.worktrees/tracker-choice`. Commit after each task with a conventional message ending in the `Co-Authored-By` line. Do not push.

Run commands from the worktree root. Prose follows the `human-writing` skill: plain sentences, no em dashes.

## Task 1: `tracker()` in project_config

Files: `agent-team/scripts/project_config.py`, `agent-team/scripts/test_project_config.py`.

1. Add tests first: no `Tracker` row returns `linear`; empty cell and `TODO(owner)` return `linear`; `github` and `jira` (also upper case `GitHub`) return lower case; `` `trello` `` raises `SystemExit`; a missing project.md file returns `linear`.
2. Add `tracker()`: `value("Tracker")`, lower-cased, default `linear`, `SystemExit` with a message naming the allowed values otherwise.

Verify: `python3 -m pytest -q agent-team/scripts/test_project_config.py` (fails before step 2, passes after).
Commit: `feat: project_config.tracker() reads the Tracker row`.

## Task 2: Operation vocabulary

Files: new `agent-team/docs/agents/trackers/README.md`.

Contents: what an adapter is and how a skill finds it (the `Tracker` row); scope (`<TEAM>`); the operation table from the spec with each operation as a name in backticks; states; labels; priority; fields; the efficiency rules; how to add a tracker. Link it from `agent-team/docs/agents/README.md`.

Verify: `grep -c '^| `' agent-team/docs/agents/trackers/README.md` lists the 15 operations.
Commit: `docs: define the tracker operation vocabulary`.

## Task 3: Linear adapter

Files: new `agent-team/docs/agents/trackers/linear.md`.

One `### \`op\`` heading per operation, each with the exact current Linear MCP call and arguments, copied from the calls in `chief-of-staff/SKILL.md`, `project-manager/SKILL.md`, `write-ticket/SKILL.md`, `open-pr`, `merge-pr` and `reference.md`. A Rules section holds the Linear-only rules now inline in chief-of-staff § Lean turns and project-manager: `fields` on every read, `save_issue` once per ticket per turn and it returns the whole issue, `addLabels` and `removeLabels` instead of `labels`, one `state` per `list_issues` call (`backlog`, `unstarted`, `started`), `cursor` paging, `includeRelations`, `updatedAt` filter. Setup holds `list_issue_labels` and `create_issue_label` for `agent` and `agent-skip`.

Verify: Task 6's test (adapter coverage) once it exists; until then `grep -c '^### `' agent-team/docs/agents/trackers/linear.md` equals 15.
Commit: `docs: add the Linear tracker adapter`.

## Task 4: GitHub adapter (draft)

Files: new `agent-team/docs/agents/trackers/github.md`.

Write from the spec's GitHub section: ID shape, states, priority, type and area labels, each operation with its `./scripts/gh.sh issue ...` or `./scripts/gh.sh api ...` command, the sub-issue and dependency endpoints with the probe and the text fallback, `Closes #N`, efficiency rules, and a Setup section with the label-creation commands (list first, create what is missing). Mark every command not yet run as `draft` until Task 9.

Verify: `grep -c '^### `' agent-team/docs/agents/trackers/github.md` equals 15.
Commit: `docs: add the GitHub Issues tracker adapter (draft)`.

## Task 5: Jira adapter

Files: new `agent-team/docs/agents/trackers/jira.md`.

First line after the title: a bold UNTESTED banner saying nobody with Jira access has run it. Then the tool-name table from the spec (Atlassian Rovo MCP v2, source URL `https://support.atlassian.com/atlassian-rovo-mcp-server/docs/supported-tools/`, checked 2026-11-03), the Primary-versus-discover note, the `project.md` rows, the status map and the transition rule (fetch transitions, match target status, stop on no match), priority map, labels, parent, `Blocks` link direction, JQL for `list-tickets` and `list-children`, and one `###` section per operation. End with the assumptions checklist from the spec's Testing section as `- [ ]` items.

Verify: `grep -c '^### `' agent-team/docs/agents/trackers/jira.md` equals 15; `grep -c '^- \[ \]' ...` is at least 8.
Commit: `docs: add the Jira tracker adapter (untested)`.

## Task 6: Docs test

Files: new `agent-team/scripts/test_tracker_docs.py`.

- Parse operation names from the table in `trackers/README.md` (backticked first cell, split on `,` for rows with two operations).
- Parametrize over `linear.md`, `github.md`, `jira.md`: every operation has a `### \`op\`` heading.
- Scan `.claude/skills/**/*.md`, `docs/agents/*.md`, `templates/*` (not `trackers/`) for the forbidden tool names listed in the spec; report file and line.
- Resolve paths from `Path(__file__).resolve().parent.parent` so it also runs in an installed repo.

Verify: `python3 -m pytest -q agent-team/scripts/test_tracker_docs.py`. The coverage tests pass. The forbidden-name test fails and lists the skill lines Tasks 7 and 8 fix; that failure is the work list.
Commit: `test: check tracker adapters cover the vocabulary and skills name no tool`.

## Task 7: Reword the skills

Change only tracker wording and tool names. Keep every gate and rule. Each file gets the one-line pointer to the vocabulary and adapter, tool lists become "Tracker: the operations in the adapter doc", `Linear` becomes "the tracker" or "the ticket", and frontmatter descriptions drop Linear.

Do these as separate commits:

1. `kickoff-feature`, `write-ticket`, `build-from-plan`, `open-pr` (add `Closes #N` rule for `github` in the PR body step; as-built header `**Linear:**` becomes `**Ticket:**`), `merge-pr`.
2. `ship-loop` incl. § Team mode.
3. `project-manager`.
4. `chief-of-staff/SKILL.md` and `reference.md`. The Linear-only rules in § Lean turns shrink to a pointer to the adapter plus the tracker-neutral versions. Setup step 1 becomes `ensure-labels`. Do not touch any gate, number, state op or report format.

For each commit: `git diff` read once with tracker words masked to confirm nothing else moved, and `python3 -m pytest -q agent-team/scripts/test_tracker_docs.py` shows fewer hits.
Commit messages: `docs: tracker-neutral wording in <skills>`.

## Task 8: Docs, templates, README

Files: `agent-team/docs/agents/{README,chief-of-staff,org-chart,ticket-writer}.md`, `agent-team/templates/project.md` (add the `Tracker` row, the Jira and GitHub row examples as comments or a short "Choosing a tracker" section, and generalise the Linear rows), `agent-team/templates/AGENTS.md`, `README.md` (Requirements: tracker MCP depends on the choice; add "Choosing a tracker" section with how to set the row, the switch caveat, and Jira untested; Known couplings line). In org-chart, the Mermaid node `Linear` becomes `Tracker`.

Verify: `python3 -m pytest -q agent-team/scripts` passes in full, including the forbidden-name test. `grep -rniE 'linear' agent-team README.md` shows only `linear.md`, the Linear options in the template and README, and the tracker README.
Commit: `docs: choosing a tracker in the README, template and role docs`.

## Task 9: Exercise the GitHub adapter for real

Target: `dbeallor/collective-wisdom`. Use `./scripts/gh.sh` from `agent-team/` (path `agent-team/scripts/gh.sh` from the root). Start with `./scripts/gh.sh auth status`. If auth is missing or a call is refused, record that operation as untested; do not guess.

Run in order and record the real output shape for each:

1. `ensure-labels`: create `status:backlog`, `status:todo`, `status:in-progress`, `status:in-review`, `priority:urgent|high|medium|low`, `type:feature|improvement|bug`, `agent`, `agent-skip` (a name that already exists is left alone and not deleted at the end). Keep a list of the ones this task created.
2. `create-ticket`: a throwaway issue, titled `tracker-choice adapter test (delete)`, plus a second one to act as parent and a third as a blocker.
3. `list-tickets` with `--json` fields, by state label, by `updated` filter and by title text; confirm Backlog (no `status:` label) can be listed.
4. `get-ticket` with fields.
5. `set-state` through each label, then close as completed (Done), reopen, close as not planned (Canceled). Check the `status:` swap happens in one edit.
6. `add-label` and `remove-label`; `set-priority`.
7. `comment` and `read-comments`.
8. `edit-description` with a patch.
9. `set-parent`, `list-children`, `set-blocked-by` through the sub-issue and dependency endpoints; run the probe and record 200 or 404. If a call fails, try the text fallback and record that.
10. `set-related` (text line) and `ticket-url`.
11. Check that adding only a label moves the issue's `updatedAt`.

Then fix `github.md` so every command and output note matches what ran, drop the `draft` marks, and add a "Verified" line with the date and `gh` version. Cleanup: close all throwaway issues (not planned), delete the labels this task created (`./scripts/gh.sh label delete <name> --yes`), and confirm with `./scripts/gh.sh issue list --state all --search 'tracker-choice adapter test'` and `./scripts/gh.sh label list`.

Verify: `python3 -m pytest -q agent-team/scripts/test_tracker_docs.py`; label list shows none of the created labels; issues are closed.
Commit: `docs: GitHub adapter verified against a live repo`.

## Task 10: Installer and CI

Files: none unless a fix is needed (`install.sh`).

1. `mkdir /tmp/tc-target && git -C /tmp/tc-target init -q && ./install.sh --dry-run /tmp/tc-target` lists `docs/agents/trackers/{README,linear,github,jira}.md` as `add`. Clean up the temp dir.
2. `shellcheck install.sh agent-team/scripts/*.sh` if shellcheck is installed; otherwise say it was skipped.
3. `python3 -m pytest -q agent-team/scripts` (CI's command, with `uvx pytest -q agent-team/scripts` as the fallback).

Commit only if a fix was needed: `fix: install the trackers docs`.

## Task 11: Final review

- `git diff origin/main --stat` and a read of the full diff for em dashes (grep the changed files for the U+2014 character), stray Linear tool names and broken relative links.
- Re-read the Linear adapter against the removed skill text: every removed rule has an entry.
- Update the spec's status to `Approved`/`Built` only after the user approves; leave `Draft` otherwise.

Verify: full pytest run, the grep checks, `git status` clean.
