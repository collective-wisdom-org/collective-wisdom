# CW-341: Read a Cursor Chief of Staff's context size in the rotation check

**Status:** Shipped
**Shipped:** in PR #361, as specified
**Ticket:** [#341](https://github.com/collective-wisdom-org/collective-wisdom/issues/341)

## Goal

On Cursor, the rotation check reads a context size for the Chief of Staff's conversation from the Cursor run store, so it prints a size and the size trigger can fire, instead of "size unknown on Cursor".

## Today

Facts from `main` at `6e85821`.

- `cos_rotation_check.py` reads a size only through `read_context()`, which calls `agent_usage.py` `context_line()`. That needs `$CLAUDE_CODE_SESSION_ID` and reads Claude Code transcripts.
- On Cursor, `main()` and `run_hook()` call `check(..., sized=False)`, so `decide()` gets `context=None`.
- `agent_usage.py` `read_store()` and `cursor_agent_runs()` already read `~/.cursor/projects/*/sdk-agent-store/*/index.db` read-only. Its `runs` table has one row per turn with `usage_json`; its `run_events` table holds the turn's stream (`request`, `status`, `thinking`, `assistant`, `tool_call`, `usage`).
- `docs/compatibility.md` G8 says `--context` reads Claude Code only, so a Cursor Chief of Staff has no context size.

## What the run store holds (checked on this machine)

The only Cursor Chief of Staff store on this machine is the 2026-11-08 trial (`~/.cursor/projects/Users-david-beallor-Documents-cw-cursor-trial`, one agent, 18 turns, `grok-4.7`).

- **`inputTokens` is a sum over the turn's requests, not the last prompt.** Turn 13 ran 9 minutes with 79 tool calls and records `inputTokens` 4,789,860, more than any context window. Turns 2 to 4 have no tool calls (one request each) and record 28,259, 29,032 and 29,557, which is the prompt.
- **The `usage` event is the same record.** Each finished turn has one `usage` event in `run_events`, equal to `usage_json`. No event or transcript line carries a per-request size, and the checkpoint blobs are encrypted.
- **The requests in a turn can be counted.** Each `tool_call` event has a `call_id` like `call-<uuid>-<i>\nfc_..._<i>`. Calls from one model request share `call-<uuid>`, with `-0`, `-1` for parallel calls. So a turn made `1 + <distinct call-<uuid> prefixes>` requests.
- **The average prompt per request tracks the real size.** `inputTokens ÷ requests` by turn: 21.6k, 28.3k, 29.0k, 29.6k, 31.6k, 39.3k, 43.9k, 47.1k, 49.2k, 52.8k, 55.8k, 57.3k, 111.4k, 169.6k, 175.5k, (16 cancelled, no usage), 200.5k, 213.2k. It only grows, and single-request turns match the prompt exactly.
- **The average is a floor on the last prompt.** A prompt grows within a turn, so the last request's prompt is at least the average. On a long turn it can be well above it: turn 13 averages 111k, and the next turn already averages 170k.

So no exact size comes out, but a floor does: it never reports more than the real prompt, so it never resets early, and it can reset late on a long turn. This spec uses the floor.

## Design

1. **`agent_usage.py` `cursor_context(projects, agent)`.** Looks through `projects/*/sdk-agent-store/*/index.db` (read-only, as `cursor_agent_runs()` does) for the store whose `agents` table has `agent` (the id as stored, `agent-<uuid>`). Returns `(tokens, started)`:
   - the latest turn with `usage_json` (highest `turn_number`), its `inputTokens` divided by its request count, rounded down;
   - the request count is 1 plus the number of distinct `call-<uuid>` prefixes in that run's `tool_call` events (the part of `call_id` before the newline, with the trailing `-<digits>` removed);
   - `started` is the earliest run's `started_at` (else `created_at`), as UTC.
   - It returns `None` when the agent's store has no run with usage yet (a new conversation, or only a running or cancelled turn).
   - It raises `LookupError` when no readable store has the agent, when a store that could hold it cannot be read, when `run_events` is missing, or when the latest usage record cannot be parsed. A missing `run_events` is an error and not "one request", because treating a sum as one prompt would reset early.
2. **`cos_rotation_check.py` reads it on Cursor.** `read_context()` gains a Cursor path: given a Cursor conversation id, it calls `cursor_context()` with `COS_CURSOR_PROJECTS_DIR` (default `~/.cursor/projects`) and the id with the `agent-` prefix added if it is bare (the reverse of `bare()`). `LookupError` becomes `Unreadable("context")`, so plain mode exits 2 with `rotation-check: cannot read context` and the hook answers with it as it does today for Claude Code. `None` (no usage yet) means size unknown, `context=None`.
3. **`check()` takes the provider, not `sized`.** `sized=False` is replaced by `cursor=True`, which reads the size through the Cursor path. Plain mode passes it when it found the conversation through `cursor_conversation()`; `--hook` passes it on Cursor's stop payload. `--record-takeover` saves the Cursor size like any other.
4. **Lines.** Nothing in `decide()` changes. With a Cursor size, the line is `ok context=<N>k` or `rotate: size <N>k >= 220k; mode <mode>` on a provider with a reset mode, and `ok (no reset on cursor; context=<N>k)` while `cursor` has mode `none`, which it keeps (out of scope). "ok (size unknown on Cursor)" stays for a conversation with no usage yet.
5. **Docs.** The `cos_rotation_check.py` docstring: on Cursor the size is read from the run store and is a floor. `docs/compatibility.md` G8: `--context` still reads Claude Code only, the rotation check reads a Cursor Chief of Staff's size from its run store as the average prompt over the latest turn's requests, a floor that can trigger late on a long turn and never early; reset mode stays `none`. The trial line that printed "ok (size unknown on Cursor)" stays: it records what that run saw. `rotation.md` and `state-keys.md` get a sentence only if they say Cursor has no size (the build checks).
6. **Test.** One table-driven test in `test_agent_usage.py` over a fixture `index.db` built in `tmp_path` (the same schema as above): a turn with no tool calls (size = `inputTokens`), a turn with two requests and parallel calls (size = sum ÷ 2), the latest turn wins over earlier ones, no usage yet (`None`), an unreadable store and a store without `run_events` (`LookupError`). One row set in `test_cos_rotation_check.py` through `main()` and `--hook` on Cursor: the fixture store gives `ok (no reset on cursor; context=<N>k)` (and `rotate: size ...` under a provider with a reset mode, through `RESET_MODES` patched), an unreadable store gives exit 2 with `cannot read context`, and no usage gives the size-unknown line. The existing `sized=False` test changes to these.

## Leaves out

- `RESET_MODES` and the Context reset row of the compatibility matrix: `cursor` stays `none` (ticket's Out of scope).
- Running the reset on Cursor; Codex and Antigravity.
- A `--context` flag for Cursor on `agent_usage.py`: the check calls the function directly.
- Decrypting checkpoint blobs or estimating growth within a turn beyond the average.

## Calls I made (surprising first)

- **The size is a floor, not the exact prompt.** The run store records a sum per turn, so the check divides by the request count. It can reset late after a long turn (turn 13 above was about 55k under), never early. The other choice was to read no size and only record why in G8; a floor still makes the trigger fire for a long-running Chief of Staff, which is what the ticket wants.
- **Request count comes from `tool_call` `call_id` prefixes.** That id format is not documented by Cursor; it held for every turn in the trial store. If the format changes, the count drops toward one per call or one per turn. The first overcounts requests and lowers the floor; the second makes the size the sum and could reset early. The test pins the parsed format so a change is noticed when the fixture is updated from a real store.
- **No usage yet is size unknown, not unreadable.** A new conversation's first check runs mid-turn before any usage exists; exit 2 there would make the hook nag every new Chief of Staff.
- **The latest turn with usage counts**, so a plain check mid-turn reads the previous turn and a cancelled turn is skipped.
- **The store is found across all Cursor projects**, as `cursor_agent_runs()` does, not only the app's folder, since agent ids are unique.
- **A missing `run_events` is unreadable**, so the check never treats a sum as one prompt.
- **One Cursor Chief of Staff run on one model (`grok-4.7`) is the only evidence.** Auto runs were not checked.

## Touches

None of data, money, auth, user email or migrations.
