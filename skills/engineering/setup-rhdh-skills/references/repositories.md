# Configure RHDH repositories

Use `rhdh doctor --json` to inspect repository discovery. The preserved configuration precedence is
environment override, project `.rhdh/config.json`, user `~/.config/rhdh-skill/config.json`, then
bounded workspace discovery.

For each missing repository:

1. Ask for or discover its checkout without modifying unrelated repositories.
2. Verify it is a Git repository with `git -C <path> rev-parse --show-toplevel`.
3. Create a `MutationPlan/v1` containing every `rhdh config set <key> <path>` operation.
4. Apply the approved plan and rerun `rhdh doctor --json`.

Use `rhdh setup submodule list` and `rhdh setup submodule add` only when the user explicitly chooses
the submodule layout. Preserve existing `.rhdh` configuration and never rewrite worklog or todo
state during repository setup.
