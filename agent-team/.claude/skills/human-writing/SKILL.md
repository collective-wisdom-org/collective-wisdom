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

Apply when drafting or editing prose for people. Read this skill before sending user-facing text unless the user asked for exact wording or a fixed template.

**Examples:** [examples.md](examples.md)

## Hard rules

### No em dashes

Do not use em dashes (—). Use commas, periods, parentheses, or two sentences. Hyphens in compound adjectives (e.g. `well-known`, `multi-tenant`) are fine.

### Avoid LLM tells

Cut or replace patterns like these (not an exhaustive list):

**Openers and closers**

- Certainly, Absolutely, Great question, I'd be happy to, Of course
- Hope this helps, Let me know if you need anything else
- Engagement bait (e.g. "Happy to dive deeper", "Feel free to reach out anytime" as filler)

**Filler transitions**

- Furthermore, Moreover, Additionally, In addition
- It's worth noting, Notably (when it adds no fact)
- In conclusion, To summarize (when the piece is already short)
- Chained "That said" / "With that in mind" / "Having said that"

**Hype and vagueness**

- delve, landscape (figurative), robust, seamless, streamlined (empty)
- leverage / utilize when **use** works
- game-changer, cutting-edge, revolutionary, empower, elevate
- "In today's [X] world", "ever-evolving", "at the end of the day"

**Tone**

- Performative enthusiasm ("Exciting news!", "I'm thrilled to...")
- Mirroring the user's adjectives back without adding information
- Hedging stacks ("might potentially perhaps", "it's possible that maybe")
- Signpost overload ("First... Second... Third..." for three short points)
- Template intros ("Let's dive in", "In this guide we'll explore")

**Formatting**

- Bold on every other phrase in chat or email
- Emoji strings as punctuation

### Do write like

- A clear colleague: direct, respectful, no performance
- **Answer first**, then context (especially Slack and support)
- **Vary sentence length**; one idea per sentence when explaining
- **Concrete nouns and verbs**; name the thing, the action, the outcome
- **Proportionate length**; short question → short answer
- **Match the channel:** Slack terse; PR summary scannable; spec precise; email one clear ask

## Scope exceptions

Do **not** rewrite:

- Code, API paths, identifiers, env vars, commit messages
- Exact wording the user supplied or quoted
- Required structured formats (legal boilerplate, mandated templates, PR test-plan checklists)
- Brand or product names the user fixed

If a **user rule** conflicts with this skill, **user rules win**.

## Workflow

1. Identify channel, audience, and one main point.
2. Draft in plain language; apply hard rules above.
3. Run **Pre-send check** below.
4. Ship.

## Pre-send check

Before sending prose to a user or external channel:

- [ ] No em dashes (—)?
- [ ] Opening line states the point or answer, not a pleasantry template?
- [ ] No hype words or empty transitions?
- [ ] Length fits the channel (not a blog post in Slack)?
- [ ] No decorative bold unless the format requires it (e.g. PR headings)?
- [ ] Would a busy teammate skim this and know what to do next?
- [ ] Exceptions respected (code, identifiers, user-requested wording)?

## Do not

- Change technical accuracy to sound casual.
- Add fluff to hit a word count.
- Invent commitments, dates, or features.
