# CW-130: Fit install.sh to repos with their own agent setup and add adoption steps

**Ticket:** [CW-130](https://github.com/collective-wisdom-org/collective-wisdom/issues/130)
**Status:** Shipped
**Shipped:** in PR #148, as specified
**Related:** #125, #126, #127, #129

## Goal

A repo that already has its own `AGENTS.md`, `.agents/skills` or `.claude/settings.json` gets told exactly what to merge by hand, and the README has one checklist from an empty repo to a running Chief of Staff.

## Today

Facts from `main` at `9ad1321`, checked 2026-11-05.

- `install.sh` seeds `AGENTS.md` from `agent-team/templates/AGENTS.md` only when it is missing (`seed_file`). An existing one is left alone with no TODO.
- `install.sh` links `.agents/skills -> ../.claude/skills` only when nothing is there. A real directory, or a link to somewhere else, is skipped with no message.
- When `.claude/settings.json` exists and differs from the shipped one, `install.sh` adds the TODO `Merge the Stop hook from agent-team/.claude/settings.json into .claude/settings.json by hand (the file differs, so it was left alone).` It says this even when the hook is already in the file, and it doesn't show the hook.
- The shipped `agent-team/.claude/settings.json` holds only the Stop hook that runs `python3 "$CLAUDE_PROJECT_DIR/scripts/cos_rotation_check.py" --hook || true`.
- `agent-team/templates/AGENTS.md` has the sections `Product`, `Required reading`, `GitHub`, `Workflow`, `Testing`, `Secrets`, `Agent config` and `Commits`.
- README § Requirements lists T3 Code, a tracker, `gh`, Python and `pytest`, and the superpowers skills. § Configure a consuming repo covers the placeholders and the merge target branch row. Nothing walks a new repo through every step.
- `agent-team/templates/project.md` already has the settings rows: `Tracker`, `Approval risk tolerance`, `Claude subscription API-equivalent usage`, `Review after conflict resolution`, `Merge target branch` (#125), `Require teammate approval` (#127), `Review mode` (on `main`; #126 is still open for the rest of its work) and `Publish release notes` (#129).
- `agent-team/scripts/test_install.py` runs the real `install.sh` against a throwaway collective-wisdom and app repo. Its fixture ships `.claude/settings.json` as `{}` and `templates/AGENTS.md` as `agents`.

## Design

All three checks run on every plain install and every `--update`, dry run or not. None of them writes to the file it checks. Each adds one entry to the `TODO:` list the installer already prints at the end.

### Existing `AGENTS.md`

When `AGENTS.md` exists (so it is not seeded), the installer looks for these four headings, each as a line `## <name>` (case-insensitive, surrounding spaces ignored):

- `Required reading`
- `GitHub`
- `Workflow`
- `Agent config`

These are the sections that carry agent-team rules: the required reading list, `./scripts/gh.sh`, one ticket one branch one PR, and where skills and subagents live. `Product`, `Testing`, `Secrets` and `Commits` are the app's own and are not checked.

If any are missing, the TODO is:

`AGENTS.md has no <Required reading, GitHub> section(s). Copy them from agent-team/templates/AGENTS.md in collective-wisdom (at <short SHA>) and fill them in for this repo.`

listing only the missing ones, in the order above. If all four are there, nothing is printed. The check is on headings only, not on what the sections say.

### `.agents/skills` that is not the link

When `.agents/skills` exists and is not a symlink whose target is exactly `../.claude/skills`, the TODO is:

`.agents/skills is a real directory, not a link to ../.claude/skills, so Codex will not see the shipped skills. Move any skills of your own from it into .claude/skills/, then replace it: rm -r .agents/skills && ln -s ../.claude/skills .agents/skills`

For a symlink to somewhere else the first clause reads `.agents/skills links to <target>, not to ../.claude/skills`. For a plain file it reads `.agents/skills is a file`. The installer never removes or relinks it.

### `.claude/settings.json` without the hook

When `.claude/settings.json` exists and differs from the shipped file:

- If it contains the text `cos_rotation_check.py`, nothing is printed. The hook is there; the rest of the file is the app's.
- Otherwise the TODO is `Add the Chief of Staff Stop hook to .claude/settings.json by hand (the file has its own settings, so it was left alone). Merge this into its "hooks" key:` followed by the shipped `agent-team/.claude/settings.json`, each line indented under the TODO.

The JSON printed is the shipped file at the installed commit, so it stays right when the hook changes. The check is a text search, not a JSON parse: no new dependency, and a hook written by hand in another shape still counts.

### README: Adopt in a repo

A new `## Adopt in a repo` section after `## Requirements`, as a numbered checklist:

1. Install the prerequisites: T3 Code; `gh` signed in (`gh auth login`, see `agent-team/docs/agents/github-auth.md`); Python 3 and `pytest`; the superpowers skills installed globally.
2. Run the installer (`./install.sh --dry-run /path/to/app`, then without `--dry-run`, or `--from v0.N`).
3. Fill `docs/agents/project.md`: every `<placeholder>`, then the settings rows, each with its default: `Tracker`, `Merge target branch`, `Review mode`, `Require teammate approval`, `Publish release notes`, `Approval risk tolerance`, `Review after conflict resolution`, `Claude subscription API-equivalent usage`. One line each on what it does, linking the README section where one exists.
4. If the repo had its own `AGENTS.md`, copy in the sections the installer's TODO names. Add a `CLAUDE.md` containing `@AGENTS.md` if it uses Claude Code.
5. If the repo had its own `.claude/settings.json`, merge the Stop hook the TODO prints.
6. If the repo had a real `.agents/skills`, replace it with the link as the TODO says.
7. Set branch protection or a ruleset on the merge target branch that requires the checks in `Required CI checks`.
8. Commit everything on a branch and merge it as the install PR.
9. Start a Chief of Staff thread in T3 Code from the root checkout on the merge target branch and say `start the team`.

The ticket says later settings tickets add their own row when they ship. Every settings row in the template today gets one in step 3.

Also in the README: § Install's sentence about what is never overwritten gains one sentence saying which TODOs an existing `AGENTS.md`, `.agents/skills` or `settings.json` gets, and § Update's last sentence about merging the hook by hand is changed to match (printed only when the hook is missing).

### Tests

One new table-driven test in `test_install.py`, `test_existing_setup`. The fixture's shipped `settings.json` becomes a small JSON with the hook command in it and its `templates/AGENTS.md` gets the four headings, so a clean install still matches. Each row puts files in the app before a plain install and lists the TODO substrings that must appear and must not appear:

| Case | Expect |
|---|---|
| `AGENTS.md` with none of the sections | TODO naming all four |
| `AGENTS.md` with all four | no `AGENTS.md` TODO |
| `.agents/skills` a real directory with a file | the `.agents/skills` TODO |
| `settings.json` differing, without the hook | the hook TODO and the `cos_rotation_check.py` line |
| `settings.json` differing, with the hook | no settings TODO |
| fresh repo | exactly today's two seed TODOs (`project.md`, `AGENTS.md`) and nothing else |

Every row also checks that the files it planted are byte for byte unchanged after the run (and `.agents/skills` is still a directory).

## Out of scope

- Merging `AGENTS.md` or `settings.json` automatically.
- Nested skill folders. The installer keeps the flat `.claude/skills/<name>/` layout.
- `--check` reporting these: it compares shipped files only, and these files are the app's.
- A `CLAUDE.md` check.

## Calls I made

- **The check runs on `--update` too, not only on a first install.** An app that hasn't merged the sections sees the reminder on every update. That keeps it from being lost, at the cost of repeating.
- **"Agent-team sections" means four headings: Required reading, GitHub, Workflow, Agent config.** Product, Testing, Secrets and Commits are app-specific, so a repo with its own testing rules isn't nagged.
- **Matching is on `## <heading>` lines only**, case-insensitive. A repo that has the rules under other headings gets the TODO anyway.
- **An existing `settings.json` that has the hook but differs now gets no TODO.** Today it gets one. The ticket asks for this.
- **The hook check is a text search for `cos_rotation_check.py`**, not a JSON parse, so no `jq` or Python is needed in `install.sh`.
- **The TODO prints the whole shipped `settings.json`**, which today is only the hook, rather than extracting the hook entry.
- **A link to anything other than `../.claude/skills` counts as "not the link"**, including an absolute link that resolves to the same place.
- **The README checklist lists all eight settings rows in the template today**, including the three not named in the ticket (approval risk tolerance, conflict resolution review, subscription usage). Review mode is on `main` even though #126 is still open.
- **The fixture's shipped `settings.json` and `templates/AGENTS.md` change** so that the table can tell "has the hook" and "has the sections" apart from a clean install.
