# Verified Zoho People MCP Workflows

Step-by-step procedures for frequent People tasks. All operations assume `mcporter` and a configured `ZOHO_PEOPLE_MCP_URL`.

## 1. Employee lookup and profile inspection

```text
getEmployeeBasicDetails -> fetchEmployeeRecordById (or getRecords on employee form)
```

1. Run `getEmployeeBasicDetails` with `searchText` (name, email, or employee ID).
2. Note the returned `erecno` and basic details (department, designation, manager).
3. If deep fields or custom fields are needed, use `fetchEmployeeRecordById` with `recordId=<erecno>` or `getRecords` on the employee form.
4. For ex-employees, do not use `getEmployeeBasicDetails`; call `getRecords` with `employeeType=inactive`.

## 2. Review and configure leave types

```text
fetchLeaveTypes -> fetchLeaveTypeDetails -> editLeaveType (or addLeaveType)
```

1. List configured types: `fetchLeaveTypes`.
2. Inspect the exact policy of the target type: `fetchLeaveTypeDetails` with `leaveTypeId`.
3. Before changing rules, read all existing fields (validity, unit, applicability, carry-forward).
4. Apply updates with `editLeaveType` by sending the merged complete JSON payload.
5. Verify the change by reading back via `fetchLeaveTypeDetails`.

## 3. Check leave balances and employee absences

```text
getEmployeeBasicDetails -> getLeaveBalance -> getLeaveRecords
```

1. Resolve the employee `erecno`.
2. Retrieve current balances: `getLeaveBalance` with `year=0` (relative: 0=current, 1=next, -1=previous).
3. Review booked requests: `getLeaveRecords` with `from` and `to` in `dd-MMM-yyyy` format and the employee filter.
4. Balances cannot be corrected through MCP. Fallback: `scripts/customize_leave_balance.py` (see [LIMITATIONS.md](LIMITATIONS.md)).

## 4. Attendance and time tracking check

```text
getAttendanceSummary -> getAttendanceDetailedReport -> getTimelogs
```

1. Overview: `getAttendanceSummary` for payable days, worked hours, and overtime.
2. Daily breakdown: `getAttendanceDetailedReport` for first-in, last-out, deviations, and breaks.
3. Specific project/job hours: `getTimelogs` filtered by user and date period.

## 5. Holidays and shift scheduling

```text
listholidays -> getApplicableShiftsForUser -> getEmployeeShiftDetails
```

1. Fetch applicable public holidays: `listholidays` with start and end dates in `dd-MMM-yyyy`.
2. Inspect available shifts: `getApplicableShiftsForUser`.
3. Read effective shift schedule: `getEmployeeShiftDetails`.
