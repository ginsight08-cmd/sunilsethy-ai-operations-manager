# Three dedicated products

Status: code prepared; new apps, databases, website links and DNS are NOT provisioned by this change.

| Product | Streamlit entry point | Proposed branded address (not live) |
| --- | --- | --- |
| BPO AI Operations Manager | bpo_app.py | bpo.generativeinsight.in |
| AI Procurement | procurement_app.py | procurement.generativeinsight.in |
| AI Vakil | vakil_app.py | vakil.generativeinsight.in |

Each entry point fixes the industry on the server and hides industry switching. Existing app.py remains the legacy deployment until a deliberate cutover. The three products share code but MUST use three different Supabase projects. Accounts, passwords, sessions, quotas, subscription configuration and data belong to the individual project. Reusing an email in another product requires a new registration there. Never use user metadata or URL parameters as the security boundary.

## Provisioning and cutover

1. Obtain approval for the hosting cost first. Supabase Free supports two active projects; three independent projects may require a paid plan. Do not upgrade automatically.
2. Create three projects, or explicitly choose which product retains the existing mixed-industry project. Do not automatically migrate existing users or data. Back up and review industry ownership before any migration; the existing project contains mixed-industry records.
3. Install the existing schema files in dependency order: supabase_vakil_schema.sql, supabase_work_hub.sql, supabase_trial_limits.sql, supabase_owner_admin.sql, then fix_owner_audit.sql. Follow OWNER_ADMIN_ROLLOUT.md for owner enrollment. Verify migrations against each new project's SQL editor before onboarding users.
4. Create three Streamlit deployments with the entry points above. Each gets its own project URL, anonymous key and service-role key through private Streamlit secrets. Never put credentials in GitHub. Keep the same PRODUCT_PROJECTS map in all three deployments. The app refuses mismatched or duplicate project bindings.
5. Set PRODUCT_ID to bpo, procurement or vakil. Set APP_PUBLIC_URL to the actual HTTPS app address. Example non-secret settings:

```toml
PRODUCT_ID = "bpo"
APP_PUBLIC_URL = "https://YOUR-ACTUAL-BPO-APP.streamlit.app/"
SUPABASE_URL = "https://YOUR-BPO-PROJECT-REF.supabase.co"
# Add SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY privately.
[PRODUCT_PROJECTS]
bpo = "YOUR-BPO-PROJECT-REF"
procurement = "YOUR-PROCUREMENT-PROJECT-REF"
vakil = "YOUR-VAKIL-PROJECT-REF"
```

6. In EACH Supabase project's Authentication / URL Configuration set Site URL to that app's actual HTTPS URL, and allow that same redirect URL. Signup now explicitly passes APP_PUBLIC_URL. This also repairs the legacy confirmation flow when its Site URL and redirect allowlist are corrected; code alone cannot fix a localhost Site URL. Test a new email confirmation followed by sign-in. Do not log or copy confirmation tokens.
7. Set up billing/webhooks separately for each product and verify that payment or credits in one product never enable another. Preserve 3 trial days, 5 analyses and 5 MB uploads; PDF remains available. Verify owner rights on the server in each project.
8. Streamlit Community Cloud supplies streamlit.app addresses. Do not point arbitrary GoDaddy CNAME records at them and assume custom-domain HTTPS works. Either add website buttons linking directly to the three actual Streamlit URLs, configure supported HTTPS redirects for the branded subdomains, or use a host that explicitly supports custom domains. Confirm whether Wix still hosts the main website before editing it. Preserve existing mail/DNS records.
9. Before public cutover, test signup/confirmation/login/signout, wrong-product credentials and tokens, owner/non-owner visibility, trial limits, subscription changes, uploads, reports and mobile navigation for all three apps. Use authorized test accounts. No live isolation claim is justified until these tests pass.

## BPO reporting

Performance Trends adds date/team filters, daily/weekly/monthly summaries, latest-period comparisons, four interactive target charts, team bars and underlying summary tables. Weeks end on Sunday. Missing dates are excluded with a notice; no fake history is generated. Productivity is a ratio of valid production/target totals; quality, SLA and AHT are record means, not weighted rates. AHT uses its original units. Partial-period comparisons require care. This is operational reporting, not Power BI feature parity or a newly trained prediction model.

## Validation

Run `python -m unittest test_product_reporting.py` from the source folder. It checks project guards, aggregation and Streamlit chart/filter rendering. Compile all changed Python files. Cloud authentication, billing, email and DNS require the provisioning checks above.
