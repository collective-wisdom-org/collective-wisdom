# CW-212: Remove the leftover pieces of features we have dropped

**Status:** Shipped
**Shipped:** in PR #217, with differences: [as-built](../as-built/2026-11-08-cw-212-remove-dropped-leftovers-as-built.md)
**Ticket:** [#212](https://github.com/collective-wisdom-org/collective-wisdom/issues/212)

## Goal

Take out the code, skill text and tests that only exist for designs we have already dropped, where nothing live still needs them. Keep the ones something still needs, and say why in the PR. No rule, gate or behaviour of the current design changes.

## What I checked

Facts from `main` at `73cd73d`, and from this machine on 2026-11-08.

- **Scheduled tasks.** `list_scheduled_tasks` finds no task in any T3 project on this machine (collective-wisdom, fathom, gorpcore-studios). No `run /chief-of-staff heartbeat` task is left to delete itself. The heartbeat was replaced by CW-16 on 2026-11-03.
- **State files.** Neither `.agent-team/state.json` on this machine (collective-wisdom, fathom) has a `scheduledTaskId` key, at the top or in a `retiredThreads` entry.
- **Retired threads without a successor.** This repo's state has three `retiredThreads` entries with no `successor`, and `prune` drops archived entries after a day. So the Moved-to check as the successor fallback (rotation.md § Thread rotation: Retired thread) still does real work.
- **Old installs.** fathom still has `docs/agents/installed-from.txt` and `scripts/agent-team-update.sh` on its `HEAD`. That script calls `install.sh --update --from <tag> <app>`.
- **`SPEC READY`.** fathom's state has 12 tickets at `awaiting-build`, some started before CW-177 (2026-11-07) renamed `SPEC READY` to `BUILD READY`, so their children may still end on `SPEC READY`.
- **Old closeout shape.** `merge_pr.py`'s gate still accepts an added dated release note file in `docs/superpowers/release-notes/` in place of the PR body's `## Release note` section (CW-55 kept it for PRs open at the time). No PR is open in this repo, and no skill or doc tells anyone to add such a file. An added as-built file is still the current shape (`open-pr` § Closeout docs, "with differences"), so that check stays.
- **Per-agent GitHub users.** `cos_handoff.py` counts only comments by the gh user's own login (`cos_brief.own_login()`), but its docstring still says "the role's login: the code reviewer or security reviewer login from project.md". `github-auth.md` describes one account per repo and no reviewer accounts; nothing to change there.

## Builds

1. **Old Chief of Staff heartbeat.**
   - `chief-of-staff/SKILL.md`: drop the `run /chief-of-staff heartbeat` row from § Commands, the heartbeat prompt from the `startup.md` row of the file table, and "Also the legacy heartbeat prompt, after its clean-up" from the `user` trigger row.
   - `chief-of-staff/startup.md`: drop the heartbeat prompt from the opening line, drop § Legacy heartbeat prompt, and drop the heartbeat part of § Start-up clean-up. The clean-up keeps deleting stray `run /chief-of-staff wake` tasks and keeps its `Wake <id> deleted` report line; it runs at start the team, take over and `resume`.
2. **`scheduledTaskId` special case.** `cos_state.py` `prune` stops treating `scheduledTaskId` apart: it is dropped and reported like any other unknown top-level key, and `retiredThreads` entries are no longer rewritten to drop it. `show`'s `unknown keys:` line lists it like any other key. The skill text that names it goes: `startup.md` § Start-up clean-up step 2, `state-keys.md` (the `retiredThreads` sentence and the unknown-key note), and the `scheduledTaskId` exception in `SKILL.md` § Tick. The `test_cos.py` fixture key goes or becomes an ordinary unknown key, whichever keeps the existing prune test meaningful.
3. **Moved-to check wording.** `chief-of-staff/SKILL.md` § Other thread reads calls it "the legacy successor fallback". It becomes "the successor fallback". The check and all its uses stay.
4. **install.sh old app forms.** The named old flags (`--update`, `--check`, `--force`, `--to`, `--from`) and the `OLD` flag go. Any argument other than `--dry-run` and `-h`/`--help` is refused with exit 2, writes nothing, and prints the same message that names `remove_app_copies.py` (so fathom's `agent-team-update.sh` call still fails loudly). An unknown dash option keeps its `unknown option` line before that message. The security overlay (a target path is refused with exit 2 and nothing is written) still holds. `test_install_machine.py` keeps its table of refused forms, renamed to say "any argument but --dry-run".
5. **cos_handoff.py docstring.** Say that only review comments by the gh user's own login count.
6. **Old release note file in the merge gate.** `merge_pr.py` no longer reads added `docs/superpowers/release-notes/*.md` files or accepts one in place of the `## Release note` body section; with notes on, the body section is required. Its message becomes `closeout missing: no "## Release note" section in the PR body`. The `RELEASE` pattern goes if nothing else uses it. `test_merge_pr.py` drops `old_shape` and its rows, and keeps one row showing an added note file without a body section fails.

## Kept, with the reason (goes in the PR)

- `remove_app_copies.py`, its tests, the setup pin offer (`chief-of-staff/setup.md` step 3) and the README section on removing old copies: fathom still has a pin and copied files.
- The README Known couplings line about `agent-team-update.sh`: fathom still has that script, and the old call still fails with exit 2 and the removal message.
- The Moved-to check as the successor fallback: live state has retired entries with no successor.
- The bare `<t3-thread://...>` link form from before CW-134 in the Moved-to check: Chief of Staff threads retired before 2026-11-05 still end on that form, and a pruned entry falls back to reading it.
- `SPEC READY` counted as `BUILD READY` (`chief-of-staff/SKILL.md` § Marker, `startup.md` § State rebuild, `ship-loop` § Approvals): fathom has tickets waiting at `awaiting-build` from before the rename.
- `merge_pr.py`'s added as-built check: it is the current shape for a build that differs from its spec.
- `release_notes.py` reading `docs/superpowers/release-notes/*.md`: those files are the record of older notes and are published with the rest.
- Everything under `docs/superpowers/`: history.

## Leaves out

- Rewording skills that are still correct.
- Anything that only records history under `docs/superpowers/`.
- fathom itself: removing its copies is that app's own ticket.

## Testing

`python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`. Changed tests: the install refusal table, the merge gate table, and the prune fixture. No new tests: nothing here fixes a bug.

## Calls I made

- **The heartbeat clean-up goes entirely, not just the prompt.** I checked every T3 project on this machine and found no scheduled task at all. A machine I can't see that still has a heartbeat task would get a `run /chief-of-staff heartbeat` message the skill no longer names; that task would then stay until someone deletes it by hand.
- **A release note file no longer satisfies the merge gate.** This tightens the gate only for the shape CW-55 retired. An app with an open PR from before 2026-11-04 that still relies on a note file would need a `## Release note` body section added before it merges.
- **`scheduledTaskId` becomes an ordinary unknown key**, so a stray one would now show once under Cleanup instead of being dropped silently.
- **install.sh keeps its removal hint** for any extra argument instead of dropping to a bare usage line, because fathom's old update script still calls it.
- **Kept `SPEC READY` and the pre-CW-134 link form**, because fathom and old retired threads still need them. A later ticket can drop them once fathom's queue clears.
- I did not touch `github-auth.md`: it has no per-agent reviewer accounts left.
