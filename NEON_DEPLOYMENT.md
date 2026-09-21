# Three dedicated products — free Neon setup

Status: three empty Neon projects exist. Streamlit integration is prepared with local tests passing. Live migrations, authentication, billing, owner enrollment and deployment still require verification. No legacy customer data has been copied.

| Product | Entry point | Neon project | Proposed address (not live) |
| --- | --- | --- | --- |
| BPO | bpo_app.py | odd-recipe-47389871 | bpo.generativeinsight.in |
| Procurement | procurement_app.py | rough-grass-93764524 | procurement.generativeinsight.in |
| AI Vakil | vakil_app.py | purple-thunder-86058443 | vakil.generativeinsight.in |

All three projects were created in AWS Singapore on Free with Better Auth enabled. Budget is strictly ₹0: do not upgrade, activate paid services or change the existing app automatically. Existing app.py continues to use Supabase; dedicated entry points use Neon.

## Deployment

1. Run neon_app_schema.sql once in each NEW Neon database, replacing PRODUCT_NAME with bpo, procurement or vakil respectively. Never run it in Supabase. This atomic transaction deliberately refuses repeated installation. Existing constraints, owner checks, audit triggers and row-level policies are retained. Every connection checks the database's product marker.
2. Deploy three Streamlit apps. Store each project's connection privately in Streamlit secrets, never GitHub. Set PRODUCT_ID, NEON_AUTH_URL, NEON_DATABASE_URL and APP_PUBLIC_URL. PRODUCT_PROJECTS must contain the three distinct IDs above under bpo, procurement and vakil. Auth and database URLs must use the same Neon endpoint. Connections require certificate-verified TLS.
3. Add each actual HTTPS app URL to that project's Better Auth trusted origins and redirect settings. Enable email/password sign-in and email verification. Signup redirects to APP_PUBLIC_URL; app access requires a verified email and online session validation. Cookies remain within one Streamlit user session. Sign-out clears them even if the provider fails.
4. Register and verify the owner separately in each app. After verifying the identity, enroll the matching gi_auth.users ID in app_owners through a reviewed database action. Never grant ownership based on submitted email or editable metadata.
5. Configure billing independently. Payment in one app must never unlock another. Preserve 3 trial days, 5 analyses, 5 MB uploads and PDF reports. Trial profiles start from the authentication provider's creation timestamp, not first login.
6. Verify live signup, confirmation, login, revocation, sign-out, owner/non-owner views, suspension, concurrent quota use, same-email registration across apps, records, reports and mobile navigation. Unit tests do not establish live deployment correctness.
7. Link actual app URLs from the website. Streamlit supplies streamlit.app addresses; arbitrary GoDaddy CNAME records do not establish supported custom-domain HTTPS. Use website buttons or supported HTTPS redirects unless a free custom-domain host is verified. Preserve mail/DNS records. Confirm whether Wix still hosts the website.

## Security boundary

NeonClient is scoped to st.session_state. It checks the verified Better Auth session online before private requests. Ordinary database operations use a non-login PostgreSQL role and row-level policies, parameterized values and table/operation allowlists. The private database connection performs profile synchronization and existing server-verified billing updates. Provider errors and database URLs are redacted. Do not expose gi_auth or owner/trial tables via a public Data API.

## Validation

Install requirements and run `python -m unittest test_neon_backend.py test_product_reporting.py`. Sixteen local tests passed: identity validation, unverified/revoked identities, isolated cookie jars, signup without automatic access, cross-account rejection, parameter binding, allowlists, error redaction, logout cleanup, product guards and reporting. Live SQL and end-to-end auth must pass before publication. Windows may report temporary-directory cleanup warnings after successful tests.
