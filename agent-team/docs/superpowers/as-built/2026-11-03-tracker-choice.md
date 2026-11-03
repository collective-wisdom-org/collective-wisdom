# As-built: Tracker choice

**Shipped:** in PR #5
**Ticket:** none (this repo has no Linear project)
**Spec:** [2026-11-03-tracker-choice-design.md](../specs/2026-11-03-tracker-choice-design.md)
**Plan:** [2026-11-03-tracker-choice.md](../plans/2026-11-03-tracker-choice.md)

## What shipped

- Tracker adapter docs in `agent-team/docs/agents/trackers/`: `README.md` (the shared operations), `linear.md`, `github.md`, `jira.md`.
- A `Tracker` row in `docs/agents/project.md` (and the template), defaulting to `linear`.
- `tracker()` in `agent-team/scripts/project_config.py` (matches the `Tracker` row by exact key, not the `Tracker scope` row), with tests in `test_project_config.py`, plus `test_tracker_docs.py` to keep the adapter docs consistent.
- Skills and role docs (chief-of-staff, project-manager, write-ticket, kickoff-feature, open-pr, merge-pr, ship-loop, build-from-plan, org-chart and others) reworded to describe tracker-neutral operations and point at the adapter.
- README and template wording on choosing a tracker.

## Verification

- `uvx pytest -q agent-team/scripts`: 208 passed.
- GitHub adapter exercised live against a throwaway issue in a real repo, then cleaned up (parent, `blocked_by` and `blocking` reads re-checked after the review, issues deleted). GitHub has no `status:backlog` label: Backlog is an open issue with no `status:` label.
- Linear adapter is the previous instructions moved into one place; no behaviour change intended.

## Not verified: Jira

The Jira adapter is **untested**. No one had Jira access, and its tool names come from Atlassian's published documentation, not a live session. Someone with Jira access must run the checklist at the end of `agent-team/docs/agents/trackers/jira.md` before Jira is advertised as supported.
- Security review fixes: the GitHub adapter sends bodies and comments with `--body-file -` and a quoted heredoc, and titles and search words in single quotes; `trackers/README.md` has a Shell safety rule that every adapter inherits, enforced by `test_tracker_docs.py`. A GitHub issue is a team ticket only if its author has triage or higher permission (collaborators permission endpoint); untrusted authors are skipped. `Approval withdrawn` counts only from the agent's own login (GitHub, Jira). Jira writes are limited to the project's keys and JQL title search escapes `"`.
