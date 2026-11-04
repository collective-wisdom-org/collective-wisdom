# As-built: Install from a pinned tag so an app update is one command

**Shipped:** in PR #70
**Ticket:** CW-59 (#59)
**Spec:** [2026-11-04-cw-59-install-from-tag-design.md](../specs/2026-11-04-cw-59-install-from-tag-design.md)
**Plan:** [2026-11-04-cw-59-install-from-tag-plan.md](../plans/2026-11-04-cw-59-install-from-tag-plan.md)

## What shipped

- `install.sh --from <tag>`: fetches `origin/main` and that one tag (the `+` refspec replaces a stale local tag), looks the tag up as `refs/tags/<tag>`, and writes `collective-wisdom <sha> v0.N` to the pin. `--to` and plain installs still write the two-field line. The parser accepts both. `--update` and `--check` show the tag, and "already at" compares the whole pin line.
- `tag-release.sh` at the root (not shipped): tags `origin/main` with the next `v0.N` (numeric, so `v0.10` follows `v0.9`), refuses when `origin/main` already has a `v0.N` tag, pushes only that tag.
- `agent-team/scripts/agent-team-update.sh` (shipped as `scripts/agent-team-update.sh`): clones into a temp folder (`$COLLECTIVE_WISDOM_REPO` or the GitHub URL), picks the given tag or the highest `v0.N` merged into `origin/main`, and runs that tag's own `install.sh --update --from <tag>`. Refuses a tag that is not on `origin/main` before running its installer, and refuses inside collective-wisdom itself. It prints the source URL on success.
- `install.sh --update --from <tag>` refuses a tag older than the pin (it would move the app backwards); `--force` overrides it. `tag-release.sh` reads tags from `origin` (`git ls-remote`), not from local tags.
- Tests: `--from`, wrapper and tag-script tables in `test_install.py`; the `world` fixture pushes tags `v0.1`, `v0.2` and `v0.9` to the bare origin.
- Docs: README (Install, Update, new Releases, Propose changes), ship-loop "Workflow files", the AGENTS template line, the Lint row in `project.md`, the CI shellcheck line.

## Differs from the spec

- `--from` accepts only `^v0\.[0-9]+$`, which also rules out a leading `-`, so there is no separate `check-ref-format` step. A bad tag exits 2.
- The tables have a few extra rows: update at the same commit adds the tag to the pin, a `--to` install leaves the tag out, the wrapper refuses `v0.9` before running its installer, a failed clone prints the credentials hint, a tag older than the pin is refused, and `--force` overrides that.

## Checks

- `uvx pytest -q agent-team/scripts`: 518 passed. Shellcheck clean.
