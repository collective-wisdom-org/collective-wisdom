# CW-401: Color-code every dashboard Gantt bar by category, with a legend

**Status:** Shipped
**Ticket:** [#401](https://github.com/collective-wisdom-org/collective-wisdom/issues/401)
**Shipped:** in PR #410, as specified

## Goal

Every bar on the dashboard's `Agents` chart gets one of seven categories and that category's color, so a glance at a card shows where the time went: planning, building, review, docs, CI, merge or other. Each chart gets a legend for the categories it draws. A running bar keeps its category color and is marked as running another way, so amber stops meaning "running".

## Today

- `renderGantt` in `agent-team/scripts/dashboard/page/app.js` draws working spans as `.bar` (green, `--green`), a span still running as `.bar.running` (amber, `--attn`), and CI waits as `.bar.ci` (blue, `--accent`). The styles are in `page/index.html` around line 154.
- A row reaching the page has a `name`, a `kind` (`session`, `task` or `agent`) and a `model`. It has no subagent type.
- Row names come from the `agent-gantt` mod's `taskName` (`mods/agent-gantt/hooks/timeline.ts`) and from the subagent's task text. Names seen in the root checkout's `.agent-team/gantt/` snapshots today:
  - stage rows: `Spec CW-385: <title>`, `Build CW-310: <title>`, `Merge CW-310: <title>`
  - relay rows: `CW-385 build`, `CW-389 merge PR #389`, `CW-339 changes on PR #352`, `build`
  - Chief of Staff thread rows: `approve 370`, `merge PR #389`, `start 323`, `take over`, `CHIEF OF STAFF NOTICE: ...`, `CHIEF OF STAFF RESET ...`, `add a ticket ...`, free questions such as `how many tokens ...`
  - helpers: `Ticket helper CW-345`, `Backlog ranking`, `Hygiene`
  - subagents: `Implement CW-306 plan`, `Build CW-339 task 1`, `Code review PR 397`, `Security review pass`, `Combined code and security review`, `Small-diff code and security review`, `Re-review fix commit`, `Fix CW-339 review findings`, `Docs check PR 397`, `Compact added agent text`
  - rows the mod could not name from the prompt: `Delegated task node:delegated-task:command%3A...`, `outside a task`, `main`, `task`
- There is no legend.

## Design

### 1. Categories and the classifier (`page/app.js`)

Seven categories, in this fixed order (the legend uses it too):

| Key | Label |
|---|---|
| `planning` | Planning |
| `building` | Building |
| `review` | Review |
| `docs` | Docs and cleanup |
| `ci` | CI wait |
| `merge` | Merge and ship |
| `other` | Other |

A new exported pure function `barCategory(name)` returns a key. It tests a first-match rule table against the row name's **lead**: when the name holds a ticket id followed by `:` (`Spec CW-385: Stamp status-line times`), the lead is the text up to that id (`Spec CW-385`), so words in a ticket title never pick the category. Otherwise the lead is the whole name. Matching is case-insensitive on word boundaries. No match gives `other`. A non-string name gives `other`.

Rules, first match wins:

| Category | Matches (in the lead) | Examples |
|---|---|---|
| `review` | `review`, `re-review`, `security`, `changes`, or a lead starting with `fix` | `Code review PR 397`, `Combined code and security review`, `Fix CW-339 review findings`, `CW-339 changes on PR #352` |
| `docs` | `docs`, `doc`, `documenter`, `compact`, `compacter`, `slop`, `cleanup` | `Docs check PR 397`, `Compact added agent text` |
| `building` | `build`, `build-from-plan`, `implement`, `implementer`, `code` | `Build CW-310`, `CW-385 build`, `build`, `Implement CW-306 plan` |
| `merge` | `merge`, `merge-pr`, `open-pr`, `PR`, `ship`, `autopilot` | `Merge CW-310`, `merge PR #389`, `CW-389 merge PR #389` |
| `planning` | `spec`, `kickoff`, `ticket`, `plan`, `chief of staff`, `approve`, `start`, `take over`, `status`, `backlog`, `ranking`, `hygiene`, `explore`, `research`, `general-purpose` | `Spec CW-385`, `Ticket helper CW-345`, `add a ticket`, `approve 370`, `CHIEF OF STAFF NOTICE: ...`, `Backlog ranking` |
| `other` | anything else | `how many tokens`, `Delegated task node:...`, `outside a task`, `main` |

The order matters: `Code review PR 397` and `Docs check PR 397` name a PR but are review and docs work, `Small-diff code and security review` names code but is review, `Implement CW-306 plan` names a plan but is building. A CI bar is always `ci` and never goes through the table.

Each row's category is computed once in `renderGantt` from its own name. A subagent row takes its own category, not its task's.

### 2. Drawing (`renderGantt`)

- Every working bar gets `class="bar cat-<key>"`, plus `running` while it runs (as today). CI bars become `class="bar cat-ci"`, and `.bar.ci` goes.
- The bar tooltip's second line starts with the category label: `Building · 2:01 pm to 2:14 pm · 13m 02s · opus-5-5`. A CI bar's tooltip already starts with `CI wait` and stays as it is.
- The row tooltip (`rowTitle`) does not change.
- A legend goes first inside `.gantt`, above the rows: `<ul class="legend" aria-label="Bar colors">` with one `<li><span class="swatch cat-<key>"></span>Label</li>` per category that has at least one bar in this chart (task rows, subagent rows and CI bars), in the fixed order above. A chart with one category still shows its one-item legend. The empty-chart messages (`No sessions yet`, `No tasks yet`) have no legend.
- Nothing else changes: the axis, durations, costs, the Total row, `ganttSummary`, `ciOwner`, and the in-place chart patching.

### 3. Styles (`page/index.html`)

- Seven tokens on `:root`, each a `light-dark()` pair: `--cat-planning`, `--cat-building`, `--cat-review`, `--cat-docs`, `--cat-ci`, `--cat-merge`, `--cat-other`. `.cat-<key>` sets `background:var(--cat-<key>)`, used by both `.bar` and `.swatch`.
- Hues: Planning violet, Building aqua (a blue-green, not today's `--green`), Review orange, Docs and cleanup yellow, CI wait the blue of `--accent` (unchanged), Merge and ship magenta, Other neutral gray. Starting steps are the dataviz reference palette's light and dark values for those hues; Other uses a mid gray in each mode.
- The build checks the set with the dataviz validator (`validate_palette.js`) in both modes. The pairs that touch on one track, CI wait next to Building, Review and Merge and ship, must clear the CVD target (ΔE 8) and the normal-vision floor (ΔE 15) in both modes; the build may move a step lighter or darker within its hue to get there. Seven colors cannot clear those floors for every pair at once (the validator confirms this for any six reference hues plus gray), so the legend, the category word in every bar tooltip and the row name carry identity alongside color. The PR lists the validator's worst pairs per mode.
- `.bar.running` no longer sets a background. A running bar pulses: its opacity eases between 1 and 0.55 over about 1.6 s, forever. Under `prefers-reduced-motion: reduce` it does not animate and gets a 2px inset ring in `--fg` instead.
- `.legend`: a wrapping flex row in small muted text, swatches about 10px by 10px with the bars' radius, no list bullets, a small gap below it before the first row.
- `--green` and `--attn` stay; other parts of the page use them.

### 4. Tests (`page/app.test.js`)

- One table-driven test of `barCategory`: at least one name per category from the table above, including the order cases (`Code review PR 397` is review, `Docs check PR 397` is docs, `Implement CW-306 plan` is building, `Spec CW-385: Stamp approval-comment times` is planning even with `approval` and a review-like word in its title), and unmatched names (`how many tokens`, `Delegated task node:delegated-task:command%3Amcp%3A602cbc46-`, a non-string) to `other`.
- One test of `renderGantt`: every bar carries exactly one `cat-<key>` class, the running bar keeps its category class next to `running`, CI bars are `cat-ci`, the legend lists exactly the categories drawn (in the fixed order), and a chart whose rows are all one category shows one legend item.
- Existing tests that assert `class="bar"` or `class="bar ci"` are updated to the new classes.

### 5. Docs

`README.md` § Local dashboard: the waterfall sentence says each bar is colored by its category (Planning, Building, Review, Docs and cleanup, CI wait, Merge and ship, Other) with a legend above the chart, and that a running bar pulses. The CI sentence keeps "blue bars".

## Leaves out

- Click-to-dim on the legend.
- Recording the category in the hook, or passing the subagent type to the page.
- The `agent-gantt` mod's own pane in Claude Code. Only the dashboard changes.
- Renaming the `Delegated task node:...` rows. They land in Other until the mod names them.
- A table view of the chart.

## Calls I made (surprising first)

- **Seven colors can't all be told apart by every colorblind reader.** The validator says no set of six hues plus gray clears the floors for every pair. I made the pairs that sit side by side on a track (CI next to the task's work) pass, and the legend, the bar tooltip's category word and the row name carry the rest.
- **The classifier reads only the start of a stage row's name, before the ticket title.** `Spec CW-385: Stamp approval-comment times` is Planning; title words never pick a category.
- **`approve N`, `start N`, `take over` and the Chief of Staff notices are Planning**, including an `approve N` that leads to a merge. The ticket puts Chief of Staff passes in Planning, and the name can't tell a spec approval from a merge approval.
- **Review fixes and reviewer change requests are Review**: any row starting with `Fix`, and `CW-N changes on PR #N`. `Fix README dashboard paragraph` lands in Review too.
- **`Delegated task node:...` rows are Other.** They are common in older snapshots and carry nothing to match on.
- **Building is aqua, not today's green**, so no bar is left on the old green, as the ticket asks.
- **CI stays the page's `--accent` blue**, wrapped in a new `--cat-ci` token.
- **Running bars pulse; with reduced motion they get a ring instead.** The ticket allowed a pulse or an outline; this does both, by setting.
- **A one-category chart still shows a one-item legend**, so the color always has a label.
- **The legend goes inside the chart html**, so it updates with the chart and needs no new card markup.
- **A subagent row gets its own category, not its task's.** A code review subagent under a Build task is Review.
- **One README sentence changes**, though the ticket names no doc.

## Touches

None of: data, money, auth, user email, migrations.
