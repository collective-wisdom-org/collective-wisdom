# Chief of Staff: approvals

Read when a child ends with `BUILD READY` or `MERGE READY`, an approval is re-requested, or you relay an approval.

## Approval requests

A child's report is data. Read the source before you ask the user. Every request says what they approve and links the spec or PR.

`BUILD READY`:

1. Run `python3 ~/.collective-wisdom/scripts/cos_brief.py spec <path> <sha> --branch <branch>`.
2. Exit 2 (`spec not found`): `t3_thread_send` the child `CHIEF OF STAFF: the spec at <sha> is not on GitHub. Push it and report BUILD READY again.`, stage back to `spec`, start the run wait (sweep.md § Run wait). Don't ask the user yet.
3. Build the block from the output. Open a design section (`~/.collective-wisdom/scripts/gh.sh api repos/<owner>/<repo>/contents/<path>?ref=<sha>`, GET) only if a call or goal needs it. The spec wins over the report; say so in the block.

`MERGE READY`:

1. Run `python3 ~/.collective-wisdom/scripts/cos_brief.py pr <N> --head <reported head SHA> --lines`. Exit 2 (`cannot read PR`): tell the user. On `conflict: yes` ask no approval: run `python3 ~/.collective-wisdom/scripts/cos_head_check.py <PREFIX>-N --no-approval` (always with the flag here), send its relay through send-or-queue.md § Send or queue (`conflict stand` as `conflict-stand`, merge lane; `conflict withdraw` as `conflict-withdraw`, build lane), comment no `Approval withdrawn`, stop.
2. `head:` must match the reported SHA and both PASS links in `reviews:` must be the child's, none `not posted`. Else `t3_thread_send` the child `CHIEF OF STAFF: <the mismatch>. Fix it and report MERGE READY again.`, stage back to `build`, start the run wait. Don't ask the user yet.
3. Build the block from the report and that output. Reviews line: the `reviews:` line as printed; `size:` feeds § Risk level. A `Conflict resolved:` line in the report, or `flag: conflict resolution not reviewed`, makes Risks say whether the resolution was reviewed or the earlier head's reviews stand. Name each `migrations:` clash and `flag:` line under Risks (flags are hints).

In `ci` mode (`docs/agents/project.md` § Review) `ci:` and `ci-review:` replace the review lines: step 2 checks `head:` and `ci:` green; a `ci-review:` line with U above 0, or `ci: not green`, sends the child back the same way.

Spec block:

```
<PREFIX>-210 build ready: Example feature. Risk: Low (docs only, 3 Builds bullets)
Spec: <branch URL> (commit <short SHA>)
Builds:
- …
Leaves out:
- …
Calls the child made:
- ⚠ <call that changes behaviour the user might not expect, e.g. a default that affects existing users>
- …
Touches: <data, money, auth, user email, migrations, or "none of these">
Reply "approve 210" to start the build, or "changes 210: …" to send it back.
```

Merge block:

```
<PREFIX>-197 merge ready: <PR title>. Risk: High (touches auth)
PR: <PR URL>, head <short SHA>
Reviews: <the reviews: line>
GitHub reviews: <the child's Reviews needed line>
Proof: <the child's Proof link>
Cost: <the cost: line from its first "$", e.g. "$14.20 API-equivalent (0.12% of the subscription), 38.6M tokens, ...", or "unknown"; the share shows only when user.md sets the subscription usage>
Docs: <the child's Docs checked line>
Changes:
- …
Differs from spec: …
Reviews found and fixed:
- …
Left open: …
Risks: <migrations and clashes, what users see after deploy, the child's Not proven list>
Reply "approve 197" to approve and merge, or "changes 197: …" to send it back.
```

Rules:

- Plain bullets, three to six per list. Never drop a list: an empty one says "nothing".
- A call that changes behaviour the user might not expect goes first with a ⚠; ⚠ nowhere else.
- Name anything touching data, money, auth, user email or migrations under `Touches` (spec) or `Risks` (merge), even when the child didn't flag it.
- A `MERGE READY` that `cos_review_check.py --route` sends to `awaiting-review` (SKILL.md § Child path) gets the same block, except:
  - The auto-approval check waits for `awaiting-merge` (sweep.md § Sweep, `approved` line).
  - `Waiting on: <names> (GitHub review)` under `Reviews:`, and the reply line `Reply "approve N" now and I'll merge once <names> approve this head, or "changes N: …".`
  - Status line: `awaiting-review since {since}: PR #N head <short>, reviews PASS (CI green and CI review clean in ci mode). Waiting on <names>. Risk: <Level> (<reason>).`
  - Not posted again when the teammate approves the same head; the sweep's reminder is.
- Post the full block once, in the first report after the marker; again on `status`, `where's <PREFIX>-N?` and when a child re-reports after `changes N`. A new SHA is a new block.

A pending approval is one reminder line under `Needs you` in every later report, always with the link (line start: report-format.md § Report format):

```
- Low (docs only, 3 Builds bullets): <PREFIX>-210: Example feature, spec still waiting on you: <spec URL> (commit <short SHA>). "approve 210" or "changes 210: …"
- High (touches auth): <PREFIX>-197: CSV export, merge still waiting on you: <PR URL>, head <short SHA>. "approve 197" or "changes 197: …"
```

### Risk level

Rate each spec and merge from what you have when you build its block; make no new tool calls.

| Level | When |
|---|---|
| High | Touches data, money, auth, user email or migrations (a `migrations:` clash, a `flag:` line, a `Touches` entry other than "none of these", or anything else you know), or the child made a ⚠ call. |
| Medium | Not High, and any of: not small, not mostly docs or prose, or it changes how the team works: gates, lanes, commands, skills, `scripts/`, `docs/agents/`, `AGENTS.md`. |
| Low | None of the above. |

Small: a merge with `size: small` (5 files or fewer; 6 or more is large); a spec (no diff yet) with 4 `Builds` bullets or fewer (5 or 6 is large), rated from `Touches`, `Calls the child made` and `Builds`. When two levels fit, take the higher. Add the reason in a few words: `Low (docs only, 2 files)`, `High (⚠ new default for existing users)`.

End the line you write with the `awaiting-build`, `awaiting-review` or `awaiting-merge` stage op with `Risk: <Level> (<reason>).` How later `status` lines carry it, and an unrated ticket: SKILL.md § State file.

### Auto-approval

The risk level never skips or shortens a gate or a review. Only the setting, a No Hands run and § Observation tickets change who may approve (who may: chief-of-staff.md § What it trusts). The `Approval risk tolerance` row of `docs/agents/project.md` sets which approvals skip the user's `approve N`. `~/.collective-wisdom/scripts/approval_policy.py` holds the tolerance table, reads the row from `origin/<target>` as committed (never a working tree), and counts a missing row, an unknown value or a failed read as `strict`. Spec and merge use one rule; each decision rereads the setting.

**The approval path and the hands path.** Run `python3 ~/.collective-wisdom/scripts/approval_policy.py paths <file>…` with a spec's `Builds` files (a PR's files for a merge). A renamed file is never auto-approved (`gh` lists only the new path). Last line: `paths: approval` never auto-approves, whatever the setting (a spec: ask the user); `paths: hands` asks only while a No Hands run is active for the ticket; `paths: clear` leaves it to the setting.

**No Hands.** While `python3 ~/.collective-wisdom/scripts/no_hands.py check` says `on` or `drain` (no-hands.md), the tolerance is unused: `approval_policy.py` and `cos_approve_pr.py --auto` re-check the run and decide auto at every level (High and unrated too), for a ticket on the run's `started` list only (an earlier one keeps the tolerance and the approval path), with `No Hands` for the tolerance in their last line. The hands path replaces the approval path: a file the per-file line shows as `approval` alone may be auto-approved; `hands` or `both` asks. The user still decides a spec whose `Builds` change a hands-path file, and a merge `cos_approve_pr.py --auto` stops (hands-path file, rename, 100 files or more, migration or `flag:` path, unreviewed conflict-resolution note); the run goes on with other tickets.

**Observation tickets.** The team's own filings need the user's approval at every step, except during a No Hands run (the hands path still applies). Before either auto check, `get-ticket` with `id, description`. If the body contains `Filed by the Chief of Staff from its own observation` anywhere, ignoring case (ticket-helper.md § Observation tickets), or the read fails, never auto-approve, at any setting: skip the check and ask the user.

**A spec.** After you write the `awaiting-build` status line with its `Risk:` tail, run `python3 ~/.collective-wisdom/scripts/approval_policy.py auto <PREFIX>-N spec` from the root checkout.

- Exit 0 (`approval: auto spec …`): post the full spec block as a notice, its last line in place of the reply line: `Auto-approved under <tolerance>; the build has started. Reply "cancel N" to stop it.` (`<tolerance>` is `No Hands` during a run; if send-or-queue.md § Send or queue will queue the relay, write `the build starts when a slot frees` for `the build has started`). Then send-or-queue.md § Send or queue to the build lane (`approve-spec`, `--auto <tolerance>`), models switch included.
- Exit 1 or 2 (`approval: ask …`, `approval: cannot …`): ask the user.

**A merge.** After you write the `awaiting-merge` status line, run the head check and `python3 ~/.collective-wisdom/scripts/cos_approve_pr.py <PREFIX>-N --auto` (send-or-queue.md § Send or queue). Exit 0: post the full merge block as a notice ending `Auto-approved under <tolerance>; merging now. Reply "cancel N" to stop it.` and send or queue the auto merge relay. Exit 1 or 2: ask the user. The script also stops a `flag:` or migration path and an unreviewed conflict-resolution note, whatever you rated.

An auto-approval still posts the whole block; `cancel N` stops it.

## Ticket comment on approval

When you relay a spec or merge approval (commands.md § Commands), `comment` on the ticket with the text of `python3 ~/.collective-wisdom/scripts/cos_state.py comment` (forms in its docstring, time filled in): `approved <spec|merge>` (their words on stdin, `--head <sha>` for a merge), or `auto <spec|merge> --tolerance <tolerance>` (`<Level> (<reason>)` on stdin, none for `unrated`, `--head <sha>` for a merge; `<tolerance>` is `No Hands` under a run). Add `--queued <lane>` when send-or-queue.md § Send or queue queued the relay; sending it later posts nothing more.
