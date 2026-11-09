# As-built: Record a Chief of Staff run and a ship-loop child on Cursor in T3 Code

**Shipped:** in PR #277
**Ticket:** CW-256
**Spec:** [2026-11-08-cw-256-cursor-run-record-design.md](../specs/2026-11-08-cw-256-cursor-run-record-design.md)

## Differs from the spec

- The spec expected G1 (Cursor reads the rule file) to be likely settled by the run. It is not: the trial machine had no `~/.cursor/rules/collective-wisdom.mdc` and no `~/.cursor/hooks.json`, so the run used the skills only. G1 stays open and points at #275.
- The spec did not expect the run to use old skills. The machine install was at commit `070a3ca`, before CW-272 and CW-258, so the Cursor Chief of Staff (Grok 4.7) started every child on Claude Code. The Ship loop cell is `partial` (a Cursor Chief of Staff drove Claude Code children to merge) and G3 now asks for a Cursor child run (#275).
- The Local dashboard cell is `partial`, not `works`: the dashboard API showed the Cursor thread's state and link, but the page was not opened and the link was not clicked, and the Cursor thread left no gantt snapshot (G9).
- Two tickets were filed (#275, and #276 for G20, a new gap found during the run), and #273 got a comment that this run cannot answer its checks.
