# Inspect or clean persisted artifacts

Cross-session handoffs live in the operating system temporary directory, namespaced by project root,
so they never enter a checkout and never reach Git. Ordinary handoffs remain in conversation and
need no file.

Invoke the named model skill `/rhdh-context` to validate an artifact before use.
Ask it to persist the artifact only when another session must consume it, or to
clean artifacts older than the requested number of days. Pass the artifact and
project root as inputs; never locate or execute `/rhdh-context` files directly.

The context skill returns validation or persistence results through its public
artifact interface. Its store rejects credential-like fields and values
recursively. If validation reports `CREDENTIAL_FIELD` or `CREDENTIAL_VALUE`,
remove the named secret at its source and create a new artifact rather than
editing a persisted copy.

Temporary storage is purged by the operating system, so an artifact from an
earlier session may be gone. The store reports `ARTIFACT_EXPIRED` and names the
skill to re-run; re-produce the artifact rather than reconstructing it by hand.
