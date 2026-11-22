# Agent docs

| Doc | What it is |
|---|---|
| `project.md` (in the app, `docs/agents/project.md`) | Repo-specific config: tracker, scope and prefix, branch pattern, commands, repo invariants |
| [`org-chart.md`](org-chart.md) | Roles, reporting lines, where the owner approves |
| [`chief-of-staff.md`](chief-of-staff.md) | Chief of Staff role doc |
| [`ticket-writer.md`](ticket-writer.md) | Ticket writing; points at the `write-ticket` skill |
| [`documenter.md`](documenter.md) | Documenter subagent: docs check against a PR diff |
| [`compacter.md`](compacter.md) | Compacter subagent: shorten agent text a build added, keep every rule |
| [`implementer.md`](implementer.md) | Implementer subagent: do the task, verify, never push or merge |
| [`code-review.md`](code-review.md) | Code-reviewer subagent: review method for a PR diff |
| [`security-review.md`](security-review.md) | OWASP-aligned PR security review, vendored security skills; [`security-review-reference.md`](security-review-reference.md): refresh commands |
| [`trackers/README.md`](trackers/README.md) | Ticket operations, one adapter per tracker (Linear, GitHub Issues, Jira) |
| [`github-auth.md`](github-auth.md) | GitHub auth and the `~/.collective-wisdom/scripts/gh.sh` wrapper; [`github-auth-setup.md`](github-auth-setup.md): MCP and PAT setup |
| [`secrets.md`](secrets.md) | Keychain secrets without the value reaching a thread |

Unless `Publish release notes` in project.md § Docs is `off`, every merge publishes all release notes to `RELEASE_NOTES.md` on the `release-notes` branch, at `https://github.com/<owner>/<repo>/blob/release-notes/RELEASE_NOTES.md` (Repo row in project.md).

Area role docs (backend, frontend, design and so on), when an app has them, sit in the app's `docs/agents/` next to `project.md` and are listed in the app's `AGENTS.md`.
