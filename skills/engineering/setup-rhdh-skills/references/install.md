# Install or repair the complete collection

The primary path installs the official `RHDH complete` skills.sh pack. The catalog is the local
source of truth for the promoted skill set and its two required external dependencies.

1. Create the installation plan:

   ```bash
   uv run scripts/setup.py install-plan --agent <agent-id> --scope global --json
   ```

   Use `--pack-url <url>` to bootstrap a release before its URL is recorded in the catalog. When no
   pack URL exists, the script creates an equivalent repository-install fallback plan.

2. Present the full `MutationPlan/v1`. Each ordered operation names its owner, adapter, operation,
   target, preview, preconditions, verification checks, and recovery procedure. The
   `materialHash` binds the summary and complete operation array. After the user approves that
   hash, save the exact plan JSON to a temporary file and apply it:

   ```bash
   uv run scripts/setup.py apply --plan <plan.json> --approved-material-hash <sha256:...> --json
   ```

3. Run `uv run scripts/setup.py doctor --json`. Repair only the skills still reported missing.
4. Ask the user to restart or rescan the agent so newly installed descriptions are loaded.

The adapter validates every operation before running the first one and executes argument arrays
directly without a command shell. If validation fails, no installation operation runs.

Completion requires all promoted skills, `grilling`, and `humanizer` to be discovered in a
supported host layout.
