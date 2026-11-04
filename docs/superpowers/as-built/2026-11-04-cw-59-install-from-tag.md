# As-built: Install from a pinned tag so an app update is one command

**Shipped:** in PR #70
**Ticket:** CW-59 (#59)
**Spec:** [2026-11-04-cw-59-install-from-tag-design.md](../specs/2026-11-04-cw-59-install-from-tag-design.md)
**Plan:** [2026-11-04-cw-59-install-from-tag-plan.md](../plans/2026-11-04-cw-59-install-from-tag-plan.md)

## Differs from the spec

- `--from` accepts only `^v0\.[0-9]+$`, which also rules out a leading `-`, so there is no separate `check-ref-format` step. A bad tag exits 2.
- `install.sh --update --from <tag>` refuses a tag older than the pin, because the update would move the app backwards; `--force` overrides it.
- `tag-release.sh` reads the tags on `origin` (`git ls-remote`), not the local ones, and `install.sh --from` replaces a stale local tag of the same name.
- `agent-team-update.sh` refuses a tag that is not on `origin/main` before it runs that tag's installer.
