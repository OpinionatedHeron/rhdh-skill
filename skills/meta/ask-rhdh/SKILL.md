---
name: ask-rhdh
description: Human wayfinder for the RHDH skills collection.
disable-model-invocation: true
---

# Ask RHDH

Turn an RHDH question into one precise model-skill invocation. This is a human entry point,
not a second discovery system: route by outcome and hand the request over intact.

## Route the request

Each row below is a model skill's own description, projected from the catalog by
`scripts/render_routes.py`. Do not hand-edit the table: run
`python scripts/render_routes.py --write` after a skill is added, removed, or
redescribed, and `--check` to detect drift. Paraphrasing a skill here creates a
competing inventory, which is what this table used to be.

<!-- BEGIN GENERATED ROUTES: python scripts/render_routes.py --write -->
| When the request is | Model skill |
|---|---|
| Resolve RHDH repositories, version compatibility, configuration, workspace status, worklogs, and todos. Use for RHDH orientation and read-only context needed by another RHDH skill; implementation work belongs to the domain skill that owns the requested outcome. | `/rhdh-context` |
| Defines the RHDH artifact protocol shared by every skill in the pack: the versioned envelope, the MutationPlan approval hash, the MutationReceipt outcome rule, SetupRequired capability handoffs, and credential redaction. Use before planning, approving, or executing any external write, when computing or checking a material hash, when returning a mutation receipt, or when handing a versioned artifact to another skill. | `/rhdh-mutation-gate` |
| Reads GitHub on behalf of the other RHDH skills: parse an issue or pull request reference, fetch issue detail into IssueContext/v1, resolve the plugin workspace an issue belongs to, read check status and failed workflow logs, and read repository files through the API. Use for a GitHub issue URL or bare #number, "which workspace is this issue in", a stale statusCheckRollup, "why did that check fail", gh or jq syntax for a forge read, and the exact payload behind a comment, label, assignee, or /publish write. | `/rhdh-forge` |
| Develops Red Hat Developer Hub and Backstage plugins: scaffold backend or frontend dynamic plugins, implement features, export and wire packages, upgrade Backstage dependencies, migrate legacy frontend plugins to NFS, diagnose and fix plugin bugs, and place tests at the cheapest effective layer. Use for code changes in rhdh-plugins or community-plugins, plugin creation, createFrontendPlugin or Blueprint migrations, Backstage version bumps, plugin test design, and Jira or GitHub plugin bug fixes. Hand off PR publication, overlay catalog work, or local RHDH execution to the named domain skill after producing the artifact defined below. | `/rhdh-plugin-development` |
| Manages the rhdh-plugin-export-overlays repository and Extensions Catalog: onboard plugins, update upstream versions, repair export or publish failures, inspect workspace health, triage and analyze overlay pull requests, and trigger publish checks. Use for source.json, plugins-list.yaml, backstage.json, catalog metadata, overlay CI, plugin import, overlay PRs, or testing exact PR artifacts before merge. | `/rhdh-overlay` |
| Operates a local Red Hat Developer Hub environment with the rhdh-local-setup customization system: enable or disable dynamic plugins, apply configuration, switch pristine and customized modes, start or stop containers, inspect health and logs, run plugin verification, and back up or restore customizations. Use for local RHDH, podman compose plugin testing, PR artifact verification, 504 or startup troubleshooting, and local Extensions Catalog checks. | `/rhdh-local` |
| Publishes verified changes from rhdh-plugins or community-plugins: detect the repository and affected workspaces, run the repository build pipeline, create package changesets, stage generated files safely, create a signed-off commit and branch, push, open a GitHub pull request, upload optional bug-fix recordings, and link Jira or GitHub issues. Use for raise PR, create or open a plugin PR, push verified plugin changes, or publish ChangeHandoff/v1. | `/rhdh-pr-create` |
| Reviews Red Hat Developer Hub pull requests through a composable fetch-analyze-post pipeline, with optional live-cluster verification for rhdh-operator changes. Use for a GitHub PR URL or number, code review, analysis-only review, inline comments, posting a review, testing operator PR images or bundles on a cluster, or a combined code and cluster review. | `/rhdh-pr-review` |
| Creates a Feature, Epic, Story, Task, Bug, or Spike in RHIDP/RHDHPLAN/RHDHBUGS from a conversation or a support case. Infers the type. | `/rhdh-jira-create` |
| Checks an existing issue against workflow exit criteria, duplicates, hierarchy, and sprint readiness. | `/rhdh-jira-refine` |
| Comments on, transitions, or assigns an existing issue such as RHIDP-1234. | `/rhdh-jira-update` |
| Prepares sprint planning: carryover, velocity, per-member capacity, and a ready queue. | `/rhdh-jira-sprint-plan` |
| Summarises a finished sprint: committed vs completed, per-member breakdown, demo checklist. | `/rhdh-jira-sprint-report` |
| Reads Jira by key or JQL and holds the `acli`, GraphQL, REST, and field-ID reference. | `/rhdh-jira-api` |
| Reports supported and end-of-life versions for RHDH and its deployment platforms. Use for RHDH, OpenShift, AKS, EKS, GKE, PostgreSQL, Red Hat build of Keycloak, Quay, or product lifecycle and compatibility questions. | `/rhdh-platform-lifecycle` |
| Reviews an RHDH Jira test plan against release scope, platform support, dates, coverage, ownership, and evidence. Use for test-plan review, test-day readiness, release validation coverage, or a Jira test-plan URL/key. | `/rhdh-test-plan-review` |
| Reports release readiness for a version: open issues by type and team, blocker bugs, CVEs, engineering epics, and release-note status. | `/rhdh-release-status` |
| Answers when a release milestone falls — GA, Feature Freeze, Code Freeze — for current and future versions. | `/rhdh-release-schedule` |
| Drafts a Feature Freeze or Code Freeze announcement for Slack. | `/rhdh-release-announce` |
| Looks up RHDH teams, their leads, and their Jira Cloud IDs. | `/rhdh-release-teams` |
| Exports the plugin-overlay CVE CSV for a released version. | `/rhdh-overlay-cve-export` |
| Manages OCP and AKS/EKS/GKE test entries, cluster pools, and coverage gaps in openshift/release. | `/rhdh-prow-jobs` |
| Commissions or decommissions Prow configuration for one RHDH release branch. | `/rhdh-prow-release-branch` |
| Triggers an RHDH nightly ProwJob on demand through the OpenShift CI Gangway API. | `/rhdh-prow-trigger` |
| Bumps Konflux task digests and applies Tekton `MIGRATION.md` changes to `.tekton` pipelines. | `/rhdh-konflux-tasks` |
| Analyzes and updates RHDH base images, Node or Go toolchains, and RPM lockfiles across rhdh, rhdh-operator, and rhdh-must-gather. Use for weekly base-image maintenance, UBI/RHEL bumps, RPM lockfile refreshes, or image-version skew. | `/rhdh-base-images` |
| Assess and improve a git repository's readiness for AI coding agents with agentready, including RHDH-aware single-repository and batch assessment. Use when asked to assess agent readiness, run agentready, improve an agent readiness score, prepare a repository for coding agents, or assess all RHDH repositories. | `/rhdh-agent-readiness` |
| Create, audit, and consolidate Agent Skills that follow the Agent Skills open standard. Use when creating or drafting a SKILL.md, diagnosing why a skill does not trigger, improving an existing skill, or consolidating overlapping skills into fewer deeper modules. | `/rhdh-skill-authoring` |
<!-- END GENERATED ROUTES -->

If the outcome is ambiguous, ask one question that separates the competing rows. Otherwise, state
the handoff in the conversation and invoke the selected model skill:

- **Domain** — the routing row that matched.
- **Outcome** — the observable result the user asked for.
- **Inputs** — the user's own wording, verbatim.
- **Constraints and approvals** — what the user has already ruled in or out.

This handoff stays in conversation and is not a versioned artifact. The selected model skill owns
every artifact the work produces. Do not translate a request into filesystem paths or
implementation details.

## Completion

Complete when exactly one row of the generated table has been named to the user, the handoff
repeats the request in the user's own words, and that skill has been invoked by name. When two rows
compete, the single disambiguating question must have been asked and answered first. When the
selected skill returns `SetupRequired/v1`, complete only once the missing capability and the
`/setup-rhdh-skills` branch that supplies it have been reported. This skill leaves no artifact of
its own behind.
