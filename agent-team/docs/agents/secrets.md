# Secrets

How a task gets a secret without the value entering a thread. The macOS keychain holds values under the service `collective-wisdom`. The registry `~/.config/collective-wisdom/secrets.md` (outside the clone, never committed) lists each name with a note, never a value. The docstring of `~/.collective-wisdom/scripts/store_secret.py` owns the commands and the name and note rules.

## Asking for a secret

1. `~/.collective-wisdom/scripts/store_secret.py list`. If the name is there, go to Fetching a secret.
2. Pick a name. Call T3's `request_secret` with `delivery: "file"`, a `label` naming the secret and a `reason`; the user types the value into the card. On `declined`, `cancelled` or `timed_out` there is no file: do not run `save`; tell the user the task is waiting on the secret.
3. `~/.collective-wisdom/scripts/store_secret.py save <name> --note "<what it is for>" --file <path>` with the `file` path the tool returned. The script reads the file and writes the keychain itself (a new value under the same name updates the entry); the value stays out of every command line and output (limits and exit codes: its docstring). The note says what the secret is for, not what it is.
4. Never ask for the value in the thread. If the user pastes one anyway, do not repeat it; tell them to rotate it.

Without `request_secret`: `~/.collective-wisdom/scripts/store_secret.py store <name>` prints one `security add-generic-password` line (one-line values only) and writes nothing; the user pastes it into their own Terminal and types the value at the prompt. When they say it is done, run `~/.collective-wisdom/scripts/store_secret.py record <name> --note "<what it is for>"` (same keychain check as `save`).

## Fetching a secret

`list` the name, then read the value only inside the command that uses it. The `security ... -w` call is the only read; no script command prints a value.

```bash
OPENAI_API_KEY="$(security find-generic-password -s collective-wisdom -a openai-api-key -w)" python3 eval.py
```

- Never echo the value or keep it in a variable that outlives the command.
- Never write it to a ticket, comment, PR, commit, state file, log or thread, command output included.

## Not covered

Deleting or rotating a secret; Linux and Windows credential stores.
