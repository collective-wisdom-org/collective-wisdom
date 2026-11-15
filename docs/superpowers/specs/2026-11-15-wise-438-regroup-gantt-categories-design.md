# WISE-438: Regroup Gantt bar categories

**Status:** Draft
**Ticket:** [#438](https://github.com/collective-wisdom-org/collective-wisdom/issues/438)

## Goal

The dashboard's `Agents` chart drops its "Docs and cleanup" category. Its work goes to the stage it belongs to: a docs check is review, a docs cleanup is building. A spec revision after `changes N` counts as planning, not review. Review bars take the lighter orange that docs bars used.

## Today

- `CATEGORIES` and `CATEGORY_RULES` in `agent-team/scripts/dashboard/page/app.js` (lines 599 to 628). `barCategory(name)` tests the rules, first match wins, against the row name's lead (the text up to a ticket id's colon, else the whole name).
- Rule order: `review` (`review`, `security`, `changes`, a lead starting with `fix`), `docs` (`docs`, `doc`, `documenter`, `compact`, `compacter`, `slop`, `cleanup`), `building`, `merge`, `planning`.
- Row names come from `taskName` in `mods/agent-gantt/hooks/timeline.ts`. A Chief of Staff relay row is named `<ticket> <work>`: the user's `changes N` relay (`the user asked for changes: ...`) gives `WISE-N changes`, and a GitHub reviewer's request gives `WISE-N changes on PR #N`. A continuation child for a spec revision is named `Spec WISE-N: <title>`, which is already `planning`.
- So `WISE-N changes` and a name like `Spec WISE-N changes` (no colon, so the whole name is the lead) land in `review` because `changes` matches first. `Docs check PR 397` and `Compact added agent text` land in `docs`.
- Colors: `--cat-*` tokens at `page/index.html` line 19 and `.cat-*` rules at line 171. `--cat-review` is `light-dark(#eb6834, #d95926)`, `--cat-docs` is `light-dark(#eda100, #c98500)`.
- The README's dashboard paragraph lists the categories: `(Planning, Building, Review, Docs and cleanup, CI wait, Merge and ship, Other)`.

## Design

### 1. Categories (`page/app.js`)

`CATEGORIES` loses `['docs', 'Docs and cleanup']`. Six remain, in this order: Planning, Building, Review, CI wait, Merge and ship, Other.

### 2. Rules, first match wins

| Category | Matches (in the lead) | Examples |
|---|---|---|
| `planning` | a lead starting with `spec`, or a bare `changes` relay: `changes` alone, after an optional ticket id | `Spec WISE-438 changes`, `WISE-438 changes`, `changes` |
| `review` | `review`, `security`, `changes`, `documenter`, `docs check` or `doc check`, or a lead starting with `fix` | `Code review PR 397`, `Docs check PR 397`, `WISE-339 changes on PR #352`, `Fix WISE-339 review findings` |
| `building` | `build`, `implement`, `implementer`, `code`, plus the old docs words: `docs`, `doc`, `compact`, `compacter`, `slop`, `cleanup` | `Build WISE-310`, `Compact added agent text`, `Collect slop`, `Docs cleanup` |
| `merge` | as today | `Merge WISE-310`, `merge PR #389` |
| `planning` | as today | `Ticket helper WISE-345`, `approve 370`, `Backlog ranking` |
| `other` | anything else | `how many tokens`, `main` |

Order matters. The new planning rule comes first so `changes` in a spec revision does not reach review. `docs check` sits in review so `building` never sees it, and the docs words sit in building, after review.

### 3. Colors (`page/index.html`)

- `--cat-review` becomes `light-dark(#eda100, #c98500)`.
- `--cat-docs` and `.cat-docs` go. `#eb6834` and `#d95926` appear nowhere in the page.

### 4. Tests and README

- `app.test.js`: the `barCategory` table loses its `docs` key. `Docs check PR 397` moves to `review`, `Compact added agent text` to `building`, and `WISE-438 changes` and `Spec WISE-438 changes` go under `planning`. `WISE-339 changes on PR #352` stays under `review`.
- The README's category list drops `Docs and cleanup`.

## Leaves out

- Renaming rows, and any change to `mods/agent-gantt` (its `taskName` stays as it is).
- The WISE-401 spec and plan: they record what shipped then, so they keep naming the docs category.
- Bars drawn before this change: the page reclassifies every row on each render, so old charts pick up the new categories at once. Nothing is stored per category.

## Calls I made

- A bare `<ticket> changes` row counts as planning. That row comes from the user's `changes N` relay sent into an existing child thread. Today a `changes N` on an idle child starts a new `Spec` or `Build` child, so the bare row mostly appears in spec-lane threads; a rare `changes N` after `MERGE READY` sent to a running build child would also show as planning. Telling them apart needs the row's lane, which the page does not get, and the ticket rules out mod changes.
- A lead starting with `spec` counts as planning before any other rule, so `Spec WISE-N changes` and any future `Spec ... review` name read as planning.
- `docs check` and `doc check` (with or without a space after `docs`) and `documenter` go to review. Every other docs word (`docs`, `doc`, `compact`, `compacter`, `slop`, `cleanup`) goes to building, so a bare `Docs` row is building.
- One table-driven `barCategory` test is updated in place; no new test file.

## Acceptance

- `barCategory` returns `planning` for `WISE-438 changes` and `Spec WISE-438 changes`, `review` for `Docs check PR 397` and `WISE-339 changes on PR #352`, and `building` for `Compact added agent text`.
- The legend has no "Docs and cleanup" entry, and no `docs` category exists in `app.js`, `index.html` or `app.test.js`.
- Review bars and their legend swatch use `#eda100` (light) and `#c98500` (dark); `#eb6834` and `#d95926` appear nowhere under `agent-team/scripts/dashboard/page/`.
- `node --test agent-team/scripts/dashboard/*.test.ts agent-team/scripts/dashboard/page/app.test.js mods/agent-gantt/hooks/*.test.ts` passes.
