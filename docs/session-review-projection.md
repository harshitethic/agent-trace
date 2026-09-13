# Session review projection

`agent_trace.review` provides a small deterministic layer between raw trace events and a review UI.

It is intentionally conservative: the projection classifies only facts that are present in the recorded event stream. It does not infer a missing tool call, retry, test, or provider event from surrounding prose.

## Ordering and relationships

Items are ordered by event timestamp with recorded source order as the tie breaker. A `parent_id` is marked `linked` only when that event ID is present in the supplied stream. Missing parents are kept verbatim, marked `orphaned`, and placed in the `gaps` filter.

This makes an incomplete trace visibly incomplete instead of manufacturing a clean execution tree.

## Filters

The first schema version exposes reviewer-oriented categories for files, tools, commands, tests, failures, retries, recovery, decisions, privacy transformations, and gaps.

Core event types provide categories such as files, tools, failures, and decisions. More semantic categories such as tests, commands, retries, and recovery require explicit event metadata (`is_test`, `is_command`, `retry_of`/`retry`, or `recovery_of`/`recovered`). The projector deliberately does not guess these from command strings or natural-language output.

## Raw evidence

Each projected item retains the source event ID, event type, timestamp, parent ID, redaction flag, source index, and a copy of the event's provider-specific `data`. A UI can therefore expose the underlying recorded fields rather than presenting derived labels as ground truth.

## Scope

This is a foundation for issue #242. It does not yet replace the local dashboard, calculate evidence health, render annotations, or add URL/keyboard navigation. Those surfaces can consume the projection without duplicating event-ordering and relationship rules.
