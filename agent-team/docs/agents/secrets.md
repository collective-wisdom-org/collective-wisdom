# Secrets

How a task gets a secret without the value entering a thread. The macOS keychain holds values under the service `collective-wisdom`. The registry `~/.config/collective-wisdom/secrets.md` (outside the clone, never committed) lists each name with a note, never a value. The docstring of `~/.collective-wisdom/scripts/store_secret.py` owns the commands and the name and note rules.

## Asking for a secret

1. Run `~/.collective-wisdom/scripts/store_secret.py list`. If the name is there, go to Fetching a secret.
2. Pick a name. Call T3's `request_secret` with `delivery: "file"`, a `label` naming the secret and a `reason`; the user types the value into the card, so it never enters the thread. On `declined`, `cancelled` or `timed_out` there is no file: do not run `save`; tell the user the task is waiting on the secret.
3. Run `~/.collective-wisdom/scripts/store_secret.py save <name> --note "<what it is for>" --file <path>` with the `file` path the tool returned. The value must be 1 to 1900 bytes (`security -i` cuts a longer line). The script reads the file and writes the keychain itself, so the value is in no command line, output or history; a new value under the same name updates the entry. It exits 1 if the keychain does not hold the item. The note says what the secret is for, not what it is. The script leaves the file to T3. 
4. Never ask for the value in the thread. If the user pastes one anyway, do not repeat it; tell them to rotate it.

Without `request_secret`, run `~/.collective-wisdom/scripts/store_secret.py store <name>`: it prints one `security add-generic-password` line (one-line values only) and writes nothing; the user pastes it into their own Terminal and types the value at the prompt. When they say it is done, run `~/.collective-wisdom/scripts/store_secret.py record <name> --note "<what it is for>"` (same keychain check as `save`).

## Fetching a secret

Look the name up with `list`, then read the value only inside the command that uses it. The `security ... -w` call is the only read; no script command prints a value.

```bash
OPENAI_API_KEY="$(security find-generic-password -s collective-wisdom -a openai-api-key -w)" python3 eval.py
```

- Never echo the value or keep it in a variable that outlives the command.
- Never write it to a ticket, comment, PR, commit, state file, log or thread, command output included.

## Not covered

Deleting or rotating a secret; Linux and Windows credential stores.
