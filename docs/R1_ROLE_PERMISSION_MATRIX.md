# R1 Role and Permission Matrix

**Status:** Accepted by the Project Owner on 2026-10-08
**Decision record:** [0002-commercial-r1-foundation.md](decisions/0002-commercial-r1-foundation.md)

## 1. Enforcement rules

1. Managed identity authenticates the user; BizPilot memberships and permissions authorize the request.
2. Every request has one verified active tenant. Membership in Tenant A grants nothing in Tenant B.
3. The API, workers, exports, files, caches, AI tools, and approval execution all enforce the same permission identifiers.
4. UI visibility is not a security control.
5. Permissions default to deny. New permissions are granted to no role until reviewed.
6. Role changes and removals take effect for new requests and invalidate incompatible pending approvals.
7. Platform roles and merchant roles cannot be combined in one authority context.

Legend: `âœ“` allowed, `Own` assigned/created records only, `Scoped` only the role's domain and policy, `â€”` denied.

## 2. Merchant roles

| Capability / permission | Owner | Admin | Operations | Growth | Finance Viewer | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Open workspace and use permitted dashboard | âœ“ | âœ“ | âœ“ | âœ“ | âœ“ | âœ“ |
| `workspace.read` | âœ“ | âœ“ | âœ“ | âœ“ | âœ“ | âœ“ |
| `workspace.update` | âœ“ | âœ“ | â€” | â€” | â€” | â€” |
| Transfer ownership / close workspace | âœ“ | â€” | â€” | â€” | â€” | â€” |
| `members.read` | âœ“ | âœ“ | â€” | â€” | â€” | â€” |
| `members.invite` / suspend / remove | âœ“ | âœ“ | â€” | â€” | â€” | â€” |
| Assign Owner role | âœ“ | â€” | â€” | â€” | â€” | â€” |
| Assign non-owner R1 roles | âœ“ | âœ“ | â€” | â€” | â€” | â€” |
| `billing.read` | âœ“ | â€” | â€” | â€” | â€” | â€” |
| `billing.manage` | âœ“ | â€” | â€” | â€” | â€” | â€” |
| `connections.read` | âœ“ | âœ“ | Scoped | Scoped | â€” | â€” |
| `connections.manage` | âœ“ | âœ“ | â€” | â€” | â€” | â€” |
| `products.read` | âœ“ | âœ“ | âœ“ | âœ“ | â€” | âœ“ |
| `products.manage` | âœ“ | âœ“ | âœ“ | â€” | â€” | â€” |
| `inventory.read` | âœ“ | âœ“ | âœ“ | âœ“ | â€” | âœ“ |
| `inventory.adjust` | âœ“ | âœ“ | âœ“ | â€” | â€” | â€” |
| `inventory.import` | âœ“ | âœ“ | âœ“ | â€” | â€” | â€” |
| `inventory.export` | âœ“ | âœ“ | âœ“ | â€” | â€” | â€” |
| `tasks.read` | âœ“ | âœ“ | âœ“ | Own | â€” | âœ“ |
| `tasks.manage` | âœ“ | âœ“ | âœ“ | Own | â€” | â€” |
| `customers.segment.read` | âœ“ | âœ“ | â€” | âœ“ | â€” | â€” |
| `customers.detail.read` | âœ“ | âœ“ | â€” | Scoped | â€” | â€” |
| `customers.export` | âœ“ | â€” | â€” | â€” | â€” | â€” |
| `campaigns.read` | âœ“ | âœ“ | â€” | âœ“ | â€” | âœ“ |
| `campaigns.draft` | âœ“ | âœ“ | â€” | âœ“ | â€” | â€” |
| Send/publish campaign | Disabled in R1 | Disabled | Disabled | Disabled | Disabled | Disabled |
| `finance.summary.read` | âœ“ | âœ“ | â€” | â€” | âœ“ | â€” |
| `finance.export` | âœ“ | â€” | â€” | â€” | âœ“ | â€” |
| Refund/payout/payment action | Disabled in R1 | Disabled | Disabled | Disabled | Disabled | Disabled |
| `approvals.read` | âœ“ | âœ“ | Scoped | Scoped | â€” | â€” |
| Approve internal inventory/task proposal | âœ“ | âœ“ | Scoped | â€” | â€” | â€” |
| Approve campaign draft | âœ“ | âœ“ | â€” | Scoped | â€” | â€” |
| Approve external/high-risk action | Disabled in R1 | Disabled | Disabled | Disabled | Disabled | Disabled |
| `audit.read` | âœ“ | âœ“ | Scoped | Scoped | â€” | â€” |
| `audit.export` | âœ“ | â€” | â€” | â€” | â€” | â€” |
| `copilot.use` | âœ“ | âœ“ | Scoped | Scoped | Scoped | Read-only |
| AI usage/budget settings | âœ“ | âœ“ | â€” | â€” | â€” | â€” |

### Scope rules

- Operations can approve only internal inventory/task proposals that require `inventory.adjust`, `inventory.import`, or `tasks.manage`; it cannot approve its own future high-risk/external action.
- Growth can approve only unsent campaign drafts. Recipient selection or sending is not enabled in R1.
- Finance Viewer receives deterministic summaries and approved exports only. Copilot tool access is limited to the same finance-read permissions.
- Viewer cannot create a proposal or invoke a mutating tool.
- Admin cannot transfer ownership, close the workspace, manage platform billing identity, export all customers, or use future high-risk actions unless a later decision explicitly grants it.

## 3. Platform roles

| Capability | Platform Owner | Platform Operator | Support Agent | Security Responder |
|---|:---:|:---:|:---:|:---:|
| Platform configuration and staff roles | âœ“ | â€” | â€” | â€” |
| Tenant identity/status/plan metadata | âœ“ | âœ“ | âœ“ | Scoped |
| Aggregate service health and usage | âœ“ | âœ“ | âœ“ | âœ“ |
| Connection/job failure metadata | âœ“ | âœ“ | âœ“ | Scoped |
| Merchant business records by default | â€” | â€” | â€” | â€” |
| View secrets/plain connector tokens | â€” | â€” | â€” | â€” |
| Tenant data access request | Approve | Request | Request | Emergency request |
| Time-limited approved tenant view | Scoped | Scoped | Scoped | Scoped |
| Mutate merchant business data | â€” | â€” | â€” | â€” |
| Suspend tenant access | âœ“ | Scoped | â€” | Incident scope |
| Revoke sessions/credentials | âœ“ | Scoped | â€” | âœ“ |
| View protected security audit | âœ“ | Scoped | â€” | âœ“ |
| Change billing configuration | âœ“ | â€” | â€” | â€” |

R1 does not implement silent impersonation. A support session requires tenant, ticket, reason, requested scope, approver, start, expiry, visible merchant-facing audit, and a banner while active. Support actions cannot approve merchant proposals or modify merchant business data.

## 4. Service identities

| Identity | Allowed | Denied |
|---|---|---|
| API runtime | Tenant-scoped application queries through restricted DB role | Schema changes, backup access, RLS bypass |
| Worker runtime | Claimed tenant-scoped jobs and approved connector calls | Arbitrary tenant selection, migrations, support access |
| Migration job | Reviewed schema migrations under deployment lock | Normal web requests, model calls, merchant workflows |
| Connector worker | Decrypt only required connection secret and call its scoped provider | General secret enumeration, browser exposure, model context |
| Backup operator | Encrypted backup/restore workflow | Normal application reads and writes |
| CI test job | Synthetic test data and read-only repository token | Production secrets, production database, deployment unless protected environment approves |

## 5. Approval rules

An approval is valid only when all are true:

- proposal tenant matches active tenant;
- approver currently has the action-specific permission;
- proposal is pending, unexpired, and not revoked;
- normalized payload hash is unchanged;
- relevant source/config/policy version has not invalidated it;
- any required separation-of-duty rule is satisfied;
- idempotency key has not already completed a different execution.

If any condition fails, execution stops and a new proposal is required.

## 6. Required tests before implementation is accepted

- each role receives exactly its allowed API/tool set;
- hidden buttons cannot be invoked directly through the API;
- active-tenant switching changes scope and cannot reuse Tenant A IDs in Tenant B;
- removed/suspended membership loses read, write, export, job, and approval access;
- Operations/Growth scoped approvals cannot cross domains;
- Finance Viewer cannot reach customer detail, campaign, inventory write, refund, or payment paths;
- Platform Support sees no merchant records without an approved support session;
- support-session expiry and revocation take effect immediately for new requests;
- worker/service identities cannot bypass RLS or claim arbitrary tenants;
- all denied attempts return sanitized errors and create appropriate security telemetry without leaking the target record.
