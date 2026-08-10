---
name: skill-authoring
description: >-
  Create, audit, and consolidate Agent Skills that follow the Agent Skills open
  standard. Use when creating or drafting a SKILL.md, diagnosing why a skill
  does not trigger, improving an existing skill, or consolidating overlapping
  skills into fewer deeper modules.
---

# Skill Authoring

Create predictable Agent Skills through progressive disclosure, strong context
pointers, checkable completion criteria, and single-sourced behavior.

## Principles

- Keep every-branch steps in `SKILL.md`; disclose branch-only reference behind
  a pointer that says when to read it.
- Keep references one level deep and independently usable.
- Keep descriptions below 1024 characters and skill bodies below 500 lines.
- Put deterministic validation and transformation in scripts.
- Use `scripts/command-metadata.json` as the source of truth for the create,
  audit, and consolidate command descriptions.

## RHDH repository profile

When authoring in this repository, read `CONTEXT.md` and the applicable ADRs
before designing the skill. ADR-0005 and ADR-0006 are binding:

- A promoted skill needs an independent trigger and one cohesive outcome. A
  broad model-invoked catalog or orientation router is not a promoted skill.
- `ask-rhdh` and `setup-rhdh-skills` are the only human-invoked skills unless a
  later ADR changes that boundary.
- Category folders are editorial. Compose named model skills through versioned
  artifact contracts, never through sibling files, imports, or host layout
  probing.
- The setup catalog is the source of truth for promoted membership, invocation,
  dependencies, and artifacts. Update it with any promoted interface change.
- Before writing material a second skill would copy, decide extract, enforce, or
  document. Read `references/architecture-patterns.md` → Duplication between
  skills. Shared runtime code is a versioned package, never a skill.
- Test scripts, artifact and adapter contracts, clean installs, and observable
  behavior. Do not test headings, menu wording, XML tags, or README prose.

Use an in-skill routing table only to disclose branches within one cohesive
domain. It must not duplicate the promoted catalog or substitute for named
skill composition.

## Required grilling dependency

Creating or interviewing for a skill requires Matt Pocock's `/grilling` skill.
Treat it as a required named skill supplied by the complete pack. If it is not
available, return `SetupRequired/v1` as defined in `references/create.md`,
direct the human to `/setup-rhdh-skills`, and stop. Audit and consolidation do
not require grilling unless they open an interview.

## Route the request

| Request | Reference |
|---|---|
| Create or draft a skill | [references/create.md](references/create.md) |
| Audit, review, or repair a skill | [references/audit.md](references/audit.md) |
| Consolidate overlapping skills | [references/consolidation-guide.md](references/consolidation-guide.md), then the final review in [references/create.md](references/create.md) |

Load only the selected branch. Its pointers identify any specification,
description, architecture, script, or quality reference needed later.

## Completion

Work is complete when the selected branch's review checklist passes, every
referenced resource resolves, and no behavior remains duplicated under an old
skill name.
