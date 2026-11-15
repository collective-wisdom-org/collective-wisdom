# CW-365 plan: CI wait as blue bars

Spec: `docs/superpowers/specs/2026-11-14-cw-365-ci-wait-blue-gantt-design.md`

1. `page/app.js`: add `ciSpansOf(ci, now)` (the normalising filter/map now inline in `ciRow`, open ends run to `now`). In `renderGantt`, build `axis = union([...active, ...ciSpans])`; `pos` and `scale` use `axis`; `total` and `length` keep using working spans. `ciRow(ci, now, place)` gains a `<span class="track">` of one `.bar` per merged CI span (no `running` class), tooltip `CI wait\n<start> to <end> · <duration>` or `<start>, running · <duration>`.
2. `page/index.html`: drop `.grow.gciwait` from the two `gtotal` grid-area rules; add `.grow.gciwait .bar { background:var(--accent); }`.
3. `page/app.test.js`: extend the CW-323 test with table cases: CI span in a gap between two working spans (left/width on the combined axis), open CI span (ends at 100%, no `running` on the bar), no CI equals `renderGantt(sessions, now)`, `Total` unchanged.
4. `README.md`: the chart sentence says CI wait draws as blue bars on the axis and stays out of the total.
5. Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
