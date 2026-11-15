# CW-346 plan: make the dashboard section headers stand out

Spec: [design](../specs/2026-11-14-cw-346-section-headers-design.md). Test command: `python3 -I -m pytest -q agent-team/scripts`.

1. In `agent-team/scripts/dashboard/page/index.html` add `--t-section:1.125rem` and rewrite the single `h2` rule: sentence case, `--fg`, weight 650, a hairline `--line` rule under the name. Markup, `app.js` and `app.test.js` do not change.
2. Run `python3 -I -m pytest -q agent-team/scripts` and the dashboard and mod `node --test` command from `AGENTS.md`; no new test, this is styling.
3. Proof: screenshots of the Ship loop tab (light and dark, desktop and phone width) and the Chief of Staff tab go in the PR.
