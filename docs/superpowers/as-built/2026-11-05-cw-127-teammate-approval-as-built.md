# As-built: require a teammate's GitHub approval and GitHub's required reviews before merge

**Shipped:** in PR #136
**Ticket:** CW-127
**Spec:** [2026-11-05-cw-127-teammate-approval-design.md](../specs/2026-11-05-cw-127-teammate-approval-design.md)

## Differs from the spec

- The spec says team names are built from the `reviewRequests` entry's organization and slug fields. gh's `reviewRequests` entry for a team carries `name` and `slug` but no organization, so `merge_pr.py` builds `@<owner>/<slug>` with `<owner>` from project.md's `Repo` row (`project_config.repo()`), and prints `@<slug>` when the repo is unset.
