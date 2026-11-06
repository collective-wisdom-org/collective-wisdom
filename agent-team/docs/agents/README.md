# Agent docs

| Doc | What it is |
|---|---|
| [`project.md`](project.md) | Repo-specific config the skills read: tracker, scope and prefix, branch pattern, commands, repo invariants |
| [`org-chart.md`](org-chart.md) | The agent team: roles, reporting lines, where the owner approves |
| [`chief-of-staff.md`](chief-of-staff.md) | Role doc for the Chief of Staff agent |
| [`ticket-writer.md`](ticket-writer.md) | Role doc for ticket writing; points at the `write-ticket` skill |
| [`documenter.md`](documenter.md) | Role doc for the documenter subagent: the docs check against a PR diff |
| [`implementer.md`](implementer.md) | Role doc for the implementer subagent: do the task, verify, never push or merge |
| [`code-review.md`](code-review.md) | Role doc for the code-reviewer subagent: the review method for a PR diff |
| [`security-review.md`](security-review.md) | OWASP-aligned PR security review and the vendored security skills |
| [`trackers/README.md`](trackers/README.md) | The ticket operations the skills use, and one adapter per tracker: Linear, GitHub Issues or Jira |
| [`status-pane.md`](status-pane.md) | The `status-pane` mod: how to turn it on and what it leaves out |
| [`github-auth.md`](github-auth.md) | GitHub auth for agents and the `./scripts/gh.sh` wrapper |

Release notes: unless `Publish release notes` in project.md § Docs is `off`, every merge publishes them all to `RELEASE_NOTES.md` on the `release-notes` branch, at `https://github.com/<owner>/<repo>/blob/release-notes/RELEASE_NOTES.md` (Repo row in project.md).

Area role docs (backend, frontend, design and so on), when an app has them, sit beside these files and are listed in the app's `AGENTS.md`.
