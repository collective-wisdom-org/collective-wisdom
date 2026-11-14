# CW-306 plan: allow infra/ ticket branches

Spec: `docs/superpowers/specs/2026-11-14-cw-306-infra-branches-design.md` (approved). Follow its Design steps 1 to 7. Test budget: `AGENTS.md` § Testing, one table-driven test per rule.

## Task 1: project_config
Add `branch_heads(rows=None)` (brace list `{a,b}/<prefix>...`, names `[a-z0-9-]+`, bad list or missing row gives `("feat/",)`). `branch_head()` returns the first. Merge target refusal (`project_config.py` ~216) refuses any head. Test in `test_project_config.py`.
Verify: `python3 -I -m pytest -q agent-team/scripts/test_project_config.py`

## Task 2: python scripts
`cos_handoff.branch_re`, `cos_merged_check`, `cos_ready_check` (`branch_prefixes`, one `matching-refs` call per head), `cos_untracked_check.prs_by_ticket`, `agent_usage.py` (3 regexes), `cos_brief.BRANCH_RE`. Add `infra/` rows to the existing tests (CW-1 vs CW-11, `fix/` no match, merge target refusal).
Verify: `python3 -I -m pytest -q agent-team/scripts`

## Task 3: dashboard
`headsFromProject` in `dashboard/titles.ts`, passed from `server.ts`; `api.ts` `ticketOf` and `merged.ts` `byBranch` use it (default `['feat/']`). Add `infra/` cases to `api.test.ts`, `merged.test.ts` and a `headsFromProject` table.
Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`

## Task 4: prose and config
Edit the skills, role docs, template and this repo's `docs/agents/project.md` exactly as spec step 5 and 6. Set the spec `Status:` to Implemented only at closeout (open-pr), not here.
Verify: `/usr/bin/grep -rn "feat/" agent-team/.claude agent-team/docs agent-team/templates` shows only intended examples; `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
