# Security review

Before merge the ship loop runs **security-review** (phase 4): on Claude Code the `security-reviewer` subagent (Opus) against the OWASP list; on Cursor a general subagent on Auto given this doc. Either way on the PR branch worktree.

## OWASP references

Frame findings against:

- **OWASP Top 10:2025**: access control (incl. SSRF), misconfiguration, supply chain, crypto, injection, insecure design, auth failures, integrity, logging, exceptional conditions.
- **OWASP ASVS** where relevant: auth (V2), access control (V4), validation (V5), data protection (V8).
- **OWASP Top 10 for LLM Apps** and **Agentic Applications (2026)** when the diff touches LLM chat, tools, MCP, RAG or agent loops.

Product overlays: the app's `docs/agents/project.md` § Security overlays. The baseline (no secrets in repo, session and auth patterns matching existing code) is in **security-review**.

## Security reviewer subagent

Read only: do not edit, commit or push. In the PR worktree on the head branch, review `git diff origin/<target>...HEAD` (`<target>` is the merge target branch) against the OWASP list the **security-review** skill gives you and return findings with severity and location. The child posts the PR comment and fixes what you find.

## PR gate

Findings are posted as PR issue comments (`## Security review (pass N)` … **Verdict:** `PASS` or `CHANGES NEEDED`). Merge requires the latest security review **PASS** plus code review **PASS** (**merge-pr**). In `ci` review mode neither agent review runs (`project.md` § Review, `open-pr` § CI review mode).

## Built-in review commands

Ad hoc only; the ship loop uses **security-review** for the comment loop and merge gate. Cursor: **`/review-security`**, if installed. Claude Code: **`/security-review`** (reviews the current branch's changes).

## Vendored open-source skills

Under `.claude/skills/` in the repo. **security-review** reads them when present and skips gracefully when absent. Refresh commands: `security-review-reference.md`.

| Directory | Upstream |
|---|---|
| `owasp-security/` | [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) |
| `agent-security/` | [olanokhin/agent-security-skill](https://github.com/olanokhin/agent-security-skill) |
| `auditing-security/` | [spencerpauly/awesome-cursor-skills](https://github.com/spencerpauly/awesome-cursor-skills) (`resources/auditing-security`) |
