---
name: "zoho-people-mcp"
description: "Zoho People via MCP: setup, action catalog, profiles, HR helpers, verified workflows, limits, and REST fallbacks."
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
2. Select only the required Actions. Resolve the exact list from the JSON catalog:

```bash
python3 scripts/lookup_actions.py --profiles
python3 scripts/lookup_actions.py --profile hr-admin --names-only
python3 scripts/lookup_actions.py --task leave-booking --names-only
```

3. Search the catalog when a profile or task lacks a required Action:

```bash
python3 scripts/lookup_actions.py --search "holiday"
python3 scripts/lookup_actions.py --action applyLeave
```

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

```bash
mcporter call "$ZOHO_PEOPLE_MCP_URL.ZohoPeople_fetchLeaveTypes" --args '{"body": {"startIndex": 1, "limit": 30}}'
```

Use the live server's schema when it differs; nested arguments go in a temp JSON file.

## Operations MCP cannot do

Some operations have no MCP Action; see [references/LIMITATIONS.md](references/LIMITATIONS.md). Leave balance corrections need the REST fallback:

```bash
python3 scripts/customize_leave_balance.py \
  --erecno 12345 --leave-type-id 67890 \
  --balance 9.5 --date 07-Sep-2026 --reason "Prorated entitlement" --apply
```

Env: `ZOHO_PEOPLE_CLIENT_ID`, `ZOHO_PEOPLE_CLIENT_SECRET`, `ZOHO_PEOPLE_REFRESH_TOKEN`, `ZOHO_PEOPLE_DC` (default `eu`), scope `ZOHOPEOPLE.leave.CREATE`. Refresh tokens stay valid until revoked; only the grant code expires. Other endpoints: import `scripts/people_api.py`.

## Answering "which Actions do I need"

The catalog is JSON, not prose. Never read the whole catalog into context to answer an Action question. Query it instead.

```bash
# Role profiles, inheritance resolved
python3 scripts/lookup_actions.py --profile employee-self-service
python3 scripts/lookup_actions.py --profile manager
python3 scripts/lookup_actions.py --profile hr-admin

# One concrete job
python3 scripts/lookup_actions.py --tasks
python3 scripts/lookup_actions.py --task employee-record-maintenance

# Keyword search across every Action name and description
python3 scripts/lookup_actions.py --search "leave type"

# Full Zoho description of a single Action, including its dependencyTools note
python3 scripts/lookup_actions.py --action editLeaveType

# Check that profiles and tasks still match the catalog
python3 scripts/lookup_actions.py --validate
```

Add `--names-only` for a copy-ready list for the Zoho MCP setup UI, or `--json` for structured output.

Data files: [references/actions.jsonl](references/actions.jsonl) holds every known Action with its Zoho description; [references/profiles.json](references/profiles.json) holds role profiles and task recipes. Format and maintenance: [references/CATALOG_FORMAT.md](references/CATALOG_FORMAT.md).

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

## Higher-impact admin Actions

`addLeaveType`, `editLeaveType`, org structure Actions (`createDivision`, `updateEntity`, and peers), `addRecord` and `updateRecord` on HR forms, attendance policy updates (`updateAttendancePolicySettings`, `updateSpecificPolicy`), salary Actions, and benefit-plan administration change configuration for everyone. Apply these safeguards:

- Confirm target form, record, and field names with `identifyForm`, `getFields`, and `getRecords` before writing.
- Resolve department, location, designation, role, and user references through their lookup tools. Never fabricate IDs.
- Read the changed configuration back after writing.
- Keep salary, compensation, and benefit Actions out of normal staff profiles.

## References

- [Action catalog](references/actions.jsonl): every known People Action with its Zoho description, one JSON object per line
- [Profiles and task recipes](references/profiles.json): role profiles and per-task Action sets
- [Catalog format](references/CATALOG_FORMAT.md): why the catalog is JSON, the record shape, and how to refresh it
- [Action profiles overview](references/ACTION_PROFILES.md): human-readable summary of the configured profiles and tasks
- [Common workflows](references/COMMON_WORKFLOWS.md): verified step-by-step procedures for frequent People tasks
- [Multi-account profiles](references/MULTI_ACCOUNT.md): portable endpoint selection for one or many Zoho accounts
- [Limitations](references/LIMITATIONS.md): operations missing from the MCP catalog, their causes, and REST fallbacks

Query the catalog with `scripts/lookup_actions.py` instead of loading `actions.jsonl` into context. Load workflows when executing a covered task.

## Troubleshooting and safety

- **No endpoint configured**: set `ZOHO_PEOPLE_MCP_URL`, use `--profile`, or pass `--mcp-url`; never print the value.
- **Profile not found or wrong app**: verify `--profiles-file`, the profile name, and its `services.people` entry.
- **Unknown form or field**: resolve with `identifyForm` and `getFields`; do not guess API names.
- **OAuth scope error**: reconnect the affected MCP connection with the required scope; never switch to another customer's endpoint.
- Zoho People contains sensitive personal data. Load only required records and never copy contents into chats, logs, or repositories.
