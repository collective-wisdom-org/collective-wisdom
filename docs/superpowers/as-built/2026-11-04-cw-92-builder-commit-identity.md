# As-built: Author and push ticket branch commits as the builder user

**Shipped:** in PR #99
**Ticket:** CW-92
**Spec:** [2026-11-04-cw-92-builder-commit-identity-design.md](../specs/2026-11-04-cw-92-builder-commit-identity-design.md)

## Differs from the spec

- The spec exits 2 on any push remote that isn't https. `git.sh` accepts only `https://github.com/*`, plus `file://` and absolute local paths, which use no credential, so a push there cannot go out under the wrong identity.
- The spec passed the token to git in a `GIT_SH_TOKEN` environment variable and answered any https host. The credential helper now fetches the token on demand with `gh auth token -u <login>`, so nothing is exported to hooks or other child processes, and it answers only for `protocol=https` and `host=github.com`.
- Only `push`, `fetch`, `pull`, `clone`, `ls-remote` and `credential` get the helper. Other subcommands get the identity environment only. `credential` is on the list so the helper can be tested with `git.sh credential fill`.
- The spec finds `push` as the first argument. `git.sh` skips git's leading options (`-C <dir>`, `-c <k=v>`, `--git-dir`, `--work-tree`, `--namespace`, `--config-env`, `--attr-source`) so they cannot hide a push, and runs its own checks with the same options.
- The push check resolves the remote like git (the argument, else `branch.<b>.pushRemote`, `remote.pushDefault`, `branch.<b>.remote`, then `origin`), checks every push URL of it, and checks the source side of each refspec (`--all`, `--mirror` and `--tags` check the matching refs) with `rev-list <src> --not --remotes=<remote>`. If `rev-list` fails, the push is refused.

## Known limits

- The push check is a guardrail against mistakes, not a security boundary.
- An alias (`-c alias.p=push p ...`) or `git rebase --exec 'git push ...'` does not run through the check.
- Edge-case refspecs fail closed or are not checked: globs make `rev-list` fail, `--delete` skips the commit check, and `--repo <url>` is not followed.
- The token reaches only the credential helper, but any process running as the user can still run `gh auth token -u <login>`.
