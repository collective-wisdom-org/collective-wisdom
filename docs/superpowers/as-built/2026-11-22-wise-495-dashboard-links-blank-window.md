# As-built: WISE-495 dashboard thread links

**Shipped:** in PR #498
**Ticket:** WISE-495
**Spec:** [2026-11-22-wise-495-dashboard-links-blank-window-design.md](../specs/2026-11-22-wise-495-dashboard-links-blank-window-design.md)

## Differs from the spec

- The spec says the press checks that "the focused composer is the Chief of Staff thread's" by a rule to be found in the live step. It shipped as an exact match on the composer's description, `Message <PREFIX> - Chief of Staff`, with the prefix passed to the script in `DASHBOARD_PRESS_PREFIX`. With no valid prefix, or before the dashboard has served its first page, the press sends nothing and answers `not-open`.
- Spec step 4 (controls fall back to copy buttons) did not ship: the live check showed T3 opens the thread once the id is encoded, so the links stay.
- The live check also showed the raw Chief of Staff id already worked; only ids containing `%3A` (child threads) blanked the window.
- The press-return test for a message that is never recorded now expects 2.5 s instead of 3.5 s, because the 1.2 s sleep before the press is gone (the 5 s wait moved into the script).
