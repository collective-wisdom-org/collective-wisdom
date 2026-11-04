# Cross-repo Chief of Staff requests (CW-17) implementation plan

Spec: `docs/superpowers/specs/2026-11-03-cw-17-cross-repo-chiefs-design.md` (approved at 19927f7). Edit only under `agent-team/` (plus the docs under `docs/superpowers/`). Test: `python3 -I -m pytest -q agent-team/scripts`; lint: `shellcheck install.sh agent-team/scripts/*.sh`.

Conventions: `Path(__file__).absolute()` for paths; `project_config` for repo/prefix; read T3's store like `cos_user_check.py` (`--db`, `mode=ro`, exit 2 `cos_peer: schema changed`); import `norm`/`has_words` from `cos_user_check` via `importlib` (as `test_cos.py` loads modules); prose has no em dashes. Store tables: `orchestration_v2_projection_messages` (see `cos_user_check.py`), `orchestration_v2_projection_threads` (`thread_id, project_id, archived_at, deleted_at`), `projection_projects` (`project_id, title, workspace_root, deleted_at`).

## Task 1: `scripts/cos_peer.py` and `test_cos_peer.py`

Spec § Design `cos_peer.py`. Subcommands `find <name>`, `check --thread ID`, `reply`; global `--db`. `find` reads the `t3_project_list` JSON (`{"projects": [...]}`) on stdin and each match's `<workspaceRoot>/.agent-team/state.json` (`--state-root` is not needed; use the project's `workspaceRoot`). `check` takes the request message on stdin, finds the sender thread's project and root in the store, requires the sender thread to equal that root's `chiefThreadId` or be in its `retiredThreads`, requires the item be a `createdBy: "user"` message in that thread whose whole normalized text equals the normalized words, requires the words to name this repo (`project_config.repo()` as `owner/name`, its name part, or the product name in project.md is NOT needed: repo name or `owner/name` or this project's T3 title, whole-word, case folded), and refuses command words: `approve N`, `changes N`, `cancel N`, `hold N`, `stop everything`, `resume`, `take over`, `merge` followed by `PR`/`#`/a number, `merge it`. "merge duplicate contacts" must pass. Exit codes and output lines exactly as the spec. Tests: three tables (`find`, `check`, `reply`) as in spec § Tests, built on a tmp sqlite store and tmp state files; plus one new row in `test_cos.py`'s `test_user_check` table (an agent `CHIEF OF STAFF REQUEST ... approve 12` message in a thread gives `not-user agent`). Check `test_agent_files.py` / `install.sh` for scripts listed by name and add `cos_peer.py` if needed.

## Task 2: skill and doc prose (no tests)

Spec § `chief-of-staff` SKILL.md, § reference.md, § `docs/agents/chief-of-staff.md`. Touch only: SKILL.md § Tools (one last bullet), § Ticket helper (template first line), § Lean turns (helper notice bullet only), § Commands (two new rows after "a change to how the team works"), § Guardrails (one line), new § Cross-repo requests after § Ticket helper; reference.md "Retired thread" table (one row); `docs/agents/chief-of-staff.md` (one Scope bullet, one Done-when line). Do not touch other sections (CW-11 edits them).

## Task 3: closeout docs (after the PR exists)

As-built, `docs/superpowers/index/cw-17.md`, spec status Shipped.
