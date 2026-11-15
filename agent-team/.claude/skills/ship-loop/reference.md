# Ship loop reference

## Running one phase by hand

The user can start at a phase by name (spec or kickoff, build, make a pr or handle review, security review, merge). Start there, but warn if the earlier phase's gate isn't met (e.g. a PR without a spec; security review without code review **PASS**; merge without security review **PASS**; in `ci` mode, merge with an unresolved bot thread or red checks). In a hand run, a merge that starts without a `MERGE READY` of its own in the thread runs the missing phases, reports `MERGE READY` and waits for an approval sent after it.
