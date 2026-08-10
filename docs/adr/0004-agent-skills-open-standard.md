# Agent Skills open standard

All promoted skills in this project follow the [Agent Skills specification](https://agentskills.io/specification) — an open format for giving AI agents new capabilities. Each promoted skill is a portable package with `SKILL.md` frontmatter, progressive disclosure (description → instructions → references), and optional bundled scripts, references, and assets. Harness-specific metadata such as `agents/openai.yaml` is additive and never replaces the standard interface. The complete collection is installed as one pack through `/setup-rhdh-skills`; installing an individual skill directory is not supported, because promoted skills reach each other by name and share setup state and a versioned package ([ADR-0006](0006-foundation-skills.md)).

## Consequences

- Skill structure is constrained by the spec (frontmatter format, directory conventions, description length limits).
- New skills should be validated against the [best practices](https://agentskills.io/skill-creation/best-practices) and [description optimization](https://agentskills.io/skill-creation/optimizing-descriptions) guidance.
- Client-specific metadata must remain optional; the standard `SKILL.md` package is authoritative.
