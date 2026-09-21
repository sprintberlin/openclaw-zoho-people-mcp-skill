# Known Limitations & Quirks in Zoho People MCP

Documented gaps and operational quirks in Zoho People MCP and API. Use this reference when an operation fails unexpectedly or an expected action is missing.

## 1. Missing Balance Adjustment in MCP

- **Issue:** Zoho People MCP exports no Action to modify an employee's leave balance (`customize-balance` or `addBalance` do not exist in the 369-Action catalog).
- **Impact:** You cannot adjust or override leave balances via MCP.
- **Workaround:**
  1. **UI:** *Leave Tracker ➔ Settings ➔ Customize Balance* (Admin).
  2. **Direct REST API fallback:** Use `scripts/customize_leave_balance.py` with Self-Client OAuth.

## 2. Empty Date of Joining (`Dateofjoining`)

- **Issue:** If `Dateofjoining` is empty in the employee record, Zoho People does not calculate leave accruals and hides prorated leave types (e.g. Vacation). Only non-accrual types like *Compensatory Off* appear.
- **Resolution:** Update `Dateofjoining` via `updateRecord` on the `employee` form (`dd-MMM-yyyy`, e.g. `07-Sep-2026`). Leave types and prorated balances become visible immediately.

## 3. Leave Balance Report Permissions

- **Issue:** `getLeaveBalance` can return *Permission Denied* even if the MCP user has admin access.
- **Resolution:** The user account linked to the MCP connection requires explicit reporting permissions in Zoho People Leave Tracker settings, or balance reading must be done via direct API.

## 4. Zia Requirement (`MCP_DISABLED`)

- **Issue:** If Zia is disabled in the Zoho People organization, all MCP actions fail with `MCP_DISABLED`.
- **Resolution:** In Zoho People: *Settings (gear) ➔ Manage Accounts ➔ Organization ➔ Enable Zia*.

## 5. Direct REST API Fallback

For operations not supported by MCP, use the direct REST API with standard OAuth:
- Environment variables: `ZOHO_PEOPLE_CLIENT_ID`, `ZOHO_PEOPLE_CLIENT_SECRET`, `ZOHO_PEOPLE_REFRESH_TOKEN`, `ZOHO_PEOPLE_DC` (default: `eu`).
- Cached access tokens in `~/.cache/zoho-people-api/tokens.json` (mode 0600).
- Scripts: `scripts/people_api.py` (OAuth + generic REST) and `scripts/customize_leave_balance.py` (dry run by default; `--apply` writes).
- Scope: `ZOHOPEOPLE.leave.CREATE,ZOHOPEOPLE.leave.READ` (write plus verification).
- Customize-balance uses `/people/api/v2/...`, query parameters, and `dateFormat` (not `dataFormat`). `newBalance` is the total entitlement; verification checks `available + taken`.
- One-time setup: create a **Self Client** in the Zoho API Console (`api-console.zoho.eu`), generate a short-lived grant code, exchange it at `https://accounts.zoho.eu/oauth/v2/token`, store credentials in a vault. The refresh token stays valid until revoked.
