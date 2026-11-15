# CW-401 plan: color-code Gantt bars by category

Spec: `docs/superpowers/specs/2026-11-15-cw-401-gantt-bar-colors-design.md` (approved).

1. `page/app.js`: add exported `barCategory(name)` (lead extraction, first-match table, `other` fallback) and a `CATEGORIES` list in the fixed order. In `renderGantt`: bars get `cat-<key>`, tooltip line 2 starts with the category label, CI bars are `bar cat-ci`, add the legend `<ul class="legend">` first inside `.gantt` for the categories drawn.
2. `page/index.html`: seven `--cat-*` `light-dark()` tokens (validated with the dataviz validator, both modes, touching pairs), `.cat-*` backgrounds for `.bar` and `.swatch`, pulse for `.bar.running` (reduced motion: inset ring), `.legend` styles; drop `.bar.running` amber and `.bar.ci`.
3. `page/app.test.js`: table-driven `barCategory` test; one `renderGantt` test (one `cat-` class per bar, running keeps category, CI is `cat-ci`, legend lists exactly the drawn categories); update tests asserting `class="bar ci"` / `bar running` / bar tooltip text.
4. `README.md` § Local dashboard: one sentence on category colors, legend, pulse.
5. Verify: `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts`, `python3 -I -m pytest -q agent-team/scripts`.
