# Audit Workflow

Use this workflow when reviewing, improving, or debugging an existing skill.

Command descriptions for audit/create/consolidate: `scripts/command-metadata.json` is the single source of truth.

## Step 1: Locate and read the skill

Read the full SKILL.md and list all files in the skill directory (`references/`, `scripts/`, `templates/`, `assets/`).

## Step 2: Run the audit checklist

Check each category. Note issues as you go. Map structural/content findings to failure modes in `references/skill-quality.md` (premature completion, duplication, sediment, sprawl, no-op, negation) when diagnosing why a skill misfires or bloats.

**Frontmatter:**

- [ ] `name` matches the directory name, lowercase+hyphens, max 64 chars
- [ ] `description` is under 1024 chars, non-empty, third person
- [ ] `description` includes trigger phrases (not just a summary of what the skill does)
- [ ] `description` covers edge phrasings users would actually say
- [ ] `description` front-loads a leading word / one trigger per branch (see `references/skill-quality.md`)

**Structure:**

- [ ] SKILL.md body is under 500 lines
- [ ] Essential principles are inline in SKILL.md (not only in a reference file)
- [ ] All referenced files exist (check every path in the SKILL.md)
- [ ] References are one level deep (no nested chains: A → B → C)
- [ ] Context pointers name *when* to load (not vague "see references/")
- [ ] Progressive disclosure: every-branch material inline; branch-specific behind pointers

**Content quality:**

- [ ] No rigid ALWAYS/NEVER rules without reasoning (explain WHY)
- [ ] No explanations of things the agent already knows from training (no-ops)
- [ ] Steps are specific and verifiable (not "handle errors appropriately")
- [ ] Success criteria / completion criteria are observable and testable
- [ ] Examples use fake data where appropriate
- [ ] No negation-only steering without a positive target behaviour

**Router pattern** (if applicable):

- [ ] The activated skill has one cohesive domain and completion contract
- [ ] Intake asks only when the request did not already select a branch
- [ ] Route table maps branches to same-skill reference or workflow files
- [ ] All referenced workflow/reference files exist
- [ ] Essential principles are in SKILL.md, not only in sub-command references
- [ ] The route does not duplicate the promoted catalog or locate another skill by path

**Composition and distribution** (for this repository):

- [ ] Promoted membership, invocation mode, dependencies, and artifacts match the machine catalog
- [ ] Named skill handoffs use declared `Type/vN` artifacts with the shared envelope
- [ ] Human-invoked skills are limited to the approved wayfinding and setup entry points
- [ ] Domain skills return `SetupRequired/v1` instead of installing or authenticating
- [ ] Tests exercise scripts, contracts, adapters, and clean installs rather than prose shape

**Scripts** (if present):

- [ ] Scripts have shebangs, `--help`, and structured output
- [ ] No interactive prompts (all input via flags/env/stdin)
- [ ] Cross-platform paths (pathlib, no hardcoded separators)
- [ ] Error messages explain what went wrong and what to do

Read `references/anti-patterns.md` for the full catalog of common failures.

## Step 3: Generate the report

Present findings grouped by severity:

1. **Critical** — skill won't trigger or produces wrong output
2. **Important** — structural issues, missing files, spec violations
3. **Minor** — style, conciseness, optimization opportunities

For each finding, state the issue, cite the specific line or section, and recommend a fix.

## Step 4: Offer fixes

Ask the user which findings to fix. Apply changes surgically — don't rewrite sections that aren't broken. Before finishing, verify modified skills against the Phase 5 review checklist in `references/create.md` (Basics through Quality).

Audit does **not** require the `grilling` skill unless you actually run an interview/grill (e.g. clarifying ambiguous scope with the user). For a pure read-and-report audit, skip the grilling setup gate.
