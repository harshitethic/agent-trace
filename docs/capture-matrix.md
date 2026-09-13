# CLI capture matrix

AgentTrace can only report events exposed by a provider's hook surface. This matrix keeps those boundaries explicit instead of treating every adapter as equivalent.

The machine-readable source is [`capture-matrix.json`](capture-matrix.json). An entry marked **unverified** is documentation of the current adapter contract, not proof that a specific provider release was exercised in a clean environment.

| Provider | Setup | Session | Prompt/response | Tools | File/command/error | Verification |
|---|---|---|---|---|---|---|
| Claude Code | `agent-strace setup --cli claude` | start + end | captured | captured | provider-defined | unverified |
| OpenAI Codex | `agent-strace setup --cli codex` | start only | captured | captured | provider-defined | unverified |

## Claude Code

- Config: `~/.claude/settings.json`
- Rollback: remove the AgentTrace hook commands written by `agent-strace setup` from that file.
- Privacy: captured fields still pass through AgentTrace redaction, but AgentTrace cannot expose fields Claude Code never emits.
- Known gap: file and command semantics depend on the hook-visible tool payload.

## OpenAI Codex

- Config: `~/.codex/hooks.json`
- Rollback: remove the AgentTrace hook commands written by `agent-strace setup` from that file.
- Current documented coverage: session start, user prompts, assistant responses, and `PreToolUse`/`PostToolUse` tool activity.
- Known gap: the current integration docs do not claim a session-end/stop hook; file, command, and error detail depends on provider payloads.

## Verification policy

A provider entry may move to `verified` only when `tested_version`, `last_verified`, and `fixture_test_reference` are all populated from a reproducible verification run. Keeping unknown values explicit prevents stale compatibility claims from looking current.
