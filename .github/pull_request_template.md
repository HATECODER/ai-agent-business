## Change

Describe what changed and why.

## Security review

- [ ] `scripts/security_gate.ps1` passed, or this is a documentation-only change reviewed in CI.
- [ ] No secret, real customer data, database, backup, token, or private key was added.
- [ ] Inputs, outputs, errors, logs, and permissions were reviewed for the changed path.
- [ ] New/changed writes remain validated, authorized, auditable, and idempotent where retry is possible.
- [ ] Auth, tenant scope, upload, connector, export, external action, finance, HR, or deletion changes include relevant negative tests and a threat-model update.
- [ ] New dependencies, endpoints, scopes, model data, or external services are listed below.
- [ ] Future-stage controls stay disabled when their gate in `SECURITY_REQUIREMENTS.md` is incomplete.

Security-relevant dependencies/scopes/data flows, or `None`:

## Verification

List commands and results. Do not paste secrets or real customer data.
