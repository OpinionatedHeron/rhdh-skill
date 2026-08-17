# Decommission RHDH Release Branch Jobs

Remove all CI configuration for a given RHDH release branch when it reaches end-of-life. Requires a local `openshift/release` checkout.

Read `../references/release-branch-config.md` for file paths and templates.

## Steps

1. **Get the release version**:
   - If not provided, list existing configs: `ls ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-*.yaml`

2. **Verify files to be removed** (show the user and ask for confirmation):
   - **CI config**: `ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}.yaml`
   - **Generated jobs** (removed by `make update`): `ci-operator/jobs/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}-*.yaml`
   - **Branch protection**: `release-{version}:` block in `core-services/prow/02_config/redhat-developer/rhdh/_prowconfig.yaml`

3. **Delete the CI config file**

4. **Remove branch protection configuration**:
   Edit `_prowconfig.yaml` to remove the entire `release-{version}:` block under `branch-protection.orgs.redhat-developer.repos.rhdh.branches`. Be careful to:
   - Only remove the block for the specified version
   - Preserve indentation and formatting of surrounding blocks
   - Not leave blank lines where the block was removed

5. **Run `make update`** to regenerate Prow job configs (this also removes the generated job files for the deleted config)

6. **Confirm completion**: Summarize what was removed

7. **Author the pull request**:
   - Use a direct title such as `ci: remove RHDH {version} release branch jobs`.
   - In the body, name the removed config, generated jobs, and branch-protection
     block. Include `make update` in the test plan and state the recovery path.
   - Invoke `/prose-editing` once on the completed title and body in the
     **flavored** register. Preserve paths, job names, contexts, versions,
     commands, and checklist state.
   - Show the edited title and body in `/mutation-gate`, then open the PR only
     after approval. The forge command only transports the approved strings.

## Important Notes

- This operation is destructive -- always confirm with the user before proceeding
- Always verify files exist before attempting deletion
