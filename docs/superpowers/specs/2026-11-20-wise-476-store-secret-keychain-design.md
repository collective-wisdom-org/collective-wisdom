# WISE-476: A store-secret command and a keychain key registry

**Status:** Shipped
**Ticket:** [#476](https://github.com/collective-wisdom-org/collective-wisdom/issues/476)
**Shipped:** in PR #477, as specified

## Goal

The user can store a secret in the macOS keychain without pasting it into a chat, and agents can see which secrets the machine holds and fetch one at the moment a task needs it. One script prints a line the user pastes into their own Terminal, and a machine-local registry lists the stored names, never the values.

## Today

- Nothing in `agent-team/` or `install.sh` uses the keychain.
- `agent-team/scripts/gh.sh` takes the GitHub login from `gh`'s own keyring. That is the only credential handling.
- `~/.config/collective-wisdom/user.md` (`agent-team/docs/agents/github-auth.md` § Account per repo, read by `agent-team/scripts/user_config.py`) is the machine-local file the team reads: logins and settings, never tokens. `user_config._rows` reads every table row in the file and matches keys by prefix.
- Agents have no list of what the machine holds and no way to ask for a value without it landing in the transcript.

## Change

### 1. `agent-team/scripts/store_secret.py`

Run as `~/.collective-wisdom/scripts/store_secret.py`. Service name for every team entry: `collective-wisdom`. A name must match `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` (letters, digits, `.`, `_`, `-`, at most 64 characters, not starting with `.` `_` or `-`); anything else exits 2 with `store_secret: <name> is not a safe secret name` and prints no command line.

| Command | What it does | Exit |
|---|---|---|
| `store <name>` | Prints exactly one line: `security add-generic-password -U -s collective-wisdom -a <name> -w`. `-w` is last with no value, so `security` prompts for it and the value never appears in the command, the shell history or the thread. `-U` updates an existing entry. Writes nothing. | 0, or 2 on a bad name |
| `record <name> --note <text>` | Runs `security find-generic-password -s collective-wisdom -a <name>` (no `-w`, so no value is read; its output is discarded and never printed). On exit 0 it adds the name with the note to the registry, or replaces the note if the name is there, and prints `recorded <name>`. When the item is not in the keychain it exits 1 with `store_secret: <name> is not in the keychain; run the store line first` and writes nothing. | 0, 1, or 2 on a bad name, a bad note, a missing `security` or an unreadable registry |
| `list` | Prints one `<name>\t<note>` line per registry row. Nothing when the registry is missing or empty. | 0, or 2 on an unreadable registry |

A note is one line of at most 120 characters with no backtick, `|` or control character; anything else exits 2. The note says what the secret is for; the agent doc says it never holds the value.

### 2. The registry: `~/.config/collective-wisdom/secrets.md`

A separate file beside `user.md`, outside the clone, never committed. `record` creates it (and the folder) when missing, with mode `0600`, as:

```
# collective-wisdom secrets

Names of the secrets this machine keeps in the macOS keychain under the service `collective-wisdom`. Never values.

| Name | Note |
|---|---|
| `openai-api-key` | OpenAI key for the eval scripts |
```

Rows are kept in the order recorded; a re-record replaces the note in place. A row whose first cell is not a backticked safe name is an error on read (`store_secret: <file>:<line>: ...`, exit 2), so a hand edit that breaks the shape is caught instead of skipped.

### 3. Agent doc: `agent-team/docs/agents/secrets.md`

Short role doc, listed in `agent-team/docs/agents/README.md`:

- **Asking for a secret.** When a task needs a secret that `store_secret.py list` doesn't show, the agent picks a name, runs `store <name>`, and asks the user to paste the printed line into their own Terminal and type the value at the prompt. Never ask for the value in the thread. After the user says it's done, run `record <name> --note "<what it is for>"`.
- **Fetching a secret.** Look the name up with `list`, then read it only inside the command that uses it, for example `OPENAI_API_KEY="$(security find-generic-password -s collective-wisdom -a openai-api-key -w)" python3 eval.py`. Never echo it, never store it in a variable that outlives the command, and never write it to a ticket, comment, PR, commit, state file, log or thread.
- **Not here:** deleting or rotating secrets, Linux and Windows stores.

### 4. Pointers

- `agent-team/templates/AGENTS.md` § Secrets and this repo's `AGENTS.md` § Secrets: one line, "A task that needs a secret: `~/.collective-wisdom/docs/agents/secrets.md`."
- `agent-team/docs/agents/github-auth.md` § Account per repo: one line that `user.md` holds no secrets and the keychain names live in `secrets.md` (`~/.collective-wisdom/docs/agents/secrets.md`).

### 5. Test: `agent-team/scripts/test_store_secret.py`

Table-driven, with `HOME` pointed at a temp folder and a fake `security` on `PATH` that records its arguments and exits 0 or 44:

- Names: valid names print the exact store line; names with a space, quotes, `$`, a backtick, `;`, `/`, a newline, a leading `-`, an empty string and a 65-character name exit 2 and print nothing on stdout.
- `record`: with the fake item present it writes the row with the note; a second record replaces the note and keeps one row; with the item absent it exits 1 and leaves no file; the fake `security` never sees `-w`; the registry file never contains the fake's stdout (a stand-in value), and its mode is `0600`.
- Notes: a backtick, `|`, a newline and a 121-character note exit 2 and write nothing.
- `list` reads back what `record` wrote, and a malformed row exits 2.

## Not changing

- `user.md`, `user_config.py` and `setup_repo.py`.
- `gh.sh` and the GitHub login.
- `install.sh`: the script ships with the rest of `agent-team/scripts/` through the machine install.
- No T3 prompt or other agent-visible channel collects a value.

## Acceptance

- `store_secret.py store openai-api-key` prints one line; pasting it in Terminal prompts for the value and stores it; pasting it again updates the entry.
- A name with spaces, quotes, `$`, backticks or other shell characters is refused and no line is printed.
- After `record`, `list` shows the name and note, and the doc's read-back line prints the value in Terminal.
- No script, doc, test or registry file holds a secret value.
- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/store_secret.py` | New: `store`, `record`, `list` |
| `agent-team/scripts/test_store_secret.py` | New: table-driven tests |
| `agent-team/docs/agents/secrets.md` | New agent doc |
| `agent-team/docs/agents/README.md` | Row for `secrets.md` |
| `agent-team/templates/AGENTS.md`, `AGENTS.md` | Pointer line under § Secrets |
| `agent-team/docs/agents/github-auth.md` | One line in § Account per repo |

## Calls I made

- **The registry is its own file, `~/.config/collective-wisdom/secrets.md`, not a table in `user.md`.** `user_config._rows` reads every table row in `user.md` and matches keys by prefix, so a Secrets table there could shadow a setting (a secret named `Spec lane limit-x` would match). A separate file also keeps `user.md`'s "logins and settings" meaning and needs no change to `setup_repo.py`.
- **Recording is a separate `record` step that checks the keychain**, not part of `store`. `store` can't know whether the user ran the line, and the ticket allows either "the user says so" or a check; `record` does the check, so the registry never lists a name the keychain doesn't hold.
- **The command is a script, `~/.collective-wisdom/scripts/store_secret.py store <name>`**, not a shell command on `PATH`. `install.sh` writes only the paths in `project.md` § Security overlays, and adding a `~/bin` link would widen that list. The user can ask any agent to "store a secret called X" and the agent runs the script.
- **Name rule: `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`.** Safe to paste unquoted in zsh and bash, and no leading `-` that `security` could read as a flag.
- **Service name `collective-wisdom`**, the ticket's example.
- **The note is required on `record`** and limited to one line of 120 characters without backticks or `|`, so it fits the table and can't break the row.
- **No `get` or `read` subcommand.** The agent runs `security find-generic-password ... -w` itself inside the command that needs the value, so the value never passes through a team script's output.
- **`list` reads the registry only**; it does not check each name against the keychain.
- **Pointers go in `AGENTS.md` (this repo and the app template) and `github-auth.md`**, not in `machine-instruction.md`, which is about where the team runs.
