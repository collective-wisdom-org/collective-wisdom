# As-built: Author and push ticket branch commits as the builder user

**Shipped:** in PR #99
**Ticket:** CW-92
**Spec:** [2026-11-04-cw-92-builder-commit-identity-design.md](../specs/2026-11-04-cw-92-builder-commit-identity-design.md)

## Differs from the spec

- The spec exits 2 on any push remote that isn't https. `git.sh` also accepts `file://` and absolute local paths, which use no credential, so a push there cannot go out under the wrong identity.
- The spec finds `push` as the first argument. `git.sh` skips git's leading options (`-C <dir>`, `-c <k=v>`, `--git-dir`, `--work-tree`, `--namespace`) so they cannot hide a push, and runs its own checks with the same options.
- The push check covers the commits of `HEAD`. `git.sh push origin other-branch` checks `HEAD`'s unpushed commits, not that ref's.
