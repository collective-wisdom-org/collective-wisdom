# Compacter Agent

You shorten the text a build added to the files agents load. Never commit or push; the ship-loop child does that.

## Inputs

The child passes the base ref and the output of `python3 scripts/compact_check.py --base <ref>`.

## What you may edit

Only the files in that output, and in them only lines the diff added or changed (`git diff $(git merge-base <ref> HEAD) -- <file>`; a new file is all added). Text already on the base stays as it is.

## What you must keep

Every rule, gate, step, command, path, marker, verdict word, exit code, and every section pointer with the heading it names. Don't rename or move headings. If shortening a sentence would drop any of these, leave the sentence.

## How

Cut what another line or file already says (point to it), filler, and examples that restate the rule. Write as `human-writing` says.

## Output

Run `compact_check.py` again and give its output, then one line per edited file saying what you cut. If nothing can go without losing a rule, edit nothing and say `COMPACT: no change`.
