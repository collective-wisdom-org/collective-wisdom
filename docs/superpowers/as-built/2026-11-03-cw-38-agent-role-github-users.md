# As-built: Give each agent role its own GitHub user and persona

**Shipped:** in PR #48
**Ticket:** CW-38 (#38)
**Spec:** [2026-11-03-cw-38-agent-role-github-users-design.md](../specs/2026-11-03-cw-38-agent-role-github-users-design.md)
**Plan:** [2026-11-03-cw-38-agent-role-github-users.md](../plans/2026-11-03-cw-38-agent-role-github-users.md)

## What shipped

- `project_config.role_login(role)` and `python3 -I scripts/project_config.py login <role>`. Roles: `chief-of-staff`, `builder`, `code-reviewer`, `security-reviewer`. A missing row, `none`, an empty cell or `TODO(...)` reads as unset; a value that is not a GitHub login, or an unknown role, is an error.
- `gh.sh` reads `AGENT_GH_ROLE`. Unset, or a role whose row is unset: the active gh account, as before. A role with a login runs that one `gh` call with `GH_TOKEN` from `gh auth token -u <login>`. A bad role, a bad row or a login missing from the keyring exits 2 with one line and no `gh` call.
- Four rows in `project.md` § Git and GitHub (this repo and the template), all `none`.
- `merge_pr.py`, `cos_handoff.py` and `cos_brief.py` (`moved_line`) count `## Code review` from the code reviewer login, `## Security review` from the security reviewer login and `Head moved to` from the builder login. An unset row falls back to the running account.
- `personas.md` (Morgan, Sam, Riley, Quinn), linked from `org-chart.md`, the docs README and, through a root link, `docs/agents/`.
- `github-auth.md` § Agent users and the role checks in § Verify.
- Skills: `ship-loop` § Team mode "GitHub users", plus short edits in `open-pr`, `security-review`, `merge-pr`, `chief-of-staff`, `project-manager` and `write-ticket`. The GitHub adapter's Own login and Team tickets rules name the Chief of Staff login.

## Differs from the spec

- `merge_pr.py` stores the resolved logins as `f["authors"]`. A bad login row ends the run with `cannot read PR #N` and exit 2.
- `docs/agents/personas.md` is a root link, because `test_root_links.py` requires every shared agent doc to be linked.

## Verification

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh agent-team/scripts/*.sh` pass.
- By hand, with a temp `PROJECT_MD` naming `cw-sam` and no such keyring account: `AGENT_GH_ROLE=builder ./scripts/gh.sh api user` exits 2 with `gh.sh: no gh login for cw-sam; run gh auth login, then gh auth switch -u <owner>`.

## Not verified

- The live check (a PR whose author is the builder user and review comments from the two reviewer users). The accounts don't exist yet, so the rows ship as `none` and nothing changes until the owner follows `github-auth.md` § Agent users.
