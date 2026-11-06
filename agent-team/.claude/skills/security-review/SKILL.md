---
name: security-review
description: >-
  OWASP-aligned security review for PRs before merge; uses Cursor's
  review-security subagent or the security-reviewer subagent on Claude Code.
user-invocable: true
---

# Security review

Before acting, read **ship-loop** § Repo invariants.

## Prerequisite

Phase 3 (**open-pr**) complete: PR exists, CI green, and the **latest code review** agent PR comment has **Verdict: PASS** (see `open-pr` § Agent review comment loop).

Work from the PR's worktree, on the PR head branch.

In `ci` mode (`docs/agents/project.md` § Review) this phase does not run: the CI review bot covers it (`open-pr` § CI review mode).

## Primary review path

When `scripts/review_scope.py` prints `docs-only` for the head, this review is skipped, and on `small` it is already posted from the combined run (`open-pr` § Review scope).

**Cursor:** read and follow the **review-security** skill in full; its subagent launch mechanics are not repeated here. When launching the security-review subagent, use:

- **Full Repository Path:** absolute path to the **worktree** containing the PR branch, not the root checkout on `main` unless the branch lives there.
- **Diff:** `branch changes` (default).
- **Custom Instructions:** the list below.

**Claude Code:** from the PR worktree on the head branch, start the `security-reviewer` agent (the `Agent` tool, `subagent_type: "security-reviewer"`) with the diff and the list below. If that type isn't listed (the session started before `.claude/agents/security-reviewer.md` existed), start a general Opus subagent with the prompt `Read docs/agents/security-review.md and follow it. Do not edit files.` plus the diff and the list. Always use the subagent, so the review runs on Opus and not on the child's own model.

**Custom Instructions** (always apply):

- Frame findings against **OWASP Top 10:2025** (A01 Broken Access Control incl. SSRF, A02 Misconfiguration, A03 Supply Chain, A04 Crypto, A05 Injection, A06 Insecure Design, A07 Auth Failures, A08 Integrity, A09 Logging, A10 Exceptional Conditions).
- Apply **OWASP ASVS** themes where relevant (V2 auth, V4 access control, V5 validation, V8 data protection). No need to cite every ASVS level.
- **Product security overlays:** the list in `docs/agents/project.md` § Security overlays (for example tenant scoping, admin checks). Always: no secrets in repo; session/auth patterns must match the existing code.
- If the diff touches **LLM chat, tools, MCP, RAG, or agent loops:** also check **OWASP Top 10 for LLM Apps** and **Agentic Applications (2026)** (prompt injection, excessive agency, insecure tool output).

## Optional deeper OWASP skills

If present on disk, read relevant sections before or after the subagent. **Do not fail** if missing:

| Path | Source |
|------|--------|
| `.claude/skills/owasp-security/SKILL.md` | agamm/claude-code-owasp |
| `.claude/skills/agent-security/SKILL.md` or repo `AI_SECURITY.md` | olanokhin/agent-security-skill |
| `.claude/skills/auditing-security/SKILL.md` | spencerpauly/awesome-cursor-skills |

Install instructions: **`docs/agents/security-review.md`**.

## PR comment loop

Mirror **open-pr** agent review, but as a **separate** security thread (never mix it with code review comments).

Post as a PR issue comment only. Post each security review comment on the PR before you mention it in the thread, and keep the comment URL:

```bash
./scripts/gh.sh pr comment <N> --body-file <path>
```

**Comment shape:**

- Title line: `## Security review (pass N)`
- When the subagent reports issues, include a compact findings table (**Severity**, **Location**, **Finding**) from the review output.
- End with **Verdict:** `CHANGES NEEDED` or `PASS`.

**Must fix before PASS:** Critical, High, and any finding tagged Must fix (same bar as code review for exploitable issues).

**Loop until PASS:**

1. Run security review (per § Primary review path) → post comment (pass N).
2. If **CHANGES NEEDED**, fix in worktree → commit → push. If a security fix changes what ships, update the `**Shipped:**` line or as-built, and the PR body's release note (if any) and `## Proof` section, in the same commit.
3. Wait for CI with `./scripts/wait-for-ci.sh <N>` (`ship-loop` § CI waits), not a bare `pr checks --watch`.
4. Re-run security review (focus on changes since last pass) → next pass comment.
5. Repeat until the **latest security review** PR comment verdict is **PASS**.

Be honest: if nothing exploitable remains, post **PASS**. Do not invent issues.

### Forbidden

- `./scripts/gh.sh pr review --approve`
- Merging is **merge-pr**'s job (`scripts/merge_pr.py`), only on a merge approval (`ship-loop` § Approvals)

## Done when

Latest **security review** PR comment is **Verdict: PASS**. Report **merge-ready** (requires code review **PASS** + security **PASS**).

## Next

**merge-pr** only on a merge approval (`ship-loop` § Approvals).

Continue this phase after phase 3 **PASS** until security **PASS** before handoff.

## Optional (user-initiated)

User may run **`/review-security`** (Cursor) or **`/security-review`** (Claude Code) ad hoc on local changes; the ship loop uses **security-review** for the gated PR comment loop above.
