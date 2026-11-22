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

Phase 3 (**open-pr**) complete: PR exists, CI green, **latest code review** PR comment **Verdict: PASS** (`open-pr` § Agent review comment loop). Work from the PR's worktree, on the PR head branch. In `ci` mode (`docs/agents/project.md` § Review) this phase does not run (`open-pr` § CI review mode).

## Primary review path

When `~/.collective-wisdom/scripts/review_scope.py` prints `docs-only` for the head, this review is skipped; on `small` it is already posted from the combined run (`open-pr` § Review scope).

**Cursor:** start a general subagent on Auto (`chief-of-staff/models.md` § Models Cursor; if the tool can't pick a model, the child's own) with the prompt `Read ~/.collective-wisdom/docs/agents/security-review.md and follow it. Do not edit files.` plus the **worktree path** (absolute, the worktree holding the PR branch, not the root checkout unless the branch lives there), the **diff** (the branch changes against `origin/<target>`) and the **Custom Instructions** below. Ignore Cursor's own `review-security` skill in the ship loop.

**Claude Code:** from the PR worktree, start the `security-reviewer` agent (`Agent` tool, `subagent_type: "security-reviewer"`; fallback `ship-loop` § Models) with the diff and the Custom Instructions below. Always use the subagent, so the review runs on Opus and not on the child's model.

**Custom Instructions** (always apply):

- Frame findings against OWASP Top 10:2025 (A01 to A10), ASVS themes and, when the diff touches LLM chat, tools, MCP, RAG or agent loops, the OWASP Top 10 for LLM Apps and Agentic Applications (2026) (prompt injection, excessive agency, insecure tool output; `~/.collective-wisdom/docs/agents/security-review.md` § OWASP references).
- **Product security overlays:** the list in `docs/agents/project.md` § Security overlays (for example tenant scoping, admin checks). Always: no secrets in the repo; session and auth patterns must match the existing code.

Vendored OWASP skills (`~/.collective-wisdom/docs/agents/security-review.md` § Vendored open-source skills): if on disk, read the relevant sections before or after the subagent; never fail if missing.

## PR comment loop

Mirror **open-pr** § Agent review comment loop as a **separate** security thread (never mix it with code review comments). Post as a PR issue comment only, each one before you mention it in the thread, and keep its URL:

```bash
~/.collective-wisdom/scripts/gh.sh pr comment <N> --body-file <path>
```

**Comment shape:** title `## Security review (pass N)`; a compact findings table (**Severity**, **Location**, **Finding**) when the subagent reports issues; end with **Verdict:** `CHANGES NEEDED` or `PASS`. **Must fix before PASS:** Critical, High, and any finding tagged Must fix.

**Loop until PASS:**

1. Run the review (§ Primary review path), post the comment (pass N).
2. On **CHANGES NEEDED**, fix in the worktree, commit, push. A fix that changes what ships updates the `**Shipped:**` line or as-built, the PR body's release note (if any) and `## Proof` in the same commit.
3. Wait for CI (`ship-loop` § CI waits).
4. Re-run the review (focus on changes since the last pass), post the next pass.
5. Repeat until the **latest security review** comment is **PASS**. If nothing exploitable remains, post **PASS**; don't invent issues.

### Forbidden

`~/.collective-wisdom/scripts/gh.sh pr review --approve`, and merging (**merge-pr**'s job, only on a merge approval, `ship-loop` § Approvals).

## Done when

The latest **security review** PR comment is **Verdict: PASS**. Report **merge-ready** (needs code review **PASS** and security **PASS**); until then keep going after phase 3 **PASS**. Ad hoc `/review-security` and `/security-review` are not part of the loop (`~/.collective-wisdom/docs/agents/security-review.md` § Built-in review commands).
