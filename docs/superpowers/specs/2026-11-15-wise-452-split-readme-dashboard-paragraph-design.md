# WISE-452: Split the README dashboard paragraph

**Status:** Draft
**Ticket:** [#452](https://github.com/collective-wisdom-org/collective-wisdom/issues/452)

## Goal

The README's `## Local dashboard` section stops being three very long lines. Git merges line by line, so today any two PRs that edit any dashboard sentence conflict. After this change two PRs conflict only when they edit the same sentence or one next to it. The words stay exactly the same.

## Today

- `README.md` line 187 is one paragraph of 11,588 characters and 57 sentences covering the whole dashboard.
- Line 189 (1,676 characters) describes the four tabs. Line 191 (986 characters) describes the backups.
- Every dashboard PR edits line 187. Open PRs #448 (WISE-445) and #450 (WISE-434) both edit `README.md`.
- No script or test parses these lines (the ticket checked `agent-team/scripts` and `agent-team/scripts/dashboard`).

## Design

### 1. Line 187 becomes an intro line and a feature list

The first sentence (`` `start the team` also starts a local dashboard ... ``) stays a paragraph on its own line. The other 56 sentences become a bullet list, one bullet per dashboard feature, in today's order:

| Bullet | Sentences today (from 2) |
|---|---|
| Header | "The header is one sentence ..." through "It shows no Chief of Staff status." |
| Bands, stages and the `Agents` chart | "Below it are the tickets in three bands ..." |
| CI wait bars | "Once the ticket's PR has run CI ..." |
| Card edges | "Your turn cards, merge and build alike ..." |
| Card top row | "Every card has the same three rows." through the avatar's image host |
| Card middle row (Approve and Changes) | "The middle row appears only ..." through the Accessibility warning |
| Mark todo | "Cards on the Backlog tab only get a blue `Mark todo` ..." and the stale-list sentence |
| Card bottom row | "The bottom row is ..." and the no-status-line sentence |
| Collapsing | "Each stage section collapses ..." |
| Ticket helpers | "A running ticket helper ..." through "A helper that files nothing ..." |
| Up next and the spec queue | "Up next lists its tickets as cards." and the Waiting to spec sentence |
| Backlog tab | "The Backlog tab lists up to 200 tickets ..." through "With a placeholder or no value there is no link." |
| `Agents` and `Details` control | "`Agents` and `Details` are one two-button control ..." and "With no login read, nothing is hidden." |
| `Details` panel | "The `Details` section starts with ..." through the `Spec` link sentence |
| Done tab | "On the Done tab ..." through the `gantt-history.json` sentence |
| Server and page | "The page keeps updating on its own ..." through the light or dark setting |
| Copy buttons | "Each thread has a copy button ..." through "Paste the link into T3." |

Inside a bullet each sentence starts its own line, indented two spaces so it reads as part of the bullet. Markdown joins those lines, so each bullet renders as one paragraph.

A sentence longer than about 400 characters is broken at a comma, semicolon, colon or parenthesis, still with no word changed. That applies to the bands sentence (about 1,000 characters), the CI wait sentence, the top row sentence, the Mark todo sentence, the Waiting to spec sentence, the Agents and Details sentence and a few others near the limit.

### 2. Line 189 becomes a list of tabs

Same treatment: one bullet each for the tab bar and its count pills, the Ship loop tab, the Chief of Staff tab, the Project manager list, and how the tabs refresh and which sessions show where. One sentence per line.

### 3. Line 191 keeps one paragraph

The backups text is a short procedure, so it stays one paragraph with one sentence per line. It renders exactly as today.

### 4. Pure restructure

`git diff --word-diff origin/main -- README.md` shows only added `-` bullet markers. No other word changes. Anything that looks wrong in the text (for example `; Below that comes` with a capital B) stays as it is.

The build splits the text as it is on `main` when the build starts. If a dashboard PR merges first, the split includes its words.

## Leaves out

- Rewording, trimming or fixing anything in the dashboard text.
- Splitting the other long README lines (82, 133, 165 and the 700 to 850 character ones).
- Moving the dashboard docs out of the README.
- A test or lint rule for line length. It would be the first check on README prose, and `AGENTS.md` § Testing says not to test prose.

## Calls I made

- **Merge timing is up to you.** PRs #448 (WISE-445) and #450 (WISE-434) are open and both edit `README.md`. Whichever merges second conflicts, once. The ticket says to merge this when no dashboard PR is open; I'll report `MERGE READY` as usual and leave the timing to you.
- Bullets with one sentence per line, not one sentence per line with no bullets. The ticket asks for a readable list, and per-sentence lines keep conflicts as small as the bullets alone can't.
- Very long sentences are broken mid-sentence at punctuation to meet the 400-character limit. That's invisible when rendered.
- The tabs paragraph (line 189) becomes a list too; the backups paragraph (line 191) stays one rendered paragraph, one sentence per line, because it reads as steps.
- No new test, and no plan file: the change touches only markdown.
- The "two throwaway edits merge cleanly" check runs locally in scratch branches and is shown in the PR's Proof, not committed.

## Acceptance

- No line in the `## Local dashboard` section is longer than about 400 characters.
- `git diff --word-diff origin/main -- README.md` shows only list markers added, no changed words.
- The section renders on GitHub as an intro line, a feature list, a tab list and the backups paragraph.
- Two throwaway edits to different dashboard bullets, made on two branches from the build's head, merge without a conflict.
