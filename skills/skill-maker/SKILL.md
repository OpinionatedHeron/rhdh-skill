---
name: skill-maker
description: >
  Relentless create-audit-consolidate workflow for Agent Skills (agentskills.io).
  Use when creating a new skill or drafting a SKILL.md. Use when auditing or
  reviewing why a skill never triggers. Use when consolidating overlapping
  skills into fewer. Use when packaging expertise, workflows, or domain
  knowledge into a reusable skill.
---

<essential_principles>

# Create, Audit, or Consolidate Skills

Create agent skills following the [Agent Skills open standard](https://agentskills.io/specification).

- Progressive disclosure: every-branch material inline; branch-specific behind pointers
- References are one level deep (no A → B → C chains)
- Descriptions under 1024 chars; SKILL.md body under 500 lines
- Surgical edits when fixing — don't rewrite unbroken sections
- Map quality issues to failure modes in `references/skill-quality.md`
- Command descriptions for audit/create/consolidate: `scripts/command-metadata.json` is the single source of truth

**Create path grilling:** Create/interview hard-requires Matt Pocock's `grilling` skill. Full gate + invoke wording live in `references/create.md` (Phase 1). Audit and consolidate skip the gate unless you actually interview.

</essential_principles>

<intake>

What do you need to do?

1. **Audit an existing skill** — Review, improve, or debug a SKILL.md
2. **Create a new skill** — Interview, draft, and review from scratch
3. **Consolidate skills** — Merge multiple skills into fewer

**Wait for response before proceeding.**

</intake>

<routing>

| Response | Workflow |
|----------|----------|
| 1, "audit", "review", "check", "fix", "improve" | `references/audit.md` |
| 2, "create", "write", "build", "new", "draft" | `references/create.md` |
| 3, "consolidate", "merge", "combine" | `references/consolidation-guide.md` — return to Phase 5 in `references/create.md` for final checklist |

</routing>

<reference_index>

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/audit.md` | Audit branch — review, improve, or debug an existing skill |
| `references/create.md` | Create branch — interview through review (Phases 1–5) |
| `references/spec-guide.md` | Drafting a SKILL.md (Phase 2) — full format reference |
| `references/description-guide.md` | Optimizing the description (Phase 3) |
| `references/scripts-guide.md` | Writing scripts (Phase 4) |
| `references/skill-quality.md` | Drafting, auditing, or reviewing — predictability vocabulary and failure modes |
| `references/anti-patterns.md` | Drafting or auditing — common failures to avoid |
| `references/architecture-patterns.md` | Choosing between simple, router, and domain expertise patterns |
| `references/api-skill-patterns.md` | Skill calls external APIs or services |
| `references/consolidation-guide.md` | Merging multiple skills into fewer |
| `references/xml-structure-guide.md` | Deciding on XML vs markdown structure |

</reference_index>
