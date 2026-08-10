# Foundation skills

Duplication between promoted skills is resolved by extracting a **foundation skill** — a model-invoked skill whose reason for existing is material that two or more skills would otherwise copy. Callers reach it through named skill composition, exactly as they reach any other model-invoked skill, and it carries an ordinary description that may fire on user intent. This follows the `grilling` skill in the external pack, which `/grill-me` and `/grill-with-docs` both compose without either owning a copy of the interview.

The rule that skills never read each other's files was enforced at the import boundary only. It said nothing about copying, so every enforcement of it produced a copy. At the time of this decision roughly 16% of the Python under `skills/` was duplicated, four copy pairs had already diverged in the working tree, and the mutation protocol existed as eight prose copies in two incompatible serializations — three of which omitted the rule that a receipt carries exactly one outcome per planned operation. Nothing detected the divergence: no test, lint rule, or CI check compared two copies.

## The rule is three-way

Duplication between skills does not always mean create one. Choose by asking which module owns the material:

- **Extract** — nothing owns it; it exists only as N copies. Create a foundation skill and invoke it by name.
- **Enforce** — a module already owns it and a caller copied past its interface. Delete the copy and cross the seam.
- **Document** — the material is a rule rather than a capability. State it once in `skill-authoring` and `AGENTS.md`, which already govern every skill. A skill nobody invokes pays permanent context load for nothing.

Shared *runtime code* is a fourth case no skill can serve. A script needs an object at run time, and there is nothing at the other end of a prompt. That is a versioned package, not a skill.

## Consequences

- Two foundation skills exist at this decision: `rhdh-artifacts` (envelope, material hash, mutation plan and receipt, setup capability, credential redaction) and `rhdh-forge` (forge reads and issue context).
- A foundation skill's description competes for model routing like every other model-invoked skill. Keep it narrow, and prefer one foundation skill over two whose triggers overlap.
- Catalog validation enforces that a declared dependency is named in the owning `SKILL.md`, so an extraction nothing invokes fails the build rather than rotting.
- The three-way rule is the first question when a reviewer finds the same text in two skills, replacing the previous implicit answer of "copy it."

## Amendments to ADR-0005

This decision amends [ADR-0005](0005-composable-skill-distribution.md) in three places. That decision otherwise stands.

- **Artifact storage.** Artifacts persist under the operating system temporary directory, not `.rhdh/artifacts/`. The previous location was documented as gitignored, which was true of this repository and of no other checkout artifacts are written to. Cross-session handoffs may therefore expire between sessions; the store reports an expired artifact and names the producing skill to re-run.
- **Install scope.** The complete pack is the only supported install. The selective-installation clause is retired, and with it the independent-installability argument that six skills used to justify duplicated modules.
- **Shared package.** Skills may depend on one versioned shared package, `rhdh_common`, declared in the PEP-723 block of standalone scripts and shipped in the wheel for the rest. What ADR-0005 forbade was uncoordinated coupling through host filesystem layout — a sibling discovered by walking directories. A versioned dependency is not that, and it preserves the portability ADR-0002 protects.
