# assets/

Reserved for supporting diagrams/screenshots for [`../README.md`](../README.md).
It is empty by design.

## Why there is nothing here

Every diagram in `docs/README.md` is an inline Mermaid/text diagram. No AWS
console screenshot was captured for this deliverable; the deployment and
invocation evidence that exists is captured as real command output and
CloudWatch/CloudTrail query results in `../../evidence/` instead (JSON and
text files, not images), each referenced directly from `docs/README.md`.

## Adding real screenshots later

If a console screenshot is added (e.g. the two Harness resources' console
pages, or a CloudWatch Logs Insights view), save it here with a name that
identifies the artifact (e.g. `stmt-interpreter-harness-console.png`) and
link it from the relevant section of `docs/README.md` -- keep that section's
existing fact/inference labeling and "what this does/does not prove"
framing intact next to the new image.
