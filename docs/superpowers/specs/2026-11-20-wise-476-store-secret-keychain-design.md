# WISE-476: A store-secret command and a keychain key registry

**Status:** Shipped
**Ticket:** [#476](https://github.com/collective-wisdom-org/collective-wisdom/issues/476)
**Shipped:** in PR #477, as specified

## Goal

The user can store a secret in the macOS keychain without pasting it into a chat, and agents can see which secrets the machine holds and fetch one at the moment a task needs it. The agent asks for the value with T3 Code's `request_secret` tool (a card the user types into; the value never reaches the thread), and one script writes it to the keychain and records the name in a machine-local registry that lists names, never values. A second command prints a line the user can paste into their own Terminal when `request_secret` isn't available.

**Changed after approval:** the user asked ("you should use t3's built in functionality to store a secret securely and write it to the keychain yourself") for `request_secret` and a `save` command. That overrides the ticket's out-of-scope line "Collecting a secret through a T3 prompt" for this PR.

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
| `save <name> --note <text> --file <path>` | Reads the value from the file `request_secret` returned (`delivery: "file"`), strips trailing newlines the way `$(cat file)` does, and writes it to the keychain. The value goes to `security -i` on stdin as `add-generic-password -U -s collective-wisdom -a <name> -X <hex of the value>`, so it never appears in a command line, in `ps` output, in the shell history or in any output, and a quote, backslash or `$` in the value can't break the command. (`-w <value>` on stdin does not survive a `'` or `\`, so the hex form is used.) `-U` updates an existing entry. It then checks the item as `record` does and adds the name and note to the registry, printing `saved <name>`. It does not delete the file; T3 owns it. The file must be a regular file (checked on the open descriptor, so a FIFO can't hang it) holding 1 to 1900 bytes once trailing newlines are stripped: `security -i` splits an input line past about 4094 characters and would store a cut-off value, so a longer value is refused (exit 2) and the `store` line is the way to store it; `security` output is discarded. | 0, 1 when the item is not in the keychain after the write, or 2 on a bad name, a bad note, a bad or empty file, a failing `security` or an unreadable registry |
| `store <name>` | The fallback when `request_secret` isn't available. Prints exactly one line: `security add-generic-password -U -s collective-wisdom -a <name> -w`. `-w` is last with no value, so `security` prompts for it and the value never appears in the command, the shell history or the thread. `-U` updates an existing entry. Writes nothing. | 0, or 2 on a bad name |
| `record <name> --note <text>` | Runs `security find-generic-password -s collective-wisdom -a <name>` (no `-w`, so no value is read; its output is discarded and never printed). Only exit 0 (found) and 44 (not found) are answers: any other `security` exit, or a 30-second timeout, exits 2 (`security exited <code>; check that the keychain is unlocked`), so a locked keychain is not read as a missing item. On exit 0 it adds the name with the note to the registry, or replaces the note if the name is there, and prints `recorded <name>`. When the item is not in the keychain it exits 1 with `store_secret: <name> is not in the keychain; run the store line first` and writes nothing. | 0, 1, or 2 on a bad name, a bad note, a missing or failing `security`, or an unreadable or undecodable registry |
| `list` | Prints one `<name>\t<note>` line per registry row. Nothing when the registry is missing or empty. | 0, or 2 on an unreadable registry |

A note is one line of at most 120 characters with no backtick, `|`, control character, line or paragraph separator, zero-width character or bidi override (U+200B to U+200F, U+202A to U+202E); anything else exits 2. The note says what the secret is for; the agent doc says it never holds the value.

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

- **Asking for a secret.** When a task needs a secret that `store_secret.py list` doesn't show, the agent picks a name and calls `request_secret` (an MCP tool on the T3 server; load it with ToolSearch if it is deferred) with `delivery: "file"`, a `label` naming the secret and a `reason`. The user types the value into the card. The agent then runs `store_secret.py save <name> --note "<what it is for>" --file <path>` with the path the tool returned, and the value never enters the thread. Never ask for the value in the thread. Without `request_secret`, run `store <name>`, have the user paste the printed line into their own Terminal and type the value at the prompt, then run `record <name> --note "<what it is for>"`.
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
- `save`: the fake `security` run as `security -i` receives the exact hex command on stdin and nothing in its arguments; a value with `'`, `"`, `\`, `$` and a space round-trips as hex; trailing newlines are stripped; an empty file, a directory and a 1901-byte value exit 2 and write nothing; with the item absent after the write it exits 1 and leaves no registry; the stand-in value never reaches the registry, stdout or stderr.
- `list` reads back what `record` wrote, and a malformed row exits 2.

## Not changing

- `user.md`, `user_config.py` and `setup_repo.py`.
- `gh.sh` and the GitHub login.
- `install.sh`: the script ships with the rest of `agent-team/scripts/` through the machine install.
- Deleting or rotating secrets, and Linux or Windows stores.

## Acceptance

- With a value in a file, `store_secret.py save openai-api-key --note "..." --file <path>` stores it in the keychain and records the name; running it again with another value updates the entry; the value appears in no output and no command line.
- `store_secret.py store openai-api-key` prints one line; pasting it in Terminal prompts for the value and stores it; pasting it again updates the entry.
- A name with spaces, quotes, `$`, backticks or other shell characters is refused and no line is printed.
- After `record`, `list` shows the name and note, and the doc's read-back line prints the value in Terminal.
- No script, doc, test or registry file holds a secret value.
- `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh` pass.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/store_secret.py` | New: `save`, `store`, `record`, `list` |
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
- **`save` takes the file `request_secret` returns, and the value goes to `security -i` on stdin as hex (`-X`).** The user suggested `-w "$(cat <file>)"`, which puts the value in the command line where `ps` shows it. `security -i` reads commands from stdin, and hex avoids the quoting that breaks `-w` there (a `'` or `\` in the value is mangled or rejected, checked on this machine).
- **`store` and `record` stay as the fallback** for a host without `request_secret`, so the earlier-approved flow still works.
- **`save` doesn't delete the file.** T3 hands out the file for one command and owns it.
- **The doc tells the agent to load `request_secret` itself** (ToolSearch when deferred) because that tool lives on the T3 server, not in this repo.
