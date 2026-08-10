# Google Sheets capability

This model-invoked skill detects Google Sheets access; it does not install `gog`, start OAuth, or
repair credentials. Those human setup actions belong exclusively to `/setup-rhdh-skills`.

## Verify

```bash
python scripts/check_gsheets.py
```

Expected output:

```
✓ gog can read the RHDH schedule
```

If the check fails because the tool, authentication, or sheet access is unavailable, stop this
branch and return:

```json
{
  "contract": "SetupRequired/v1",
  "id": "google-workspace-setup-required",
  "createdAt": "YYYY-MM-DDTHH:MM:SSZ",
  "data": {
    "ownerSkill": "setup-rhdh-skills",
    "route": "google-workspace",
    "reason": "Google Sheets capability is unavailable",
    "missing": ["gog|google-auth|sheet-access"],
    "nextCommand": "/setup-rhdh-skills google-workspace"
  }
}
```

Do not reproduce login or installation instructions here. Resume only after the human runs the
setup route and this read-only check succeeds.
