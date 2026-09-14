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
| Environment variable | `ZOHO_PEOPLE_MCP_URL` must be set |

### Environment Variable Setup

This skill requires the `ZOHO_PEOPLE_MCP_URL` environment variable. Without it, the Python scripts will not work.

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

### Multiple Organizations

If you manage multiple Zoho People orgs, each gets its own MCP endpoint. You can:

- Set one default via `ZOHO_PEOPLE_MCP_URL`
- Pass others explicitly in scripts or `mcporter` calls
- Use a wrapper script or `.env` file per project

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

Ready-to-use scripts for common People operations. All scripts require `ZOHO_PEOPLE_MCP_URL` to be set.

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

## People Action Catalog and Profiles

Zoho People exposes roughly 240 MCP Actions. Enabling all of them gives a normal agent unnecessary access to salary data, benefit administration, leave-type deletion, and organization structure changes.

This repository is the canonical home for both documents:

- [`references/ACTION_PROFILES.md`](references/ACTION_PROFILES.md) contains copy-ready least-privilege profiles for a self-service employee, a manager, an HR admin, and a deliberately unbundled developer/administrator role.
- [`references/ZOHO_PEOPLE_MCP_ACTIONS.md`](references/ZOHO_PEOPLE_MCP_ACTIONS.md) contains the complete catalog of known People Actions and descriptions.
- [`references/COMMON_WORKFLOWS.md`](references/COMMON_WORKFLOWS.md) contains verified step-by-step procedures.

For a normal HR operator, start with the **People HR Admin** profile. It includes employee lookup, leave configuration, org structure, and admin reports. It deliberately excludes leave-type deletion, salary, and benefit-plan administration.

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

### `ZOHO_PEOPLE_MCP_URL not set`

Set the environment variable with your MCP endpoint URL. See [Environment Variable Setup](#environment-variable-setup).

### `Invalid oauth scope to access this URL`

The MCP connection token may have expired or may not include the required scope. Go to [mcp.zoho.eu](https://mcp.zoho.eu), revoke and reconnect the affected app to get a fresh token.

### Date format errors

Most People APIs use `dd-MMM-yyyy`, for example `07-Sep-2026`. `getLeaveBalance` uses a relative year: `0` current, `1` next, `-1` to `-3` past.

## Repository Files

- `SKILL.md`: Agent Skill instructions.
- `references/ACTION_PROFILES.md`: Least-privilege Action profiles for new People MCP connections.
- `references/COMMON_WORKFLOWS.md`: Verified workflows for frequent People tasks.
- `references/ZOHO_PEOPLE_MCP_ACTIONS.md`: Complete catalog of known People Actions.
- `skill-card.md`: ClawHub release card metadata.
- `scripts/list_employees.py`: List or search Zoho People employees.
- `scripts/inspect_employee.py`: Inspect one employee record by erecno.
- `scripts/list_leave_types.py`: List leave types and fetch full configuration.
- `scripts/leave_balances.py`: Fetch leave balances for one employee.
- `scripts/attendance_summary.py`: Fetch attendance summaries.

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
  --version 1.0.0 \
  --source-repo sprintberlin/openclaw-zoho-people-mcp-skill \
  --source-ref main \
  --source-path . \
  --changelog "Initial public People MCP skill"
```
