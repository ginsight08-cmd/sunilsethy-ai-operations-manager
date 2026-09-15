# Owner access console

Uses the existing app login. A database-owned UUID allowlist authorizes every
console RPC; user-editable profile metadata never grants ownership. No owners
are enrolled by the migration. Enrollment must target one verified Auth account
and be approved separately. Never place service credentials in the frontend.

The console changes trial defaults for future signups, extends a customer's
expiry from the later of now/current expiry, adds credits, and suspends app
access. All mutations record actor, target, reason (account changes), and
before/after values. Latest 200 accounts and 100 audit entries are displayed;
exact-email search finds older accounts. Owner access cannot be edited here.

Suspension is an application gate checked on every rerun, not a Supabase Auth
ban or session revocation. It also denies trial analysis admission. It does not
revoke direct access under existing workspace-table RLS policies. This console
does not manage passwords, payments, billing entitlements or customer documents.

Apply supabase_owner_admin.sql once before deploying app.py and owner_admin.py.
Existing accounts retain their current three-day expiry and five-analysis limit.
Do not rerun this one-time migration; use a new migration for future changes.
The public signup offer reads database defaults. A settings/access lookup failure
blocks app access with a retry/signout message rather than assuming permission.

Owner identity enrollment and a real signed-in owner smoke test are required
before claiming the console is ready for the owner. SQL role tests do not replace
browser authentication testing. Use MFA on the owner's Auth account when available.
