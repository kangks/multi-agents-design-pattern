# ClaudeHarnessEvidence

A narrowed, **repeatable** evidence proof: Mode A (Claude Agent SDK alone,
local) and Mode B (Claude Agent SDK coordinator + separately deployed
AgentCore Harness specialists), deployed and invoked for real against
`AWS_PROFILE=ml-sandbox AWS_REGION=us-east-1`.

**No VPC/NAT/EIP exists in this deployment.** Nothing here claims fixed
network egress or network isolation -- that is an explicitly separate,
unimplemented Phase 2, documented with its own prerequisites in
[`docs/README.md`](docs/README.md#phase-2-vpcnateip-and-a-customer-controlled-collector-not-implemented).

**Main document:** [`docs/README.md`](docs/README.md) -- business activity
diagram, a claim-to-evidence table, exact reproduce commands, local
prerequisites, every ARN and session id produced, true (observed, not
assumed) limitations, and the separated Phase 2 plan.

## Layout

```
ClaudeHarnessEvidence/
├── mode_a/          # Local Claude Agent SDK control (no AgentCore) -- serial vs concurrent
├── agentcore/        # AgentCore project: 2 Harness specialists (StmtInterpreter, LedgerReconciler)
├── coordinator/      # Claude Agent SDK coordinator + authenticated invocation adapter (Mode B)
├── tests/            # pytest suite for mode_a and coordinator (run separately, see docs/README.md)
├── evidence/         # Captured run outputs: JSON evidence files, deploy diff, ARNs, denial tests
└── docs/             # Customer reproduction guide (this project's main deliverable)
```

Not touched by this work: `RevenueAssurance/`, `ParallelPatternsDemo/`,
`U42ParallelDemo/`, `GovernedHarnessSubagentDesign/`.
