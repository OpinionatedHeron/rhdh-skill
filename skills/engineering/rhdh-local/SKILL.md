---
name: rhdh-local
description: >-
  Operates a local Red Hat Developer Hub environment with the
  rhdh-local-setup customization system: enable or disable dynamic plugins,
  apply configuration, switch pristine and customized modes, start or stop
  containers, inspect health and logs, run plugin verification, and back up or
  restore customizations. Use for local RHDH, podman compose plugin testing,
  PR artifact verification, 504 or startup troubleshooting, and local
  Extensions Catalog checks.
compatibility: "Python 3 and podman or docker; rhdh-local-setup checkout for runtime operations."
---

# RHDH Local

Own local execution and return evidence to the calling workflow. All commands
use this skill's standalone CLI; another skill does not need to be installed.

## Capability gate

1. Run `python scripts/rhdh-local --help`.
2. Locate `rhdh-local-setup` through `RHDH_LOCAL_SETUP_DIR` or by walking from
   the current directory. Run `python scripts/rhdh-local --json status`.
3. If the setup is absent, state the required environment variable or checkout
   layout and stop only the runtime branch.
4. Never read secrets from `.env` into conversation context. Ask only for
   missing variable names and let the container runtime consume their values.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Enable a catalog or PR artifact | `workflows/enable-plugin.md` |
| Disable a plugin | `workflows/disable-plugin.md` |
| Switch pristine/customized mode | `workflows/switch-mode.md` |
| Verify a plugin end to end | `workflows/test-plugin.md` and `references/dynamic-plugin-testing.md` |
| Inspect status or enabled packages | Run `python scripts/rhdh-local --json status` or `python scripts/rhdh-local --json plugins list` |
| Apply customizations | Run `python scripts/rhdh-local --json apply` |
| Start or stop | Run `python scripts/rhdh-local --json up [flags]` or `python scripts/rhdh-local --json down` |
| Check health | Run `python scripts/rhdh-local --json health` |
| Back up or restore | Run `python scripts/rhdh-local --json backup` or `python scripts/rhdh-local restore <archive>`; restore is a dry run until `--force` |
| Troubleshoot startup, networking, or 504s | `references/troubleshooting.md` |
| Configure environment variables | `references/env-reference.md` |

## Invariants

- Edit only source files under `rhdh-customizations/`. Run `apply` after every
  edit so copies under `rhdh-local/` stay synchronized.
- Use this CLI's `up` and `down` commands when Lightspeed or Orchestrator is
  enabled; they own the compose lifecycle and shared networks.
- Obtain package references from `spec.dynamicArtifact` or an incoming artifact.
  Never construct OCI references from naming conventions.
- Preserve the `includes:` block in dynamic plugin overrides. Put backend
  packages before their frontend packages.
- A plugin test succeeds only with recorded installation, boot, health, and UI
  results relevant to the request. Distinguish an expected credential error
  from a load failure.

## Artifact contracts

This skill consumes `ChangeHandoff/v1`:

```yaml
contract: ChangeHandoff/v1
id: local-test-id
createdAt: ISO-8601
data:
  summary: local verification request
  files: []
  verification:
    contract: VerificationEvidence/v1
    id: incoming-verification-id
    createdAt: ISO-8601
    data: {subject: plugin, checks: [], result: pending}
  packages: [{dynamicArtifact: exact-reference, pluginConfig: null}]
  requiredEnvironmentVariables: []
  testEntities: []
  cleanupAfter: true
```

It returns `VerificationEvidence/v1`:

```yaml
contract: VerificationEvidence/v1
id: local-test-evidence-id
createdAt: ISO-8601
data:
  subject: local-test-id
  checks: [{check: installation | startup | health | ui, result: pass | fail | skipped, evidence: null}]
  result: pass | fail | partial
  mode: customized | pristine
  packages: []
  logs: []
  cleanup: completed | retained | not-requested
```

Preserve exact artifact values and record skipped checks with a reason. Return
`VerificationEvidence/v1` to the caller in conversation; do not write into another
skill's directory.

## Completion

Report source customization files changed, CLI commands run, observed health
and UI evidence, cleanup state, and final `VerificationEvidence/v1`.
