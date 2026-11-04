# Reliable Chief of Staff relays (CW-11) implementation plan

Spec: `docs/superpowers/specs/2026-11-03-cw-11-reliable-relays-design.md` (approved at c42e51d). Edit only under `agent-team/` (plus the docs under `docs/superpowers/`). Test command: `python3 -I -m pytest -q agent-team/scripts`; lint: `shellcheck install.sh agent-team/scripts/*.sh`.

Conventions to match: `Path(__file__).absolute()` for paths, `project_config` for prefix/repo/branch head, `fail()` printing `cos_<name>: <what>` and exiting 2, `gh.sh` through `subprocess.run(..., timeout=30)`, tests load the module with `importlib.util` and a `run()` helper like `test_cos_merged_check.py`, fixture project is prefix `ABC`, repo `example/app`.

## Task 1: shared review parser and `cos_ready_check.py`

Files: `agent-team/scripts/cos_brief.py`, `agent-team/scripts/cos_ready_check.py` (new), `agent-team/scripts/test_cos_ready_check.py` (new).

- In `cos_brief.py` split `review_line` into `latest_review(heading, comments)` (returns `None` or `(comment, pass_n_text, verdict)`) and the formatting. `cos_brief.py pr` output must not change; existing tests stay green.
- `cos_ready_check.py` per spec § 1: `--file`, `--prs FILE`, `--refs FILE`; lines `ready`, `building`, `no-pr`, `pushed`, `writing`, `unreadable`; summary `ready-check: <C> checked, <R> may have reported`; exit 0/1/2. Branch match: ticket `branch`, else `<branch_head()><tid.lower()>-` prefix (so ABC-1 does not match abc-11). Expose a function `check(state, prs, refs)` returning `(lines, ready_tickets)` so the sweep can call it without a subprocess; `main()` handles files, gh and exit codes.
- Tests: one table each for build lane, spec lane, exit codes (spec § 6).

## Task 2: `cos_sweep.py`

Files: `agent-team/scripts/cos_sweep.py` (new), `agent-team/scripts/test_cos_sweep.py` (new); small `check()`-style entry points in `cos_merged_check.py` and `cos_parent_check.py` only if needed (keep their CLI and output unchanged, existing tests green).

- Spec § 2. Order: merged check with apply, then ready check on the updated state, then parent check without the archive lines. Prints each part's lines and summary, then `sweep: read in full: <list>; merged: <list>` (with `; didn't run: <parts>` when a part fails). Exit 0 nothing, 1 something listed or merged, 2 any part didn't run. A part that cannot run prints its `cos_<name>: <what>` line; the others still run.
- Test table: ready + old-parent listed once with both reasons; ticket just merged is not ready; one part failing still prints the others and exits 2; nothing found exits 0.

## Task 3: `cos_handoff.py`

Files: `agent-team/scripts/cos_handoff.py` (new), `agent-team/scripts/test_cos_handoff.py` (new).

- Spec § 4. Reuse `cos_brief.check_summary` and `latest_review` so it never disagrees with `cos_brief.py pr`. `--file`, `--pr FILE`. `reject: <field> <value>` exit 1 for bad branch/specPath/specSha; exit 2 when state or GitHub unreadable. `PR: none yet` when `pr` is null.
- One test table: awaiting-merge with a PR fixture, awaiting-spec with no PR, moved head, bad branch/spec path.

## Task 4: skill prose (no tests)

Files: `agent-team/.claude/skills/chief-of-staff/SKILL.md`, `agent-team/.claude/skills/ship-loop/SKILL.md`, `agent-team/.claude/skills/merge-pr/SKILL.md`, `agent-team/docs/agents/chief-of-staff.md` if its script list needs the new names.

- Spec § 3 and § 5, line by line. Plain sentences, no em dashes (`human-writing`). Keep the edits to the sections the spec names. Every place that ran the merged check (and the separate parent-check call outside archiving) runs `python3 scripts/cos_sweep.py --thread <this thread's id>`.

## Task 5: closeout docs (after the PR exists, per `open-pr` § Closeout docs)

As-built, index entry `docs/superpowers/index/cw-11.md`, spec status Shipped.
