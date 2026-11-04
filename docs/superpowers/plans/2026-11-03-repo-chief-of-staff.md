# Chief of Staff for collective-wisdom itself: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a Chief of Staff run from the collective-wisdom root against one copy of the team's files, and give every Agent-tool subagent the documenter's agent-file pattern.

**Architecture:** Root symlinks into `agent-team/` (skills, agents, settings, scripts, shared role docs) plus a real root `docs/agents/project.md`. Scripts find the repo root without following symlinks. Three new subagent files point at role docs.

**Tech Stack:** Python 3 + pytest, bash, markdown. Tests run with `python3 -I -m pytest -q agent-team/scripts`.

**Spec:** `docs/superpowers/specs/2026-11-03-repo-chief-of-staff-design.md`

## Global Constraints

- Ticket: GitHub issue #9, prefix `CW`, branch `feat/cw-9-repo-chief-of-staff`, repo `dbeallor/collective-wisdom`.
- Edit files under `agent-team/`, never through the root links. `project.md` lives only at root `docs/agents/project.md`, never in `agent-team/`.
- No change to what `install.sh` ships to apps, other than the new agent files and role docs.
- Commits are conventional (`feat:`, `fix:`, `docs:`, `infra:`) and end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Agent frontmatter keys: `name`, `description`, `model`, `tools`. Models: implementer `sonnet`; code-reviewer and security-reviewer `opus`.

## Review Focus

- A script run through a symlinked `scripts/` reads the wrong `project.md` or `state.json` (`resolve()` follows the link).
- `cos_rotation_check` never sees a skill change at the root, because `git log -- .claude/skills/...` stops at a symlink, so the CoS never rotates on a skill edit.
- A new file in `agent-team/docs/agents/` has no root link, so the CoS can't read it.
- A dangling link after a rename in `agent-team/`.
- An agent file whose body points at a role doc that doesn't exist, or that loses its `model`.

---

### Task 1: Scripts find the root without following symlinks

**Files:**
- Modify: `agent-team/scripts/project_config.py:12`, `cos_state.py:51`, `docs_index.py:7`, `cos_merged_check.py:34`, `merge_pr.py:34`, `pr_diff_delta.py:24`, `cos_rotation_check.py:33-34`, `cos_idle_check.py:110`, `cos_parent_check.py:89`
- Test: `agent-team/scripts/test_symlinked_root.py` (create), `agent-team/scripts/test_cos_rotation_check.py` (add tests)

**Interfaces:**
- Produces: `cos_idle_check.DEFAULT_STATE: Path` and `cos_parent_check.DEFAULT_STATE: Path`, both `Path(__file__).absolute().parent.parent / ".agent-team" / "state.json"`, used where the inline default is now. `cos_rotation_check.skill_paths() -> list[str]`: `SKILL_PATHS` with each entry resolved through symlinks and made relative to `git rev-parse --show-toplevel`.

- [ ] **Step 1: Write `test_symlinked_root.py`.** Fixture `app` in `tmp_path`: copy `agent-team/scripts` to `tmp_path/real/scripts`; `tmp_path/app/scripts` is a symlink to it; `tmp_path/app/docs/agents/project.md` holds a prefix row `ZZ`. Parametrized test `test_root_is_the_link_parent(app, module, attr, rel)` runs `python3 -I -c` in a subprocess with `PROJECT_MD` removed from the env, inserting `app/scripts` on `sys.path`, importing `module` and printing `getattr(module, attr)`. Assert the output equals `app / rel`. Cases: `(project_config, DEFAULT, docs/agents/project.md)`, `(cos_state, DEFAULT_FILE, .agent-team/state.json)`, `(cos_idle_check, DEFAULT_STATE, .agent-team/state.json)`, `(cos_parent_check, DEFAULT_STATE, .agent-team/state.json)`, `(docs_index, INDEX, docs/superpowers/index)`, `(merge_pr, ROOT, "")`, `(pr_diff_delta, ROOT, "")`, `(cos_merged_check, ROOT, "")`, `(cos_rotation_check, ROOT, "")`. Add `test_agent_usage_names_the_repo_not_agent_team(app)`: `git init` `app`, call `agent_usage.project_name(app/"scripts"/"agent_usage.py")`, assert it equals `"app"`.
- [ ] **Step 2: Run** `python3 -I -m pytest -q agent-team/scripts/test_symlinked_root.py`. Expected: FAIL (paths land under `real/`; `DEFAULT_STATE` missing).
- [ ] **Step 3: Replace `Path(__file__).resolve()` with `Path(__file__).absolute()`** in the nine places listed under Files, and add the two `DEFAULT_STATE` constants, used by `cos_idle_check`'s argparse default and `cos_parent_check`'s `path`. Leave `cos_brief.py` (folder only) and `agent_usage.py` (its git lookup already reaches the right repo) as they are.
- [ ] **Step 4: Run** the same file. Expected: PASS.
- [ ] **Step 5: Add to `test_cos_rotation_check.py`** `test_skill_paths_follow_symlinks(tmp_path, monkeypatch)`: in a `git init` repo, real files at `agent-team/.claude/skills/chief-of-staff/SKILL.md`, `agent-team/.claude/skills/project-manager/SKILL.md`, `agent-team/docs/agents/chief-of-staff.md`; root `.claude/skills` → `../agent-team/.claude/skills` and `docs/agents/chief-of-staff.md` → `../../agent-team/docs/agents/chief-of-staff.md`; `monkeypatch.setattr(crc, "ROOT", tmp_path)`. Assert `crc.skill_paths()` equals the three `agent-team/...` paths in `SKILL_PATHS` order, and that after committing then editing the chief-of-staff `SKILL.md` and committing again, `crc.skill_commit()` returns the second commit's SHA (`git rev-parse HEAD`). Add `test_skill_paths_unchanged_without_links`: with real folders and no links, the paths equal `SKILL_PATHS`.
- [ ] **Step 6: Run** that file. Expected: FAIL (`skill_paths` missing).
- [ ] **Step 7: Implement `skill_paths()`** in `cos_rotation_check.py` and make `skill_commit` pass `*skill_paths()` to `git log`. Resolve with `os.path.realpath(ROOT / p)` and `os.path.relpath(…, toplevel)`; get `toplevel` from the existing `git()` helper. Skip an entry that doesn't exist.
- [ ] **Step 8: Run** `python3 -I -m pytest -q agent-team/scripts`. Expected: all PASS.
- [ ] **Step 9: Commit** `fix: scripts keep the invoked root when scripts/ is a symlink (#9)`.

### Task 2: Subagent files and role docs

**Files:**
- Create: `agent-team/.claude/agents/implementer.md`, `code-reviewer.md`, `security-reviewer.md`; `agent-team/docs/agents/implementer.md`, `code-review.md`
- Modify: `agent-team/.claude/skills/build-from-plan/SKILL.md:27`, `open-pr/SKILL.md` (§ Agent review comment loop and the team-mode documenter bullet), `security-review/SKILL.md` (the subagent paths), `agent-team/docs/agents/security-review.md`, `org-chart.md`, `README.md` (docs table)
- Test: `agent-team/scripts/test_agent_files.py` (create)

**Interfaces:**
- Produces: Agent types `implementer`, `code-reviewer`, `security-reviewer`, started with `subagent_type`. Each skill keeps the documenter's fallback sentence ("if that type isn't listed … start a general `<model>` subagent with the prompt `Read docs/agents/<name>.md and follow it.`").

- [ ] **Step 1: Write `test_agent_files.py`.** `ROOT` is `Path(__file__).absolute().parent.parent`. For every `ROOT/.claude/agents/*.md`: parse the frontmatter, assert the keys `name` (equal to the file stem), `description`, `model`, `tools` are present, and that the body names a `docs/agents/*.md` path that exists under `ROOT`. Add `test_expected_agents` asserting the stems are exactly `{code-reviewer, documenter, implementer, security-reviewer}`, and `test_models` asserting `model` is `sonnet` for implementer and documenter and `opus` for the two reviewers.
- [ ] **Step 2: Run** it. Expected: FAIL (three agents missing).
- [ ] **Step 3: Create the three agent files** in the documenter's shape. `implementer`: all tools (omit `tools`? the test requires the key, so write `tools: "*"`), body `Read docs/agents/implementer.md and follow it.`; role doc text is the user-level file's body ("Implement the task you are given. Do not replan. Edit files, run commands, and verify. Return a short summary of what changed and how it was verified.") plus one line that it never pushes or merges. `code-reviewer`: tools `Read, Grep, Glob, Bash`, body points at `docs/agents/code-review.md`. `security-reviewer`: same tools, body points at `docs/agents/security-review.md`.
- [ ] **Step 4: Write `docs/agents/code-review.md`.** Move the review method out of `open-pr` § Agent review comment loop into it: read `reviewing-code`, review `git diff origin/main...HEAD` in the PR worktree, use the docs check result in the brief, return findings with severity and location, never approve or request changes on GitHub, never edit files. The comment heading, `Docs checked:` line, pass numbering, verdict wording and posting command stay in `open-pr`; link to that section rather than copy it.
- [ ] **Step 5: Update the skills** to name the types: `build-from-plan` (start the `implementer` agent; fallback sentence), `open-pr` (start the `code-reviewer` agent; drop the `model: "opus"` call-site text; keep "in team mode always run it in that subagent"), `security-review` (the Claude Code subagent path uses `security-reviewer`; same fallback). Keep every gate and verdict rule unchanged.
- [ ] **Step 6: Update docs.** `org-chart.md`: fix the Implementer, Code review and Security review rows' "Defined in" to the new files, and add a line under the table: roles that are T3 threads or a pass have no agent file because `delegate_task` takes a provider, model and prompt, not an agent type. `docs/agents/README.md`: add rows for `implementer.md` and `code-review.md`.
- [ ] **Step 7: Run** `python3 -I -m pytest -q agent-team/scripts`. Expected: PASS (the tracker-docs test also checks the skills for forbidden tracker words, so it guards the edits).
- [ ] **Step 8: Commit** `feat: agent files for the implementer and both reviewers (#9)`.

### Task 3: Root layout and the Chief of Staff's config

**Files:**
- Create (symlinks): `.claude/skills` → `../agent-team/.claude/skills`; `.claude/agents` → `../agent-team/.claude/agents`; `.claude/settings.json` → `../agent-team/.claude/settings.json`; `scripts` → `agent-team/scripts`; `.agents/skills` → `../.claude/skills`; `docs/superpowers/README.md` → `../../agent-team/docs/superpowers/README.md`; for each entry of `agent-team/docs/agents/` (including `trackers`), `docs/agents/<name>` → `../../agent-team/docs/agents/<name>`
- Create: `docs/agents/project.md`, `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md`), `docs/superpowers/index/cw-9.md`
- Modify: `.gitignore` (add `.agent-team/`, `.claude/worktrees/`, `.env`, `.claude/settings.local.json`), `.github/workflows/ci.yml`, `README.md`, `agent-team/docs/agents/chief-of-staff.md`
- Test: `agent-team/scripts/test_root_links.py` (create)

**Interfaces:**
- Consumes: Task 1 (scripts work through the link), Task 2 (every `agent-team/docs/agents/` entry exists before linking).

- [ ] **Step 1: Write `test_root_links.py`.** `TOP = Path(__file__).absolute().parent.parent.parent`; skip the module when `TOP/"install.sh"` is missing (apps don't have it). Tests: (a) every symlink in `git ls-files -s` with mode 120000 resolves to an existing path; (b) every entry of `TOP/agent-team/docs/agents` has a link at `TOP/docs/agents/<name>`; (c) `TOP/docs/agents/project.md` is a regular file and `TOP/agent-team/docs/agents/project.md` does not exist; (d) `TOP/.claude/skills`, `.claude/agents`, `scripts` resolve into `TOP/agent-team`.
- [ ] **Step 2: Run** it. Expected: FAIL (no links).
- [ ] **Step 3: Create the links** with `ln -s` using the targets above. Never hand-edit through them.
- [ ] **Step 4: Write `docs/agents/project.md`** from `agent-team/templates/project.md`, with the spec's values: tracker `github`, scope `dbeallor/collective-wisdom`, prefix `CW`, repo and owner login `dbeallor`, approver David, branch pattern `feat/cw-N-short-title`, test `python3 -I -m pytest -q agent-team/scripts`, required CI checks `script-tests` and `shellcheck`, no migrations. Invariants add: edit `agent-team/`, never the root links; never ship this `project.md`. Docs check lists `README.md`, `AGENTS.md`, `docs/agents/`, `agent-team/docs/agents/`, `agent-team/.claude/skills/`. Delete the Linear-only and Jira-only rows. Write `AGENTS.md` from `templates/AGENTS.md` for this repo (what it is, that the product is the agent team, no app stack).
- [ ] **Step 5: Index the spec and plan** in `docs/superpowers/index/cw-9.md` (table format from `docs/superpowers/README.md`).
- [ ] **Step 6: CI.** Add `docs/**`-independent coverage: the existing `script-tests` job already runs the new tests; add `fetch-depth: 0` is not needed. Confirm `shellcheck` still points at `agent-team/scripts/*.sh`.
- [ ] **Step 7: Docs.** README: add "Running a Chief of Staff in this repo" (the root links, `project.md` is local, edit `agent-team/`, run the CoS from the root checkout) and name all four agent files in the layout line for `.claude/agents/`. `chief-of-staff.md`: one line that the CoS reads `scripts/` and `docs/agents/` through the repo's root, which may be links.
- [ ] **Step 8: Verify.** From the worktree root run each and expect the stated result: `python3 -I -m pytest -q agent-team/scripts` passes; `python3 scripts/cos_rotation_check.py --skill-commit` prints a commit SHA; `python3 -c "import sys; sys.path.insert(0,'scripts'); import project_config as p; print(p.prefix(), p.repo())"` prints `CW dbeallor/collective-wisdom`; `./install.sh --dry-run "$(mktemp -d)"` after `git init` on that dir lists no `project.md` from this repo and only the template seed.
- [ ] **Step 9: Commit** `infra: run a Chief of Staff from the collective-wisdom root (#9)`.

---

**Self-review notes:** every spec section maps to a task (script fix → 1, subagent pattern and org-chart line → 2, root layout, `project.md`, README, dangling-link check → 3). Task 3 step 6 is a confirmation, not new work. The spec's "check" scripts: `cos_brief.py` needs no change (only imports its own folder); `agent_usage.py` is covered by a test in Task 1.
