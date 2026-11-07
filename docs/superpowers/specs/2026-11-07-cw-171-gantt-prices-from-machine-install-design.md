# CW-171: Read the agent-gantt price table from the machine install

**Status:** Draft
**Ticket:** [#171](https://github.com/collective-wisdom-org/collective-wisdom/issues/171)
**Follows:** CW-169 (#170), which removed this repo's root `scripts` link.

## Goals

The `agent-gantt` cost column shows dollar amounts in this repo and in an app, read from the price table the machine install already has at `~/.collective-wisdom/scripts/prices.json`. It shows a dash only when that file is missing or unreadable, and the pane's note then names that path.

## Today

Facts from `main` at `1f8a178`.

- `mods/agent-gantt/hooks/register.tsx` sets `PRICES_PATH = 'scripts/prices.json'`. `loadPrices` reads it with `$.fs.read(PRICES_PATH)`, which resolves a relative path under the session's working directory. A miss stores `table: null` and the note `scripts/prices.json is missing or unreadable here.`, drawn as `Costs hidden: <note>`.
- No session folder has `scripts/` now: apps never did, and CW-169 removed this repo's link. So the column is a dash everywhere.
- The table is `agent-team/scripts/prices.json`, reached on the machine at `~/.collective-wisdom/scripts/prices.json` (`install.sh` links `~/.collective-wisdom` to the clone's `agent-team/`; the path is fixed, with no variable to move it).
- `mods/agent-gantt/types/index.d.ts` lines 22 and 26 name `scripts/prices.json` in two comments.
- `README.md` line 170 says costs come from `scripts/prices.json` in the session's folder and that an app and this repo show a dash.
- `agent-team/scripts/approval_policy.py` lines 42-43 say `PATH_FILES` matches "the bare name of the `scripts` root link, which `gh` can list as a file". There is no root link now.
- `mods/agent-gantt/.claude-plugin/plugin.json` is at `version` `0.1.0`. README says a PR that changes a mod bumps it.

### The open question: what path `$.fs.read` accepts

Settled from the mod API types (`claude-code.d.ts` in the bundled `plugin-authoring` skill, Claude Code 2.1.318):

- `$.fs`: "a relative path is under the session's working directory ... An absolute path is used as given." So an absolute path works.
- `~` is not expanded. Nothing in the types promises it, and the `$.fs.stat` notes name `~` as a spelling the engine cannot resolve.
- `$.env.get("HOME")` resolves with the variable or `undefined`. The name must be a string literal, and `claude plugin validate` lists the names a module reads.

So the mod builds the path from `HOME`.

## Builds

### 1. `register.tsx`

- Replace `PRICES_PATH` with `PRICES_PATH = '.collective-wisdom/scripts/prices.json'` (relative to home) and a shown name `~/.collective-wisdom/scripts/prices.json` for the note.
- In `loadPrices`, inside the existing `try`: `const home = await $.env.get('HOME')`; if it is unset or empty, throw so the `catch` sets the dash. Otherwise read `${home}/${PRICES_PATH}` with `$.fs.read`.
- The miss note becomes `~/.collective-wisdom/scripts/prices.json is missing or unreadable. Run ./install.sh in the collective-wisdom clone.` The pane still prefixes it with `Costs hidden:`.
- Update the `loadPrices` doc comment to say where it reads from.
- Nothing else changes: the same `prices-1` atom shape, the same load-once rule (forced again by `/agent-gantt`), and `costOf` in `rows.ts` untouched.

### 2. Comments and docs

- `types/index.d.ts`: the two comments name `~/.collective-wisdom/scripts/prices.json`.
- `README.md` line 170: costs come from `~/.collective-wisdom/scripts/prices.json`, the machine install's copy of the table `agent_usage.py` reads, so the column works in an app and in this repo; the dash shows only when that file is missing. Keep the 5 minute cache write sentence.
- `approval_policy.py` lines 42-43: reword to say it also matches the bare name `scripts`, because `gh` lists a link by that name as a file (an old branch may still carry one). Comment only. `PATH_FILES`, `PATH_DIRS` and every rule stay as they are.

### 3. Version

- `mods/agent-gantt/.claude-plugin/plugin.json`: `0.1.0` to `0.1.1`.

### 4. Tests and proof

- No new test. `loadPrices` is a file read and an env read through the engine; a test would restate it (`AGENTS.md` § Testing). `rows.test.ts` covers `buildRows`, which this does not change.
- Run `node --test mods/agent-gantt/hooks/rows.test.ts` (Node 24+) and `python3 -I -m pytest -q agent-team/scripts`.
- Run `claude plugin validate mods/agent-gantt` and confirm it passes and lists `HOME` among the env names read.
- Proof by hand where the session allows it: install the mod from the branch, open `/agent-gantt` in this repo and see dollar amounts; then point the check at a missing file (for example a session with `HOME` set to an empty temp folder) and see the dash and the new note. Whatever the build session cannot run goes under the PR's `Not proven`.

## Leaves out

- Any change to approval rules, `PATH_FILES` or `PATH_DIRS`.
- The price numbers, `prices.json` itself and `agent_usage.py`.
- A fallback to the old session-relative `scripts/prices.json`, or to a copy the mod ships under `$.plugin.root`.
- Hosts without `HOME` (Windows): they get the dash, as today. `install.sh` does not support them either.

## Overlap with CW-97 and CW-98

Both are open and wait on spec approval.

- CW-97 (open an agent from its pane row) edits `register.tsx`'s `ui.render` handler and the rows. This ticket touches only `PRICES_PATH`, `loadPrices` and its note. Small textual overlap; whichever lands second rebases.
- CW-98 (history mode) adds a JSON output to `agent_usage.py`, which prices with the same `prices.json`. No conflict with this ticket's change; its pane code would read live prices from the same path this ticket sets. Both bump `plugin.json`, so the later PR takes the next version.

## Calls I made

- The path is built from `HOME`, not `~`, because `$.fs` does not expand `~`. With `HOME` unset the column shows a dash and the same note.
- No fallback to the old `scripts/prices.json` in the session folder. No repo has it now, and one path keeps the note simple.
- The miss note says to run `./install.sh`, since a missing file means the machine install is missing or old.
- The mod does not ship its own copy of the price table. One table, read by both `agent_usage.py` and the mod, stays the rule from README.
- No new test, per `AGENTS.md` § Testing; the proof is the plugin validate run plus a by-hand pane check.
- `plugin.json` goes to `0.1.1` (a fix, not a feature).
- The `approval_policy.py` comment keeps explaining why the bare `scripts` entry exists, now as a link an old branch may carry, instead of deleting the explanation.
