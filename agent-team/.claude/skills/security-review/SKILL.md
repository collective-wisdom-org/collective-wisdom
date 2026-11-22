---
name: security-review
description: >-
  OWASP-aligned security review for PRs before merge; uses the
  security-reviewer subagent, or a general subagent given security-review.md.
user-invocable: true
---

# Security review

Read **ship-loop** § Repo invariants first.

## Prerequisite

Phase 3 (**open-pr**) complete: PR exists, CI green, **latest code review** comment **Verdict: PASS** (`open-pr` § Agent review comment loop). Work in the PR's worktree on the PR head branch. In `ci` mode (`docs/agents/project.md` § Review) this phase does not run (`open-pr` § CI review mode).

## Primary review path

When `~/.collective-wisdom/scripts/review_scope.py` prints `docs-only` for the head this review is skipped; on `small` it is already posted from the combined run (`open-pr` § Review scope).

**Cursor:** a general subagent on Auto (`chief-of-staff/models.md` § Models Cursor; the child's own model if the tool can't pick one) with the prompt `Read ~/.collective-wisdom/docs/agents/security-review.md and follow it. Do not edit files.` plus the absolute **worktree path** of the PR branch, the **diff** (branch changes against `origin/<target>`) and the **Custom Instructions** below. Ignore Cursor's own `review-security` skill.

**Claude Code:** from the PR worktree, the `security-reviewer` agent (`Agent` tool, `subagent_type: "security-reviewer"`; fallback `ship-loop` § Models) with the diff and the Custom Instructions. Always the subagent, so it runs on Opus, not the child's model.

**Custom Instructions** (always):

- Frame findings against OWASP Top 10:2025, ASVS themes and, when the diff touches LLM chat, tools, MCP, RAG or agent loops, the OWASP Top 10 for LLM and Agentic Applications (2026) (`~/.collective-wisdom/docs/agents/security-review.md` § OWASP references).
- Product security overlays: `docs/agents/project.md` § Security overlays. Always: no secrets in the repo; session and auth patterns match the existing code.
- Vendored OWASP skills, when on disk: `~/.collective-wisdom/docs/agents/security-review.md` § Vendored open-source skills.

## PR comment loop

Mirror **open-pr** § Agent review comment loop as a **separate** security thread (never mixed with code review comments): PR issue comments only, each posted before you mention it, URL kept: `~/.collective-wisdom/scripts/gh.sh pr comment <N> --body-file <path>`.

**Comment shape:** title `## Security review (pass N)`; a compact findings table (**Severity**, **Location**, **Finding**) when there are issues; end with **Verdict:** `CHANGES NEEDED` or `PASS`. **Must fix before PASS:** Critical, High, and any finding tagged Must fix.

**Loop until PASS:** run the review (§ Primary review path) and post the comment (pass N). On **CHANGES NEEDED**, fix in the worktree, commit and push (closeout docs per `open-pr` § Closeout docs, same commit), wait for CI (`ship-loop` § CI waits), re-run the review (focus on changes since the last pass) and post the next pass, until the **latest security review** comment is **PASS**. If nothing exploitable remains, **PASS**; don't invent issues.

### Forbidden

Any GitHub review (`ship-loop` § Repo invariants); merging (**merge-pr**'s job, only on a merge approval, `ship-loop` § Approvals).

## Done when

The latest **security review** comment is **Verdict: PASS**. Report **merge-ready** (needs code review **PASS** and security **PASS**); until then keep going after phase 3 **PASS**.
