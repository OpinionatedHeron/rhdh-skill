# Create Feature

Create a RHDHPLAN Feature from conversation context. Grills the user on scope, customer value, and acceptance criteria before creating. Optionally chains into Epic decomposition.

## Workflow

### Step 0 — Grilling prerequisite

Load `references/grill.md` → Grilling prerequisite and Validate before creating. Hard-require grilling before create. Also load `references/sizing.md` and `references/fields.md` before the grill.

### Step 1 — Draft from Context

Load `assets/templates/feature.txt` for structure and `assets/examples/feature-example.txt` for tone calibration. Apply **synthesize, then grill gaps** from `references/work-breakdown.md`: fill from conversation first; do not re-ask settled topics.

Draft as many template sections as possible from existing context:

- Feature Overview, Goals, AC, Out of Scope, Customer Considerations, Documentation, Upstream engagement

Fold settled **implementation / testing decisions** from the chat into AC or Out of Scope (or note them for a comment after create) so they are not lost. Keep the RHDH Feature template — do not switch to a generic PRD.

When drafting **Customer Considerations**, one-line check against `references/fields.md`: use support case key / persona / use case only — no customer names.

Present the draft: "Based on our conversation, here's what I have so far. Review and tell me what's missing or wrong."

### Step 2 — Fill Gaps + Challenge

Invoke the installed skill named `grilling` once for Fill Gaps + Challenge. Do
not locate its files or re-implement its cadence. Apply the RHDH domain
challenges from `references/grill.md` to the completed draft.

For any template sections the agent couldn't fill from context, ask targeted questions:

1. **Feature Overview** — what is this? Elevator pitch.
2. **Goals** — what does the user get? Which persona benefits?
3. **Requirements / Acceptance Criteria** — what must be true for this to be complete? Include non-functional requirements.
4. **Out of Scope** — what is explicitly NOT included?
5. **Customer Considerations** — support case key / persona / use case — no customer names; see `references/fields.md`
6. **Documentation Considerations** — what docs need creating/updating?
7. **Upstream engagement** — does this need Backstage community alignment?

Skip questions the draft already answered well.

### Step 3 — Infer Fields

Infer all Jira fields from the conversation per the Field Inference section in `references/grill.md`. Present recommendations for confirmation.

Key fields for Features: Priority, Team, Size (T-shirt), Assignee (Feature Owner), Components, and Labels.

**Components:** Infer likely components from the feature description. Validate them against the project's component list per `references/feature-exploration.md` → Component Validation. Confirm with the user.

**Labels — ask about each during the grill:**

| Label | Question |
|-------|----------|
| `demo` | Does this feature need a customer-facing demo? |
| `rhdh-testday` | Should this feature be tested during release test day? |
| `rhdh-X.Y-candidate` | Which release does this target? |
| `stretch` | Is this a stretch goal? |
| `RHDH-Customer` | Did this originate from a support case or customer engagement? If yes, apply a single `RHDH-Customer` label (never also `rhdh-customer`). |

**Customer identity (before create):** Prefer support key in summary/description; apply `RHDH-Customer` as a Jira label; put customer-identifying detail only in restricted-visibility comments. See `references/fields.md`.

**Documentation:** If the feature involves documentation, set the `Documentation` component. After creation, prompt: "Create a Doc EPIC from this Feature? (Feature → More → Create Doc EPIC from RHDHPlan)"

**Cross-team dependencies:** Ask if other scrum teams are affected. If yes, note them — they become Epics in Step 8.

### Step 4 — Review

Render the filled template and inferred fields as a temporary markdown file for user review. Use a portable temp path (`$TMPDIR` / `%TEMP%` / Python `tempfile`):

```bash
REVIEW=$(mktemp "${TMPDIR:-/tmp}/feature-review.XXXXXX.md")  # Windows: %TEMP%\feature-review.md or tempfile
cat > "$REVIEW" << 'EOF'
## Feature: {summary}

### Description
{filled template content}

### Fields
- **Priority**: {value} — {rationale}
- **Team**: {value}
- **Size**: {value} — {rationale}
- **Assignee**: {value}
- **Labels**: {values}
EOF
```

Present to the user: "Review the Feature before creating. Edit the file or tell me what to change. [approve / edit / cancel]"

- **approve** — proceed to duplicate check and creation
- **edit** — user modifies the file or provides changes verbally, agent updates
- **cancel** — abort creation

### Step 5 — Duplicate Check and Feature Request Link

Before creating, run the pre-creation check from `references/duplicates.md` using the proposed summary. Search RHDHPLAN Features specifically (`issuetype = Feature`).

Also search for accepted Feature Requests that this Feature may originate from:

```bash
jql: "project = RHDHPLAN AND issuetype = 'Feature Request' AND status = Accepted AND summary ~ \"KEYWORD1 KEYWORD2\""
```

If a matching Feature Request is found: "Found accepted Feature Request {KEY}: {summary}. Link this Feature to it?" If yes, add a `Related` issue link after creation.

If a likely duplicate Feature is found, present it and ask: "This may already exist as {KEY}: {summary}. Use the existing issue instead?"

### Step 6 — Create Feature

Before create: re-check customer identity + label rules per `references/grill.md` → Validate before creating. Strip customer names from summary/description if present; ensure at most one `RHDH-Customer` label.

Fill the template with grill results. Save to a temp file. Then convert to ADF using the helper script (see Gotcha #6). `acli create` accepts ADF via `--description-file`:

```bash
FEATURE_ADF=$(mktemp)  # on Windows: use %TEMP% or Python tempfile
python scripts/jira-wiki-to-adf.py feature-filled.txt "$FEATURE_ADF"
```

Create the issue — note `--priority` and `--yes` do not exist on `create` (see Gotcha #18):

```bash
acli jira workitem create --project RHDHPLAN --type Feature \
  --summary "Feature summary" \
  --description-file "$FEATURE_ADF" \
  --assignee "ACCOUNT_ID" \
  --label "rhdh-2.1-candidate"
```

Then set priority, Team, and Size through the authenticated host adapter. Include this redacted
payload in the approved mutation plan:

```json
{
  "fields": {
    "priority": {"name": "Major"},
    "customfield_10795": {"value": "M"}
  }
}
```

Set Team via REST — follow API preference order in SKILL.md.

### Step 7 — Comments

Follow the comment suggestion behavior from `references/grill.md` — proactively suggest decision trail, elaboration, and abandoned paths as comments.

Add each approved comment via:

```bash
acli jira workitem comment --key RHDHPLAN-XXX --comment "comment text" --yes
```

### Step 8 — Chain Decomposition

After the Feature is created:

> "Break this Feature into Epics? The RHDH process typically creates Epics per team (Eng, QE, Doc). [y/N]"

If yes, load `references/work-breakdown.md` and:

1. Ask: "Which teams are involved?" Default suggestion: Eng + Doc (QE is often covered within the Eng epic).
2. Propose the Epic batch **before creating any** (see `to-epic.md` Batch Review). For each Epic, state **blocking edges** (which other Epics must land first) and a team-scoped outcome — not a horizontal tech layer.
3. Quiz granularity / blockers / merge-split per `work-breakdown.md` → Quiz before create. Only then create.
4. For each approved Epic, invoke the `to-epic` workflow with context carried down:
   - Feature scope, AC, and customer considerations are established — don't re-grill on these
   - Epic grill narrows to: delivery scope for *this team*, dependencies, team-specific AC
5. Each Epic is linked to the parent Feature via `customfield_10018` (cross-project parent link — see Gotcha #16 and to-epic.md Step 7)

## Error Handling

| Error | Action |
|-------|--------|
| RHDHPLAN project inaccessible | Stop. User lacks project access. |
| `acli create` fails | Fall back to REST API. See SKILL.md Error Handling. |
| Duplicate check finds match | Present match. If user confirms duplicate, open existing issue instead. |
| Team field update fails via acli | Fall back to REST. See `references/rest-api-fallback.md`. |

## Caveats

1. **Feature Owner responsibility.** Creating a Feature implies ownership. Ensure the assignee understands the Feature Owner responsibilities (single point of contact, coordinates cross-team dependencies, ensures sizing and labels).
2. **Candidate label convention.** The label format is `rhdh-X.Y-candidate` (e.g., `rhdh-2.1-candidate`). Ask which release this targets during the grill. **Do not remove candidate labels without PM approval.**
3. **Description stays structured.** Only template sections go in the description. Decision trail, elaboration, abandoned approaches, and customer-identifying detail go in comments (restricted visibility when needed). Prefer support key in summary/description; apply `RHDH-Customer` as a Jira label — see `references/fields.md`.
4. **Rescoping.** If the feature is too large for a single release, suggest splitting. Document what's deferred and why as a comment. Adjust the candidate label if the target release changes. See `references/feature-exploration.md` → Rescoping.
5. **Feature Exploration checklist.** After creation, the Feature should pass the full checklist in `references/feature-exploration.md` before moving to Backlog.
