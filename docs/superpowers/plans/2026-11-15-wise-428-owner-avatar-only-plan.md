# WISE-428 plan: owner avatar only, pinned right

Spec: `../specs/2026-11-15-wise-428-owner-avatar-only-design.md`

## Task 1: badge and layout

Files: `agent-team/scripts/dashboard/page/app.js`, `agent-team/scripts/dashboard/page/index.html`, `agent-team/scripts/dashboard/page/app.test.js`.

- `ownerBadge`: drop the `.login` span; add `role="img"` and `aria-label="<escaped login>"` to `.owner`.
- CSS: `.head:has(> .id)` grid columns `minmax(0, max-content) auto 1fr`, remove `justify-content:start`; remove `.owner .login`; remove `gap` and `max-width` from `.owner`.
- Test: in the owner test, assert no `class="login"`, and `title` and `aria-label` hold the escaped login.
- Verify: `node --test agent-team/scripts/dashboard/page/app.test.js` and `python3 -I -m pytest -q agent-team/scripts`.
