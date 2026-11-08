# CW-248 dashboard dark colors: plan

Spec: `docs/superpowers/specs/2026-11-08-cw-248-dashboard-dark-colors-design.md`

## Task 1: change the dark halves

In `agent-team/scripts/dashboard/page/index.html`, `:root` (lines 11 to 13), change only the second value of each `light-dark()` pair, per the spec's Design table:

| Variable | Dark before | Dark after |
|---|---|---|
| `--bg` | `#0d1117` | `#000000` |
| `--card` | `#161b22` | `#111111` |
| `--fg` | `#e6edf3` | `#f5f5f5` |
| `--muted` | `#9198a1` | `#a1a1a1` |
| `--line` | `#30363d` | `#ffffff14` |
| `--b-neutral` | `#30363d` | `#262626` |
| `--b-neutral-fg` | `#c9d1d9` | `#d4d4d4` |
| `--tint-merge` | `#2a1316` | `#2d1918` |
| `--tint-build` | `#261f10` | `#282113` |
| `--err-bg` | `#2d1214` | `#241110` |
| `--b-low` | `#12261e` | `#1d3420` |
| `--b-medium` | `#272115` | `#372e1a` |
| `--b-high` | `#2d1214` | `#3c2422` |

Acceptance: `git diff` shows only those 13 dark values changed; every light value is byte for byte the same; no other line changes.

## Task 2: verify

- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`
- `python3 -I -m pytest -q agent-team/scripts`
- Proof in the PR: a computed diff (only dark halves changed) and contrast ratios. Screenshots could not be attached, so they are listed under Not proven.

No new tests (spec § Tests).
