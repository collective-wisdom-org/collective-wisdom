# Chief of Staff for collective-wisdom itself (design)

**Status:** Shipped

## Intent

Run a Chief of Staff (CoS) in this repo, so changes to the agent team (skills, scripts, role docs) ship through the same spec → build → review → merge loop the apps use. Each repo gets its own CoS: its own `project.md`, tracker and `.agent-team/state.json`. This repo is the first one that is both the source of the team and a user of it.

Tickets live in GitHub Issues on `dbeallor/collective-wisdom`, so the GitHub tracker adapter gets tested for real.

## Goals

- `python3 scripts/cos_state.py show` and the other CoS scripts work from the collective-wisdom root.
- One copy of every skill, script and role doc. A PR that edits `agent-team/` changes what the CoS runs after merge.
- This repo's own facts live in a root `docs/agents/project.md` that `install.sh` never ships.

## Non-goals

- No change to what apps get from `install.sh`, other than script path handling (below).
- No multi-repo CoS and no cross-repo state.
- No agent files for the T3-thread roles (Chief of Staff, ticket helper, ship-loop child) or the project manager pass. `.claude/agents/` only defines types started with the `Agent` tool; those roles are threads or a pass, and already follow the skill + role doc pattern.
- No tracker migration tooling.

## Anti-goals

- A second copy of the skills that can drift.
- This repo's config leaking into apps through the shared `agent-team/docs/agents/`.

## Approaches

- **A. Root links into `agent-team/`.** One source, no sync step. Costs some symlinks and one script fix. **Chosen.**
- B. `install.sh .` and commit copies. Two copies need a drift check in CI.
- C. Treat `agent-team/` as the CoS root. Puts `project.md` in the shipped tree and breaks the "mirrors a consuming repo" rule.

## Design

### Root layout

- `.claude/skills` → symlink to `../agent-team/.claude/skills`; `.claude/agents` → `../agent-team/.claude/agents`; `.claude/settings.json` → `../agent-team/.claude/settings.json` (the Stop hook).
- `scripts` → symlink to `agent-team/scripts`.
- `docs/agents/` is a real folder. It holds `project.md` (this repo's, not shared) and one symlink per file or folder in `agent-team/docs/agents/` (including `trackers/`).
- `docs/superpowers/README.md` → link to the shared one. `specs/`, `plans/`, `as-built/` and `index/` here hold this repo's own history. This spec is the first.
- `AGENTS.md` at the root, from `templates/AGENTS.md`, filled in for this repo. `CLAUDE.md` containing `@AGENTS.md`.
- `.agents/skills` → `../.claude/skills`, as `install.sh` does.
- `.gitignore` gets the template lines (`.agent-team/`, `.worktrees/`, …) plus `.claude/worktrees/`.

### Script path fix

Eight scripts find the repo root with `Path(__file__).resolve().parent.parent`. `resolve()` follows the `scripts` symlink, so the root becomes `agent-team/`: `project.md` and `state.json` would be read from the wrong place. Change those to `.absolute()`, which keeps the invoked path. Behaviour in apps is unchanged, because there `scripts/` is a real folder. `project_config.py`, `cos_state.py`, `cos_idle_check.py`, `cos_parent_check.py`, `cos_merged_check.py`, `merge_pr.py`, `pr_diff_delta.py` and `docs_index.py` need it; `cos_brief.py` and `cos_rotation_check.py` only use their own folder, so they need a check, not a change. `agent_usage.py` names the project from the folder, so it needs a look too.

A test runs each of these scripts through a symlinked `scripts` folder and checks that the root it finds is the link's parent.

### `project.md` for this repo

Filled in from the template: tracker `github`, repo `dbeallor/collective-wisdom`, prefix `CW`, branch pattern `feat/cw-N-short-title`, approver David. Test command `python3 -I -m pytest -q agent-team/scripts`. Required CI checks `script-tests` and `shellcheck`. Repo invariants add: edit `agent-team/`, never the root links; never ship this repo's `project.md`. Docs check lists `README.md`, `agent-team/docs/agents/` and `agent-team/.claude/skills/`.

### Subagents follow one pattern

Three roles are Agent-tool subagents, and only the documenter is defined in the repo. The pattern is the documenter's: `agent-team/.claude/agents/<name>.md` with `name`, `description`, `model` and `tools` in the frontmatter and a one-line body that points at `docs/agents/<name>.md`, which holds the real instructions.

- `implementer`: add `agent-team/.claude/agents/implementer.md` (`model: sonnet`, all tools) and `docs/agents/implementer.md`, from the user-level file's text. Apps get it on install. `build-from-plan` stops saying to pass `model: "sonnet"` and names `subagent_type: "implementer"`.
- `code-reviewer`: add the agent file (`model: opus`, tools Read, Grep, Glob, Bash) and `docs/agents/code-review.md`, which takes the review method now spread through `open-pr` § agent review comment loop (comment format, verdict, pass numbering stay in `open-pr`; the role doc says how to review and what to return). `open-pr` starts it by `subagent_type`.
- `security-reviewer`: add the agent file (`model: opus`, same tools) pointing at the existing `docs/agents/security-review.md`. `security-review` starts it by `subagent_type`.
- Each skill keeps the documenter's fallback: if the type isn't listed (session started before the file existed), start a general subagent with the same model and the prompt "Read `docs/agents/<name>.md` and follow it."
- The models move from call-site text into the agent file's frontmatter. The skills' rule that team-mode reviews run in the Opus subagent stays.
- `org-chart.md` gets a line saying why the thread roles and the project manager have no agent file (`delegate_task` takes a provider, model and prompt, not an agent type), its "Defined in" column lists the new files, and `docs/agents/README.md` list the new files; `README.md` layout line for `.claude/agents/` names all four. `install.sh` already syncs the folder.
- A test checks every `.claude/agents/*.md` has the four frontmatter keys and a body naming a `docs/agents/*.md` file that exists.

### Install and docs

`install.sh` already ignores root-only files, so it needs no change. Add a "Running a Chief of Staff in this repo" section to the README, and note in `agent-team/docs/agents/chief-of-staff.md` that the CoS reads `scripts/` and `docs/agents/` through the repo's own root, which may be links.

## Verification

- Script tests pass in CI, including the new symlink test.
- `python3 scripts/cos_state.py show` and `python3 scripts/project_config.py`-style reads return this repo's values from the root.
- `./install.sh --dry-run` into a scratch repo lists no `project.md` from this repo.
- `ls -l` shows every link resolves (a check script, run in CI, fails on a dangling link).

## Calls I made

- Prefix `CW`. Change it if you want something else.
- Specs and history for this repo go in a root `docs/superpowers/`, not `agent-team/docs/superpowers/` (where the tracker-choice spec is). I left that one where it is.
- Per-file links in `docs/agents/` rather than linking the whole folder, so `project.md` stays out of `agent-team/`.
- Role doc for code review is new and mostly moved text; I keep the PR comment format and verdict rules in `open-pr` so the gates don't move.
- The repo copy of `implementer` overrides your user-level one inside repos that install it. The text is the same.
- Symlinks need no Windows support; the team already needs T3 Code and `gh` on macOS or Linux.

## Left to the builder

Exact link targets, the dangling-link CI check, wording of the README section, and whether `agent_usage.py` and the two scripts marked "check" need changes.
