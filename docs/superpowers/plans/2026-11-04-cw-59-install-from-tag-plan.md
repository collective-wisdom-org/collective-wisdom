# CW-59 plan: install from a pinned tag

Spec: [2026-11-04-cw-59-install-from-tag-design.md](../specs/2026-11-04-cw-59-install-from-tag-design.md). Edit shared files under `agent-team/` only.

1. `install.sh`: add `--from <tag>` (fetch `origin main` and that one tag, look up `refs/tags/<tag>`, refuse `-` prefix, bad `check-ref-format`, `--to` together, `--check` together); pin regex accepts the optional ` v0.N` field; `--from` writes the three-field pin, everything else the two-field one; tag shown in the `--update` header, in `--check` output and in the "already at" comparison (whole pin line); update usage text and header comment.
2. `tag-release.sh` (root, not shipped): `--dry-run`, next `v0.N` numeric, refuse when `origin/main` already tagged, annotated tag, push only that tag.
3. `agent-team/scripts/agent-team-update.sh`: app root via `git rev-parse --show-toplevel`, refuse in collective-wisdom itself, clone `$COLLECTIVE_WISDOM_REPO` or the GitHub URL into a temp folder, pick the tag (given or highest `v0.N` merged into `origin/main`), run the tag's `install.sh --update --from <tag>` with `--dry-run`/`--force` passed through, remove the temp folder, exit with the installer's code.
4. Tests in `agent-team/scripts/test_install.py`: fixture gains tags `v0.1` (A), `v0.2` (B), `v0.9` (S) pushed to the bare origin; three tables (`--from`, wrapper, `tag-release.sh`) per the spec.
5. Docs: `README.md` (file list, Install, Update, new Releases, Propose changes, pin format), `ship-loop` Workflow files line, `agent-team/templates/AGENTS.md` line, `docs/agents/project.md` Lint row, `.github/workflows/ci.yml` shellcheck line.
6. Check: `python3 -I -m pytest -q agent-team/scripts`; `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
