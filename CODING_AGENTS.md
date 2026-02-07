# CODING_AGENTS.md

## Commit Message Output Style

- Always format requested commit messages as multi-line text.
- First line is the summary/title.
- Follow with detail lines prefixed by `- `.
- Keep each detail on its own line.
- Do not include double quotes, single quotes, or backticks in commit message output.

Example:

```text
Fix RxMER SNMP transport lifecycle between precheck and capture
- Build separate CableModem instances for precheck and capture
- Add CableModem factory helper in RxMER worker
- Add regression test for distinct precheck/capture CableModem instances
```

## CaptureWorker Rule

- Keep CaptureWorker classes lean.
- CaptureWorker classes should focus on the PNM operation flow only.
- Move shared back-and-forth behavior to common utilities or base services.
- Do not embed generic transport, parsing, and cross-operation lifecycle mechanics directly in endpoint-specific CaptureWorker classes.
