---
name: "zoho-people-mcp"
description: "Zoho People via MCP with action catalog, least-privilege profiles, employee, leave, and attendance helper scripts, and verified record workflows."
---

# Zoho People MCP

Use Zoho People through an MCP endpoint from `mcp.zoho.eu`. This skill is the canonical home for People-specific MCP action documentation and least-privilege action profiles.

Source: [sprintberlin/openclaw-zoho-people-mcp-skill](https://github.com/sprintberlin/openclaw-zoho-people-mcp-skill)

## Requirements

- A Zoho People MCP endpoint from `mcp.zoho.eu`
- `mcporter`
- Endpoint configuration via `ZOHO_PEOPLE_MCP_URL`, `--profile`, or `--mcp-url`

Treat the endpoint as a credential. Never print it, commit it, or copy it into tickets, prompts, or chats.

## First setup

1. Create or open a Zoho People connection at `mcp.zoho.eu`.
2. Select only the required Actions. Start with [references/ACTION_PROFILES.md](references/ACTION_PROFILES.md).
3. Use [references/ZOHO_PEOPLE_MCP_ACTIONS.md](references/ZOHO_PEOPLE_MCP_ACTIONS.md) only when a profile lacks a required Action.
4. Configure one default endpoint with `ZOHO_PEOPLE_MCP_URL`, or create named profiles using [references/MULTI_ACCOUNT.md](references/MULTI_ACCOUNT.md).
5. Inspect the selected live server before relying on an Action:

```bash
mcporter list "$ZOHO_PEOPLE_MCP_URL"
```

The catalog describes possible Actions. It does not prove that an Action is enabled on a particular MCP server. Runtime tool names usually have the `ZohoPeople_` prefix, while the Zoho MCP setup UI uses the Action name without that prefix.

## Endpoint selection

For one account, set `ZOHO_PEOPLE_MCP_URL`. For multiple accounts, pass `--profile NAME` to a bundled helper. Profiles live in `~/.config/zoho-mcp/profiles.json` by default and can resolve endpoints through an environment variable, a local URL file, or a direct URL. One-off `--mcp-url URL` overrides everything, but may expose the credential in shell history or process listings.

Resolution order is `--mcp-url`, selected profile, then the environment fallback. Profile selection is `--profile`, `ZOHO_PEOPLE_MCP_PROFILE`, then `ZOHO_MCP_PROFILE`. See [references/MULTI_ACCOUNT.md](references/MULTI_ACCOUNT.md) for the shared CRM, People, and Books format.

## Safe workflow

1. Confirm the correct Zoho account and organization. Never reuse an endpoint from another customer.
2. Identify the employee first. `getEmployeeBasicDetails` is the first-choice lookup by name, email, employee ID, or erecno. Paginate with `sIndex` and `limit`. For ex-employees use `getRecords` on the employee form with `employeeType=inactive`.
3. Never take an erecno from raw user text. Resolve it through a lookup tool, or use the current user context.
4. Read before writing. For writes through form tools, resolve the form with `identifyForm`, fields with `getFields`, picklist options with `getFieldOptions`, and lookup options with `getLookupOptions`. Send IDs for lookup fields, never display strings.
5. For writes, send only intended fields and read the affected record back immediately.
6. Do not use leave-type delete, org structure changes, salary, benefit-plan administration, or other administrative Actions unless the task explicitly requires them.

## Date and time conventions

- People APIs use `dd-MMM-yyyy` for most dates, for example `07-Sep-2026`.
- `getLeaveBalance` uses a relative `year`: `0` current, `1` next, `-1` to `-3` back.
- Attendance summary values reported in seconds must be converted to `hh:mm` before display.
- Times in regularization, permission, and on-duty requests are minutes from midnight, for example `09:00` becomes `540`.

## Common calls

List configured leave types:

```bash
cat > /tmp/people_leave_types.json <<'JSON'
{"body": {"startIndex": 1, "limit": 30}}
JSON
mcporter call "$ZOHO_PEOPLE_MCP_URL.ZohoPeople_fetchLeaveTypes" --args "$(< /tmp/people_leave_types.json)"
```

Look up an employee:

```bash
cat > /tmp/people_employee.json <<'JSON'
{"body": {"searchText": "Miller", "sIndex": 1, "limit": 20}}
JSON
mcporter call "$ZOHO_PEOPLE_MCP_URL.ZohoPeople_getEmployeeBasicDetails" --args "$(< /tmp/people_employee.json)"
```

Use the schema shown by the live MCP server when it differs from these examples. For deeply nested arguments, use a temporary JSON file instead of fragile shell quoting.

## Bundled scripts

The scripts resolve the endpoint via `--mcp-url`, `--profile` (`~/.config/zoho-mcp/profiles.json`), or `ZOHO_PEOPLE_MCP_URL`, call `mcporter` without shell expansion, paginate results, and normalize common Zoho MCP response envelopes.

```bash
python3 scripts/list_employees.py --search "Miller" --json --limit 20
python3 scripts/inspect_employee.py 12345 --json
python3 scripts/list_leave_types.py --json
python3 scripts/list_leave_types.py --details "Vacation"
python3 scripts/leave_balances.py --erecno 12345 --year 0 --json
python3 scripts/attendance_summary.py --erecno 12345 --json
```

Supported options:

- `list_employees.py`: `--search`, `--json`, `--full`, `--limit`, `--page-size`, `--timeout`
- `inspect_employee.py`: positional erecno, `--json`, `--timeout`
- `list_leave_types.py`: `--details` name or ID, `--json`, `--limit`, `--page-size`, `--timeout`
- `leave_balances.py`: `--erecno`, `--year`, `--json`, `--timeout`
- `attendance_summary.py`: `--erecno`, `--json`, `--limit`, `--page-size`, `--timeout`
- All helpers: `--mcp-url`, `--profile`, `--profiles-file`

Run any helper with `--help` without configuring credentials. Unknown or incomplete options must exit with status 2.

## Leave safety

- `applyLeave` requires `fetchLeaveBasicInfo` for the form, `getFields` for mandatory fields, and `getLeaveBalance` for applicable types. Map the chosen leave type name to its ID internally.
- `cancelLeave` needs the leave record ID and a reason.
- Leave type changes go through `fetchLeaveTypes` and `fetchLeaveTypeDetails` before `editLeaveType`. Send the merged complete leave-type JSON, not a sparse partial.
- `deleteLeaveType` permanently deletes the leave type and its report data. Keep it disabled by default.

## Higher-impact admin Actions

`addLeaveType`, `editLeaveType`, `deleteLeaveType`, org structure Actions (`createDivision`, `updateEntity`, and peers), `addRecord` and `updateRecord` on HR forms, salary Actions, and benefit-plan administration change configuration for everyone. Apply these safeguards:

- Confirm target form, record, and field names with `identifyForm`, `getFields`, and `getRecords` before writing.
- Resolve department, location, designation, role, and user references through their lookup tools. Never fabricate IDs.
- Read the changed configuration back after writing.
- Keep salary, compensation, and benefit Actions out of normal staff profiles.

## References

- [Action profiles](references/ACTION_PROFILES.md): recommended least-privilege selections for new MCP servers
- [Common workflows](references/COMMON_WORKFLOWS.md): verified step-by-step procedures for frequent People tasks
- [Complete People Actions catalog](references/ZOHO_PEOPLE_MCP_ACTIONS.md): all known People Actions and descriptions
- [Multi-account profiles](references/MULTI_ACCOUNT.md): portable endpoint selection for one or many Zoho accounts

Load the profile reference when configuring a connection. Load workflows when executing a covered task. Load the full catalog only when a profile lacks a required Action.

## Troubleshooting and safety

- **No endpoint configured**: set `ZOHO_PEOPLE_MCP_URL`, use `--profile`, or pass `--mcp-url`; never print the value.
- **Profile not found or wrong app**: verify `--profiles-file`, the profile name, and its `services.people` entry.
- **Unknown form or field**: resolve with `identifyForm` and `getFields`; do not guess API names.
- **OAuth scope error**: reconnect the affected MCP connection with the required scope; never switch to another customer's endpoint.
- Zoho People contains sensitive personal data. Load only required records and never copy contents into chats, logs, or repositories.
