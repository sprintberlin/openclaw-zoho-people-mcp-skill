## Description: <br>
Connects an agent to Zoho People through MCP so it can look up employees, inspect leave types, check leave balances, query attendance, and use mcporter-based helper scripts for common People operations. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[sprintcx](https://clawhub.ai/user/sprintcx) <br>

### License/Terms of Use: <br>
MIT <br>


## Use Case: <br>
Developers and HR operators use this skill to connect an agent to Zoho People via MCP, configure the required MCP endpoint, look up employees, inspect leave configuration, and query attendance through mcporter. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: The ZOHO_PEOPLE_MCP_URL endpoint is credential-bearing and could expose People access if echoed, logged, or shared. <br>
Mitigation: Treat the MCP URL like a password, avoid printing the full value, and start with read-only Zoho scopes. <br>
Risk: Helper scripts pass the credential-bearing MCP endpoint to mcporter, so local process visibility and logs should be treated carefully. <br>
Mitigation: The scripts call mcporter directly without shell expansion and never print ZOHO_PEOPLE_MCP_URL intentionally. Run them only on trusted systems. <br>
Risk: Read-write Zoho People actions can create or update employee, leave, and attendance records if enabled on the MCP server. <br>
Mitigation: Enable only the People actions needed for the use case and keep delete, salary, and benefit-plan administration disabled unless explicitly required. <br>
Risk: Zoho People contains sensitive personal data. <br>
Mitigation: Load only required records and never copy contents into chats, logs, or repositories. <br>


## Reference(s): <br>
- [Zoho People MCP ClawHub page](https://clawhub.ai/sprintcx/skills/zoho-people-mcp) <br>
- [GitHub source repository](https://github.com/sprintberlin/openclaw-zoho-people-mcp-skill) <br>
- [Zoho MCP portal](https://mcp.zoho.eu) <br>


## Skill Output: <br>
**Output Type(s):** [guidance, shell commands, configuration, code] <br>
**Output Format:** [Markdown guidance with bash, JSON, and Python examples] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Requires ZOHO_PEOPLE_MCP_URL, a named profile, or a one-off endpoint; bundled helper scripts can print table or JSON output from Zoho People MCP calls.] <br>

## Skill Version(s): <br>
1.3.0 <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
