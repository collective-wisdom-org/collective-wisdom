# CW-382 plan: CI wait bars on the task rows

Spec: `docs/superpowers/specs/2026-11-15-cw-382-ci-wait-bars-on-tasks-design.md`

1. `agent-team/scripts/dashboard/page/app.js`: add and export `ciOwner(items, spans)` returning, per CI span, the index of the owning top-level task (latest own finished working-span end `<=` span start, ties to the earlier task, else the earliest task). Remove `ciRow`. In `renderGantt`, group the CI spans by owner, and have `line()` for a depth-0 task append that task's merged CI spans as `<span class="bar ci">` after its working bars (same `place`, tooltip `CI wait\n<start> to <end> · <duration>` or `<start>, running · <duration>`, never `running`). Axis, total, durations and costs stay as they are.
2. `page/index.html`: remove the `.grow.gciwait` rules; add `.bar.ci { background:var(--accent); }`.
3. `page/app.test.js`: replace the CW-365 CI test with a table test of `ciOwner` (gap after a task, starts while a later task runs, still running, before any task finished) and a `renderGantt` test (bar on the owner's track with expected left/width, class `bar ci` not `running`, no `CI wait` row, Total and row durations/costs unchanged, no CI equals today).
4. `README.md` § Local dashboard: chart sentence says CI wait draws as blue bars on the track of the task that waited.
5. Run `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` and `python3 -I -m pytest -q agent-team/scripts`.
