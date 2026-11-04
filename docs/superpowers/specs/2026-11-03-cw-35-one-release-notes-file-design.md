# CW-35: Pick a way to show all release notes in one file on GitHub

**Ticket:** [CW-35](https://github.com/dbeallor/collective-wisdom/issues/35)
**Status:** Shipped

## Goal

The user wants one release notes file they can open on GitHub. It must not bring back the merge conflicts that one shared file caused. This ticket compares the options and recommends one. It builds nothing.

## Non-goals

- Building the combined file. That is a separate ticket.
- Changing the per-PR note rule (`release-notes/<prefix>-N.md`) or the format of existing notes.

## Today

Facts from `main` at `f2a03d0`.

- Each PR adds `docs/superpowers/release-notes/<prefix>-N.md`. Two PRs never edit the same lines, so they never conflict.
- `scripts/release_notes.py` prints every note, newest first, to stdout. Reading them all means running it locally.
- `scripts/merge_pr.py` refuses to merge a PR with no added `release-notes/*.md` whose first line is `# YYYY-MM-DD <title>`. It squash-merges through the REST API, then fast-forwards root `main`. Every team merge goes through it.
- `main` has no branch protection or rulesets. The rule in `project.md` ("Never push to `main`; push only the ticket's own `feat/cw-N-*` branch") is a team rule in `project.md` and the skills, not something GitHub enforces. It governs agents' git pushes; `merge_pr.py` already writes to GitHub through the API (the merge, branch deletes).
- `.github/workflows/ci.yml` runs tests on PRs and on push to `main`. `install.sh` does not copy `.github/` into apps, so a new workflow would not reach an installed app without a new copy rule.
- The repo has no GitHub Releases and no tags.

## Options

Each option is judged on five questions from the ticket: does it avoid merge conflicts, can it be read on GitHub, is it always up to date, what does it push to `main`, and does it work in an installed app.

| Option | No conflicts | Read on GitHub | Up to date | Pushes to `main` | Installed app |
|---|---|---|---|---|---|
| A. Merge step writes the file to `main` | Yes | Yes, `main` | Yes, after each team merge | Yes, a second commit per merge | Yes, `merge_pr.py` ships |
| B. CI on push to `main` commits the file to `main` | Yes | Yes, `main` | Yes, within a minute | Yes, a bot commit per merge | Needs a new `.github/` copy rule and write permission per app |
| C. Scheduled job commits the file | Yes | Yes | Lags up to one period | Yes, a bot commit per run | Same as B |
| D. GitHub Release per merged PR | Yes | One Releases page, not a file | Yes, if the merge step creates it | No, but adds a tag per PR | Yes, if `merge_pr.py` does it |
| E. One shared file with `merge=union` | Not on GitHub (see below) | Yes, `main` | Yes | No | Yes |
| F. Merge step writes the file to a separate `release-notes` branch | Yes | Yes, stable link to that branch | Yes, after each team merge | No | Yes, `merge_pr.py` ships |

### A. Merge step writes the combined file to `main`

After the squash merge, `merge_pr.py` runs `release_notes.py`, writes `RELEASE_NOTES.md` and commits it to `main`. It is current the moment a team merge finishes and needs nothing new in apps. But it adds a second, unreviewed commit on `main` for every merge, which is the kind of push to `main` that rule forbids. It also makes root `main` and `origin/main` race: the script would have to push from the root checkout, or write through the contents API and fast-forward again.

### B. CI workflow on push to `main` commits the file back

A job on push to `main` runs `release_notes.py` and commits the result with `GITHUB_TOKEN`. It catches every push, including merges done by hand in the GitHub UI. A push made with `GITHUB_TOKEN` does not start another workflow run, so it doesn't loop. Costs: a bot commit on `main` after every merge (same rule problem as A), `contents: write` permission in the workflow, and root `main` falling one commit behind until the next fast-forward. Apps get it only if `install.sh` learns to copy a workflow file, which it avoids today.

### C. Scheduled job

The same as B on a cron, so it lags by up to one period and still commits to `main`. Strictly worse than B.

### D. GitHub Releases, one per merged PR

The merge step creates a release, tagged for example `pr-36`, with the note as its body. GitHub shows every release on one Releases page, newest first, with no push to `main`. But it is a page, not a file, and the ticket asks for a file. It adds a tag per PR, and "release" suggests versions this repo doesn't have. The notes would live in two places, the per-PR file and the release body, and could drift if a note is edited after merge.

### E. One shared file with `merge=union`

`.gitattributes` with `RELEASE_NOTES.md merge=union` makes local git keep both sides' lines instead of conflicting. GitHub's own conflict check and merge button do not honour `.gitattributes` merge drivers, by multiple reports; I did not test it here. So two open PRs that both add a note would still show as conflicting on GitHub, which is the problem CW-13 fixed. It also means changing the per-PR note rule, which is out of scope. Ruled out.

### F. Merge step writes the combined file to a separate `release-notes` branch (recommended)

After the merge and the fast-forward, `merge_pr.py` runs `release_notes.py` from root `main` and writes the output as `RELEASE_NOTES.md` on a branch named `release-notes`, through the GitHub API. The branch holds only that file, with no history shared with `main`. The README links to `https://github.com/<owner>/<repo>/blob/release-notes/RELEASE_NOTES.md`, which GitHub renders like any Markdown file.

- **No conflicts.** No PR touches the combined file.
- **Read on GitHub.** One stable link, rendered as Markdown.
- **Up to date.** Rebuilt from every note on `main` after each team merge, so a missed run (a hand merge, a failed write) is fixed by the next merge.
- **Nothing pushed to `main`.** The only write is to `release-notes`, which no one branches from or merges.
- **Installed app.** `merge_pr.py` already ships, so apps get it on their next `install.sh` run with no workflow or permission change. The branch name and file path come from fixed defaults, so no new `project.md` key is needed.

The cost: the file is not on `main`, so a clone of `main` doesn't have it (`release_notes.py` still prints the same thing locally), and a hand merge in the GitHub UI leaves it stale until the next team merge.

## Recommendation

Build F.

A and B are the closest rivals, and both put an unreviewed commit on `main` after every merge, against a rule the whole team leans on. B also needs workflow write permission and a new install copy rule for apps. D isn't a file. E doesn't stop conflicts on GitHub. F gives one rendered file, never conflicts, stays current with every team merge, and ships to apps through a script they already run.

### What stays as it is

- `release_notes.py` stays unchanged. F uses its stdout as the file contents.
- The `merge_pr.py` closeout check stays unchanged. Every PR must still add its own dated note, because that note is what the combined file is built from. F adds a step after the merge; it does not touch the gate.

### Shape of the build ticket

For the separate ticket, not built here:

- After a successful merge and fast-forward (and on the "already merged" path, so a rerun repairs it), `merge_pr.py` publishes `release_notes.py` output to `release-notes:RELEASE_NOTES.md`. It creates the branch as an orphan if it is missing and skips the commit if the contents haven't changed.
- A failed publish never fails the merge. The script still exits 0 and prints a `merge-pr: warn` line before the final `merge-pr: merged ...` line (callers parse the last line), and the next merge repairs the file. Two merges close together can race on the branch ref; the stale one fails as a warning and the next merge repairs it.
- The README and `docs/superpowers/README.md` § Release notes link to the rendered file. `install.sh` seeds `docs/superpowers/README.md` only when it is missing and never touches an app's own `README.md`, so existing apps need the link in a doc `install.sh` syncs, such as one under `docs/agents/`.
- A test covers the publish step's three cases: branch missing, contents changed, contents unchanged, plus the rule that a failed publish leaves the exit code at 0.

## Calls I made

- **Recommend a separate branch (F), an option the ticket didn't list.** Every listed option that gives a real file on GitHub commits to `main`, and the team rule says never push to `main`. F is the one way I found to get a file with no `main` commit. Its practical gains over A: no unreviewed commit on `main`, no race with the root fast-forward, no extra CI run on `main`. F writes to a branch that isn't the ticket's own, so the build ticket should also add a line to `project.md` and the skills saying the merge step may write `release-notes`.
- **The merge step publishes, not CI.** `merge_pr.py` already reaches every installed app. A workflow would need `install.sh` to start copying `.github/` and each app to grant write permission. The trade is that hand merges in the GitHub UI leave the file stale until the next team merge.
- **A publish failure never fails the merge.** The merge has already happened by then, and the next merge rebuilds the file from scratch.
- **`merge=union` is ruled out on reports, not a test.** Several sources say GitHub's merge ignores `.gitattributes` merge drivers. Testing it would mean opening two throwaway PRs in this repo, which I didn't do at the spec stage.
- **Delivery.** The build stage for this ticket posts the comparison and recommendation as a comment on #35 and ships this spec, its as-built, index entry and release note. It changes no skill or script. I don't file the build ticket; the Chief of Staff or the user does.
