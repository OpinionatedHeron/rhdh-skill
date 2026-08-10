# Mutation protocol

Detail behind the plan, hash, and receipt shapes in `SKILL.md`. Read this when
constructing a plan, reproducing a hash, or deciding whether an approval still
holds.

## Operation fields

Every entry in `data.operations` carries all nine fields. An operation missing
one is invalid, not merely incomplete.

| Field | Meaning |
|---|---|
| `order` | Position in the batch, starting at 1 and matching the array index. Operations execute in this order. |
| `ownerSkill` | The skill that will execute the operation. |
| `adapter` | The interface used, such as `github`, `git`, `acli`, `shell`, `openshift`, or `skills-cli/v1`. |
| `operation` | The adapter's operation name, such as `github.pull-request.create` or `jira.issue.update`. |
| `target` | The exact resource written: repository, issue key, branch, namespace, or pinned head SHA. |
| `preview` | The exact structured input, such as `{"commandOrRequest": "..."}` or `{"argv": [...]}`. A preview is what will run, not a paraphrase. |
| `preconditions` | Conditions checked immediately before execution; an unmet precondition stops the batch. |
| `checks` | Evidence captured after execution, such as a created URL or a status check. |
| `recovery` | How to undo or contain the operation if it succeeds wrongly or fails halfway. |

Empty arrays are legitimate values for `preconditions`, `checks`, and
`recovery`. Omitting the keys is not.

## Computing the hash

The hash input is the complete `data` object with `materialHash` removed,
serialized as UTF-8 JSON with sorted keys and separators `,` and `:`. For this
plan material:

```json
{
  "summary": "Trigger Overlay publication for the current PR head",
  "operations": [{
    "order": 1,
    "ownerSkill": "rhdh-overlay",
    "adapter": "github",
    "operation": "github.comment.create",
    "target": "redhat-developer/rhdh-plugin-export-overlays#42@abc1234",
    "preview": {"body": "/publish"},
    "preconditions": ["open"],
    "checks": ["capture-comment-url"],
    "recovery": []
  }]
}
```

the canonical string is:

```text
{"operations":[{"adapter":"github","checks":["capture-comment-url"],"operation":"github.comment.create","order":1,"ownerSkill":"rhdh-overlay","preconditions":["open"],"preview":{"body":"/publish"},"recovery":[],"target":"redhat-developer/rhdh-plugin-export-overlays#42@abc1234"}],"summary":"Trigger Overlay publication for the current PR head"}
```

and the hash is
`sha256:14540cf91b4a71fb9515c4a5b7b1cad4658c41841439024275591b87f894bfe9`.

Any difference in whitespace, key order, or field content produces a different
hash, which is the point: the approval binds the summary and every material
operation field.

## When an approval stops holding

Re-plan and ask for a new hash approval whenever bound material changes,
including a changed branch, head SHA, file set, PR or comment body, recipient,
namespace, manifest, review event, cleanup step, or the addition of a new
irreversible action. Reject execution when the material hash differs from the
approved one instead of re-deriving a hash from the changed plan.

An approval covers one batch. When an earlier operation produces material a
later one needs, close the first batch with its receipt, build a new exact plan
from the real result, and obtain a new approval.

## Recording outcomes

Execute operations in `order`. On failure, stop and record the remaining
operations as `skipped`; the receipt still carries one outcome per planned
operation. Beyond the identity fields and `status`, record what the caller will
need afterward: the created or changed resource and its URL, the evidence named
in `checks`, and any recovery action still outstanding. A failed batch that left
a partial change reports that recovery explicitly rather than reporting failure
alone.

## Validating and persisting

Keep ordinary handoffs in conversation. To validate an artifact against its
contract, or to persist a cross-session handoff, invoke `/rhdh-context` and pass
the artifact. It checks the envelope, the operation shapes, the material hash,
and the receipt binding, and it rejects credential-shaped content at any depth.
Do not load its files or re-implement its checks.
