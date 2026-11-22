---
name: human-writing
description: >-
  Rewrites or drafts user-facing copy, UI strings, PR descriptions, Slack messages,
  emails, blog posts, and spec prose so it reads like a clear human colleague, not
  generic LLM output. Use when the user asks to sound human, avoid AI tells, skip
  em dashes, polish messaging, or improve tone for any channel.
user-invocable: true
---

# Human writing

Apply when drafting or editing prose for people. Read this before sending user-facing text. Identify channel, audience and one main point first. Examples: [examples.md](examples.md).

## Hard rules

### No em dashes

No em dashes (—). Use commas, periods, parentheses or two sentences. Hyphens in compound adjectives (`well-known`, `multi-tenant`) are fine.

### Avoid LLM tells

Cut or replace patterns like these:

- **Openers and closers:** Certainly, Absolutely, Great question, I'd be happy to, Of course; Hope this helps, Let me know if you need anything else; engagement bait ("Happy to dive deeper", "Feel free to reach out anytime" as filler).
- **Filler transitions:** Furthermore, Moreover, Additionally, In addition; It's worth noting, Notably (when it adds no fact); In conclusion, To summarize (in a short piece); chained "That said" / "With that in mind" / "Having said that".
- **Hype and vagueness:** delve, landscape (figurative), robust, seamless, streamlined (empty); leverage / utilize where **use** works; game-changer, cutting-edge, revolutionary, empower, elevate; "In today's [X] world", "ever-evolving", "at the end of the day".
- **Tone:** performative enthusiasm ("Exciting news!", "I'm thrilled to..."); mirroring the user's adjectives without new information; hedging stacks ("might potentially perhaps"); signpost overload ("First... Second... Third..." for three short points); template intros ("Let's dive in", "In this guide we'll explore").
- **Formatting:** bold on every other phrase in chat or email; emoji strings as punctuation.

### Do write like

A clear colleague: direct, respectful, no performance. **Answer first**, then context. **Vary sentence length**; one idea per sentence when explaining. **Concrete nouns and verbs**: name the thing, the action, the outcome. **Proportionate length**: short question, short answer. **Match the channel:** Slack terse; PR summary scannable; spec precise; email one clear ask.

## Scope exceptions

Do **not** rewrite code, API paths, identifiers, env vars, commit messages; exact wording the user supplied or quoted; required structured formats (legal boilerplate, mandated templates, PR test-plan checklists); brand or product names the user fixed. A **user rule** that conflicts with this skill wins.

## Pre-send check

Before sending prose to a user or external channel, confirm: the hard rules hold; the opening line states the point, not a pleasantry; length fits the channel (not a blog post in Slack); no decorative bold unless the format requires it (e.g. PR headings); a busy teammate could skim it and know what to do next; the scope exceptions are respected.

## Do not

Change technical accuracy to sound casual. Add fluff to hit a word count. Invent commitments, dates or features.
