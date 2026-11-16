# WISE-466: Rename the Mark todo dashboard button to Start shipping

**Status:** Shipped
**Ticket:** [#466](https://github.com/collective-wisdom-org/collective-wisdom/issues/466)
**Shipped:** in PR #471, as specified

## Goal

The blue button on Backlog cards in the local dashboard reads `Start shipping` instead of `Mark todo`. It still sends `mark N todo` to the Chief of Staff thread; only the words people see change.

## Today

- `agent-team/scripts/dashboard/page/app.js`: `todoControl(r, chiefLink)` draws `<a class="todo" ...>Mark todo</a>`, or `<button type="button" class="todo" data-copy="mark N todo">Mark todo</button>` when there is no usable thread link.
- `pressAction(command)` returns `Mark todo` for a command starting `mark `, so a failed press reads `Mark todo not sent: ...` (and `Mark todo may not have sent: ...` for `unchecked`).
- Comments in `app.js` (on `pressAction`, `pressMessage`, `todoControl`, `ticket()`, `renderBacklog` and the error-line handler) name the control `Mark todo`.
- `README.md` § Local dashboard names it in three places: the `Approve not sent` (or `Mark todo not sent`) line, the "The page never sends a message itself" line and the `(Mark todo the same)` aside, and the Backlog card bullet.
- `agent-team/scripts/dashboard/page/app.test.js` expects `Mark todo` in the Backlog control table, the press message table and the `pressAction` table, and names it in two test titles.

## Change

1. `app.js`: both forms of `todoControl` show `Start shipping`. `pressAction` returns `Start shipping` for a `mark ` command, so every press line for this control starts `Start shipping not sent:` or `Start shipping may not have sent:`. Comments that name the control say `Start shipping`.
2. `README.md` § Local dashboard: each `Mark todo` that names the button or its error line becomes `Start shipping`. The Backlog bullet reads "Cards on the Backlog tab only get a blue `Start shipping` button ...", and still says it sends `mark 419 todo`.
3. `app.test.js`: the expected HTML, the `pressAction` row and the press message loop use `Start shipping`; the two test titles say `Start shipping`.

No test is added: the existing tables already fail if the label or the error line is wrong.

## Not changing

- The `mark N todo` command, which the Chief of Staff parses, and `todoCommand`.
- The `todo` CSS class, the `markTodo` option of `ticket()` and the `todoControl` name (internal names nobody sees).
- The link's `title` tooltip, which describes the command typed in, not the button.
- `server.test.ts`: its test title "takes only an exact approve or mark todo command" and the `mark todo` row name the command, not the button.
- Past specs, plans and as-built docs under `docs/superpowers/`.

## Acceptance

- A Backlog card shows `Start shipping`, with or without a Chief of Staff thread link.
- After a failed press, the error line starts with `Start shipping`.
- `grep -r "Mark todo" README.md agent-team/scripts/dashboard/` finds nothing.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and the pytest suite pass.

## Files

| File | Change |
|---|---|
| `agent-team/scripts/dashboard/page/app.js` | Button text in both forms, `pressAction` name, comments |
| `agent-team/scripts/dashboard/page/app.test.js` | Expected label and line, two test titles |
| `README.md` | § Local dashboard, three places |

## Calls I made

- **Internal names stay** (`markTodo` option, `todoControl`, `todoCommand`, the `todo` class). The ticket keeps the class and `todoCommand`; renaming the rest would touch code with no visible effect.
- **No comment keeps the old name.** The ticket allows comments that explain the old name; none is needed, so the grep finds nothing at all.
- **`server.test.ts` is left alone.** The ticket lists it, but its only matches are lowercase `mark todo` naming the command, which stays.
- **The tooltip is unchanged.** It says the thread opens with `mark N todo` typed in, which is still true.
- **No release note beyond the PR's own** `## Release note` section, and the README is the only living doc touched.
