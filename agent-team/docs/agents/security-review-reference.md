# Security review reference

Read from `security-review.md` § Vendored open-source skills, only to refresh a vendored skill from upstream.

## Refreshing the vendored skills

From the repo root (adjust clone paths as needed):

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

After copying, spot-check diffs and commit only skill and reference files (no secrets).
