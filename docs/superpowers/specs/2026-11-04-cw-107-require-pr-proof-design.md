# CW-107: Require proof that the change works in every PR

**Ticket:** [CW-107](https://github.com/dbeallor/collective-wisdom/issues/107)
**Status:** Shipped
**Shipped:** in PR #109, as specified

## Goal

Every PR the agent team opens carries a `## Proof` section: evidence for each Acceptance item that a reviewer can check in a minute or two, and a `Not proven` list that says plainly what has no proof and why. The merge script refuses a PR without one, the code reviewer checks it, and `MERGE READY` points at it instead of keeping its own list of missed checks.

## Today

Facts from `main` at `82211a2`, checked 2026-11-04.

- `open-pr` § Verify says to run the plan's verification and fix failures. Nothing puts the result in the PR.
- `open-pr` § Create PR fixes the body: ticket link, spec path, `Closes #N`, a `## Release note` section, the as-built path when one exists.
- `open-pr` § Closeout docs: the as-built template ends with an optional `## Checks that didn't run` section.
- `open-pr` § Agent review comment loop step 2 and `security-review` § PR comment loop step 2 say to keep the release note current when a fix changes what ships.
- `ship-loop` § Team mode, Build stage: `MERGE READY` ends with `Checks that didn't really run: <bullets, or "none">`, explained in the paragraph under the block (skipped CI jobs, skipped tests, manual checks the plan listed that couldn't run).
- `chief-of-staff/approvals.md`: the merge block's `Risks:` line includes "checks that didn't really run", taken from the child's `MERGE READY`.
- `scripts/merge_pr.py` `gate()` refuses a merge with `closeout missing: no "## Release note" section ...` when the body section is empty and no release note file was added. It reads the section with `release_notes.section(body)`, which returns the text under `## Release note` up to the next `## ` heading.
- `scripts/test_merge_pr.py` `test_gate` is the table-driven gate test; its `green()` fixture body has `## Summary`, `## Release note` and `## Test plan`.
- `docs/agents/code-review.md` § Method: the reviewer reads the diff and the docs check result. It gets no ticket text and no PR body.
- `merge-pr` SKILL § Closeout in PR lists what the script needs; no proof.

## Change

### 1. The `## Proof` section (`open-pr`)

A new § Proof in `open-pr`, between § Verify and § Superpowers docs. § Create PR's body overlay adds "a `## Proof` section (§ Proof)".

Shape:

````markdown
## Proof

- **<Acceptance item, short>**: <what shows it holds>

  ```
  $ <command>
  <trimmed output: the lines that show the result>
  ```

- **<next item>**: CI run <link>, job `<name>` passed at <short SHA>.

Not proven:
- <item or check>: <why: blocked, no browser, needs a deploy, needs credentials, ...>
````

Or `Not proven: nothing` when every item has proof.

Rules:

- One entry per Acceptance item in the ticket. A ticket with no Acceptance list uses its Scope bullets.
- Evidence is one of: a command and its trimmed output, a CI run link, a screenshot on GitHub for a visual change, or a short note of what was done and what was seen. Output is real output from this branch, trimmed to the lines that show the result; never written by hand.
- An item with no evidence goes under `Not proven`, with the reason. So do the checks `MERGE READY` used to list: skipped CI jobs, tests marked skip, and manual checks the plan listed that couldn't run.
- Write it after § Verify and before `gh pr create`, so the PR opens with it.
- Keep it current: when a fix commit changes what an entry shows, update the entry in the same push, with `./scripts/gh.sh pr edit <N> --body-file <path>`. `open-pr` § Agent review comment loop step 2 and `security-review` § PR comment loop step 2 add "and the `## Proof` section" next to the release note.

### 2. Merge gate (`scripts/merge_pr.py`)

- `release_notes.section(body, heading="Release note")` takes the heading as a parameter; the existing callers don't change.
- `gate()`, right after the release note check: read `section(f["body"], "Proof")`.
  - Empty or absent: `proof missing: no "## Proof" section in the PR body`.
  - No line starting `Not proven` in it: `proof missing: the "## Proof" section has no "Not proven" line`.
- The module docstring's list of what the gate checks gets the proof line.
- `merge-pr` SKILL § Closeout in PR names the `## Proof` section next to the release note.

Test: new rows in `test_gate`, next to the release note rows. `green()`'s body gains a `## Proof` section with `Not proven: nothing`. Rows: no section; a heading with nothing under it before the next `## `; a section with no `Not proven` line; CRLF line endings pass.

### 3. Code review (`docs/agents/code-review.md`, `open-pr`)

- § Agent review comment loop: the review brief also includes the ticket's Acceptance list (or Scope, when there is none) and the PR body's `## Proof` section.
- `code-review.md` § Method gains a step: check the Proof against the Acceptance list. A **Must fix** when an Acceptance item has neither evidence nor a `Not proven` entry, when evidence doesn't show what it claims (output that doesn't contain the result, a link to a run on another SHA, a command that doesn't exercise the item), or when something listed as proven is plainly not.

### 4. `MERGE READY` (`ship-loop`) and the approval block

Edits stay inside the `MERGE READY` block and the paragraph right under it, so CW-72's edits to `ship-loop` merge cleanly.

- Replace `Checks that didn't really run: <bullets, or "none">` with:

  ```
  Proof: <PR URL>#proof
  Not proven: <the PR's Not proven list, copied as is, or "nothing">
  ```

- Replace the paragraph that defines "Checks that didn't really run" with one saying the Proof link and `Not proven` come from the PR body's `## Proof` section (`open-pr` § Proof), and that `Not proven` must match it word for word.
- `chief-of-staff/approvals.md` merge block: `Risks:` takes "the child's Not proven list" instead of "checks that didn't really run", and a `Proof: <link>` line is added under `Reviews:`.

### 5. As-built template

Drop the `## Checks that didn't run` section from the as-built template in `open-pr` § Closeout docs. The PR's `Not proven` list holds it, so there is one list.

## Calls I made

- **The gate also requires a `Not proven` line**, not only a non-empty `## Proof` section. The ticket asks only for the section. Without the line check, a PR could pass with proof for the easy items and silence about the rest, which is what the ticket is trying to stop.
- **No grandfathering.** Once this ships (here, and in apps after their next update), any open PR without a `## Proof` section is refused at merge until its body gets one. The release note says so.
- **Docs-only PRs need proof too.** For a prose change, evidence can be a note pointing at the lines that make the item hold, or a test run that still passes. The gate doesn't tell docs-only from code.
- **`MERGE READY` copies `Not proven` from the PR** instead of only linking to it. The PR body stays the one source; the copy lets the Chief of Staff fill the approval block's `Risks:` line without reading the PR, and it must match word for word.
- **The as-built loses its `Checks that didn't run` section.** The ticket doesn't mention it; I took "one list, not two" to cover it too.
- **Screenshots must live on GitHub.** An agent with no way to attach one lists the visual check under `Not proven` ("no way to attach a screenshot"). Committing image files to the branch is not allowed for this.
- **No Acceptance list means the Scope bullets** are the items to prove.
- **The reviewer gets the ticket's Acceptance list and the PR body in its brief**, rather than reading them with `gh` itself, so it stays a pure diff-and-brief reader.
- The gate checks shape only (section present, `Not proven` line present). Whether the evidence is real is the code reviewer's job.

## Out of scope

- What verification the plan runs.
- Videos, or hosting screenshots anywhere but GitHub.
- Checking evidence content in the script (for example, matching CI links to the head SHA).
- Back-filling `## Proof` into merged PRs.

## Testing

`python3 -I -m pytest -q agent-team/scripts` with the new `test_gate` rows. Lint: `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` (no shell changes expected). This PR's own body carries a `## Proof` section in the new shape.
