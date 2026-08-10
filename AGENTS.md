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

The `skills/engineering/`, `skills/operations/`, and `skills/maintainers/`
folders are editorial. Compose through `/skill-name` prose and versioned
artifacts, never through sibling category paths.

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
- Cross-skill handoffs use typed artifacts with `contract`, `id`, `createdAt`,
  and contract-specific `data`. The version is part of `contract`. Artifacts
  persist under the operating system temporary directory, so a cross-session
  handoff may expire; the store reports the expiry and names the producing skill
  to re-run.
- External mutations require a user-approved `MutationPlan` before an adapter
  executes. Every operation declares `order`, `ownerSkill`, `adapter`,
  `operation`, `target`, `preview`, `preconditions`, `checks`, and `recovery`.
  The plan's `materialHash` binds all plan data except the hash itself. Record
  the outcome as a `MutationReceipt` carrying the same hash and plan ID. Its
  ordered outcomes map one-to-one to the plan operations by `order`,
  `ownerSkill`, `adapter`, `operation`, and `target`; every operation records
  `completed`, `failed`, or `skipped`.
  `SetupReceipt` may summarize capability status, but never replaces the
  `MutationReceipt` for an applied setup plan.
- Adapters isolate external variation such as Jira/GitHub issues, GitHub/GitLab
  forges, Podman/Docker, lifecycle sources, and CI systems.

Keep shared behavior behind the owning skill interface. Do not reach into
another skill's references or scripts.

When the same material would appear in two skills, decide which module owns it:
**extract** a foundation skill when nothing does, **enforce** the existing
interface when a module already does, or **document** the rule once here and in
`skill-authoring` when it is a rule rather than a capability. Copying is not a
fourth option. Shared runtime *code* is the one case no skill can serve: it
lives in the versioned `rhdh_common` package, declared as a dependency, never in
hand-synced copies between skills. See ADR-0006.

## Testing

Test behavior and contracts:

- deterministic scripts and CLIs;
- artifact schema validation and round trips;
- adapter contracts;
- catalog membership, invocation metadata, distribution exclusions, and links;
- workflow integration at named-skill and artifact seams.

Do not add tests that require incidental prose, headings, menu numbering, or
exact wording. Prose may change without changing the interface.

## Versioning and cutover

Git tags are the only authoritative versions. The `skills` CLI resolves tags,
not version files.

After merging changes to behavior, scripts, or `SKILL.md` files, create and push
an appropriate semantic-version tag. Use patch for behavior fixes, minor for new
backward-compatible capabilities, and major for breaking changes.

No tag exists yet, so both the pack and the `rhdh-common` git source resolve the
default branch. Tag them together: the first release tag must land in the same
change that pins `rhdh-common` in every PEP-723 block, or scripts will import a
runtime from a different commit than the skill that calls them.

## Agent project configuration

### Issue tracker

GitHub Issues via `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels are `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` plus root `docs/adr/`. See
`docs/agents/domain.md`.
