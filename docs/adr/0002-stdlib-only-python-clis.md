# stdlib-only Python CLIs

Both CLIs (`rhdh` and `rhdh-local`) use only Python 3.9+ standard library — zero external dependencies. This means no `click`, `rich`, `typer`, or any other package. The trade-off is rougher developer ergonomics in exchange for zero-install portability. The CLIs run wherever Python exists — no `pip install`, no virtualenv, no version conflicts. For agent tooling that needs to "just work" in any environment an agent might run in, that constraint is worth the cost.

## Implementation patterns

- **`argparse`** for argument parsing (stdlib, not click/typer)
- **`OutputFormatter`** for auto-detecting TTY vs piped output (human-readable vs JSON)
- **`urllib`** only inside a narrow authenticated adapter; any bearer credential is retrieved from
  the owning native CLI, used transiently in memory for the request header, and excluded from public
  arguments, output, logs, plans, and artifacts
- **`uv`** as the dev tool runner (`uv run pytest`) — not shipped with the CLIs, but used for development and testing

New scripts and CLI commands in this project should follow these same patterns.

## Exceptions

Scripts that must round-trip YAML while preserving comments, key ordering, and
quoting may use `ruamel.yaml`. The current uses are private adapters owned by
`rhdh-ci` and `rhdh-platform-support`. Such scripts declare dependencies with
PEP 723 inline metadata and run through `uv run --script`, which provides an
ephemeral environment without a user-facing install step.

The exception is capability-based, not category-based: it applies only when
the standard library cannot preserve the required YAML representation. The
Google Sheets schedule adapter delegates to the native-store `gog` CLI and is
not an exception. The main CLIs and every ordinary script remain stdlib-only.
