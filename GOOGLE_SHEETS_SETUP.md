# Google Sheets integration

The app uses Google Identity Services popup authorization code flow and the Sheets read-only scope. Customers supply a spreadsheet URL and choose a worksheet. This does not list all Drive files or write to spreadsheets.

## Owner configuration

1. Use the dedicated Google Cloud project `generative-insight-sheets` and enable the Google Sheets API.
2. Configure Google Auth Platform branding, support/developer email, audience and the `https://www.googleapis.com/auth/spreadsheets.readonly` data-access scope.
3. Create a Web application OAuth client. Add the app origins to Authorized JavaScript origins, with no trailing slash: `https://generative-insight-bpo.streamlit.app`, `https://generative-insight-procurement.streamlit.app`, and `https://generative-insight-vakil.streamlit.app` if enabled there. Popup code exchange uses the origin as redirect URI.
4. Keep the Google client secret in Streamlit Secrets, never in this repository. Set `GOOGLE_SHEETS_CLIENT_ID`, `GOOGLE_SHEETS_CLIENT_SECRET` and `GOOGLE_SHEETS_ORIGIN` (the matching origin of that app).
5. While the Google app is in Testing, explicitly add authorized test users. Complete Google's required review before advertising public availability; sensitive-scope access is subject to Google verification.

## Connection lifecycle

Authorization codes are single-use and tied to the authenticated Streamlit session through a random, expiring nonce. The browser component accepts messages only from its parent origin. Token exchange happens on the server. The OAuth client secret never enters the component. Access tokens live only in the current server session and are cleared on sign-out, user change, disconnect or expiry. Refresh tokens are not persisted. Users must reconnect after session expiry or a server restart. Background syncing is not implemented.

Import buttons fetch only the selected workbook/worksheet from fixed Google API endpoints. Arbitrary fetch URLs are rejected. Data is converted into the existing upload interface, retaining upload-size and trial-analysis enforcement. Refreshing unchanged data is subject to existing idempotent analysis admission. A changed dataset can consume another analysis credit. Connection failures are redacted and do not log tokens or raw provider responses.

First row: unique column headers. Date cells: use YYYY-MM-DD formatting. The initial import supports at most 10,000 grid rows and 100 grid columns; unused excess grid rows/columns must be removed or a smaller reporting worksheet used. Imports exceeding the plan size limit fail rather than truncate.

Before rollout, verify: Google consent popup on the actual deployed origin; cancel/deny handling; expired authorization; worksheet selection; read-only import; repeat/changed refresh and trial usage; sign-out/user isolation; disconnect/revocation; oversized and malformed sheet errors. Unit checks alone do not verify OAuth approval or browser popup compatibility.
