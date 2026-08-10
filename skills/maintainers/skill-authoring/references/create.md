# Create Workflow (Phases 1–5)

Interview, draft, optimize, script, and review a new skill from scratch.

Command descriptions for audit/create/consolidate: `scripts/command-metadata.json` is the single source of truth.

## Phase 1: Interview

### Grilling prerequisite (hard gate)

Creating or interviewing requires the named `/grilling` skill. It is installed
and discovered by `/setup-rhdh-skills`; this skill neither locates nor installs
pack dependencies.

If `/grilling` is unavailable, stop and return:

```json
{
  "contract": "SetupRequired/v1",
  "id": "grilling-setup-required",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "missing": ["grilling"],
    "nextCommand": "/setup-rhdh-skills install"
  }
}
```

Resume the original create request only after setup reports the dependency
available.

### Interview cadence

Invoke `/grilling` and follow its interface. Do not paraphrase its cadence rules.

Use grilling to walk the focus areas and architecture decision tree below. If a fact can be answered by exploring the codebase, explore instead of asking.

Focus areas, roughly in order:

1. **Purpose and audience.** What task does this skill cover? What specific problem does it solve? What does the user do today without it?
2. **Scope boundaries.** What should this skill NOT do? What adjacent tasks belong to other skills?
3. **Input/output.** What does the user provide? What does the skill produce? Specific formats?
4. **Edge cases.** What goes wrong? Common mistakes? Gotchas for new users?
5. **Success criteria.** How do you know the skill worked correctly?
6. **What can be scripted?** Look for deterministic operations that should be code, not LLM instructions. Scripts are cheaper, faster, and more reliable.
7. **References needed?** Domain knowledge too large for SKILL.md that should live in separate files?
8. **Existing patterns.** Similar skills or workflows to draw from? Check the codebase.
9. **Platform constraints.** macOS, Windows, and Linux? Scripts must handle path separators, temp directories, and shell differences.
10. **External services and APIs.** Does the skill call external APIs or services? If yes, read `references/api-skill-patterns.md` — it covers credential handling, schema discovery, instance-specific values, and error placement.

### Architecture decision tree

After the interview questions above, decide the architecture. Most skills are simple — only escalate when the answers demand it.

**Question 1: How many distinct things can a user want to do?**

- One specific thing → **Simple skill** (single SKILL.md, under 200 lines)
- Multiple things with shared principles → continue to Q2

**Question 2: Is there shared domain knowledge across those operations?**

- No, each operation is self-contained → **Simple skill** (or multiple separate simple skills)
- Yes, multiple operations share knowledge → **Router skill** (SKILL.md + `references/`)

**Question 3: Does it cover a full lifecycle (build, debug, test, ship)?**

- No → **Router skill** is sufficient
- Yes → **Domain expertise skill** (exhaustive references, full lifecycle workflows)

| What you're building | Pattern |
|---|---|
| "A skill that commits with a conventional message" | Simple |
| "A skill that manages PRs — create, review, merge, close" | Router |
| "A skill for building and shipping macOS apps" | Domain expertise |
| "A skill that audits other skills" | Simple (upgrade to Router if it grows) |

For Router and Domain expertise patterns, also ask:

- **Does the skill need project-level context?** If every command needs the same background, design a context file pattern with a loader script.
- **Are there mandatory setup gates?** Steps that must pass before any work begins. Gates prevent generic output.
- **Does behavior vary by task type?** If so, design a register/mode system that classifies the task first, then loads different references.

Read `references/architecture-patterns.md` for implementation details of each pattern.

**Consolidation signal check:** If the interview reveals the new skill overlaps significantly with existing skills (shared scripts, cross-references, linear pipeline), consider consolidating instead of creating. Read `references/consolidation-guide.md` for the signals and workflow.

Do not proceed to Phase 2 until the user confirms the scope is complete.

## Phase 2: Draft the SKILL.md

Write the skill following the spec. Read `references/spec-guide.md` for the full format reference before drafting. Read `references/skill-quality.md` before drafting (predictability via information hierarchy, checkable completion criteria, strong context pointers, pruning) and again during Phase 5 Quality.

**Starter templates:** Use `templates/simple-skill.md` for a linear workflow or
`templates/router-skill.md` for branches within one cohesive domain. Copy the
smallest suitable template, then replace its generic boundaries with the real
interface and completion contract.

### Frontmatter

```yaml
---
name: skill-name        # lowercase, hyphens, max 64 chars
description: |           # max 1024 chars — implicit trigger for model-invoked skills
  What the skill does. Use when [specific triggers].
  Also use when [additional triggers].
---
```

For a model-invoked skill, make the description slightly "pushy" because agents tend to undertrigger.
Include what it does and genuine phrases or contexts that should activate it. A human-invoked entry
skill disables implicit invocation; its description is catalog copy, not a model trigger.

### Body structure

Follow progressive disclosure — three loading levels:

1. **Metadata** (~100 tokens): `name` and `description` are available for model-invoked skills;
   human-only entries are selected explicitly
2. **Instructions** (< 500 lines): Full SKILL.md body loaded when skill activates
3. **Resources** (as needed): `references/`, `scripts/`, `assets/` loaded only when required

Keep the SKILL.md body under 500 lines. If approaching this limit, split domain-specific content into `references/` files with clear pointers about when to read them.

### Deduplication check

Before writing domain knowledge into a new reference file, check if it already exists in another reference. Shared data (exit criteria, field mappings, workflow rules) must live in exactly one file. New references should point to the existing source — not embed a copy.

Common trap: a new sub-command reference duplicates tables from an existing reference because it "needs them for context." Instead, add a one-line pointer: "Load `references/workflows.md` for exit criteria per status."

**Exception: intentional duplication.** When two sub-commands need the same query pattern but referencing each other would create a transitive loading chain (A → B → C), duplicate the pattern and add a note: "Same query pattern as X.md Step N — duplicated here to avoid transitive loading." This is cheaper than forcing the agent to load an unrelated file.

### Writing patterns

- **Imperative form**: "Run the command" not "You should run the command"
- **Explain WHY, not just what**: Avoid rigid ALWAYS/NEVER rules without reasoning. Agents generalize from principles better than from rigid rules. Instead of "ALWAYS use pdfplumber. NEVER use PyPDF2," write "Use pdfplumber over PyPDF2 — it handles malformed PDFs more gracefully and preserves layout metadata needed for table extraction." Principles adapt to edge cases; rigid rules break.
- **Don't explain what the agent already knows**: Skip basic programming concepts, standard library usage, and well-known tool behavior. Only add context the agent doesn't have — project-specific conventions, non-obvious behavior, domain-specific gotchas. A 30-token code example beats a 150-token explanation of what a library is.
- **Output templates**: Define exact formats when the output structure matters
- **Concrete examples**: Show input → output for non-obvious workflows
- **Gotchas sections**: Common mistakes the agent should avoid
- **Checklists**: Multi-step workflows with validation gates
- **Conditional loading**: "Read `references/api-errors.md` if the API returns a non-200 status code" — not "see references/ for details"
- **Absolute bans**: When certain patterns are always wrong, use match-and-refuse lists. "If you're about to write X, stop and do Y instead." More effective than vague "be careful" guidance.
- **Avoid hardcoded thresholds**: Don't write arbitrary numbers as rules (e.g., "when you have 3+ sub-commands" or "if more than 5 issues") unless the threshold comes from a real constraint (API limit, spec requirement). Instead, describe the signal that triggers the behavior (e.g., "when you're copying the same text into another sub-command"). Hardcoded numbers feel authoritative but are usually guesses that don't generalize.

Read `references/anti-patterns.md` during drafting to avoid known pitfalls.

### Instruction structure

Use descriptive Markdown headings and short sections. Structure is an authoring
aid, not a public protocol; never require tests to preserve headings, tags, or
menu numbering.

### Sub-command router (when applicable)

For branches that share one domain model and completion contract, use a route
table in `SKILL.md`. Do not use an in-skill router to duplicate the promoted
skill catalog.

```markdown
## What would you like to do?

1. **Craft a feature** — Build end-to-end
2. **Audit code** — Technical quality checks

Wait only when the request did not already select a branch.

## Route

| Response | Workflow |
|----------|----------|
| 1, "craft", "build" | `references/craft.md` |
| 2, "audit", "check" | `references/audit.md` |
```

Paths like `references/craft.md` above are **example only** — substitute real command reference names for the skill you are building.

Back the router with a `scripts/command-metadata.json` as the single source of truth:

```json
{
  "craft": {
    "description": "Full build flow. Use when building a new feature end-to-end.",
    "argumentHint": "[feature description]"
  }
}
```

### Setup gates (when applicable)

Non-negotiable checks before any file edits. Gates prevent generic output from missing context.

```markdown
## Setup (non-optional)

| Gate | Required check | If fail |
|---|---|---|
| Context | Project config loaded via `python scripts/load_context.py` | Run the loader first |
| Config | Config file exists and is valid | Return the project setup owner's exact setup route |
| Command | Sub-command reference is loaded | Load the reference |
| Mutation | All gates above pass | Do not edit project files |
```

`scripts/load_context.py` in the table above is **example only** — name the loader to match the skill you are building.

### Register/mode system (when applicable)

When behavior varies by task type, classify first, then load different references:

```markdown
## Register

Every task is **library** (published, API-stable) or **application** (internal, can break).
Identify before acting. Load the matching reference: [references/library.md] or [references/application.md].
```

### Capability-gating

Steps that depend on optional environment capabilities (browser automation, specific CLI tools) must degrade gracefully:

```markdown
### Automated Scan (Capability-Gated)

Run the automated scanner when ALL of these are true:
- The target files exist and are readable
- The required CLI tool is installed

If unavailable, state in one line that the step is skipped and why. Do not ask the user to install tooling.
```

### Structured artifacts as handoffs

When one skill produces output another consumes, define a named, versioned
artifact in the repository contract catalog. Use the shared `contract`, `id`,
`createdAt`, and `data` envelope. The producer owns the meaning; the consumer
declares the contract it accepts. Do not make a reference file or script path
the handoff interface.

```markdown
### Plan Structure

**1. Summary** (2-3 sentences)
**2. Primary Goal**
**3. Approach**
...
```

### Self-critique loops

For build/implementation commands, mandate inspect-and-fix passes with explicit exit bars:

```markdown
### Critique and fix loop

After the first pass, write a short self-critique and patch. Repeat until no material issues remain:
1. Does it match the requirements?
2. Does it pass the [quality test]?
3. Check every expected scenario.
4. Check edge cases.

The exit bar is not "it works." It is: [explicit quality threshold].
```

## Phase 3: Description Optimization

For model-invoked skills, the description is the only skill content agents see at startup. Human-invoked descriptions are human-facing catalog text. Read `references/description-guide.md` for the full optimization process.

Quick validation:

1. Write should-trigger queries — at least enough to cover each branch and near-miss; prefer 8–10 per `references/description-guide.md`, minimum cover each branch
2. Write should-not-trigger queries — near-misses that share keywords but need different skills (same coverage bar as should-trigger)
3. Check: would the description correctly distinguish these?
4. Revise if needed — broaden for missed triggers, narrow for false triggers
5. Verify under 1024 characters

For skills with sub-commands, the main description covers the skill broadly. Each sub-command's description in `command-metadata.json` is optimized separately for auto-trigger keyword matching.

## Phase 4: Scripts

Read `references/scripts-guide.md` for the full guide.

**Bias toward scripts.** Every deterministic operation should be a script, not an instruction. Scripts are cheaper (no LLM tokens), faster (no reasoning), and more reliable (no hallucination).

For each piece of the skill's workflow, ask: "Could a script do this?" If yes, write the script.

**Should be scripts:**

- Validation (input format, required fields, schema compliance)
- File generation from templates
- Data extraction and transformation
- API calls with structured responses
- Setup and environment checks
- Output formatting
- Context loading (read project files, resolve paths, return JSON)
- Cleanup (remove deprecated files after skill updates)

**Should stay as instructions:**

- Deciding between architectural approaches
- Reviewing code for quality or style
- Explaining tradeoffs to the user
- Creative writing or design decisions
- Interview/discovery conversations

Key patterns:

- **Python without dependencies**: stdlib only, `argparse` for CLI parsing
- **YAML round-trip exception**: PEP 723 with `ruamel.yaml` and `uv run --script`, only as allowed by
  ADR-0002
- **All scripts**: Structured output (JSON when piped), clear exit codes, descriptive `--help`

### Context loader pattern

For skills that need project-level context, write a loader script:

The script should follow all standard patterns: `argparse` with `--help`, structured JSON output (pretty when interactive, compact when piped), clear exit codes (0 = found, 1 = missing), `pathlib` for cross-platform paths, and stdlib-only imports. See the "Context File System" section in `references/architecture-patterns.md` for a skeleton.

The SKILL.md references it — for example only: "Load context via `python scripts/load_context.py`. Consume the full JSON output. Never pipe through `head`, `tail`, or `grep`." Rename the script to match the skill.

## Phase 5: Review

Before presenting the final skill, verify against this checklist:

### Basics

- [ ] `name` is lowercase, hyphens only, max 64 chars
- [ ] `description` is under 1024 chars and includes trigger phrases
- [ ] `description` is slightly pushy — covers edge phrasings that should activate the skill
- [ ] SKILL.md body is under 500 lines
- [ ] Instructions use imperative form

### Architecture (if applicable)

- [ ] A route table exists only when it discloses branches within one cohesive skill
- [ ] `command-metadata.json` is authoritative when scripts or generated interfaces consume command metadata
- [ ] Setup gates are defined with fail actions for each gate
- [ ] Register/mode system classifies before loading references
- [ ] Capability-gated steps degrade gracefully with one-line skip reasons
- [ ] Model-invoked skills do not duplicate the promoted catalog or route by sibling path
- [ ] Named skill handoffs declare versioned artifacts in the machine catalog
- [ ] Human/model invocation metadata matches the approved repository boundary

### References

- [ ] Domain knowledge split into `references/` with clear "when to read" pointers
- [ ] Each reference is self-contained — no transitive loading (see `spec-guide.md` → Reference Architecture)
- [ ] Reference loading is conditional, not eager ("Read X if Y happens")
- [ ] Shared concerns (auth, config) extracted into their own reference, not embedded in a consumer
- [ ] Error handling lives in the reference for the tool that produces the error
- [ ] Multi-approach skills include a decision table routing to the correct reference
- [ ] Model-invoked skills do not start browser-only setup; human `/setup-rhdh-skills` may own
      required OAuth consent or installation steps

### Scripts

- [ ] Scripts (if any) have shebangs, structured output, and `--help`
- [ ] Context loader returns JSON, handles missing files, resolves fallback paths
- [ ] Scripts are cross-platform (pathlib, tempfile, no hardcoded paths)
- [ ] Scripts are idempotent — safe to re-run
- [ ] External mutations bind the complete plan to a canonical hash and emit one identity-matched
      `MutationReceipt/v1` outcome per operation, including failures and skips

### API/Service Skills (if applicable)

- [ ] Credentials remain inside an authenticated adapter backed by a native tool store or host
      connector; workflow commands, plans, logs, and artifacts contain no credential material
- [ ] Credential setup delegates to `/setup-rhdh-skills`; domain skills only detect capability
- [ ] Capability gate checks authenticated adapter readiness without inspecting credential material
- [ ] API schema discovery is documented (OpenAPI download, GraphQL introspection, or live endpoints)
- [ ] API examples have been validated against the live endpoint
- [ ] Instance-specific values include programmatic discovery methods

### Consolidation (if merging existing skills)

- [ ] No references to old skill names anywhere in the project (`grep -rn` the entire repo)
- [ ] The machine catalog contains the new promoted names, invocation modes, dependencies, and artifacts
- [ ] Script docstrings and `--help` text reference the new skill name, not the old ones
- [ ] Reference paths resolve correctly from each file's location (no `references/references/` nesting)
- [ ] All example files from old skills are represented in the consolidated examples
- [ ] Scripts in the same skill use consistent patterns (NO_COLOR, shell flags, TTY checks, exit codes)
- [ ] README, ADRs, and other docs updated to reflect new skill structure
- [ ] New description covers all trigger phrases from all old skills' descriptions
- [ ] Tests cover scripts, contracts, adapters, and clean installation—not prose shape

### Quality

Read `references/skill-quality.md` again during this Quality pass (same file as before drafting).

- [ ] No time-sensitive information (URLs to specific versions, dates that will go stale)
- [ ] Examples use fake data where possible (emails, names, tokens) — see `spec-guide.md` → Fake Data in Examples
- [ ] Consistent terminology throughout
- [ ] Concrete examples included for non-obvious workflows
- [ ] Absolute bans defined for patterns that are always wrong (pair with positive target — avoid negation-only)
- [ ] Self-critique loops defined for build/implementation commands with explicit exit bars
- [ ] Steps have checkable completion criteria; no obvious premature-completion traps
- [ ] No duplication / sediment / no-ops left after pruning (see `references/skill-quality.md`)
