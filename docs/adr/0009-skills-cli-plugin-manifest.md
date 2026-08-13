# Skills CLI plugin manifest

**Status:** Accepted.

## Context

`npx skills add` shows a flat searchable list unless the cloned repository
declares plugins in `.claude-plugin/marketplace.json` (or `plugin.json`). The
CLI maps each listed skill path to a `pluginName` and switches the install
prompt to a grouped tree (select a category header to toggle every skill in
it).

This repository already groups promoted skills into editorial categories in
`catalog.json` (`jira`, `plugins`, `ci`, `release`, `reference`, `meta`). Those
folders remain editorial for install layout — skills still flatten into host
skill directories — but the same membership is the natural grouping for the
installer UI.

Shipping a Claude Code marketplace plugin was considered and rejected: the pack
installs through skills.sh / `npx skills` and `/setup-rhdh-skills`, not
`claude plugins install`.

## Decision

Keep `.claude-plugin/marketplace.json` as a **generated projection** of
`skills/meta/setup-rhdh-skills/assets/catalog.json`:

- One marketplace plugin per catalog category.
- Plugin `name` is the category label shown in the installer (`CI` spelled as an
  acronym so the CLI does not render "Ci").
- Each plugin lists `./skills/<category>/<name>` paths in catalog order.
- No root `plugin.json` umbrella — that shape implies a single Claude plugin
  bundle we do not ship.

Regenerate with `scripts/generate_plugin_manifest.py` (`--write` / `--check`).
Pre-commit rewrites the file when the catalog (or the manifest) changes; tests
fail on drift.

Document the directory in `.claude-plugin/README.md` so the files are not
removed as "leftover marketplace" scaffolding.

## Consequences

- `npx skills add redhat-developer/rhdh-skills` shows six collapsible groups
  instead of a flat list of ~40 skills.
- Category membership has one source of truth: the setup catalog. The manifest
  cannot invent skills the catalog does not list.
- Editorial category renames require a catalog change; the manifest follows.
- Contributors must not treat `.claude-plugin/` as a product surface for Claude
  Code plugin distribution.
