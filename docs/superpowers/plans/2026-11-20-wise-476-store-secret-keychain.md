# WISE-476 plan: store-secret command and keychain key registry

Spec: [../specs/2026-11-20-wise-476-store-secret-keychain-design.md](../specs/2026-11-20-wise-476-store-secret-keychain-design.md)

Test command: `python3 -I -m pytest -q agent-team/scripts` and `shellcheck install.sh tag-release.sh agent-team/scripts/*.sh`

## Task 1: `agent-team/scripts/store_secret.py`

`store`, `record` and `list` as the spec's § Change 1 and 2 define them. Standard library only. Registry path `Path.home()/.config/collective-wisdom/secrets.md`, created with mode 0600. The `security` binary is found through `PATH` (so tests can fake it); its output is discarded. Follow the style of `user_config.py` (module docstring with usage, `main(argv)` returning an exit code).

## Task 2: `agent-team/scripts/test_store_secret.py`

Table-driven, as spec § Change 5, with `HOME` set to a temp folder and a fake `security` script on `PATH`. Keep the test lines below the script's lines.

## Task 3: docs

- New `agent-team/docs/agents/secrets.md` (spec § Change 3), a row in `agent-team/docs/agents/README.md`.
- Pointer line under § Secrets in `agent-team/templates/AGENTS.md` and `AGENTS.md`; one line in `agent-team/docs/agents/github-auth.md` § Account per repo. Call the script and docs as `~/.collective-wisdom/...` (`test_call_sites.py`). No em dashes.
