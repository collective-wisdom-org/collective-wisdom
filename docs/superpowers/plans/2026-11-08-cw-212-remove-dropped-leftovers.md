# CW-212 plan: remove the leftovers of dropped features

**Spec:** [2026-11-08-cw-212-remove-dropped-leftovers-design.md](../specs/2026-11-08-cw-212-remove-dropped-leftovers-design.md)

Work under `agent-team/` and `install.sh`. One commit per task. Test command: `python3 -I -m pytest -q agent-team/scripts`; lint: `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.

1. **Heartbeat.** Edit `chief-of-staff/SKILL.md` (file table row, `user` trigger row, Commands row) and `startup.md` (opening line, Start-up clean-up, drop § Legacy heartbeat prompt). Keep stray-wake deletion and the `Wake <id> deleted` report.
2. **scheduledTaskId.** `cos_state.py`: `op_prune` and the `show` unknown-keys line treat it like any unknown key; stop rewriting `retiredThreads` entries. Remove the mentions in `startup.md`, `state-keys.md`, `SKILL.md` § Tick. Adjust the `test_cos.py` fixture/prune test so it still fails for a real bug.
3. **Wording.** `SKILL.md` § Other thread reads: "the successor fallback" (drop "legacy").
4. **install.sh.** Drop the named old flags and `OLD`; any argument but `--dry-run`, `-h`, `--help` is refused with exit 2 and the same removal message, nothing written. Rename the refusal table in `test_install_machine.py`.
5. **cos_handoff.py** docstring: only comments by the gh user's own login count.
6. **merge_pr.py.** Drop the added-release-note-file path (`RELEASE` use, `want` list entry, notes loop); message `closeout missing: no "## Release note" section in the PR body`. `test_merge_pr.py`: drop `old_shape` and its rows; keep one row where an added note file with no body section fails. Check `release_notes.py` and docs still correct.
7. Run tests and lint; grep for leftover mentions of removed things.
