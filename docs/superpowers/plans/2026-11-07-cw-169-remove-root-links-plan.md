# CW-169 plan: remove the root links

Spec: [design](../specs/2026-11-07-cw-169-remove-root-links-design.md). Shared files are edited under `agent-team/`. One write scope, run in order by one implementer.

## Tasks

1. Delete the links and the shipped settings file (spec § 1): `git rm` the 18 tracked links (`git ls-files -s | grep '^120000'`), and `git rm agent-team/.claude/settings.json`. Check `.claude/` and `.agents/` are gone from the tree.
2. Tests (spec § 2): `git rm agent-team/scripts/test_root_links.py`. Add one test to `agent-team/scripts/test_agent_files.py`: `docs/agents/project.md` at the top is a real file (not a link) and `agent-team/docs/agents/project.md` does not exist. In `test_call_sites.py` drop the `EDITED` dict and its use. Run `python3 -I -m pytest -q agent-team/scripts`; it fails until task 3 fixes the trackers README, so run it after task 3.
3. Paths in docs (spec § 3): edit `AGENTS.md`, `docs/agents/project.md`, `CONTRIBUTING.md`, `README.md`, `agent-team/docs/agents/chief-of-staff.md`, `agent-team/.claude/skills/chief-of-staff/approvals.md`, `agent-team/docs/agents/trackers/README.md`, `agent-team/docs/superpowers/README.md` as the spec says. Prose follows `human-writing`: plain sentences, no em dashes.
4. Verify (spec § 4): `git ls-files -s | grep '^120000'` is empty; `python3 -I -m pytest -q agent-team/scripts`; `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`; `python3 ~/.collective-wisdom/scripts/docs_index.py` from the worktree top; the spec's grep finds nothing outside the old records.

Tests stay within `AGENTS.md` § Testing: one added test, one file and one dict removed.
