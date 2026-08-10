# RHDH Skills

Ubiquitous language for the Red Hat Developer Hub skill collection and the
plugin, release, and repository work it supports.

## Language

### Skill architecture

**Promoted skill**:
A public Agent Skill included in the repository catalog and complete
distribution. It is either human-invoked or model-invoked.
_Avoid_: public module, top-level skill

**Human-invoked skill**:
A user-selected entry point that orients or configures the collection. It is
never selected automatically and never invoked by another skill.
_Avoid_: model router, orchestrator

**Model-invoked skill**:
A task-oriented capability that an agent may select automatically or another
model-invoked skill may invoke by name.
_Avoid_: sub-skill, leaf skill

**Editorial category**:
A reader-facing grouping of promoted skills. It is not a namespace, dependency
boundary, or composition path.
_Avoid_: package, subsystem

**Named skill composition**:
Composition in which a model-invoked skill calls another model-invoked skill by
its stable name and exchanges a declared artifact contract.
_Avoid_: sibling load, relative-path composition

**Artifact contract**:
A versioned, credential-free handoff between skills. The contract identifies
the meaning and required data independently of any category or filesystem path.
_Avoid_: shared file, prompt blob

**Mutation plan**:
The complete proposed external changes bound to a material hash and presented
for human approval before execution.
_Avoid_: confirmation prompt, dry run

**Mutation receipt**:
The one-to-one ordered record of every completed, failed, or skipped operation
in an approved mutation plan, tied to its plan ID and material hash.
_Avoid_: success message, command output

**Setup capability**:
A prerequisite such as an installed skill, repository location, tool, or
authenticated external service that is diagnosed and configured through the
human setup entry point.
_Avoid_: hidden prerequisite, skill-local setup

**Authenticated adapter**:
A capability module backed by a native CLI credential store or host connector.
It owns transient credential retrieval, request authentication, and redaction;
the calling workflow sees only credential-free inputs and outputs.
_Avoid_: token file, auth shell variable, raw authenticated fallback

### Plugin overlays

**Workspace**:
The unit of overlay ownership and configuration for one upstream Backstage
plugin.
_Avoid_: project, package, module

**Overlay**:
The RHDH-specific export and build definition applied to an upstream Backstage
plugin. It is not a filesystem or CSS overlay.
_Avoid_: wrapper, shim, adapter

**Publish trigger**:
A `/publish` request that starts the overlay validation and build workflow for a
change request.

**Plugin Owner**:
An external contributor or team responsible for its own plugins and Workspaces.
_Avoid_: contributor, maintainer

**Core Team**:
The COPE/Plugins team responsible for repository-wide triage, merge decisions,
and infrastructure.
_Avoid_: maintainers, admins

### Support tiers

**Supported**:
A generally available plugin fully supported by Red Hat. Its Workspace changes
receive the highest triage priority.

**Tech Preview**:
A productized plugin available as a technology preview. Its Workspace changes
receive high triage priority.

**Community**:
A development-preview or community-maintained plugin. Its Workspace changes
receive lower triage priority.
_Avoid_: mandatory workspace, non-mandatory workspace
