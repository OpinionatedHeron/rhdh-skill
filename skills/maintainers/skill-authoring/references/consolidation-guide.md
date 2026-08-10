# Consolidating Multiple Skills

Read this when asked to merge, consolidate, or combine existing skills into fewer skills.

## When to Consolidate

Look for these signals that separate skills should be one:

### Strong signals (consolidate)

- **One cohesive trigger**: Users describe the outcomes with the same leading
  intent and expect one completion contract.
- **Shallow boundaries**: Deleting a skill moves only routing prose or a small
  checklist into its caller rather than exposing a meaningful interface.
- **Near-identical scripts**: Two scripts with the same structure, differing only in a flag value or file path.
- **Duplicate files**: Same example YAML, same reference doc, or same version map appearing in multiple skills.
- **One source of meaning**: The split causes the same policy or domain facts to
  be maintained in several places.

### Weak signals (maybe consolidate)

- **Same audience**: All skills target the same persona, but the workflows are genuinely independent.
- **Same domain**: Skills cover the same product/area but handle unrelated concerns (e.g., CI debugging vs local testing).
- **Linear pipeline**: Producer and consumer may be better as separate deep
  skills joined by a named, versioned artifact.
- **Shared setup**: Central setup can remove prerequisite duplication without
  merging task-oriented skills.

### Don't consolidate

- **No shared context**: Skills have different prerequisites, different audiences, and no cross-references.
- **Different tools**: One skill uses `acli`, another uses `yarn` — they share nothing but the product name.
- **Deep seam**: A skill hides substantial policy, transport, state, or adapter
  complexity behind a small artifact interface.
- **Independent trigger**: Users reasonably ask for either outcome without the
  other, and each has distinct completion criteria.

## Consolidation Workflow

### Step 1: Analyze

Before writing any code:

1. Read every SKILL.md in the candidate set.
2. Map the cross-references. Draw the dependency graph — which skills point to which.
3. Inventory shared content: scripts, references, examples, version maps, prerequisites.
4. Apply the deletion test to every candidate boundary: identify where its
   complexity would move if the skill disappeared.
5. Identify the seams: which meaning becomes local to a deep skill and which
   data crosses a stable artifact contract.

### Step 2: Design the consolidated skill

Choose the architecture from trigger independence, interface depth, locality,
and leverage. File length determines progressive disclosure after the skill
boundary is chosen; it does not choose the boundary.

For sub-command routers:

- Preserve outcomes, not old folder boundaries. Several old skills may become
  one branch, or one old skill may split across deeper owners.
- Shared setup goes through the repository setup entry point. Shared domain
  meaning belongs to one owner skill and crosses boundaries as an artifact.
- Deep-dive references from the old skills move to `references/` with their original filenames.

### Step 3: Merge scripts

When consolidating near-identical scripts:

1. Diff the scripts. Identify what actually differs (usually a flag value, a directory name, or an optional step).
2. Keep the more mature script's structure (better error handling, more features).
3. Add a `--type` or `--mode` flag to express the variant behavior.
4. Verify both paths still work — run `--help` and test with both `--type` values.
5. **Harmonize patterns between scripts** in the same skill. Watch for:
   - One script checks `NO_COLOR`, the other doesn't
   - One builds a shell command string while the other uses validated argv; retain the structured
     `shell=False` boundary
   - One checks `stdout.isatty()` but logs to `stderr`
   - Different exit code conventions
   - Different JSON output formats

### Step 4: Consolidate examples

- Diff example files across the old skills. Often 60%+ is identical.
- Create one unified example file with sections for each variant.
- Remove duplicates — one example per pattern, not one per old skill.

### Step 5: Update all consumers

This is where consolidations break. Search the **entire project** for old skill names:

```bash
grep -rn "old-skill-name" --include="*.md" --include="*.py" --include="*.json" --include="*.yaml" --exclude-dir=.git .
```

**Must update:**

| Location | What to change |
|----------|---------------|
| Machine catalog | Promoted name, invocation, dependencies, artifact contracts |
| Human entry skills | Wayfinding and setup routes |
| README.md | Generated or summarized catalog documentation |
| ADRs / docs | Historical references to old skill names |
| Script docstrings | `--help` text referencing old workflow names |
| Other skills' references | Cross-references like "see the X skill" |
| CI / build configs | Paths to moved files |

**Gotcha: renumber menus.** If a router's intake menu had items 6-9 and you consolidated them into item 6, renumber 10→7, 11→8, etc. Update the routing table to match. Agents parse "pick a number" literally.

### Step 6: Audit reference paths

Reference files use relative paths. After moving files, paths break in subtle ways:

- A reference in `references/export.md` that says `Read references/export-options.md` is wrong — it would resolve to `references/references/export-options.md` from the file's perspective.
- Choose a convention: paths relative to the file, or paths relative to SKILL.md. Document which.
- Be consistent — don't mix conventions within the same skill.

**Recommended convention:** Paths in SKILL.md are relative to SKILL.md. Paths in reference files point to siblings by filename only (e.g., `Read export-options.md (in this directory)`).

### Step 7: Review

Run the standard Phase 5 review checklist from `references/create.md`, plus these consolidation-specific checks:

- [ ] No references to old skill names anywhere in the project
- [ ] Route tables select only same-skill branches and do not duplicate the promoted catalog
- [ ] Named dependencies and artifact contracts match the machine catalog
- [ ] Script docstrings and `--help` text reference the new skill name
- [ ] Reference paths resolve correctly from each file's location
- [ ] All example files from old skills are represented in the consolidated examples
- [ ] Scripts in the same skill use consistent patterns (NO_COLOR, shell flags, TTY checks, exit codes)
- [ ] README skill tables and directory trees match the new structure
- [ ] Script, contract, adapter, and clean-install tests pass without prose-shape assertions

## Anti-Patterns

### Incomplete grep

Searching for old names in `skills/` only. Old names appear in README, ADRs, CI configs, and script help text. Search the entire project.

### Path assumptions after moves

Copying a reference file without updating its internal relative paths. A file that said `../rhdh/references/versions.md` may need a different path after moving to a new directory.

### Keeping empty directories

After deleting old skills, empty directories or `__pycache__/` may linger. Clean up.

### Forgetting the description

The new consolidated skill's description must cover all trigger phrases from all old skills. Check each old description and verify the new one would trigger for the same queries.
