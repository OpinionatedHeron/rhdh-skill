---
name: rhdh-platform-support
description: >-
  Reports supported and end-of-life versions for RHDH and its deployment
  platforms. Use for RHDH, OpenShift, AKS, EKS, GKE, PostgreSQL, Red Hat build of
  Keycloak, Quay, or product lifecycle and compatibility questions.
compatibility: "Python 3.9+; uv for PEP 723 YAML-backed scripts; gh for remote openshift/release access."
---

# RHDH platform support

Produce lifecycle facts without changing repositories or external systems.

## Interfaces

- Produces: `LifecycleAssessment/v1`.
- Consumes: no cross-skill artifact.
- All repository and YAML access stays behind this skill's local adapters.

## Route

| Question | Load | Run |
|---|---|---|
| RHDH support and compatible OCP versions | `workflows/check-rhdh.md` | `scripts/check_rhdh_lifecycle.py` |
| OpenShift support phases | `workflows/check-ocp.md` | `scripts/check_ocp_lifecycle.py` |
| Azure AKS support and configured versions | `workflows/check-aks.md` | `scripts/check_aks_lifecycle.py` |
| AWS EKS support and configured versions | `workflows/check-eks.md` | `scripts/check_eks_lifecycle.py` |
| Google GKE support | `workflows/check-gke.md` | `scripts/check_gke_lifecycle.py` |
| PostgreSQL support | `workflows/check-pg.md` | `scripts/check_pg_lifecycle.py` |
| RHBK, Quay, or another Red Hat product | `workflows/check-redhat.md` | `scripts/check_lifecycle.py` |

Load one workflow. Use the bundled script for deterministic retrieval and
classification; add judgment only after its output is available.

## Output contract

Return the shared `LifecycleAssessment/v1` contract:

```json
{
  "contract": "LifecycleAssessment/v1",
  "id": "rhdh-support-YYYY-MM-DD",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "product": "RHDH",
    "asOf": "YYYY-MM-DD",
    "versions": [],
    "configuredVersions": [],
    "compatibility": [],
    "sources": [],
    "warnings": []
  }
}
```

Preserve the script's source dates and uncertainty. Distinguish vendor lifecycle
from versions merely configured in `openshift/release`. Do not infer that a
configured version is supported.

## Composition

Other skills invoke the named skill `rhdh-platform-support` and consume
`LifecycleAssessment/v1`. They must not import `rhdh_lifecycle` or locate this
skill on disk: `rhdh_lifecycle` is a private, local adapter.

## Completion

Complete when every product and version named in the request appears in
`data.versions` with the support phase and the source date the script returned,
`data.sources` names each endpoint the answer rests on, and every version the
script could not classify appears in `data.warnings` rather than being dropped or
estimated. A version found only in `openshift/release` appears under
`data.configuredVersions` and is never reported as supported. If a lifecycle
source was unreachable, name the product that remains unassessed instead of
returning the partial list as the answer.
