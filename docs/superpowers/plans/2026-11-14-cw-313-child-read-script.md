# CW-313 plan: read child threads through a script

Spec: `docs/superpowers/specs/2026-11-14-cw-313-child-read-script-design.md` (approved at dc928f0). Test command: `python3 -I -m pytest -q agent-team/scripts` (needs `pytest`, e.g. `uvx pytest -q agent-team/scripts`). Lint: `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` (no shell file changes expected).

Edit under `agent-team/`. Follow `AGENTS.md` § Testing: one table-driven test per rule, test lines no more than feature lines, no prose tests. Build the SQLite fixtures in the tests with only the columns the script reads.

## Task 0: check the store before coding

Read-only checks against `~/.t3/userdata/statev2.sqlite` (`mode=ro`, never write). Record the findings in the plan's task 1 notes (a short list in the commit message is enough).

1. Positions. `t3_thread_read` returns `position` and `nextPosition`; the store's `orchestration_v2_turn_item_positions.ordinal` for the Chief of Staff thread `mcp:81b7d808-05e0-4366-82a6-af96531c6f95` reaches 4000023 while a read returned positions up to 77. Work out how a read's `position`/`nextPosition` maps to the store (offset, per-kind base, or a different count) and which value the script must print as `next` so a later `--after <p>` and a fallback `t3_thread_read afterPosition=<p>` agree. Use the Chief of Staff thread and one finished child; compare against the position values in a `t3_thread_read` result (the tool is available to the parent: ask for the numbers in your report rather than calling it, or read them from the thread items the parent pasted: messages at positions 0, 10, 21, 26, 42, 51 ... 77 for `mcp:81b7d808-...`).
2. Environment id. `~/.t3/userdata/environment-id` holds the id used in thread links (`<t3-thread://v2/<environment id>/<thread id>>`); confirm it equals the id in a real `link` (the Chief of Staff thread's link starts `fa8d9b7c-8629-46cf-bc5f-096683c72719`). If so, the script reads it from that file and no `t3EnvironmentId` state key is added (this replaces spec § 4's state fallback; when the file is missing, print the thread id in place of the link).
3. Delivered mark. For finished children, compare `payload_json.delegatedCompletion` on runs and `completion_delivery_state` on subagent rows (find where it lives with `.schema` and `grep`-style `sqlite_master` queries) between a child the Chief of Staff has read and one it has not. Report whether `t3_thread_read` of a child's last message changes a stored mark that something later depends on (a repeat run-finished notice, an unsettled thread). If the store shows no difference, or you cannot establish one, keep one `t3_thread_read` with `itemId: <item>` and `maxCharsPerItem: 1` in the `child-read` plan line (the safe default).
4. How `dynamic_tool` turn items look (`payload_json`) so `--wait --store` can feed `wait_calls()` the same shape a `t3_thread_read` activity read gives: `{"runId", "type": "dynamic_tool", "text": "<json with toolName and output>"}`.

## Task 1: `agent-team/scripts/cos_child_read.py` and `test_cos_child_read.py`

Spec § 1. Same `query()` and `--db` shape as `cos_user_check.py`. Exit 2 with `cos_child_read: schema changed` on any `sqlite3.Error` or missing column, `cos_child_read: thread not found` when the thread row is missing. Marker block rules, field patterns (reuse the `cos_handoff.py` path and SHA patterns by import where it exposes them), the 200-character line cut, 1,500-character block cut with the `cut <item> at <offset>` line, and the 400-character `tail:` for `marker none` on a `completed` run. A `running` run prints `marker none`; nothing new after `--after` prints `marker none new=0`.

The test builds a small SQLite file and runs the table from spec § 8.

## Task 2: `cos_idle_check.py --store`

Spec §§ 4, 5. Add `--store [--db PATH]` for the idle check (reads each active ticket's `childThreadId` from state, then the store; same `ok`/`full` lines and exit codes; `provider` lines when the store's provider differs; up to 5 `sub` lines under each `ok`; the link on the `ok` line) and `--wait <T> --store <childThreadId>` (last run and its last 10 `dynamic_tool` items from the store into `wait_calls()` and `check_wait()`). A store error is exit 2 `cos_idle_check: schema changed`. The stdin forms stay unchanged. Update the docstring. Test: one table-driven test per spec § 8.

## Task 3: `cos_tick.py`

Spec § 2, 4. `read_line()` prints `child-read <T> <child> afterPosition=<p>`. `idle_lines()` prints the one `run python3 .../cos_idle_check.py --store [--skip T]` line and no `idle-read` lines or heredoc. Update the docstring and `test_cos_tick.py` expected lines.

## Task 4: `cos_sweep.py`

Spec § 6. Print only action lines and the last line; `--verbose` prints everything. Update the docstring and `test_cos_sweep.py`.

## Task 5: `agent-team/.claude/skills/chief-of-staff/SKILL.md` (and any file `test_agent_files.py` / `test_call_sites.py` / `test_section_pointers.py` tie to it)

Spec § 7: plan line table (`child-read`, the idle check `run` line and the `idle-read` fallback), § Child path (marker, fields, block and `next` from the script's lines; full read only for a cut `BLOCKED` block, a `field …=?`, a `cut` line or an unsettled `--step`), the Stuck check's wait check (`--wait … --store`), § Lean turns Reads, § Report format `Running` sub-lines (from `sub` lines; the `t3_thread_list` call only when the script printed thread ids instead of links), § Sweep, § Tools (`cos_child_read.py`). Fallback sentence: exit 2 means the old `t3_thread_read` with today's limits and one Cleanup line, `Child read script unavailable; used thread read`. Keep it compact; do not restate script docstrings.

## Done when

`python3 -I -m pytest -q agent-team/scripts` is green, `cos_child_read.py` run against the real store prints sensible lines for the Chief of Staff thread and for this build's thread, and `git status` shows only the files above.
