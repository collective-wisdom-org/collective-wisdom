# As-built: Have the Chief of Staff create user.md when this machine has none

**Shipped:** in PR #292
**Ticket:** CW-281
**Spec:** [2026-11-13-cw-281-create-user-md-design.md](../specs/2026-11-13-cw-281-create-user-md-design.md)

## Differs from the spec

- The spec says the check skips only the second pass through the start-up clean-up in `resume`. It also skips the `wake` command, because `wake` runs only clean-up step 1 (the SKILL.md `wake` row refers to that step by number, so the steps were not renumbered). startup.md § User settings check says so.
- On `yes` the Chief of Staff runs `setup_repo.py status` again and writes only while `user_md` is still `no-file` or `no-row`.
- A subscription figure is accepted only as `none` or a plain number (a leading `$` and commas are stripped) and is otherwise asked again.
- If the dry run exits 2, the script's line goes under Needs you in place of the question.
- For `no-row` only the one new row is shown, not the rest of the file, so other repos' logins stay out of the thread.
- Another login must be one of `gh_logins`.
