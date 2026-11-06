# CW-107 plan: require proof that the change works in every PR

Spec: [2026-11-04-cw-107-require-pr-proof-design.md](../specs/2026-11-04-cw-107-require-pr-proof-design.md). All paths below are under `agent-team/`.

1. `scripts/release_notes.py`: `section(body, heading="Release note")` takes the heading as a parameter, matched with `re.escape`. Existing callers stay as they are.
2. `scripts/merge_pr.py`: in `gate()`, right after the release note file loop, read `release_notes.section(f["body"], "Proof")`. Empty: `proof missing: no "## Proof" section in the PR body`. No line starting `Not proven`: `proof missing: the "## Proof" section has no "Not proven" line`. Add the proof line to the module docstring's list of gate checks.
3. `scripts/test_merge_pr.py`: `green()` body gains `## Proof` with `Not proven: nothing`. New `test_gate` rows next to the release note rows: no section, empty section, no `Not proven` line, CRLF passes. Fix any other fixture body that must now pass the gate.
4. Docs (prose, no tests):
   - `.claude/skills/open-pr/SKILL.md`: new § Proof between § Verify and § Superpowers docs; § Create PR body overlay; drop `Checks that didn't run` from the as-built template; fix loop step 2 and § Closeout docs "later fix commits" keep Proof current; review brief includes Acceptance list and Proof section.
   - `.claude/skills/security-review/SKILL.md` step 2: add the Proof section next to the release note.
   - `.claude/skills/merge-pr/SKILL.md` § Closeout in PR: name `## Proof`.
   - `docs/agents/code-review.md` § Method: Proof check step.
   - `.claude/skills/ship-loop/SKILL.md`: only the `MERGE READY` block and the paragraph under it.
   - `.claude/skills/chief-of-staff/approvals.md`: merge block `Proof:` line and `Risks:` wording.
5. Verify: `python3 -I -m pytest -q agent-team/scripts`, `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
6. Open the PR with a `## Proof` section, closeout docs, docs check, code review, security review, per ship-loop § Team mode.
