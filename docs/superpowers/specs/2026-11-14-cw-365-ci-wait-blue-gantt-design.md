# CW-365: Draw CI wait as blue bars on the dashboard gantt

**Status:** Draft
**Ticket:** [#365](https://github.com/collective-wisdom-org/collective-wisdom/issues/365)

## Goal

A ticket's chart shows its PR's CI wait only as a `CI wait` line with a duration (CW-323). Draw that wait as blue bars on the chart's axis, next to the green working bars, so it reads at a glance when the PR waited on CI.

## Today

- `ciWait` in `agent-team/scripts/dashboard/ci.ts` turns the PR's check runs into spans `[start, end | null]`. They reach the page as `entry.ci`.
- `ciRow` in `agent-team/scripts/dashboard/page/app.js` draws a text row below `Total`: the name `CI wait`, the merged duration, an empty cost cell, a tooltip with the commit count and the clock range. It has no `.track`, and `.grow.gciwait` in `page/index.html` uses the `Total` row's grid areas (no track).
- `renderGantt` positions bars on an axis of active time: the union of every working span, so a gap takes no width (CW-216). CI wait happens while no agent works, so it falls in a gap and has no place on the axis.
- Working bars are `.bar` on a `.track`: green, amber (`.bar.running`) while open. The blue token is `--accent` (light `#2563eb`, dark `#60a5fa`).

## Design

### 1. The axis (`renderGantt`)

The axis becomes the union of the working spans and the CI spans (open CI ends run to `now`, as today). Every bar, working or CI, is placed with the same `pos(t)` on that axis. A gap with no work and no CI still takes no width.

What stays: `total` (the `Total` row's duration), `ganttSummary`'s `ms`, each row's duration and every cost are still computed from the working spans only. With no CI spans the axis is the working union, so the chart is the same as today.

### 2. The `CI wait` row

- It stays below `Total`, with the same name, duration, empty cost cell, `running` class and row tooltip as today.
- It gains a `<span class="track">` holding one `.bar` per merged CI span (overlapping spans from a push that cancelled a run draw as one bar), positioned like the working bars: `left` and `width` in percent of the axis, at least 0.5% wide.
- Each bar's tooltip: `CI wait`, then `<start> to <end> · <duration>`, or `<start>, running · <duration so far>` while open. Times use the dashboard's `clock` (12-hour am/pm).
- The bars carry no `running` class, so an open span is blue, not amber. The row's duration keeps its amber `running` colour as today.

### 3. Styles (`page/index.html`)

- `.grow.gciwait` drops out of the `Total` row's grid rules, so it lays out like a working row: name, duration and cost on top with the track below in a narrow chart, and `name track dur cost` in a wide one.
- `.grow.gciwait .bar { background:var(--accent); }`. `--accent` already switches for light and dark mode.

### 4. Tests (`page/app.test.js`)

One table-driven test of bar positions, extending the CW-323 test:

- a working span, then a gap with a CI span in it, then a working span: the CI bar sits between the two working bars and every bar's `left` and `width` match the combined axis;
- a CI span still running at `now`: its bar ends at the right edge of the track and has no `running` class;
- no CI spans: the chart html equals today's (`renderGantt(sessions, now)`);
- `Total` duration and cost are the same with and without CI spans.

### 5. Docs

`README.md` § Local dashboard: the chart sentence says CI wait takes width on the axis and draws as blue bars on the `CI wait` line, still left out of the total.

## Leaves out

- The agent-gantt mod pane and the Cursor hook. They have no CI data.
- Review wait and merge-approval wait.
- Any change to how CI spans are read (`ci.ts`, `api.ts`).
- CI bars on the Chief of Staff and project manager charts (they get no `ci`).

## Calls I made (surprising first)

- **Working bars get narrower once CI shows.** CI wait now takes width, so a chart with a long CI wait squeezes the working bars to make room, and they shift right after each wait. The ticket asks for this ("Make CI wait spans take width"); the `Total` duration does not change.
- **An open CI span keeps the axis growing to `now`.** While a check runs, the chart's right edge is now, so every working bar shrinks a little each refresh. It stops once CI finishes.
- **The `CI wait` row stays below `Total`, not among the working rows.** `Total` sums the rows above it, and CI wait is not in it.
- **Overlapping CI spans draw as one bar**, with that merged span's tooltip. They are the same colour, so separate overlapping bars would look the same and only the tooltips would differ.
- **The row's duration stays amber while CI runs.** Only the bar is blue; the duration's running colour matches the other running rows' text.
- **A running bar's tooltip shows the duration so far**, unlike a running working bar, which shows only `<start>, running`. The ticket asks for start, end and duration.
- **One README sentence changes**, though the ticket names no doc.

## Touches

None of: data, money, auth, user email, migrations.
