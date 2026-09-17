# Action Catalog Format

This document describes how MCP Action knowledge is stored in this skill. The same layout is meant to be reused for the other Zoho MCP skills (CRM, Books, and further apps), so an agent learns the structure once and can then answer "which Actions do I need for this task" in any of them.

## Problem

A Zoho MCP app exposes hundreds of Actions. People currently has 369, Books has over a thousand. Written as prose Markdown, that catalog has three defects:

1. An agent must load thousands of lines into context to answer a small question.
2. Hand-written profile lists drift away from the real catalog, so Action names in a profile may no longer exist.
3. Zoho adds, renames, and removes Actions, and a prose file makes that invisible in review.

## Design

JSON is the only source of truth. There is no generated or hand-maintained Markdown catalog.

| File | Purpose |
|---|---|
| `references/actions.jsonl` | Every known Action, one JSON object per line |
| `references/profiles.json` | Role profiles and task recipes, referencing Action keys |
| `scripts/import_actions.py` | Rebuilds `actions.jsonl` from a Zoho MCP setup UI dump |
| `scripts/lookup_actions.py` | Answers profile, task, and search questions without loading the full catalog |

### Why JSONL for the catalog

One Action per line keeps Git diffs readable. When Zoho changes the catalog, review shows exactly which lines were added, changed, or marked removed, instead of one unreadable blob diff.

### Action record

```json
{"key":"applyLeave","name":"applyLeave","summary":"Submits a leave request for an employee...","description":"Full text as delivered by the Zoho MCP setup UI.","added":"2026-09-17"}
```

- `key`: unique identifier used by profiles and tasks. Equal to `name`, except for grouped Actions.
- `name`: the Action name shown in the Zoho MCP setup UI.
- `summary`: shortened first line for fast scanning and list output.
- `description`: the untouched description text delivered by Zoho. It is the authoritative usage hint, including any `dependencyTools` note.
- `added`: date the Action first appeared in the catalog.
- `removed`: set when an Action disappears from a newer dump. The record is kept, so history stays visible.
- `variant`: only for grouped Actions. Zoho lists some families as `lms courses`, `lms enroll course`, and similar. Those become keys such as `lms.courses` and `lms.enroll_course`.

Risk levels, module tags, and dependency graphs are deliberately not modelled. Zoho already states dependencies inside `description`, and any extra hand-maintained metadata would be the next thing to drift.

### Profiles

A profile is what an agent gets by default for a role. Profiles compose through `extends`, so a manager profile does not repeat the employee profile.

```json
"manager": {
  "name": "People Manager",
  "description": "...",
  "extends": "employee-self-service",
  "actions": ["approvalReject", "getReportees"]
}
```

`denied` removes inherited Actions again. The HR Admin profile uses this to keep salary, compensation, and destructive settings deletes out, even though it inherits broadly.

### Task recipes

A task recipe answers the practical question directly: which Actions must be enabled to complete one concrete job, such as booking leave or correcting a date of joining. Recipes are flat, do not inherit, and may overlap freely. They are an experiment in whether task-level granularity is more useful in daily work than role profiles.

## Usage

```bash
# Which profiles and task recipes exist
python3 scripts/lookup_actions.py --profiles
python3 scripts/lookup_actions.py --tasks

# Which Actions does a role need, inheritance resolved
python3 scripts/lookup_actions.py --profile hr-admin

# Which Actions does one concrete job need
python3 scripts/lookup_actions.py --task leave-booking

# Copy-ready list for the Zoho MCP setup UI
python3 scripts/lookup_actions.py --task leave-booking --names-only

# Find an Action by keyword
python3 scripts/lookup_actions.py --search "holiday"

# Read the full Zoho description of one Action
python3 scripts/lookup_actions.py --action applyLeave
```

## Maintaining the catalog

1. Open the Zoho MCP setup UI for the app and copy the complete Action list into a text file.
2. Rebuild the catalog:

   ```bash
   python3 scripts/import_actions.py /tmp/people_actions_dump.txt --dry-run
   python3 scripts/import_actions.py /tmp/people_actions_dump.txt
   ```

3. Validate that profiles and tasks still reference existing Actions:

   ```bash
   python3 scripts/lookup_actions.py --validate
   ```

4. Fix any profile or task entry the validation rejects, then commit. The importer reports added, changed, and removed Actions so the change is visible in the commit message.

The catalog describes Actions that can exist for the app. It does not prove that an Action is enabled on a specific MCP server. Always confirm against the live server:

```bash
mcporter list "$ZOHO_PEOPLE_MCP_URL"
```

Runtime tool names carry the `ZohoPeople_` prefix; the catalog and the setup UI use the bare Action name.
