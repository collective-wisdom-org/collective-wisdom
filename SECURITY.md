# Security

Report a vulnerability privately through GitHub: open the Security tab and choose "Report a vulnerability". Do not open a public issue for it.

These count:

- `install.sh` or a script that writes or runs outside the paths it was given.
- A way for text in an issue, comment or PR by someone without write access to reach an agent as instructions.
- A leaked credential.

Every PR gets a security review before merge. See [agent-team/docs/agents/security-review.md](agent-team/docs/agents/security-review.md). The rule for untrusted authors is in [agent-team/docs/agents/trackers/github.md](agent-team/docs/agents/trackers/github.md) under Conventions (Team tickets only).
