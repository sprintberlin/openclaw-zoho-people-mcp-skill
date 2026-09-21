# Zoho People MCP

Connect your agent to Zoho People through the Model Context Protocol (MCP). This skill provides everything you need to look up employees, inspect leave types, check leave balances, and query attendance using `mcporter`.

This repository contains the public source for the ClawHub skill [`@sprintcx/zoho-people-mcp`](https://clawhub.ai/sprintcx/skills/zoho-people-mcp).

## What This Skill Includes

- Agent Skill instructions in `SKILL.md` (portable SKILL.md format)
- ClawHub release card metadata in `skill-card.md`
- Ready-to-use Python helpers for employees, leave types, leave balances, and attendance
- Security-conscious `mcporter` calls through `subprocess.run([...])` without shell expansion

## Requirements

| Requirement | Details |
|---|---|
| Zoho People MCP Server | A configured endpoint from [mcp.zoho.eu](https://mcp.zoho.eu) |
| mcporter | MCP client CLI (bundled with OpenClaw; elsewhere `npm i -g mcporter`) |
| Endpoint selection | `ZOHO_PEOPLE_MCP_URL` for one account; named profiles or `--mcp-url` for multiple accounts |

### Single-account setup

For the common single-account case, set `ZOHO_PEOPLE_MCP_URL`. The helper scripts also support named profiles and one-off URL overrides.

Add this to your shell profile, for example `~/.bashrc` or `~/.zshrc`:

```bash
export ZOHO_PEOPLE_MCP_URL="https://your-org-zoho-people-xxxxx.zohomcp.eu/mcp/YOUR_TOKEN/message"
```

Or set it per session:

```bash
ZOHO_PEOPLE_MCP_URL="https://your-org-zoho-people-xxxxx.zohomcp.eu/mcp/YOUR_TOKEN/message" python3 scripts/list_employees.py
```

To verify that it is set without printing the credential:

```bash
if [ -n "$ZOHO_PEOPLE_MCP_URL" ]; then echo "ZOHO_PEOPLE_MCP_URL is set"; else echo "ZOHO_PEOPLE_MCP_URL is not set"; fi
```

Treat `ZOHO_PEOPLE_MCP_URL` like a password. It contains People access credentials.

## How to Get Your MCP URL

1. Go to [mcp.zoho.eu](https://mcp.zoho.eu) and sign in with your Zoho account.
2. Click **Add Connection** or **New Connection**.
3. Select **Zoho People** from the list of available apps.
4. Choose the data center matching your Zoho account: EU, US, IN, AU, JP, or CN.
5. Grant the requested OAuth scopes. Start with read-only access unless write actions are explicitly needed.
6. After authorization, copy the generated MCP endpoint URL. It looks like:

   ```text
   https://your-org-zoho-people-xxxxx.zohomcp.eu/mcp/abc123def456/message
   ```

7. Set it as `ZOHO_PEOPLE_MCP_URL`.

### Multiple organizations and customer accounts

Use one shared profile file instead of changing global environment variables:

```json
{
  "version": 1,
  "profiles": {
    "acme": {
      "services": {
        "people": {"env": "ACME_PEOPLE_MCP_URL"}
      }
    }
  }
}
```

```bash
python3 scripts/list_employees.py --profile acme
```

The default file is `~/.config/zoho-mcp/profiles.json`. Endpoint resolution is `--mcp-url`, selected profile, then the app environment variable. Prefer profile entries using `env` or `url_file`; direct URLs in JSON are supported but make the file credential-bearing. Full format: [`references/MULTI_ACCOUNT.md`](references/MULTI_ACCOUNT.md).

## Quick Start

### List available tools on your MCP server

```bash
mcporter list $ZOHO_PEOPLE_MCP_URL
```

### Look up an employee

```bash
cat << 'EOF' > /tmp/people_employee.json
{
  "body": {"searchText": "Miller", "sIndex": 1, "limit": 20}
}
EOF
mcporter call "$ZOHO_PEOPLE_MCP_URL.ZohoPeople_getEmployeeBasicDetails" --args "$(< /tmp/people_employee.json)"
```

### List leave types

```bash
cat << 'EOF' > /tmp/people_leave_types.json
{
  "body": {"startIndex": 1, "limit": 30}
}
EOF
mcporter call "$ZOHO_PEOPLE_MCP_URL.ZohoPeople_fetchLeaveTypes" --args "$(< /tmp/people_leave_types.json)"
```

## Python Scripts

Ready-to-use scripts for common People operations. They accept `--profile`, `--profiles-file`, and `--mcp-url`, with `ZOHO_PEOPLE_MCP_URL` as the single-account fallback.

The bundled Python scripts call `mcporter` directly through `subprocess.run([...])` and do not invoke a shell. This avoids shell expansion of the credential-bearing `ZOHO_PEOPLE_MCP_URL`.

### `list_employees.py`

```bash
python3 scripts/list_employees.py
python3 scripts/list_employees.py --search "Miller"
python3 scripts/list_employees.py --search "Miller" --json --limit 20
```

### `inspect_employee.py`

```bash
python3 scripts/inspect_employee.py 12345 --json
```

### `list_leave_types.py`

```bash
python3 scripts/list_leave_types.py
python3 scripts/list_leave_types.py --json
python3 scripts/list_leave_types.py --details "Vacation"
```

### `leave_balances.py`

```bash
python3 scripts/leave_balances.py --erecno 12345 --year 0 --json
```

### `attendance_summary.py`

```bash
python3 scripts/attendance_summary.py --erecno 12345 --json
```

### `customize_leave_balance.py`

Sets and verifies one employee's total leave entitlement via direct REST (MCP has no Action for this):

```bash
python3 scripts/customize_leave_balance.py --erecno 12345 --leave-type-id 67890 \
  --balance 9.5 --date 07-Sep-2026 --reason "Prorated entitlement" --apply
```

Requires `ZOHO_PEOPLE_CLIENT_ID`, `ZOHO_PEOPLE_CLIENT_SECRET`, `ZOHO_PEOPLE_REFRESH_TOKEN` (Self Client, scopes `ZOHOPEOPLE.leave.CREATE,ZOHOPEOPLE.leave.READ`), optional `ZOHO_PEOPLE_DC`. Setup and other gaps: [`references/LIMITATIONS.md`](references/LIMITATIONS.md). `scripts/people_api.py` is the reusable OAuth/REST module.

## People Action Catalog and Profiles

Zoho People exposes 369 MCP Actions. Enabling all of them gives a normal agent unnecessary access to salary data, benefit administration, and organization structure changes.

The catalog is JSON, not prose, so an agent can answer "which Actions do I need for this task" without reading thousands of lines:

- [`references/actions.jsonl`](references/actions.jsonl) is the complete catalog, one JSON object per Action, with the description Zoho itself delivers.
- [`references/profiles.json`](references/profiles.json) holds the role profiles and the per-task Action recipes.
- [`references/CATALOG_FORMAT.md`](references/CATALOG_FORMAT.md) documents the format and how to refresh it after a Zoho catalog change.
- [`references/ACTION_PROFILES.md`](references/ACTION_PROFILES.md) is a short human-readable overview of the configured profiles and tasks.
- [`references/COMMON_WORKFLOWS.md`](references/COMMON_WORKFLOWS.md) contains verified step-by-step procedures.

Query it with the bundled CLI:

```bash
# Which role profiles and task recipes exist
python3 scripts/lookup_actions.py --profiles
python3 scripts/lookup_actions.py --tasks

# Which Actions does a role need, inheritance resolved
python3 scripts/lookup_actions.py --profile hr-admin

# Which Actions does one concrete job need, copy-ready for the Zoho setup UI
python3 scripts/lookup_actions.py --task leave-booking --names-only

# Find an Action, or read its full Zoho description
python3 scripts/lookup_actions.py --search "holiday"
python3 scripts/lookup_actions.py --action applyLeave

# Check that profiles and tasks still match the catalog
python3 scripts/lookup_actions.py --validate
```

For a normal HR operator, start with the **People HR Admin** profile. It includes employee lookup, leave configuration, attendance rules, org structure, and admin reports. It deliberately excludes salary, compensation, and destructive settings deletes.

After configuring the connection at [mcp.zoho.eu](https://mcp.zoho.eu), verify the actual result rather than trusting the profile document:

```bash
mcporter list "$ZOHO_PEOPLE_MCP_URL"
```

The profile and catalog use the Action names shown in the Zoho MCP setup UI. Runtime tool names normally add the `ZohoPeople_` prefix.

## Token Optimization (Large MCP Catalogs)

Connecting large MCP servers to OpenClaw can cost a large number of input tokens per session if all tool schemas are loaded eagerly up front.

To avoid loading schemas on session start, enable OpenClaw's built-in Tool Search in `~/.openclaw/openclaw.json`:

```json5
{
  tools: {
    toolSearch: {
      mode: "directory"
    }
  }
}
```

## Troubleshooting

### No endpoint configured

Set `ZOHO_PEOPLE_MCP_URL`, use `--profile`, or pass `--mcp-url`. For profile errors, verify the selected name, `--profiles-file`, and the `services.people` entry. See [Multi-account profiles](references/MULTI_ACCOUNT.md).

### `Invalid oauth scope to access this URL`

The MCP connection token may have expired or may not include the required scope. Go to [mcp.zoho.eu](https://mcp.zoho.eu), revoke and reconnect the affected app to get a fresh token.

### Date format errors

Most People APIs use `dd-MMM-yyyy`, for example `07-Sep-2026`. `getLeaveBalance` uses a relative year: `0` current, `1` next, `-1` to `-3` past.

## Repository Files

- `SKILL.md`: Agent Skill instructions.
- `references/actions.jsonl`: Complete Action catalog, one JSON object per Action.
- `references/profiles.json`: Role profiles and per-task Action recipes.
- `references/CATALOG_FORMAT.md`: Catalog format, record shape, and refresh procedure.
- `references/ACTION_PROFILES.md`: Human-readable overview of profiles and task recipes.
- `references/COMMON_WORKFLOWS.md`: Verified workflows for frequent People tasks.
- `references/LIMITATIONS.md`: Known MCP gaps, causes, and direct REST fallbacks.
- `references/MULTI_ACCOUNT.md`: Portable single-account and multi-account endpoint profiles.
- `skill-card.md`: ClawHub release card metadata.
- `scripts/lookup_actions.py`: Query Actions, profiles, and task recipes; validate them.
- `scripts/import_actions.py`: Rebuild the catalog from a Zoho MCP setup UI dump.
- `scripts/list_employees.py`: List or search Zoho People employees.
- `scripts/inspect_employee.py`: Inspect one employee record by erecno.
- `scripts/list_leave_types.py`: List leave types and fetch full configuration.
- `scripts/leave_balances.py`: Fetch leave balances for one employee.
- `scripts/attendance_summary.py`: Fetch attendance summaries.
- `scripts/people_api.py`: Self Client OAuth and generic People REST access.
- `scripts/customize_leave_balance.py`: Adjust one employee's leave balance via REST.
- `scripts/mcp_endpoint.py`: Shared endpoint and profile resolver.
- `tests/test_endpoint_resolution.py`: Credential-free resolver tests.
- `tests/test_actions_lookup.py`: Catalog, profile, and lookup CLI tests.
- `tests/test_people_api.py`: Credential-free tests for the REST fallback.

## Security Notes

The repository version calls `mcporter` directly through `subprocess.run([...])` without shell expansion.

Zoho People contains sensitive personal data. Load only required records and never copy contents into chats, logs, or repositories.

## Publish

Publish under the SprintCX ClawHub organization:

```bash
clawhub skill publish . \
  --slug zoho-people-mcp \
  --name "Zoho People MCP" \
  --owner sprintcx \
  --version 1.3.0 \
  --source-repo sprintberlin/openclaw-zoho-people-mcp-skill \
  --source-ref main \
  --source-path . \
  --changelog "Document MCP limitations and add REST fallback for leave balances"
```
