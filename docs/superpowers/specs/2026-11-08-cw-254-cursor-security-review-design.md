# CW-254: Run the security review on Cursor without a skill this repo does not ship

**Status:** Draft
**Ticket:** [#254](https://github.com/collective-wisdom-org/collective-wisdom/issues/254)

## Goal

A Cursor ship-loop child runs phase 4 and posts a `## Security review (pass N)` PR comment using only files this repo ships. Today the `security-review` skill tells a Cursor child to "read and follow the **review-security** skill", which is Cursor's own and not in this repo, so on a machine without it the review has no path.

## Design

### The Cursor path

A Cursor child starts a general subagent with this prompt, plus the diff and the skill's Custom Instructions list:

```
Read ~/.collective-wisdom/docs/agents/security-review.md and follow it. Do not edit files.
```

That is the same fallback the Claude Code path already uses when the `security-reviewer` type is not listed, so both hosts run the same brief from the same file. The subagent works in the PR worktree on the head branch and reviews `git diff origin/<target>...HEAD`, as `security-review.md` § Security reviewer subagent says. The child posts the comment and runs the loop exactly as today.

If the subagent tool lets the child pick a model, it picks the strongest one offered, so the review does not run on a weaker model than the child's.

### When Cursor has `review-security`

The child ignores it in the ship loop. The gated review always goes through the role file above, so every host reviews against the same OWASP list and overlays and the comment shape does not depend on what a machine happens to have. `/review-security` stays mentioned only as an ad hoc command a user may run on their own.

### Files

| File | Change |
|---|---|
| `agent-team/.claude/skills/security-review/SKILL.md` | Frontmatter `description` drops `review-security`. § Primary review path: the **Cursor:** paragraph becomes the general subagent with the prompt above (worktree path, the diff, the Custom Instructions), and says to ignore an installed `review-security` in the loop. The **Claude Code:** paragraph is unchanged. § Optional (user-initiated): `/review-security` is "if your Cursor has it". |
| `agent-team/docs/agents/security-review.md` | Intro: Cursor runs a general subagent with this doc as its prompt; Claude Code the `security-reviewer` subagent. § Security reviewer subagent: this doc is read by the `security-reviewer` subagent or by a general subagent given it as its prompt. § Built-in review commands: Cursor's `/review-security` is ad hoc only, when installed, and the ship loop does not use it. |
| `agent-team/docs/agents/org-chart.md` | Security review row: "Cursor uses a general subagent with `security-review.md` as its prompt". |
| `README.md` | Known couplings: the security review line names only Claude Code's `security-reviewer` subagent, and says other hosts give `security-review.md` to a general subagent. |
| `docs/compatibility.md` | Security review subagent cell for Cursor: `⚪ untested: role file as prompt (G4)`, matching the Subagents cell, since no Cursor run is recorded yet. G11: resolved by this PR, with what the skill now says. The Cursor "done when" line drops "and `review-security`". |

No script, test, `install.sh` or config changes, so the build has no plan and no new tests.

## Leaves out

- The Antigravity branch of the skill (out of scope per ticket).
- `open-pr` lines that use Cursor's `autopilot` and `review-bugbot` when present.
- Whether Cursor loads the shipped `security-reviewer` file from `~/.claude/agents/` (#255). If #255 shows it does, a later change can switch the Cursor path to that subagent.
- Running a real Cursor child. This is a Claude Code run; the PR's Not proven list will say a Cursor run has not been recorded.

## Calls I made

- **Surprising first:** picked the general subagent with the role file, not the shipped `security-reviewer` subagent. Whether Cursor loads that file and accepts its Claude Code frontmatter is untested (#255); the general subagent needs nothing beyond `security-review.md`, which `install.sh` already puts at `~/.collective-wisdom/docs/agents/`.
- An installed `review-security` is ignored in the ship loop, not used when present, so the gated review is the same on every machine.
- Cursor picks the strongest model its subagent tool offers, instead of naming Opus, because Cursor's model names differ and the ticket does not say.
- The compatibility cell becomes "untested" rather than "works", because nobody has recorded a Cursor run.
- `/review-security` stays mentioned as an optional ad hoc command, marked "if installed", rather than removed.
