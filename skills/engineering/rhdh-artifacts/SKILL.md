---
name: rhdh-artifacts
description: >-
  Defines the RHDH artifact protocol shared by every skill in the pack: the
  versioned envelope, the MutationPlan approval hash, the MutationReceipt
  outcome rule, SetupRequired capability handoffs, and credential redaction.
  Use before planning, approving, or executing any external write, when
  computing or checking a material hash, when returning a mutation receipt, or
  when handing a versioned artifact to another skill.
compatibility: "No tools required. Validation and persistence run through /rhdh-context."
---

# RHDH Artifacts

RHDH skills exchange work as versioned artifacts and gate every external write
on a plan the user approved by hash. This skill owns that protocol so no calling
skill restates it. Invoke it by name before building a plan, approving a hash,
returning a receipt, or emitting a capability handoff.

Artifacts are JSON objects. The material hash and the artifact store are defined
over that JSON, so a YAML rendering is presentation only and must round-trip to
the same object.

## Envelope

Every artifact, including a nested one, has exactly four top-level fields:

```json
{
  "contract": "<Name>/v1",
  "id": "<stable-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {}
}
```

- `contract` names the versioned shape. Reject an unknown contract rather than
  guessing at its fields.
- `id` holds letters, numbers, dots, underscores, and hyphens, and stays stable
  for the same subject so a later artifact can reference it.
- `createdAt` is UTC ISO-8601 to the second, generated when the artifact is
  produced. Never copy a timestamp out of an example.
- `data` carries every contract-specific field. Nothing contract-specific sits
  beside it.

A nested artifact, such as `VerificationEvidence/v1` inside `ChangeHandoff/v1`,
is a complete envelope and keeps its own `id` and `createdAt`.

## Mutation contract

Each calling skill names what counts as a mutation in its own domain. Reading,
analysis, dry runs, and drafting in chat are not mutations. Everything a skill
does name is executed only from a plan whose hash the user approved:

```json
{
  "contract": "MutationPlan/v1",
  "id": "<owner>-mutation-<stable-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "summary": "...",
    "operations": [{
      "order": 1,
      "ownerSkill": "<calling-skill>",
      "adapter": "<adapter-name>",
      "operation": "<adapter.operation-name>",
      "target": "<exact-resource>",
      "preview": {"commandOrRequest": "<exact-structured-input>"},
      "preconditions": [],
      "checks": [],
      "recovery": []
    }],
    "materialHash": "sha256:<canonical-plan-data-hash>"
  }
}
```

Compute `materialHash` from the UTF-8 JSON encoding of the complete `data`
object with `materialHash` removed, keys sorted, and separators `,` and `:`.
This binds the summary and every material operation field.

Build the plan only after every target and payload is exact. Show the complete
plan and the exact hash, and execute only after the user approves that hash. A
request to publish, post, trigger, or update is intent, never plan approval, and
neither is earlier discussion or an earlier confirmation of content. Execute no
operation absent from the approved plan.

## Mutation receipt

Every approved plan ends in one receipt:

```json
{
  "contract": "MutationReceipt/v1",
  "id": "<owner>-receipt-<stable-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "planId": "<approved-plan-id>",
    "materialHash": "sha256:<approved-hash>",
    "outcomes": [{
      "order": 1,
      "ownerSkill": "<same-as-plan-operation>",
      "adapter": "<same-as-plan-operation>",
      "operation": "<same-as-plan-operation>",
      "target": "<same-as-plan-operation>",
      "status": "completed | failed | skipped"
    }]
  }
}
```

Return exactly one ordered outcome for every planned operation, including
failures and operations skipped after a failure. Each outcome repeats the plan's
`order`, `ownerSkill`, `adapter`, `operation`, and `target`. An aggregate
summary of what happened is not a receipt, and the store rejects it.

## Setup capability

When a required capability, credential, or named skill is unavailable, stop that
branch and return:

```json
{
  "contract": "SetupRequired/v1",
  "id": "<owner>-setup-required",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "ownerSkill": "setup-rhdh-skills",
    "route": "<setup-branch>",
    "reason": "<what is unavailable>",
    "missing": ["<capability-or-skill>"],
    "nextCommand": "/setup-rhdh-skills <setup-branch>"
  }
}
```

`route` and the command argument name the same setup branch, such as `install`,
`jira`, `atlassian-mcp`, `openshift-ci`, `local-runtime`, `repositories`,
`google-workspace`, `private-data`, or `artifacts`. Detecting a missing
capability is a model skill's job; installing, authenticating, or repairing one
belongs to the human entry point.

## Credentials

Artifacts never carry credential material. Pass a secret directly to the tool
that owns it and leave it out of conversation, configuration JSON, and artifact
`data`. The store rejects credential-shaped keys and values at any depth; a
rejection means the producer put a secret in an artifact, not that the field
needs a different name.

## Conditional references

- Read [references/mutation-protocol.md](references/mutation-protocol.md) when
  building, hashing, or validating a plan or receipt: operation field meanings,
  a worked hash example, re-plan triggers, and validation through
  `/rhdh-context`.
- Read [references/handoff-contracts.md](references/handoff-contracts.md) when
  handing implemented work to another skill as `ChangeHandoff/v1` or reporting
  `VerificationEvidence/v1`.

## Completion

Complete when the caller can act without copying prose from here. For a plan:
the exact `data` object, the `materialHash` computed over it with `materialHash`
removed and keys sorted, and the statement that approval of that hash alone
authorizes execution. For a receipt: one outcome per planned operation, each
repeating its `order`, `ownerSkill`, `adapter`, `operation`, and `target`. For a
handoff: the four-field envelope with a `createdAt` generated now rather than
copied from an example. A protocol answer that leaves a planned operation
without an outcome, puts a contract-specific field outside `data`, or carries
credential material inside one is not complete. The caller keeps its own
preconditions, adapters, and recovery.
