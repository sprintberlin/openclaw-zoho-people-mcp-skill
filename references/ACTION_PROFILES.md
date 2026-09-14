# Recommended Zoho People MCP Action Profiles

Zoho People exposes roughly 240 MCP Actions. Do not enable the entire catalog for a normal agent. Start with the smallest profile that covers the role and add individual Actions only after a real requirement appears.

Names below match the Zoho MCP setup UI and the complete catalog in `ZOHO_PEOPLE_MCP_ACTIONS.md`. Runtime tools usually appear as `ZohoPeople_<Action>`, for example `ZohoPeople_getLeaveBalance`.

## Profile overview

1. **People Employee, self-service**: own profile, leave, attendance, time tracking, and HR help desk.
2. **People Manager**: employee profile plus team visibility, approvals, and team reports.
3. **People HR Admin**: recommended operational profile. Employee form records, leave configuration, org structure, and admin reports. No deletes by default.
4. **People Developer or Administrator**: no blanket profile. Add configuration, salary, benefits, and performance Actions individually for a defined task.

## People Employee, self-service

```text
getEmployeeBasicDetails
fetchEmployeeRecordById
listholidays
fetchLeaveTypes
getLeaveBalance
getLeaveRecords
getCompoffRecords
getAttendanceSummary
getAttendanceDetailedReport
getStatus
checkIn
checkOut
applyLeave
cancelLeave
addOnDuty
applyPermission
addRegularization
addShiftChangeRequest
getApplicablePermForUser
getApplicableShiftsForUser
getAllODTypes
getAllRegReasons
getApprovals
getTimelogs
addTimelog
editTimelog
deleteTimelogs
getCurrentlyRunningTimer
getRunningTimer
startTimer
getMyTasks
addnewhelpdeskticket
```

Safeguards:

- `checkIn` and `checkOut` are self-only. No user may run them on behalf of another employee.
- `getLeaveRecords` defaults to `dataSelect=MINE`. Keep that default for self-service profiles.
- `deleteTimelogs` removes time records. Omit it for plain employees if timelogs are corrected through edits.

## People Manager

Select every Action from **People Employee, self-service** that the manager still needs personally, then add:

```text
getReportees
getTeamMembersOnLeave
getOnDutyApprovals
getPermissionApprovals
getRegularizationApprovals
getShiftChangeApprovals
approvalReject
getEmployeeShiftDetails
getDepartmentShiftGrouping
getEarlyLateCheckInData
employeeInsights
```

Safeguards:

- `approvalReject` approves or rejects requests. Verify the requester, dates, and balance before deciding.
- Team reads must use the reportee erecno resolved via `getReportees` or `getEmployeeBasicDetails`, never guessed IDs.
- `employeeInsights` uses `repType=myReports` or `teamReports` for managers. `adminReports` belongs to the HR Admin profile.

## People HR Admin

This is the recommended default for an HR operator or operational agent working across the organization. It can read employee records, manage leave configuration, and maintain org structure. It cannot delete leave types, change salary data, or administer benefit plans by default.

Select the People Manager profile, then add:

### Employee form records

```text
identifyForm
getFormView
getFields
getFieldOptions
getLookupOptions
getRecords
getRecordCount
getRecordByIDSectionWise
getRecordsViewUrl
addRecord
updateRecord
```

Safeguards:

- `addRecord` and `updateRecord` write HR forms. Resolve form, field, and lookup IDs first; never send display strings for lookup fields.
- Show at most 25 records in chat. Offer `getRecordsViewUrl` for larger sets.

### Leave configuration

```text
fetchLeaveTypeDetails
addLeaveType
editLeaveType
```

Safeguards:

- Resolve leave types via `fetchLeaveTypes` before every read or write of a specific type.
- Send the merged complete leave-type JSON to `editLeaveType`, not a sparse partial.
- Keep `deleteLeaveType` disabled. It permanently removes the leave type and its report data.

### Org structure and directories

```text
getDepartmentDetails
getLocationDetails
getEntities
getUnits
getDivisions
createEntity
updateEntity
createUnit
updateUnit
createDivision
updateDivision
fetchallgroups
fetchgroupmembers
```

Safeguards:

- Org structure changes affect every employee. Confirm the target ID via the matching `get*` tool before create or update.

### Admin reports

```text
getAttritionReport
employeeInsights
```

Use `repType=adminReports` here. Display attrition as a table and prefer `employeeInsights` for headcount questions.

## People Developer or Administrator

No blanket profile. Typical individually added groups:

- Salary and compensation: `fetchEmployeeSalaries`, `fetchSingleEmployeeSalary`, `fetchSingleEmployeeBreakupDetails`, `fetchRevisions`, `fetchSingleEmployeeRevisions`, `mycompensation`
- Benefits administration: benefit plan, category, provider, plan year, and enrollment Actions
- Performance configuration: KRA, competency, skill, review question, and appraisal Actions
- File module: `fileModulePermInitialData`, `getAllFiles`
- Leave type deletion: `deleteLeaveType`

Add each Action for a defined task, remove it when the task ends, and prefer read-only variants while investigating.

## Verification

After configuring the connection at [mcp.zoho.eu](https://mcp.zoho.eu), verify the actual result rather than trusting this document:

```bash
mcporter list "$ZOHO_PEOPLE_MCP_URL"
```

The profile and catalog use the Action names shown in the Zoho MCP setup UI. Runtime tool names normally add the `ZohoPeople_` prefix.
