# WISE-419: Mark todo button, plan

Spec: [2026-11-15-wise-419-mark-todo-button-design.md](../specs/2026-11-15-wise-419-mark-todo-button-design.md)

## Task 1: button, style, test

Files: `agent-team/scripts/dashboard/page/app.js`, `index.html`, `app.test.js`.

1. `app.js`: add exported `todoCommand(r)` and `todoControl(r, chiefLink)`; add a `markTodo` option to `ticket()` that puts the control between the switch and the meta line; `renderBacklog` takes `chiefLink = ''` and passes `markTodo: true, chiefLink`; `drawStatus()` passes `last.chief?.threadLink`.
2. `index.html`: `a.todo, button.todo` sized like `a.approve`, filled with `--accent` and `--on-accent`.
3. `app.test.js`: one table-driven test as the spec lists.

Verify: `node --test agent-team/scripts/dashboard/page/app.test.js` and `python3 -I -m pytest -q agent-team/scripts`.
