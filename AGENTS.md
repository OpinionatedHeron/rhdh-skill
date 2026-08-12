# AGENTS.md

Agent Skills for Red Hat Developer Hub engineering, operations, and repository
maintenance. Skills follow the Agent Skills open standard. Read `CONTEXT.md`
for domain language and `docs/adr/` for architectural decisions.

## 1. Think Before Coding

Do not assume or hide confusion.

- State assumptions explicitly.
- Surface multiple interpretations and tradeoffs.
- Prefer the simpler approach when it satisfies the request.
- Stop and ask when ambiguity would materially change the result.

## 2. Simplicity First

Write the minimum code that solves the requested problem.

- Add no speculative features or single-use abstractions.
- Keep CLI implementation stdlib-only except for the documented PEP 723 YAML
  exception in ADR-0002.
- If a change can be substantially smaller without losing behavior, simplify it.

## 3. Surgical Changes

Touch only what the request requires. Preserve unrelated work and match the
existing style. Remove only the imports, variables, functions, or files made
obsolete by your own change.

## 4. Goal-Driven Execution

Translate the request into observable success criteria and verify them. Run
`uv run pytest` before reporting repository work complete.

## 5. No Irreversible Commands Without Confirmation

Never force-push, reset HEAD, merge branches, or run destructive commands
without explicit confirmation.

## 6. Learn From Corrections

When an implementation is corrected, apply the correction and record reusable
project-specific knowledge in the owning skill reference.

## Skill architecture

Skills are grouped by domain: `skills/jira/`, `skills/plugins/`, `skills/ci/`,
`skills/release/`, `skills/reference/`, `skills/meta/`. Those folders are
editorial and are stripped at install. Compose through `/skill-name`, never
through sibling category paths.

A promoted skill claims exactly one trigger phrase. Two skills that would claim
the same utterance are one skill; one skill answering several unrelated
utterances is several skills. Split by verb, never by noun, and weight the split
by what a misroute costs — merge where a misroute produces a wrong write, split
where it produces an obvious wrong answer. See ADR-0005.

Only `ask-rhdh` and `setup-rhdh-skills` are human-invoked. They carry
`disable-model-invocation: true` in `SKILL.md` and
`policy.allow_implicit_invocation: false` in `agents/openai.yaml`. Every other
promoted skill is model-invoked and omits both flags. Every promoted skill has
an `agents/openai.yaml` interface entry.

The complete pack also requires external `/grilling` and `/humanizer` skills.
Creation/interview flows use grilling; PR-review prose uses humanizer.

Keep drafts and retired skills outside the promoted discovery root:

- `internal/in-progress/`
- `internal/deprecated/`

Do not add them to promoted manifests or catalogs.

## Composition contracts

- `/ask-rhdh` is a catalog, not an orchestrator. It recommends a named skill
  and performs no setup or mutation.
- `/setup-rhdh-skills` owns setup routing, configuration, authentication, and
  compatibility with existing CLI/state locations.
- Credentials stay inside an authenticated adapter backed by a native tool
  store or host connector. Workflow instructions and non-adapter scripts may
  detect capability, but only that adapter may retrieve a transient credential
  and authenticate a request. Public arguments, output, logs, plans, and
  artifacts remain credential-free. Setup owns login and never creates a
  parallel credential store.
- `/rhdh-context` owns shared repository and version context.
- Skills pass context by invoking each other by name. There is no artifact
  envelope and no artifact store. When the user needs context to survive into a
  later session, tell them to run `/handoff`.
- Every external write goes through the write gate in `/rhdh-mutation-gate`:
  state each operation with its target, exact command, preview, and failure
  behaviour; get approval for that stated set; execute; report the outcome of
  every operation, including the skipped ones. The plan renders as a table in
  the conversation. A plan too large for the transcript goes to a file in the
  temporary directory and the path is printed. Read-only inspection needs no
  gate. See ADR-0007.
- `/rhdh-forge` constructs forge payloads and never executes them. A caller that
  needs a write receives a command, not an effect.
- Adapters isolate external variation such as Jira/GitHub issues, GitHub/GitLab
  forges, Podman/Docker, lifecycle sources, and CI systems.

Keep shared behavior behind the owning skill interface. Do not reach into
another skill's references or scripts.

Duplication is judged by layer. **Prompt duplication is forbidden**: when the
same instructions, protocol, or domain rule would appear in two skills,
**extract** a reference skill when nothing owns it, **enforce** the existing
interface when a module already does, or **document** it once when it is a rule
rather than a capability — here for rules governing this repository, in
`rhdh-skill-authoring` for rules that must ship with the pack, since this file
does not travel with it. **Code duplication is acceptable**: bundled scripts are
self-contained so a skill can be installed alone, and there is no shared runtime
package. See ADR-0006.

Every promoted model-invoked skill keeps the `rhdh-` prefix. Folders are stripped
at install, so the prefix is the only isolation the pack has against the router's
global namespace. See ADR-0008.

## Testing

Test behavior and contracts:

- deterministic scripts and CLIs;
- adapter contracts;
- catalog membership, invocation metadata, distribution exclusions, and links;
- that no promoted skill directory sits outside a domain category;
- workflow integration at named-skill seams.

Do not add tests that require incidental prose, headings, menu numbering, or
exact wording. Prose may change without changing the interface.

## Versioning and cutover

Git tags are the only authoritative versions. The `skills` CLI resolves tags,
not version files.

After merging changes to behavior, scripts, or `SKILL.md` files, create and push
an appropriate semantic-version tag. Use patch for behavior fixes, minor for new
backward-compatible capabilities, and major for breaking changes.

No tag exists yet, so the pack resolves the default branch. Bundled scripts have
no shared runtime dependency to pin alongside it.

## Agent project configuration

### Issue tracker

GitHub Issues via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels are `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` plus root `docs/adr/`. See
`docs/agents/domain.md`.
