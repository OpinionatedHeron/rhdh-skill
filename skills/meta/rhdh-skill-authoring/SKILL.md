---
name: rhdh-skill-authoring
description: >-
  Creates, audits, and consolidates Agent Skills that follow the Agent Skills
  open standard, and hands back a drafted or repaired skill with the review
  checklist for its branch applied. Use for "create a skill", "draft a
  SKILL.md", "package this expertise as a skill", "why does this skill never
  trigger", "audit this SKILL.md", "improve this skill", or merging overlapping
  skills into fewer deeper modules. Covers frontmatter, descriptions that
  trigger, progressive disclosure, completion criteria, and bundled scripts.
---

# Skill Authoring

Create predictable Agent Skills through progressive disclosure, strong context
pointers, checkable completion criteria, and single-sourced behavior.

## Principles

- **One skill per trigger phrase.** A skill claims one thing a user would say.
  Two skills that would answer the same utterance are one skill; one skill that
  answers several unrelated utterances is several skills.
- **Split by verb, never by noun.** Verbs route; nouns collide. `create` and
  `refine` are two skills. Feature, Epic, and Story are one skill that infers the
  type, because the user often does not know which they want.
- **Weight the split by what a misroute costs.** Merge where a misroute produces
  a wrong *write*; split where it produces an obvious wrong *answer*. A read-only
  misroute is visible immediately; a wrong mutation is not.
- **A skill needing a disambiguating sub-command is two skills.** If the body
  opens by asking which mode the user wants, the router should have decided.
- Keep every-branch steps in `SKILL.md`; disclose branch-only reference behind
  a pointer that says when to read it.
- Keep references one level deep and independently usable.
- Keep descriptions below 1024 characters and skill bodies below 500 lines.
  The body limit governs `SKILL.md` only — measure the whole directory too, and
  settle it with the question the line count only hints at: **which of these
  vocabularies does a caller have to learn?** One trigger phrase commits the
  caller to one. Two skills in this pack reached 4,029 and 7,784 total lines
  while their `SKILL.md` files stayed comfortably compliant.
- Put deterministic validation and transformation in scripts.

## Duplication

Judge it by layer, not by volume (ADR-0006).

**Prompt duplication is forbidden.** When the same instructions, protocol, or
domain rule would appear in two skills: **extract** a reference skill when nothing
owns it, **enforce** the existing interface when a module already does, or
**document** it once when it is a rule rather than a capability. Two callers is
the threshold for extracting; one caller means it belongs inside its owner.

**Code duplication is expected.** Bundled scripts are self-contained so a skill
can be installed alone. Copy the helper rather than reaching across a seam.

Where a rule has to reach the agent at *runtime*, in someone else's repository,
it must live in a skill. `AGENTS.md` governs work inside this repository and does
not ship with the pack.

## Naming

Every promoted model-invoked skill keeps the `rhdh-` prefix (ADR-0008). Folders
are stripped at install, so the prefix is the only isolation the skill has in a
namespace that already holds dozens of unrelated skills. Name by domain then
verb, and keep the literal proper nouns — project keys, repository names, tool
names, an example issue key — in the description, because a literal token is the
strongest routing anchor available.

## RHDH repository profile

When authoring in this repository, read `CONTEXT.md` and the applicable ADRs
before designing the skill. ADR-0005 through ADR-0008 are binding:

- A promoted skill needs an independent trigger and one cohesive outcome.
- `ask-rhdh` and `setup-rhdh-skills` are the only human-invoked skills unless a
  later ADR changes that boundary.
- Category folders are editorial. Compose model skills by stable name, never
  through sibling files, imports, or host layout probing.
- Skills hand work over in prose: the producer reports its result in the
  conversation and the consumer reads it. An external write invokes
  `/rhdh-mutation-gate`; context that must survive into a later session is the
  user running `/handoff` (ADR-0007).
- A missing capability stops that branch and names the exact
  `/setup-rhdh-skills <route>`. Detecting is a model skill's job; installing and
  authenticating belong to the human entry point.
- The setup catalog is the source of truth for promoted membership, invocation,
  and dependencies. Update it with any promoted interface change.
- Before writing material a second skill would copy, decide extract, enforce, or
  document. Read `references/architecture-patterns.md` → Duplication between
  skills. Bundled scripts stay self-contained; there is no shared runtime
  package.
- Test scripts, adapters, catalog membership, clean installs, and observable
  behavior. Do not test headings, menu wording, XML tags, or README prose.

## Required grilling dependency

Creating or interviewing for a skill requires Matt Pocock's `/grilling` skill.
Treat it as a required named skill supplied by the complete pack. If the host
cannot invoke it by name, stop before drafting anything, say that creation is
gated on `grilling`, and name `/setup-rhdh-skills install`. Audit and
consolidation do not require grilling unless they open an interview.

## Conditional references

Load exactly one branch. Its own pointers name any specification, description,
architecture, script, or quality reference needed later.

- Read [references/create.md](references/create.md) to interview, draft, and
  review a new skill from scratch — "create a skill", "draft a SKILL.md",
  "package this expertise".
- Read [references/audit.md](references/audit.md) to review, repair, or diagnose
  an existing skill — "why does this never trigger", "check this SKILL.md",
  "improve this skill".
- Read [references/consolidation-guide.md](references/consolidation-guide.md) to
  merge overlapping skills into fewer, or to test whether a merge already went
  too far. Finish through the Phase 5 review in
  [references/create.md](references/create.md).

## Completion

Work is complete when the selected branch's review checklist passes, every
referenced resource resolves, and no behavior remains duplicated under an old
skill name.
