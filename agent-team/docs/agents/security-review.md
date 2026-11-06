# Security review

Before merge, the ship loop runs **security-review** (phase 4). On Cursor that skill uses the **review-security** subagent; on Claude Code, the `security-reviewer` subagent (Opus) against the OWASP list. Either way it runs on the PR branch worktree.

## OWASP references

Reviews frame findings against:

- **OWASP Top 10:2025** — access control (incl. SSRF), misconfiguration, supply chain, crypto, injection, insecure design, auth failures, integrity, logging, exceptional conditions.
- **OWASP ASVS** themes where relevant — auth (V2), access control (V4), validation (V5), data protection (V8).
- **OWASP Top 10 for LLM Apps** and **Agentic Applications (2026)** when the diff touches LLM chat, tools, MCP, RAG, or agent loops.

Product overlays are listed in [`project.md`](project.md) § Security overlays; the baseline (no secrets in repo, session and auth patterns matching existing code) is in **security-review**.

## Security reviewer subagent

The `security-reviewer` subagent (`.claude/agents/security-reviewer.md`) reads this doc. You are read only: do not edit, commit or push. In the PR worktree on the head branch, review `git diff origin/<target>...HEAD` (`<target>` is the merge target branch) against the OWASP list the **security-review** skill gives you and return findings with severity and location. The child posts the PR comment and fixes what you find.

## PR gate

Security findings are posted as PR issue comments (`## Security review (pass N)` … **Verdict:** `PASS` or `CHANGES NEEDED`). Merge requires the latest security review **PASS** plus code review **PASS** (see **merge-pr**). In `ci` review mode (`project.md` § Review) neither agent review runs; see `open-pr` § CI review mode.

## Built-in review commands

- **Cursor:** **`/review-security`** wraps the security-review subagent.
- **Claude Code:** **`/security-review`** reviews the current branch's changes.

Use either ad hoc; the ship loop uses **security-review** for the PR comment loop and merge gate.

## Vendored open-source skills

These live under `.claude/skills/` in the repo. **security-review** reads them when present and skips gracefully when absent.

| Directory | Upstream |
|-----------|----------|
| `owasp-security/` | [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) |
| `agent-security/` | [olanokhin/agent-security-skill](https://github.com/olanokhin/agent-security-skill) |
| `auditing-security/` | [spencerpauly/awesome-cursor-skills](https://github.com/spencerpauly/awesome-cursor-skills) (`resources/auditing-security`) |

To refresh from upstream, from the repo root (adjust clone paths as needed):

```bash
# agamm/claude-code-owasp: OWASP checklists and reference files
git clone --depth 1 https://github.com/agamm/claude-code-owasp /tmp/claude-code-owasp
cp -R /tmp/claude-code-owasp/.claude/skills/owasp-security .claude/skills/owasp-security

# olanokhin/agent-security-skill: AI, agent and MCP paths
git clone --depth 1 https://github.com/olanokhin/agent-security-skill /tmp/agent-security-skill
cp -R /tmp/agent-security-skill/skills/agent-security .claude/skills/agent-security
# Or symlink AI_SECURITY.md into the repo root if you prefer a single doc

# spencerpauly/awesome-cursor-skills: lightweight audit steps
git clone --depth 1 https://github.com/spencerpauly/awesome-cursor-skills /tmp/awesome-cursor-skills
cp -R /tmp/awesome-cursor-skills/resources/auditing-security .claude/skills/auditing-security
```

After copying, spot-check diffs and commit only skill/reference files (no secrets).
