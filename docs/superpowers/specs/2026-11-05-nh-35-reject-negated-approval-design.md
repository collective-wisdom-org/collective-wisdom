# NH-35: Make cos_user_check.py reject a negated approval

**Ticket:** [NH-35 (noahstotland/nohands#35)](https://github.com/noahstotland/nohands/issues/35)
**Status:** Shipped
**Shipped:** in PR #124, as specified
**Full spec:** the app's copy, `docs/superpowers/specs/2026-11-05-nh-35-reject-negated-approval-design.md` in noahstotland/nohands

## Goal

"do not approve 30 yet" must not count as the user's `approve 30`. `cos_user_check.py` (`latest` and `item`) fails closed when the command's words are negated in the user's message, and still passes a plain `approve N`.

## Change

- New `command_in(words, text)` returns `None`, `"negated"` or `"ok"`. A match is negated when its sentence holds a negation word (`no`, `not`, `never`, `nor`, `cannot`, `dont`, `cant`, `wont`, or any `n't` word) outside the matched words, before or after them. A sentence ends at `.`, `!`, `?` or `;` followed by whitespace or the end of the text. Line breaks do not end one. Curly apostrophes count. A negation word that starts the next sentence also negates ("Approve 30? No, not yet."). An ellipsis does not end a sentence. Any negated occurrence negates the message.
- `latest` still picks the newest user-role message with the words; if that one is negated it prints `not-user negated <itemId> <snippet>` and exits 1, with no fall back to an older message. `item` prints `reject: words negated`.
- `has_words` is unchanged, so `cos_peer.py` is unaffected.
- `chief-of-staff/SKILL.md` (the `cos_user_check.py latest` paragraph) says what `not-user negated` means, keeps the strict check for `approve N`, `cancel N` and `resume` only, passes the user's whole message as the words for every other command or answer, requires a quoted heredoc, and notes the exit 2 thread-read fallback does not run a negated approve, cancel or resume.
- One table-driven test in `test_cos.py` (both `latest` and `item`), one for the no-fall-back rule, one for the whole-message words.

## Left out

Intent beyond negation ("wait", "later", questions, conditionals) still passes. The Chief of Staff's own read of the snippet stays the second check.

## Calls I made

- The whole sentence counts, not just the words right before the command, so "approve 30, no rush" is refused.
- The script rule applies to every command `latest` serves, so the Chief of Staff keeps it strict only for `approve N`, `cancel N` and `resume`, and passes the user's whole message as the words for everything else (`changes N`, answers, `hold N`, `stop everything`, ticket requests). A whole-message match ignores its own negation, so feedback like "don't rename the file" and a "don't merge yet" hold still work (code review passes 1 to 3).
- A line break does not end a sentence, so "approve 30" on the line after a "don't …" line is refused.
- `don t` (space for apostrophe) is not caught.
