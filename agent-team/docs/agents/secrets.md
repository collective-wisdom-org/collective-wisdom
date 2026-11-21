# Secrets

How a task gets a secret without the value entering a thread. The macOS keychain holds values under the service `collective-wisdom`. The registry `~/.config/collective-wisdom/secrets.md`, outside the clone and never committed, lists each name with a note, never a value.

The script is `~/.collective-wisdom/scripts/store_secret.py` with four commands: `save <name> --note "<text>" --file <path>`, `store <name>`, `record <name> --note "<text>"` and `list`. A name is letters, digits, `.`, `_` and `-`, at most 64 characters, and does not start with `.`, `_` or `-`.

## Asking for a secret

1. Run `~/.collective-wisdom/scripts/store_secret.py list`. If the name the task needs is there, go to Fetching a secret.
2. Pick a name. Call `request_secret`, a tool on the T3 server, with `delivery: "file"`, a `label` that names the secret and a `reason`. The user types the value into the card, so it never enters the thread. If it returns `declined`, `cancelled` or `timed_out` there is no file: do not run `save`; tell the user the task is waiting on the secret.
3. Run `~/.collective-wisdom/scripts/store_secret.py save <name> --note "<what it is for>" --file <path>` with the `file` path the tool returned. The value must be 1 to 1900 bytes (`security -i` cuts a longer line, so it is refused); a longer one is not supported. The script reads the file and writes the keychain itself, so the value is in no command line, output or history. Running it again with a new value updates the entry. It then adds the name to the registry, and exits 1 if the keychain does not hold the item. The note says what the secret is for, not what it is. The script does not delete the file; T3 owns it.
4. Never ask for the value in the thread, and never accept it there. If the user pastes one anyway, do not repeat it and tell them to rotate it.

Without `request_secret`, run `~/.collective-wisdom/scripts/store_secret.py store <name>` instead. It prints one `security add-generic-password` line and writes nothing. The user pastes it into their own Terminal and types the value at the prompt; the prompt takes one line, so `store` is for single-line values. When they say it is done, run `~/.collective-wisdom/scripts/store_secret.py record <name> --note "<what it is for>"`, which makes the same keychain check as `save`.

## Fetching a secret

Look the name up with `list`, then read the value only inside the command that uses it:

```bash
OPENAI_API_KEY="$(security find-generic-password -s collective-wisdom -a openai-api-key -w)" python3 eval.py
```

- Never echo the value, and never keep it in a variable that outlives the command.
- Never write it to a ticket, comment, PR, commit, state file, log or thread, including command output that would print it.
- The script has no command that prints a value; the `security ... -w` call above is the only read.

## Not covered

Deleting or rotating a secret, and the Linux and Windows credential stores.
