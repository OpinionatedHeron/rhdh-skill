# Handoff contracts

Two contracts move implemented work between skills. Read this when producing or
consuming either one.

## ChangeHandoff/v1

A verified change, ready for another skill to publish, package, or run. The
producer owns the change; the consumer never diagnoses or edits product code.

```json
{
  "contract": "ChangeHandoff/v1",
  "id": "<change-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "summary": "concise change summary",
    "files": [],
    "verification": {
      "contract": "VerificationEvidence/v1",
      "id": "<change-verification-id>",
      "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
      "data": {"subject": "<change-id>", "checks": [], "result": "pass"}
    }
  }
}
```

`summary`, `files`, and `verification` are required.

- `files` lists repository-relative paths the change touches, and it is the
  publication set: a publisher stages exactly these paths and treats anything
  else dirty in the checkout as outside the change.
- `verification` is a complete nested envelope with its own `id` and
  `createdAt`, not a bare `data` block.
- A consumer treats the checkout as authoritative and reports any mismatch
  against the handoff rather than trusting the artifact over the working tree.

Producers add the fields their consumer needs beside these three, such as
`repository`, `workspace`, `changeKind`, `issue`, `sourceRepository`,
`sourceRef`, `packages`, or recordings. Consumers ignore fields they do not use.

## VerificationEvidence/v1

What was checked, and what the checks proved.

```json
{
  "contract": "VerificationEvidence/v1",
  "id": "<verification-id>",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "subject": "<artifact-id-or-resource>",
    "checks": [],
    "result": "pass | fail | partial"
  }
}
```

`result` is `pass`, `fail`, or `partial`, and nothing else. Evidence is produced
after checks run, so there is no pending result: a check that has not run yet is
absent from `checks`, and a run that could not complete is `partial` with the
reason recorded. Each entry in `checks` names the command or condition and its
observed outcome. Never record a check that was not executed.

Skills that verify against a cluster, a local runtime, or a live PR add the
context that makes the evidence reproducible, such as the deployed bundle or
manifests, the original and final state, and the cleanup result. A failed
verification returned to the skill that owns the code carries the exact command
and its output.
