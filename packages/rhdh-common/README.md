# rhdh-common

Shared runtime code for RHDH skill scripts. This is the fourth arm of the
duplication rule in [ADR-0006](../../docs/adr/0006-foundation-skills.md): a
script needs an object at run time, and there is nothing at the other end of a
prompt, so shared runtime code is a versioned package rather than a foundation
skill.

## Modules

| Module | Provides |
|---|---|
| `rhdh_common.output` | `OutputFormatter`, `detect_output_mode`, ANSI colour constants |
| `rhdh_common.process` | `run_command`, `find_tool`, `find_acli` |
| `rhdh_common.jsonio` | `log`, `error_exit` — stderr progress, JSON error on stdout |
| `rhdh_common.jira` | `FIELDS`, `enrich`, `flatten` — acli Jira field extraction, including the custom-field IDs |
| `rhdh_common.versions` | `ver_sort_key`, `fetch_json`, `is_date`, `to_date`, `filter_supported_eol_entries` |
| `rhdh_common.openshift_release.repo` | `resolve_repo_root`, `GITHUB_REPO` |
| `rhdh_common.openshift_release.yaml` | `list_yaml_files`, `fetch_yaml`, `fetch_yaml_text`, `extract_branch` (needs the `yaml` extra) |

## Consuming it

Standalone scripts declare it in their PEP-723 block:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["rhdh-common"]
#
# [tool.uv.sources]
# rhdh-common = { git = "https://github.com/redhat-developer/rhdh-skill", subdirectory = "packages/rhdh-common" }
# ///
```

Add the extra — `"rhdh-common[yaml]"` — when the script reads openshift/release
YAML. The `rhdh` and `rhdh-local` CLIs get the package from the `rhdh-skill`
wheel, which vendors it.

## Why the source is unpinned

The git source carries no `tag` or `rev`, so it resolves from the default
branch. That matches how the pack itself ships: with no tags in the repository,
`npx skills add` also resolves the default branch, so a script and the runtime
it imports come from the same commit. Pinning the package while the skills
around it track the branch would pair new skill code with old runtime code.

Pin both together or neither. When the first release tag is cut, add a matching
`tag` here in the same change.

Two consequences to know about:

- Until this package exists on the default branch, `uv run` fails for an
  installed skill with `has no subdirectory packages/rhdh-common`. Inside a
  repository checkout it resolves from the local workspace and works normally.
- `rhdh_common.mutation` owns the material hash that binds a `MutationPlan/v1`
  to what a human approved. An unpinned source means two runs can canonicalize
  differently if that module changes between them, which would surface as a
  hash mismatch rather than silent divergence — but it is the reason to pin
  this package first once tagging starts.
