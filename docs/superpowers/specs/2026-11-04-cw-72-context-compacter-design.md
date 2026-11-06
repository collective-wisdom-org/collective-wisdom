# CW-72: Add a context compacter agent to the ship loop

**Ticket:** [CW-72](https://github.com/dbeallor/collective-wisdom/issues/72)
**Status:** Shipped
**Shipped:** in PR #154, with differences: [as-built](../as-built/2026-11-05-cw-72-context-compacter.md)

## Goal

When a build adds text to the files agents load, a compacter subagent tightens the added text before the PR opens, so the files don't creep back up after #23 shrank them.

## Today

Facts from `main` at `63a7c21`, checked 2026-11-04.

- `agent-team/.claude/skills/build-from-plan/SKILL.md` runs the plan's tasks through the implementer, then § When all tasks pass goes to **open-pr**. Nothing in the ship loop looks at size.
- `open-pr` runs closeout docs, then § Docs check (the documenter), then the code review loop. `security-review` follows.
- Subagents are pointers in `agent-team/.claude/agents/` (`implementer`, `documenter`, `code-reviewer`, `security-reviewer`). Each names a role file in `agent-team/docs/agents/`. `scripts/test_agent_files.py` checks every pointer's frontmatter and that the role file it names exists.
- `scripts/test_section_pointers.py` (from #23) checks that every `§ Heading` pointer in skills, `docs/agents/` and `templates/` names a real heading.
- #23 measured size in characters (`wc -c`, about 4 per token). There is no size check anywhere.
- `docs/agents/org-chart.md` lists the subagents in its Roles table and its "Who reports to whom" chart. `docs/agents/README.md` indexes the role files.
- `install.sh` copies `agent-team/scripts/` into apps, so a new script ships with the next tag.

## Change

### 1. Trigger script: `agent-team/scripts/compact_check.py`

Decides whether the pass runs and prints the sizes the pass reports.

- **Files it counts.** Markdown files the agents load, under `agent-team/`:
  - `.claude/skills/**/*.md`, except the vendored `agent-security` and `owasp-security` skills;
  - `.claude/agents/*.md`;
  - `docs/agents/**/*.md`;
  - `templates/AGENTS.md`.
- **Change set.** Files from that list that differ between the merge base of `origin/main` and `HEAD` and the working tree, plus untracked ones (`git ls-files --others --exclude-standard`). Working tree, not `HEAD`, because a solo build doesn't commit. `--base <ref>` overrides `origin/main`.
- **Size.** Characters of the file text. A new file is 0 before; a deleted file is 0 after.
- **Output.** One line per counted file (`<path> <before> <after> <+/-delta>`), a `total` line, then a last line that is either `compact: run (+<net> characters)` or `compact: skip (<reason>)`. The reasons are `no agent files changed` and `net <delta> characters`, for a net of zero or less.
- **Rule.** Run when the net across the change set is above 0.
- **Outside collective-wisdom.** In an app (no `install.sh` at the repo top) it prints `compact: skip (not collective-wisdom)`. Shared files in an app change only by install PR, and compacting the installed copies would make them drift from collective-wisdom.
- **Exit codes.** 0 for run and skip. 2 when git fails (no merge base, bad ref), with a `compact: cannot read <what>` line.

Tests: one table-driven test in `scripts/test_compact_check.py` over a temp git repo: skill text added (run), text removed (skip, net), only a non-agent file changed (skip, no agent files), a vendored skill grown (skip), an agent file grown in an untracked new file (run), a bad base ref (exit 2).

### 2. The compacter subagent

- `agent-team/.claude/agents/compacter.md`: a pointer like the others, `model: sonnet`, tools `Read, Edit, Grep, Glob, Bash`, body `Read docs/agents/compacter.md and follow it.`
- `agent-team/docs/agents/compacter.md`, the role file:
  - **Inputs** from the child: the base ref, and the `compact_check.py` output.
  - **What it may edit.** Only the files in that output, and in them only lines the diff added or changed (`git diff <merge base> -- <file>`). Text that was already on `main` stays as it is.
  - **What it must keep.** Every rule, gate, step, command, path, marker, verdict word, exit code, and every `§` pointer and the heading it names. It doesn't rename or move headings. When shortening a sentence would drop any of these, it leaves the sentence.
  - **How.** Cut repetition of what another line or file already says (point to it instead), filler, and examples that restate the rule. Prose follows `human-writing`.
  - **Never** commit, push, or touch files outside the list.
  - **Output.** The `compact_check.py` output run again after its edits, then one line per edited file saying what it cut. If nothing could be cut without losing a rule, it says `COMPACT: no change` and edits nothing.

### 3. Where it runs

`build-from-plan`, a new § Compaction pass, placed before § When all tasks pass:

1. After the last task passes, run `python3 scripts/compact_check.py`.
2. On `compact: skip`, go on. On exit 2, run it once more; a second exit 2 in team mode is `BLOCKED:`.
3. On `compact: run`, start the compacter (`Agent`, `subagent_type: "compacter"`, foreground; fall back to a general Sonnet subagent with `Read docs/agents/compacter.md and follow it.` when the type isn't listed, as for the implementer).
4. Check its edits: `git status` shows only files from the list. Run the test command from `project.md` (it includes `test_section_pointers.py`). Read the compacter's diff, and revert any hunk that drops or changes a rule.
5. In team mode, commit `docs: compact agent text for <PREFIX>-N` and push. Solo, leave it uncommitted with the build.
6. Keep the before and after totals. `open-pr` puts them in the PR body as a `Context size:` line (before total, after total, net change from `main`), or `Context size: pass skipped (<reason>)`.

Since this runs before **open-pr**, it is before closeout docs and the docs check, so the documenter and both reviews see the compacted text.

### 4. Docs

- `ship-loop` phase 2: one line saying build ends with the compaction pass (`build-from-plan` § Compaction pass).
- `open-pr` § Create PR overlays: the `Context size:` line in the PR body.
- `docs/agents/org-chart.md`: a Compacter row in the Roles table (Sonnet subagent, writes only agent text the diff added, no tickets, no merges, no agents) and a node in the chart under the child.
- `docs/agents/README.md`: a row for `compacter.md`.

## Acceptance

- A PR whose diff adds text to a skill has a compaction pass before the docs check, and its body has a `Context size:` line with sizes.
- A PR that touches no counted files, or doesn't grow them, has `Context size: pass skipped (<reason>)` and no compacter run.
- `test_section_pointers.py` and `test_agent_files.py` pass with the new files.
- `test_compact_check.py` covers the trigger rules above.

## Non-goals

- The one-time shrink of existing files (#23).
- What the code review and security review check, or when they are skipped (#54).
- A size limit or CI check that fails a PR.
- Running the pass in apps, or on app-local files (`project.md`, area role docs, the app's `AGENTS.md` prose).
- Running the pass again on review-fix commits in phases 3 and 4.
- The install PR in the app. It follows the next tag, as for every shared change.

## Calls I made

- **Any net growth triggers the pass, with no floor.** A 30-character addition starts a subagent. The ticket says "the net size grows"; a floor (say 500 characters) would save runs and is easy to add later.
- **The pass runs once, at the end of the build, not after review fixes.** Fixes from code and security review can add text that never gets compacted. Re-running it would move the head after a PASS review and restart the review loop.
- **It runs only in collective-wisdom.** In an app the script skips. App-local files the agents load (`project.md`, the app's `AGENTS.md`) aren't covered.
- **The compacter edits only lines the diff added or changed.** Text already on `main` is #23's job, so the pass can't turn a small PR into a rewrite.
- **The trigger is a script, not judgement in the skill.** That makes it testable, as the ticket's acceptance asks, and gives the size numbers the pass reports.
- **Size is characters,** the measure #23 used, not tokens or words.
- **Vendored skills (`agent-security`, `owasp-security`) are not counted,** since they track an upstream copy.
- **The compacter runs on Sonnet,** like the implementer and documenter.
- **The child reviews the compacter's diff and reverts any hunk that loses a rule,** in addition to the tests. The code review sees the result too.
- **The sizes go in the PR body** (`Context size:` line), not in a PR comment or the spec.
