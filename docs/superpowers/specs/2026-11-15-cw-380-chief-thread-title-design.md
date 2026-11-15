# CW-380: Set the Chief of Staff thread title to "<PREFIX> - Chief of Staff" every time it starts

**Status:** Draft
**Ticket:** [#380](https://github.com/collective-wisdom-org/collective-wisdom/issues/380)

## Goal

Every Chief of Staff thread is titled exactly `<PREFIX> - Chief of Staff` (`CW - Chief of Staff`, `GUY - Chief of Staff`), so the user can tell one repo's Chief of Staff thread from another's. The title is set on `start the team`, `take over` and `resume`, built by a script from `project.md`, and never composed by the model.

## Today

Facts from `main` at `fe561cc`.

- No Chief of Staff file renames the thread. The title is T3 Code's first-message title, or whatever the model picks under the user's global "rename the thread to its real task" rule.
- `project_config.prefix()` returns the issue prefix from `docs/agents/project.md` and raises `SystemExit` when the row has no usable `[A-Z][A-Z0-9]*` value. The module's CLI takes only `no-ci` and exits 2 with the message on stderr for anything else.
- Every start path reaches one of two places:
  - `start the team` with empty state runs `startup.md` § Setup step 4 (store `chiefThreadId`, `skillCommit`, start the dashboard).
  - `take over`, `resume` (`kill-switch.md` § Resume step 4) and resume mode (`rotation.md` § Thread rotation: Resume mode) all run the lean take-over pass, whose step 3.1 runs `startup.md` § Start-up clean-up and "the dashboard step (startup.md Setup step 4)". Finish take over reruns the same steps.

## Design

### Title builder

`project_config.py` gains:

```python
def chief_thread_title():
    """The Chief of Staff thread title, e.g. `CW - Chief of Staff`. Raises SystemExit like prefix()."""
    return f"{prefix()} - Chief of Staff"
```

and a CLI command, `python3 ~/.collective-wisdom/scripts/project_config.py chief-title`, that prints the title and exits 0. With no usable prefix it exits 2 with `prefix()`'s message on stderr, through the existing `SystemExit` handler. The usage line names both commands.

### Skill step

`startup.md` gets a short section, `## Thread title`:

1. Run `python3 ~/.collective-wisdom/scripts/project_config.py chief-title`.
2. Exit 0: `t3_thread_update` with `action: "rename"`, no `threadId`, and the printed line as the title, verbatim. Never type or edit the title yourself.
3. Exit 2, or the rename fails: add one Cleanup line, `Thread title not set: <the script's line or the tool error>`, and carry on. The pass never stops for the title.
4. On a host without `t3_thread_update` (Cursor), skip the section with no report line.

It says the title wins over any rule that renames a thread to its task (including a user's global T3 thread-title rule): the Chief of Staff thread is never renamed to anything else. Renaming to the same title is a no-op, so the step runs on every start.

Call sites, so all three commands hit it:

- `startup.md` § Setup step 4: run § Thread title right after storing `chiefThreadId`, before the dashboard.
- `rotation.md` take-over step 3.1: "startup.md § Start-up clean-up, then § Thread title, then the dashboard step". Take over, the `resume` command, resume mode and Finish take over all run 3.1, so none needs its own line.

### Test

`test_project_config.py` gets one table-driven test of the CLI (it runs `project_config.py chief-title` with `PROJECT_MD` set): `CW`, `GUY` and `GORP` print `<PREFIX> - Chief of Staff` with exit 0; a missing row, a `TODO(...)` cell and a lower-case `cw` exit 2 with the prefix message on stderr and nothing on stdout.

## Leaves out

- Titles of ship-loop children and helpers, and any non-Chief-of-Staff thread.
- A rename on every tick. A user who renames the thread by hand gets it back at the next start, take over or resume, not sooner.
- A state field for the title: the rename is idempotent, so nothing needs to remember it ran.

## Calls I made

- **The title step runs on every start, take over and resume, even when the title is already right.** T3 can't be asked cheaply for the current title, and renaming to the same name is harmless.
- **A failed title is a Cleanup line, not a Needs you line.** It is cosmetic; the user doesn't have to act on it, and fixing the prefix row is the setup check's job.
- **The step lives in take-over step 3.1, not in each command's own steps.** All four entry paths already share 3.1, so one call site covers them and a future path that runs the lean pass gets it too.
- **Cursor skips the step silently.** Cursor threads have no rename tool, and a line on every start there would be noise.
- **The builder is a `project_config.py` CLI command, not a new script.** It sits next to `prefix()` and reuses its error handling.
- **The test runs the CLI, not just the function,** because the skill calls the CLI and its exit code is what keeps the pass alive.

## Touches

None of data, money, auth, user email or migrations. Files: `agent-team/scripts/project_config.py`, `agent-team/scripts/test_project_config.py`, `agent-team/.claude/skills/chief-of-staff/startup.md`, `agent-team/.claude/skills/chief-of-staff/rotation.md`. Both skill files and `scripts/` are on the approval path, so this spec and its merge wait for the user.
