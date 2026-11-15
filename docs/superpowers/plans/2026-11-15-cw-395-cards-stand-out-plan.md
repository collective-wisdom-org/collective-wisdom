# CW-395 plan: dashboard cards stand out

Spec: `docs/superpowers/specs/2026-11-15-cw-395-cards-stand-out-design.md`

## Task 1: `agent-team/scripts/dashboard/page/index.html`

1. Add `--edge:light-dark(#00000014, #ffffff1a);` to `:root`.
2. Append `0 0 0 1px var(--edge)` to the `box-shadow` of `.ticket`, `.ticket.attn`, `.ticket.blocked` and `.cos-card`. Order: inset left edge (attn, blocked only), ring, then `0 1px 2px var(--shadow)`.
3. Touch nothing else (tabs, `.seg`, `.track` keep their rules).

No new test (styling only, `AGENTS.md` § Testing). Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`.
