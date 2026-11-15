# As-built: Read a Cursor Chief of Staff's context size in the rotation check

**Shipped:** in PR #361
**Ticket:** CW-341
**Spec:** [2026-11-14-cw-341-cursor-context-size-design.md](../specs/2026-11-14-cw-341-cursor-context-size-design.md)

## Differs from the spec

- Design 2 says an unreadable Cursor run store makes the `--hook` answer `rotation-check: cannot read context`, as on Claude Code. It shipped silent: while the provider's reset mode is `none` (Cursor today), the Cursor hook returns without an answer on an unreadable store, so it does not wake the Chief of Staff for a turn that can do nothing. Plain mode still exits 2 with `rotation-check: cannot read context`, and a provider with a reset mode still gets the followup. The hook test row for this is `test_hook_on_cursor_answers_with_a_followup_only_for_the_chief_once`.
