# WISE-429 one-click Mark todo: plan

**Spec:** [spec](../specs/2026-11-15-wise-429-mark-todo-one-click-design.md)

Test command: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.

## Task 1: page and tests (`agent-team/scripts/dashboard/page/app.js`, `app.test.js`)

1. `approveControls`: `data-return` holds the whole command (`approve N`), not the number.
2. `todoControl`: with a thread link, add `title` (`Opens the Chief of Staff thread with "mark N todo" typed in and presses Send for you. If it can't, press Send.`) and `data-return="mark N todo"`. Copy button unchanged.
3. Export `pressAction(command)`: `Mark todo` for a command starting `mark `, else `Approve`.
4. `pressMessage(answer, repeat, action = 'Approve')`: every line starts `<action> not sent:`; the busy line reads `another one-click send was still running`. `PRESS_MESSAGES` become functions or templates of the action.
5. Click handler and `pressReturn`: pass the command; rename `pressedTicket` to `pressedCommand`; call `pressMessage(answer, repeat, pressAction(command))`. Update the comment to name both controls.
6. Tests: update the Mark todo table (link case has title and `data-return`), the approve-controls table (`data-return="approve N"`), and the `pressMessage` table (each reason for both actions; repeat-busy and sent empty); one small table for `pressAction`.

## Task 2: README

`README.md` § Local dashboard: Mark todo presses Send for you like Approve (same permission), the error line says `Mark todo not sent` and why, and the "never sends a message itself" sentence names both controls.
