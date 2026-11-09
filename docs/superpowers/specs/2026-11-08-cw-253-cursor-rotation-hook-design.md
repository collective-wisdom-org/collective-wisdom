# CW-253: Install the Chief of Staff rotation hook for Cursor

**Status:** Shipped
**Shipped:** in PR #262, as specified
**Ticket:** [#253](https://github.com/collective-wisdom-org/collective-wisdom/issues/253)

## Goal

A Chief of Staff thread on Cursor that is due to rotate gets the same `rotate:` stop that a Claude Code one gets, from a hook that `./install.sh` puts in `~/.cursor/hooks.json` once, however often it is run.

## Today

Facts from `main` at `cbc35dc`.

- `install.sh` merges one Stop hook into `~/.claude/settings.json` (`mpython hook`): `{"hooks": {"Stop": [{"hooks": [{"type": "command", "command": ...}]}]}}`, running `python3 -I "$HOME/.collective-wisdom/scripts/cos_rotation_check.py" --hook || true`. It skips the file when its `hooks` already mention `cos_rotation_check.py` (`present`), and leaves a file that is not a JSON object with a list under `hooks.Stop` alone, with a TODO (`invalid`).
- `cos_rotation_check.py --hook` (`run_hook`) reads Claude Code's stdin JSON, and does nothing unless `session_id` equals `chiefSessionId` in state and `stop_hook_active` is false. On a line that does not start with `ok` it prints `{"decision": "block", "reason": "<line>; run chief-of-staff/rotation.md § Thread rotation"}`. It moves to `$CLAUDE_PROJECT_DIR` first.
- Plain mode (the Chief's call every working turn) saves `chiefSessionId` from `$CLAUDE_CODE_SESSION_ID`, and reads the thread's context size from Claude Code transcripts (`agent_usage.py --context`). With no such transcript it prints `rotation-check: cannot read context` and exits 2. So on Cursor today the plain call fails every turn and `chiefSessionId` is never set.
- `docs/compatibility.md`: the Stop hook cell for Cursor is `🔴 not supported` (G7), and G7 says Cursor, Codex and Antigravity get no hook.

What Cursor's docs say (<https://cursor.com/docs/hooks>, read 2026-11-08):

- User hooks live in `~/.cursor/hooks.json`: `{"version": 1, "hooks": {"stop": [{"command": "..."}]}}`. Cursor reloads the file when it changes. Each entry may also carry `timeout`, `loop_limit` (default 5 for a stop hook) and others.
- Every hook gets on stdin `conversation_id`, `generation_id`, `hook_event_name`, `workspace_roots`, `transcript_path` and a few more. A stop hook also gets `status` (`completed`, `aborted` or `error`) and `loop_count`. There is no `session_id` field.
- A stop hook asks the agent to go on by printing `{"followup_message": "..."}`: Cursor sends it as the next user message. `decision: block` is not a Cursor field.
- A user hook runs from `~/.cursor/`. Cursor sets `CURSOR_PROJECT_DIR` and, for Claude compatibility, `CLAUDE_PROJECT_DIR` to the workspace root.
- The docs name no environment variable that gives the agent's own shell its conversation id.
- On this machine, Cursor keeps transcripts at `~/.cursor/projects/<workspace path with / as ->/agent-transcripts/<conversation_id>/<conversation_id>.jsonl`, so the folder name is the `conversation_id` the hook gets.

## Design

### 1. `--hook` reads either payload

`run_hook` tells the two apart by the payload. A payload with `conversation_id` and `hook_event_name` `stop` is Cursor's; anything else is Claude Code's, read exactly as today.

| | Claude Code | Cursor |
|---|---|---|
| Session id | `session_id` | `conversation_id` |
| Already sent back once | `stop_hook_active` true | `loop_count` > 0 |
| Also skipped | | `status` other than `completed` (the user stopped it, or it errored) |
| Size trigger | on | off (no context size on Cursor, G8) |
| Answer on `rotate:` or `cannot read` | `{"decision": "block", "reason": R}` | `{"followup_message": R}` |

`R` is the same string on both. Everything else in `run_hook` stays: silent outside a repo with `docs/agents/project.md`, silent for an app's own copy, never writes, exits 0 on any error.

The move to the project folder already uses `$CLAUDE_PROJECT_DIR`, which Cursor also sets; it also tries `$CURSOR_PROJECT_DIR` first when set, since a user hook starts in `~/.cursor/`.

### 2. The size trigger is off on Cursor

`check` takes the context size as optional. When it is unknown, `decide` skips the size trigger and its `ok` line says so (`ok (size unknown on Cursor)` in place of `ok context=...`). The skill-change trigger, the holds and the quiet-turn wait are the same on both. Without this, the Cursor hook would block every Chief of Staff stop with `cannot read context`.

### 3. Plain mode saves the Cursor conversation id

Plain mode keeps `$CLAUDE_CODE_SESSION_ID` when it is set. When it is not, it looks for the newest transcript under `~/.cursor/projects/<slug of the app root>/agent-transcripts/` changed in the last 2 minutes. If there is one, the run is on Cursor: it saves that folder name as `chiefSessionId` (same `save_top` path as today) and runs the check with the size unknown. If there is none, plain mode does what it does today (a Codex Chief still exits 2 on context; out of scope).

The newest transcript in the root checkout's folder is the Chief's own: the Chief of Staff is the session working in the root checkout, children work in worktrees (their own folders), and the transcript being written while the check runs is the running one. `COS_CURSOR_PROJECTS_DIR` overrides `~/.cursor/projects` for tests, beside `COS_PROJECTS_DIR`.

### 4. `install.sh` merges `~/.cursor/hooks.json`

A new `mpython` mode, `cursor-hook`, next to `hook`, with the same rules:

- No file: write `{"version": 1, "hooks": {"stop": [{"command": C}]}}` (`created`).
- `hooks` already mentions `cos_rotation_check.py`: nothing (`present`), so a rerun adds no second entry.
- Otherwise append `{"command": C}` to `hooks.stop`, keep every other key and hook, and add `"version": 1` only when `version` is missing (`added`).
- Not a JSON object, or `hooks` / `hooks.stop` of the wrong type: leave it alone and print a TODO with the entry to add by hand (`invalid`).
- Written through the same temp file and rename, so a linked file stays a link; `--dry-run` writes nothing.

`C` is the same command as the Claude Code hook. `install.sh` prints `added  ~/.cursor/hooks.json (stop hook)` like the settings line. `loop_limit` is left at Cursor's default; the hook answers only when `loop_count` is 0.

### 5. Docs

- `docs/agents/project.md` § Security overlays: add `~/.cursor/hooks.json` to the paths `install.sh` may write.
- `docs/compatibility.md`: Stop hook cell for Cursor `🟡 partial: skill-change rotation only, no size trigger (G8)`, until a Cursor Chief of Staff has run it (then `works`); the note under Matrix 1 and G7 say Codex and Antigravity get no hook.
- `README.md` install paragraph: names `~/.cursor/hooks.json`.
- `chief-of-staff/rotation.md` and `state-keys.md`: the hook is in both files, and `chiefSessionId` is the Claude session id or the Cursor conversation id.

### Tests

- `test_cos_rotation_check.py`: one table over payloads (Claude Code and Cursor; chief and other session; already sent back; Cursor `status` not `completed`) checking which answer, if any, is printed and its shape. One case for plain mode finding a fresh Cursor transcript and saving its id, and the size trigger staying off.
- `test_install_machine.py`: one table over `~/.cursor/hooks.json` starting states (missing, other hooks, already present, no `version`, not an object, `stop` not a list), checking the file after a run and after a second run.

## Leaves out

- Codex and Antigravity hooks.
- Gantt snapshots from Cursor hooks (separate ticket).
- A context size for Cursor threads (G8): the size trigger stays off there, and the item-count fallback in `rotation.md` still applies.
- A Cursor project-level `.cursor/hooks.json`.

## Not proven before merge

- No Cursor CLI is on this machine, so no Cursor Chief of Staff runs the hook in this PR. The tests feed it Cursor's documented payload. Whether T3 Code's Cursor provider loads `~/.cursor/hooks.json`, runs the command through a shell (for `$HOME`), and writes transcripts where the Cursor app does stays unproven until a Cursor Chief of Staff thread runs.

## Calls I made

- **The Chief's Cursor id comes from the newest transcript folder**, since Cursor names no variable for it. Another Cursor chat open in the root checkout at the same moment could claim the id; the next plain call from the Chief puts its own back.
- **Size trigger off on Cursor** rather than estimating the size from the transcript file. Rotation on Cursor comes only from a skill change; the compatibility cell says partial.
- **One follow-up per stop**: the hook answers only at `loop_count` 0, like `stop_hook_active` on Claude Code, and leaves `loop_limit` at Cursor's default.
- **No answer when the stop `status` is `aborted` or `error`**, so a user stopping the Chief is not overridden.
- **Same command string as the Claude Code hook**, so the two installs stay in step.
- **`version: 1` added only when missing**; an existing version is kept.
- The spec edits `docs/agents/project.md` § Security overlays, as the ticket asks.
