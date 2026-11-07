# As-built: Choose the GitHub account per repo from the user install

**Shipped:** in PR #167
**Ticket:** CW-162
**Spec:** [2026-11-06-cw-162-github-account-per-repo-design.md](../specs/2026-11-06-cw-162-github-account-per-repo-design.md)

## Differs from the spec

- A `user.md` that exists but cannot be read (permissions, undecodable bytes) is an error that names the file. The spec only says a missing file is no mapping.
- `login()` finds its row by scanning every table row for a backticked repo key, so it does not depend on the `## GitHub accounts` heading.
- The standalone `test_gh_sh` env-var test became rows of the new table: an unmapped repo runs with `GITHUB_TOKEN` and `GH_TOKEN` set to a PAT and sees both unset.
- `open-pr/SKILL.md` and `chief-of-staff/approvals.md` also named the old rows and were updated.
- `gh.sh` follows a symlink to find its own folder, so it works when reached through `~/.collective-wisdom`.
- With a mapped login, `gh.sh` also clears `GH_ENTERPRISE_TOKEN` and `GITHUB_ENTERPRISE_TOKEN` for the token lookup and the final `gh` call, not only `GITHUB_TOKEN` and `GH_TOKEN`.
