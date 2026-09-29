# CloudTrail findings for this deployment (2026-09-27)

`aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=InvokeHarness`
returned **0 events**, checked twice, several minutes apart, after multiple real `InvokeHarness`
calls had already succeeded (confirmed via their own responses).

`aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventSource,AttributeValue=bedrock-agentcore.amazonaws.com`
DID return events -- but only control-plane/management calls: `GetHarness`, `ListTagsForResource`
(both from `AWSCloudFormation` during deploy), `GetWorkloadAccessToken`, `GetAgentRuntime`. No
`InvokeHarness` or `InvokeAgentRuntime` entries appeared for either this project's calls or
(when checked) prior projects' invocations in this account.

**[FACT]** `InvokeHarness`/`InvokeAgentRuntime` are data-plane operations. AWS CloudTrail's
default trail records management (control-plane) events only; data-plane events for most AWS
services (S3 object-level, DynamoDB item-level, Bedrock model invocations, and -- consistent
with what was observed here -- AgentCore harness/runtime invocations) require an explicitly
configured **data events** selector on a trail to be recorded at all.

**Conclusion for this project:** CloudTrail is confirmed to record *who deployed/configured*
these harnesses (control-plane). It was not observed to record *who invoked* them, under this
account's current trail configuration. Any customer-facing claim that "CloudTrail proves this
call happened" must first confirm a data-events trail is configured for
`bedrock-agentcore.amazonaws.com` -- this deployment does not have one, and no claim beyond
this observation is made.
