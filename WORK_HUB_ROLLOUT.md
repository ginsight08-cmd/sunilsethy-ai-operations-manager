# Shared work hub — Referent-inspired product expansion

Reference reviewed on 15 September 2026:
- https://referent.law/
- https://referent.law/legal-crm/
- https://referent.law/law-firm-automation-software/

These are public vendor descriptions, not independently verified product tests.
The implementation uses Generative Insight's branding and existing Streamlit app.

## Product direction

Build the shared client → work → task/document → review → billing workflow
across BPO, Manufacturing, Legal, Retail, Logistics and Healthcare. Existing
industry analysis remains available through Industry tools. The new navigation
is Shared work hub. Existing authentication and the 15-day trial gate apply.

## Implemented in this change

| Capability | Behavior |
| --- | --- |
| Client intake | Manual Lead → Qualified → Active/Archived records, contact details and source |
| Work records | Linked to clients; title, context, responsible person, due date and status |
| Tasks | Linked to work; Open/In progress/Done, deadlines and attention queue |
| Documents | HTTPS references linked to work; original provider retains access control |
| Drafts | Manual content, intended recipient and review queue |
| Approvals | Draft → Pending review → Approved/Rejected; editing requires review again |
| Time/billing prep | Manual minutes, hourly rate and separate per-currency estimates |
| Activity | Database-triggered version history; no client-side audit writes/deletes |
| Persistence | Supabase records scoped to signed-in account and industry |
| Concurrency | Updates require the last-read version; stale edits are rejected |

Approval does not send a message, file a legal document, issue an invoice or
take payment. It is the account owner's recorded decision, not a second-person
approval. Responsible-person names do not grant other users access.

## Required setup before publication

1. Apply `supabase_work_hub.sql` in the existing Supabase project's SQL Editor.
   It adds tables/triggers/policies; it does not alter existing Vakil tables.
2. Test with two separate non-production Supabase users: each must be unable to
   select, update, or link the other's records, or directly insert audit events.
3. Test client → work → task → draft → review, then reload and sign in again.
4. Verify direct API attempts to approve a new draft, edit approved content
   without returning to Draft, or overwrite a stale version are rejected.
5. Merge the app change only after migration and hosted integration checks pass.

No service-role key is used by the UI. Existing authenticated Supabase access is
reused. Do not put credentials into GitHub or project backups.

## Remaining work for end-to-end reference coverage

| Workstream | Required implementation/setup |
| --- | --- |
| Legacy records | Previewed, deduplicated import/link of Vakil clients/cases and existing BPO improvements; existing records are not automatically copied |
| Team workspaces | Organization membership, roles, invitations and independent reviewer enforcement |
| File storage | Private bucket, tenant-aware upload policy, file scanning, versions and authorized download |
| Gmail/Calendar/Drive | User-specific OAuth, scoped consent, encrypted refresh tokens, disconnect and sync workers |
| AI drafting/chat | Chosen model/provider, grounding in authorized records, source links, usage limits and prompt-injection boundaries |
| Background automation | Durable job queue, retry/idempotency, approval-bound payloads and verified provider receipts |
| Billing | Invoice numbering, line items, taxes, review/issue flow and reconciliation; no trust accounting claimed |
| Public intake | Separate authenticated/signed intake flow, spam prevention and explicit consent |
| Legal deadlines | Jurisdiction-specific reviewed rules and source evidence; current due dates are entered manually |
| Mobile/MCP | Native apps or PWA and an authenticated MCP API require separate delivery |

The current view loads the latest 500 records per industry and labels that
limit. Portfolio totals are for loaded records; the activity view shows the
latest 100 events. Global search, server pagination and larger-scale reporting
remain to be implemented before production use beyond that volume.

## Validation

`python -m unittest test_work_hub -v` exercises domain validation, billing
arithmetic, review transitions and stale-update handling. Python files compile.
These tests do not replace applying the migration and checking RLS on a real
Supabase instance. Do not call this full Referent feature parity or a completed
end-to-end integration until the remaining workstreams are implemented/tested.
