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
