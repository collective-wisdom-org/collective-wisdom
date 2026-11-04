# CW-71: Publish all release notes to a release-notes branch after each merge

**Ticket:** [CW-71](https://github.com/dbeallor/collective-wisdom/issues/71)
**Status:** Shipped
**Shipped:** in PR #85, as specified

## Goal

After every team merge, `scripts/merge_pr.py` writes the full release notes list as `RELEASE_NOTES.md` on a `release-notes` branch through the GitHub API. Anyone can read all the notes in one file on GitHub. `main` gets no new commit.

## Today

Facts from `main` at `469567f`, checked 2026-11-04.

- `release_notes.py` `main()` reads the file notes from the working tree (`NOTES.glob("*.md")`, `read_text`), so it follows symlinks and reads untracked files. It reads the PR notes with `merged_prs()` (`gh pr list --state merged --base main --limit 500`). It sorts and prints both in one function, and exits 1 when the PRs can't be read.
- `merge_pr.py` `main()` merges, calls `cleanup()` (branch delete, then `git pull --ff-only` on root `main`), then prints the last line. The "already merged" path runs the same `cleanup()` and prints its own last line. Every gh and git call goes through the injected `run`, which the tests replace with a fake.
- Nothing publishes the notes, and no rule covers a write to a branch other than the ticket's own.

## Change

### `release_notes.py`: split the text from the reading

Move the sort and the text out of `main()` into one function, `render(files, prs)`, where `files` is a list of `(file name, text)` pairs and `prs` is the merged PR list. It returns the text `main()` prints today, and still writes the undated-note warning to stderr. `main()` reads the working tree and gh as now, calls `render`, prints it and keeps its exit codes. Its printed output doesn't change, and its tests pass unchanged. The PR says so.

### `merge_pr.py`: the publish step

A new function, `publish(pr, sha, run)`, runs after `cleanup()` succeeds, on both the merge path and the "already merged" path, before the last line. It never raises. Each problem prints one `merge-pr: warn <reason>` line and skips the rest; the exit code and the last line stay as they are. When `cleanup()` fails the script exits 2 as today and doesn't publish; the rerun publishes.

Steps, every call through `run` (so through `gh.sh` as the owner, with no `--verbose` and no `GH_DEBUG`):

1. **Merged PRs.** `gh pr list` with the same arguments as `merged_prs()`. If it fails or the JSON doesn't parse: warn `cannot read merged PRs; release notes not published` and stop. The file never drops the PR notes.
2. **File notes from git objects.** In the root checkout, `git ls-tree -z refs/remotes/origin/main -- docs/superpowers/release-notes/`. Keep entries named `*.md` directly in that folder whose mode is `100644` or `100755` (regular blobs). Skip symlinks (`120000`), submodules and folders. Read each with `git cat-file blob <oid>`. The working tree is never read, so untracked drafts and symlink targets can't leak. `cleanup()` has just pulled, so `origin/main` contains the merge. If `git merge-base --is-ancestor <merge SHA> refs/remotes/origin/main` fails, warn and stop.
3. **Text.** `release_notes.render(files, prs)` plus a final newline. It is byte for byte what `python3 scripts/release_notes.py` prints on a clean checkout of `origin/main`.
4. **Branch check.** `GET repos/{owner}/{repo}/git/ref/heads/release-notes`.
   - 404: the branch is missing. Go to 5 with no parent.
   - Found: read its commit's tree (`git/trees/<tree sha>`). If the tree is anything but exactly one blob named `RELEASE_NOTES.md`, warn `release-notes branch holds other files; not published` and stop. If that blob's SHA equals the git blob SHA of the new text (computed locally, `sha1("blob <len>\0" + bytes)`), the file is current: print nothing and stop.
   - Any other error: warn and stop.
5. **Write.** `POST git/trees` with one entry (`RELEASE_NOTES.md`, mode `100644`, the text as `content`) and no base tree. `POST git/commits` with message `docs: release notes after #<N>`, that tree, and the old tip as the only parent (none for a new branch). Then:
   - missing branch: `POST git/refs` with `refs/heads/release-notes`;
   - existing branch: `PATCH git/refs/heads/release-notes` with `force=false`.

   A 422 (the branch appeared, or moved and the update isn't a fast-forward) warns `release-notes update rejected; the next merge repairs it`. The ref is never forced, so a slow run can't overwrite a newer file.

The JSON bodies go to `gh api` on stdin (`--input -`), so `run` gains an optional `input` argument. The existing fake runners accept `cmd` only; `publish` passes `input` only on the three POST/PATCH calls, which the existing tests never reach: their fake returns no PR list, so `publish` warns at step 1, and they still see exit 0 and a last line starting `merge-pr: `. They pass unchanged.

### The one permission

Add to `docs/agents/project.md` § Repo invariants and `agent-team/templates/project.md` § Repo invariants, after the "never push to main" line:

> Exception: the publish step in `scripts/merge_pr.py` writes `RELEASE_NOTES.md` on the `release-notes` branch through the GitHub API after a merge. No agent, skill or other script writes that branch, by push or by API.

`agent-team/.claude/skills/merge-pr/SKILL.md` § Merge gets the same rule in one sentence, plus what the script does: after the fast-forward it publishes `RELEASE_NOTES.md` to `release-notes`, and a failed publish prints `merge-pr: warn ...` without changing the exit code or the last line. In team mode a warn line is reported in `MERGED #N` and is not a reason to stop.

Installed apps keep their own `project.md` (install only seeds it), so for them the skill sentence is the rule.

### Where readers find it

- Root `README.md`, in the list near the `docs/superpowers/README.md` line: one line linking `https://github.com/dbeallor/collective-wisdom/blob/release-notes/RELEASE_NOTES.md`.
- `agent-team/docs/agents/README.md` (synced into apps as `docs/agents/README.md`): one line under the table, `Release notes: every merge publishes them all to RELEASE_NOTES.md on the release-notes branch, at https://github.com/<owner>/<repo>/blob/release-notes/RELEASE_NOTES.md (Repo row in project.md).`
- `agent-team/docs/superpowers/README.md` § Release notes: one sentence saying `merge_pr.py` publishes the same text there after each merge.
- The merge-pr skill's **Closeout in PR** paragraph: one clause pointing at that file.
- `docs/agents/project.md` and the template, § Docs, Release notes row: add the published file's location.

## Tests

All in `agent-team/scripts/test_merge_pr.py`, with a fake `run` that serves the PR list, the git reads and the API calls from a table.

- **Publish, table-driven.** Rows: branch missing (creates the ref, no parent); contents changed (PATCH with `force=false`, parent is the old tip); contents unchanged (no POST or PATCH); branch holds another file too (warn, no write); PATCH answers 422 (warn); PR list fails (warn, no write).
- **Git objects only.** A real temp git repo with a remote: one committed note, one committed symlink note pointing at a file outside the repo, and one untracked note. The text `publish` would write contains the committed note and neither of the others.
- **Failed publish keeps the merge result.** `main` with a fake whose publish calls fail: exit 0, the `merge-pr: warn` line comes right before the last line, and the last line starts `merge-pr: merged #7`.

Existing `merge_pr.py` and `release_notes.py` tests pass unchanged.

## Verify

- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`.
- After this PR's own merge (root `main` still runs the old script, so nothing publishes yet), the next team merge creates `release-notes`. Then `git fetch origin release-notes && git show origin/release-notes:RELEASE_NOTES.md | diff - <(python3 scripts/release_notes.py)` on a clean root `main` prints nothing, and `git log origin/main` has no publish commit.

## Overlap with open work

- **CW-41** (in build) rewrites the sort in `release_notes.py` `main()` and adds a git lookup for file note merge times, plus the § Release notes sentence on ordering in `agent-team/docs/superpowers/README.md`. This PR moves that sort into `render()` unchanged. Whichever lands second moves the other's change: CW-41's sort goes inside `render()`, and its merge-time lookup must feed `render()` from both `main()` and `publish()`, or the published file and the script's output differ. My README edit is one separate sentence.
- **CW-52** (queued to build) edits `merge_pr.py` `read_facts()`, `FIELDS` and `gate()`, `github-auth.md`, and the merge-pr skill's § Pre-merge checks and § Team mode. This PR adds `publish()`, a few lines at the end of `main()` and the `input` argument on `run`, and doesn't touch the gate, `github-auth.md`, § Pre-merge checks or § Team mode. My merge-pr edits are in § Merge and **Closeout in PR**.
- **CW-72** (spec stage) edits `ship-loop`, `build-from-plan`, `org-chart` and, per CW-52's spec, `docs/agents/README.md`. This PR adds one line under that README's table and doesn't touch the others.
- Merge `origin/main` into this branch before building and again before `MERGE READY` if any of them has merged.

## Non-goals

- Sorting by merge time (#41) and deleting the CW-55 and CW-51 files (#69). Until #69 merges, the CW-55 note shows twice in the file, as in the script's output.
- A workflow, schedule or GitHub Release. Changing the note format or the closeout gate.
- Fixing a file left stale by a hand merge in the GitHub UI before the next team merge.

## Calls I made

- **The file notes come from `origin/main` after the pull, not from the merge commit itself.** The ticket says "at the merge commit". A rerun on an old PR, or two merges close together, would then publish an older tree (for example bring back files #69 deletes) on top of a newer file. `origin/main` always contains the merge, and the script checks that it does. It is still git objects only, so the security point holds.
- **No publish when `cleanup()` fails.** The script already exits 2 there and is meant to be rerun; the rerun takes the "already merged" path and publishes.
- **The publish commit is made as the owner,** since `merge_pr.py` drops `AGENT_GH_ROLE`. Message: `docs: release notes after #<N>`.
- **Unchanged contents are checked by git blob SHA,** computed locally and compared with the tree entry, so no download. An unchanged file prints no line at all.
- **The new branch is an orphan** (a commit with no parent), so it never shares history with `main` and holds only the one file.
- **Each published commit has the old tip as its parent,** so the branch keeps a history of the file and the update is a fast-forward.
- **`run` gets an optional `input` argument** so JSON bodies go on stdin, rather than long `-f` arguments. The existing fakes keep working because they are never called with it.
- **A warn line doesn't stop a team merge.** The merge child reports it in `MERGED #N` and goes on to move the ticket to Done.
- **The link in apps' docs is a pattern** (`<owner>/<repo>` from project.md), since the synced file is the same in every app.
- **Installed apps get the permission through the merge-pr skill only,** because install never updates an app's own `project.md`. The template carries it for new installs.
