# Zoho People MCP Action Profiles & Task Recipes

This document provides human-readable guidance on the least-privilege profiles and task recipes configured in this skill.

The machine-readable source of truth is [`references/profiles.json`](profiles.json), validated against [`references/actions.jsonl`](actions.jsonl). Use the bundled CLI `scripts/lookup_actions.py` for automated inspection, token-efficient queries, and copy-ready lists.

## Role Profiles Overview

Start with the smallest role profile that covers the user or agent's responsibilities.

```bash
# List all role profiles
python3 scripts/lookup_actions.py --profiles

# Inspect actions in a profile (including inherited actions)
python3 scripts/lookup_actions.py --profile hr-admin

# Get copy-ready action names only (one per line)
python3 scripts/lookup_actions.py --profile hr-admin --names-only
```

1. **People Employee, self-service (`employee-self-service`)**: 45 Actions
   - Own profile, leave booking, personal attendance, timelogs, and HR helpdesk cases.
   - Safe default for all regular employees. No managerial or admin visibility.
2. **People Manager (`manager`)**: 55 Actions
   - Inherits `employee-self-service`.
   - Adds team visibility, shift schedules, reportees, and approval handling (`approvalReject`, `getReportees`, `employeeInsights`).
3. **People HR Admin (`hr-admin`)**: 94 Actions
   - Inherits `manager`.
   - Adds operational HR administration: employee form records (`addRecord`, `updateRecord`), leave policy setup (`addLeaveType`, `editLeaveType`), attendance policy and rules (`getAttendancePolicySettings`, `updateAttendancePolicySettings`), holidays, org structure, and admin reports.
   - Explicitly denies salary, compensation, and destructive settings deletes (`deleteCandidate`, `deleteSpecificPolicy`, `fetchEmployeeSalaries`, etc.).
4. **People Developer or System Administrator**:
   - No blanket profile. Add sensitive configuration, salary, benefits, and performance Actions individually for a defined task.

## Task Recipes Overview

Task recipes answer the question: *"Which specific Actions do I need to unlock on the MCP server to solve this exact job?"*

```bash
# List all 20 configured task recipes
python3 scripts/lookup_actions.py --tasks

# Inspect a specific task recipe
python3 scripts/lookup_actions.py --task leave-booking

# Copy-ready action names for Zoho MCP setup UI
python3 scripts/lookup_actions.py --task leave-booking --names-only
```

Available recipes:
- `employee-lookup`: Search by name/email/ID, read erecno and basic details.
- `employee-record-maintenance`: Create or update HR form records (e.g. date of joining).
- `leave-type-configuration`: Inspect and configure leave policies and applicability.
- `leave-booking`: Balance checks, preview calculation, and leave application.
- `leave-balance-reporting`: Absence lists, team availability, and booked vs. balance.
- `holiday-calendar`: Public holidays and weekend/holiday policy review.
- `attendance-reporting`: Working hours, overtime, payable days, and daily punch reports.
- `attendance-policy-configuration`: Working hours, FILO, round-off, and grace periods.
- `attendance-regularization`: Correction requests, approvals, and regularization rules.
- `shift-management`: Shift timings, groupings, and shift change requests.
- `time-tracking`: Jobs, timelogs, running timers, and timesheets.
- `remote-work-policy`: WFH requests, approvals, and remote work policies.
- `approvals-inbox`: Multi-module approval listings and approve/reject actions.
- `hr-helpdesk`: Internal ticket creation, categories, triage, and resolution.
- `helpdesk-reporting`: HR case volumes and escalation reports.
- `onboarding`: Candidate management, invite workflows, and onboarding status.
- `org-structure`: Business units, entities, divisions, departments, and locations.
- `workforce-analytics`: Headcount, attrition, and diversity reporting.
- `performance-management`: KRAs, competencies, skills, and appraisal cycles.
- `okr-management`: Organization, department, and user objectives and key results.

## Format and Philosophy

See [`references/CATALOG_FORMAT.md`](CATALOG_FORMAT.md) for full documentation on why and how the catalog format is standardized on JSONL + JSON.
