# CW-97: Open an agent from its row in the Gantt pane

**Ticket:** [CW-97](https://github.com/collective-wisdom-org/collective-wisdom/issues/97)
**Status:** Draft
**Related:** #96 (the pane, PR #149)

## Goal

Click a row in the agent pane and the main view shows that agent's transcript. A button in the pane header brings you back to the main conversation. This works for nested subagents too, and for agents that have already ended, with a plain message when the transcript can't be shown.

## Today

Facts from `main` at `58db4e8`, checked 2026-11-05.

- `mods/agent-gantt/hooks/register.tsx` draws the pane in a `ui.render` hook on `{ component: 'Pane', requestId: 'agent-gantt' }`. Each row is a `Box` holding two `Text`s: the info columns and the bar. Nothing on it can be pressed.
- The pane keeps one record per agent in `$.state` and never drops one, so a row stays after its agent ends. The `main` row is the main loop (id `main`, not a real agent id).
- `mods/agent-gantt/.claude-plugin/plugin.json` is at version `0.1.0`.
- What the Claude Code mod API offers, from the types for this build (2.1.314):
  - `$.ui.view({ agentId })` puts an agent's transcript in the main view, "as the person's own switch from the tasks list does". `$.ui.view({})` goes back to the main conversation. It works only while answering the person's own input, such as a press.
  - It returns `{}` when the view moved, or `{ deny }` with a reason: not the person's input, no agent holds the id or the tasks list shows none for it, a teammate was stopped or runs in its own pane, the view moved meanwhile, or the session draws none.
  - `Button` takes `key`, `plain`, `dimColor` and `onPress`, and its children may be strings and `Text`. `plain` draws the label alone, without `[ ]`. A click, or Enter while it has the focus, presses it.
  - A pane's `ui.render` hook gets `e.props.view`, the transcript in view (`agentId` absent for the main conversation). A switch re-runs the hook with the new view.
  - `$.ui.toast(text)` shows a short message.

## Design

All changes are in `mods/agent-gantt/hooks/register.tsx`, plus a version bump and a README line.

### Rows open their agent

- The info part of each row (name, repo, start, end, tokens, cost, child count) becomes a `plain` `Button` with `key={row.id}`. The bar stays a plain `Text` beside or under it, as now. A row looks the same as before; it inverts under the pointer or focus as every Button does.
- Pressing a subagent row calls `$.ui.view({ agentId: row.id })`. Nested subagents work the same way: their record id is the id `$.agent.list()` gives them.
- Pressing the `main` row calls `$.ui.view({})`, the same as the back button.

### Back to main

- While an agent is in view (`e.props.view.agentId` set), the pane's first line is a `plain` `Button` labelled `← main`, and pressing it calls `$.ui.view({})`. While the main conversation is in view the line is not drawn, so the pane looks as it does today.
- The row of the agent in view is drawn in bold, so you can tell which transcript is open.

### When a transcript can't be shown

- If `$.ui.view` returns `{ deny }`, the mod shows a toast: `Can't open <row name>: <deny>`. The reason is the engine's own text.
- An agent that has ended is not treated specially: the press asks for its transcript like any other. If the engine still lists it, the transcript opens; if not, the toast says why. The mod doesn't guess ahead of time.

### Version

`plugin.json` goes to `0.2.0`, per the CW-96 rule that a PR changing the mod bumps it.

### Tests

No new automated test. The change is pane wiring: a press calls one engine function, and the result is a view switch or a toast. `AGENTS.md` § Testing says not to test small UI interactions, and the row builder (`rows.ts`) does not change. The PR still runs `node --test mods/agent-gantt/hooks/rows.test.ts`.

### Proof

The PR's Proof section, checked by hand in a real session:

- Press a running subagent's row: its transcript opens and its row turns bold; the `← main` button appears.
- Press a nested subagent's row: its transcript opens.
- Press `← main`: the main conversation is back and the button is gone.
- Press the row of an agent that has ended: its transcript opens, or a toast says why it can't.

## Out of scope

- Opening other T3 Code threads. A mod only reaches agents inside its own session.
- Hotkeys for rows or the back button.
- Changing how rows are built or ordered.

## Calls I made

- ⚠️ **The back button shows only while an agent is in view.** The ticket says the header has a back button; drawing it only when there is somewhere to go back from keeps the pane unchanged in the common case. The main row also goes back, so there is always a way.
- ⚠️ **No new automated test.** The change is UI wiring with no logic worth a table test; proof is by hand.
- The "can't open" message is a toast with the engine's reason, not a line kept in the pane. It answers one press and goes away.
- The `main` row is pressable and goes back to the main conversation.
- The row in view is drawn bold.
- Only the info columns are the Button; the bar stays plain text, since a Button may hold only strings and `Text` and the bar sits on its own line in a narrow pane.
- The mod version goes to `0.2.0`.
- The README's Agent pane section gets one sentence about clicking a row.
