# CW-360 plan: bolder section dividers

Spec: `docs/superpowers/specs/2026-11-14-cw-360-section-dividers-design.md`

## Task 1: CSS in `agent-team/scripts/dashboard/page/index.html`

1. In `:root`, add `--section-line:light-dark(#d1d5db, #ffffff40);` next to `--line`. Leave `--line` unchanged.
2. In the `h2` rule, change `border-bottom:1px solid var(--line)` to `border-bottom:2px solid var(--section-line)`.
3. Nothing else changes.

Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, and `git diff` shows only those two edits.
