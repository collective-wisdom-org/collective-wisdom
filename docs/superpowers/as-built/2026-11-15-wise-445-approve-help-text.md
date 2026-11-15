# As-built: Say on the dashboard Approve and Changes links when the Approve press works

**Shipped:** in PR #448
**Ticket:** WISE-445
**Spec:** [2026-11-15-wise-445-approve-help-text-design.md](../specs/2026-11-15-wise-445-approve-help-text-design.md)

## Differs from the spec

- The spec puts the README sentence right after the Accessibility and Automation sentence. It shipped after the "Until then ... you press Send." sentence, because between them "Until then" lost its meaning.
- The Changes sentence is a second constant, `CHANGES_TIP`, beside `PRESS_TIP`, not an inline string.
- WISE-429 (Mark todo presses Send) merged first, so `PRESS_MESSAGES` lines take an action name. The new `not-frontmost` and generic lines are shared with Mark todo: they read "try Mark todo again" and "press Send ... yourself". Mark todo's hover title is unchanged.
