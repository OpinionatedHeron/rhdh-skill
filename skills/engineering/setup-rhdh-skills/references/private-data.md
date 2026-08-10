# Configure the private-data checkout

The internal repository contains Jira Rich Filter exports used for release coordination.

1. Clone it into a user-selected workspace:

   ```bash
   git clone git@gitlab.cee.redhat.com:rhidp/rhdh-skill-private-data.git
   ```

2. Register the resolved checkout through the preserved CLI contract:

   ```bash
   rhdh config set private-data <absolute-checkout-path>
   ```

3. Verify that `jira-rich-filter/rhidp-operational-rich-filter.json` exists.
4. Record the repository path and verification result in `SetupReceipt/v1`.

Repository contents may be private. Keep them outside skill artifacts and conversation unless a
workflow explicitly needs a bounded derived result.
