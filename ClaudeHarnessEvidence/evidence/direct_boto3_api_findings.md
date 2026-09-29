# Direct boto3 Harness invocation: verified API findings

Confirmed on this deployment on 2026-09-27, region us-east-1.

## InvokeAgentRuntime against a harness's underlying runtime ARN: REJECTED

```
botocore.exceptions.ClientError: ValidationException
The agent runtime arn:aws:bedrock-agentcore:us-east-1:654654616949:runtime/harness_ClaudeHarnessEvidence_StmtInterpreter-Kjn7S9CyYC
is managed by a harness and cannot be invoked directly. Use the InvokeHarness API with the
relevant harness ID instead.
```

## InvokeHarness against the harness ARN: WORKS

```python
client = boto3.client("bedrock-agentcore")
resp = client.invoke_harness(
    harnessArn="arn:aws:bedrock-agentcore:us-east-1:654654616949:harness/ClaudeHarnessEvidence_StmtInterpreter-Jx8JUA8O1S",
    runtimeSessionId="<>=33 chars>",
    messages=[{"role": "user", "content": [{"text": "..."}]}],
)
for event in resp["stream"]:
    ...  # messageStart, contentBlockDelta{delta:{text}}, contentBlockStop, messageStop, metadata
```

Confirmed input shape (`InvokeHarness`): `harnessArn` (required), `runtimeSessionId` (required,
>= 33 characters -- confirmed by a `ValidationException` at 32 chars), `messages` (required,
Converse-style `[{"role", "content": [{"text"|"toolUse"|"toolResult"|"reasoningContent"}]}]`),
plus optional `model`, `systemPrompt`, `tools`, `skills`, `allowedTools`, `maxIterations`,
`maxTokens`, `timeoutSeconds`, `actorId` overrides. Output: `stream`, an event stream with
`messageStart`/`contentBlockStart`/`contentBlockDelta`/`contentBlockStop`/`messageStop`/
`metadata`/`internalServerException`/`validationException`/`runtimeClientError` event types.

## AWS-level denial for a malformed/nonexistent harness ARN

```
botocore.exceptions.ClientError: ValidationException: Invalid harness ARN format.
```

## CLI invocation pathway (also verified, used as the documented fallback)

```
agentcore invoke --harness StmtInterpreter --target sandbox --prompt "<text>" --session-id "<>=33 chars>"
```

Response shape: `{"success": true, "response": "{\"text\": \"...\", \"sessionId\": \"...\"}", "sessionId": "..."}`.

Nothing above is a fabricated SDK method -- both the boto3 `invoke_harness` operation and the
CLI `--harness` invocation path were independently confirmed against this real deployment.
