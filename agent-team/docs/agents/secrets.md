# Secrets

How a task gets a secret without the value passing through a thread. The macOS keychain holds the values under the service `collective-wisdom`. A registry outside the clone, `~/.config/collective-wisdom/secrets.md`, lists each name with a note, never a value, and is never committed.

The script is `~/.collective-wisdom/scripts/store_secret.py` with three commands: `store <name>`, `record <name> --note "<text>"` and `list`. A name is letters, digits, `.`, `_` and `-`, at most 64 characters, and does not start with `.`, `_` or `-`.

## Asking for a secret

1. Run `~/.collective-wisdom/scripts/store_secret.py list`. If the name the task needs is there, go to Fetching a secret.
2. Pick a name and run `~/.collective-wisdom/scripts/store_secret.py store <name>`. It prints one `security add-generic-password` line and writes nothing.
3. Ask the user to paste that line into their own Terminal and type the value at the prompt. The value never appears in the command, the shell history or the thread. Running the line again updates the entry.
4. Never ask for the value in the thread, and never accept it there. If the user pastes one anyway, do not repeat it and tell them to rotate it.
5. When the user says it is done, run `~/.collective-wisdom/scripts/store_secret.py record <name> --note "<what it is for>"`. It checks that the keychain holds the item and exits 1 if not, so the registry never lists a name the keychain lacks. The note says what the secret is for, not what it is.

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
