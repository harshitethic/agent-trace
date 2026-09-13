"""Deterministic projection of trace events into reviewer-facing evidence.

This module does not infer missing activity.  It only classifies facts present in
TraceEvent fields and marks broken relationships explicitly so UI consumers can
show gaps instead of inventing a complete story.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Literal

from .models import EventType, TraceEvent

ReviewCategory = Literal[
    "commands",
    "decisions",
    "failures",
    "files",
    "gaps",
    "privacy",
    "recovery",
    "retry",
    "tests",
    "tools",
]
RelationshipState = Literal["none", "linked", "orphaned"]


@dataclass(frozen=True)
class ReviewItem:
    event_id: str
    event_type: str
    timestamp: float
    parent_id: str | None
    relationship: RelationshipState
    categories: tuple[ReviewCategory, ...]
    redacted: bool
    source_index: int
    data: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewProjection:
    schema_version: int
    items: tuple[ReviewItem, ...]
    orphaned_event_ids: tuple[str, ...]

    def filter(self, category: ReviewCategory) -> tuple[ReviewItem, ...]:
        return tuple(item for item in self.items if category in item.categories)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "items": [item.to_dict() for item in self.items],
            "orphaned_event_ids": list(self.orphaned_event_ids),
        }


def _explicit_categories(event: TraceEvent) -> set[ReviewCategory]:
    categories: set[ReviewCategory] = set()
    if event.event_type in (EventType.FILE_READ, EventType.FILE_WRITE):
        categories.add("files")
    if event.event_type in (EventType.TOOL_CALL, EventType.TOOL_RESULT):
        categories.add("tools")
    if event.event_type == EventType.ERROR:
        categories.add("failures")
    if event.event_type == EventType.DECISION:
        categories.add("decisions")
    if event.redacted:
        categories.add("privacy")

    data = event.data
    if data.get("is_test") is True or data.get("category") == "test":
        categories.add("tests")
    if data.get("is_command") is True or data.get("category") == "command":
        categories.add("commands")
    if data.get("retry_of") or data.get("retry") is True:
        categories.add("retry")
    if data.get("recovery_of") or data.get("recovered") is True:
        categories.add("recovery")
    if data.get("privacy_transformed") is True:
        categories.add("privacy")
    return categories


def build_review_projection(events: Iterable[TraceEvent]) -> ReviewProjection:
    """Build a stable review projection without guessing provider semantics.

    Parent links are checked only against event IDs present in the supplied event
    stream.  Missing parents are surfaced as ``orphaned`` and categorized as a
    gap; no synthetic parent is created.
    """
    indexed = list(enumerate(events))
    known_ids = {event.event_id for _, event in indexed if event.event_id}
    items: list[ReviewItem] = []
    orphaned: list[str] = []

    for source_index, event in indexed:
        categories = _explicit_categories(event)
        parent_id = event.parent_id or None
        if parent_id is None:
            relationship: RelationshipState = "none"
        elif parent_id in known_ids:
            relationship = "linked"
        else:
            relationship = "orphaned"
            categories.add("gaps")
            orphaned.append(event.event_id)

        items.append(
            ReviewItem(
                event_id=event.event_id,
                event_type=event.event_type.value,
                timestamp=event.timestamp,
                parent_id=parent_id,
                relationship=relationship,
                categories=tuple(sorted(categories)),
                redacted=event.redacted,
                source_index=source_index,
                data=dict(event.data),
            )
        )

    # Timestamp is the primary execution order. source_index makes ties stable
    # and preserves recorded order when providers emit identical timestamps.
    items.sort(key=lambda item: (item.timestamp, item.source_index))
    return ReviewProjection(
        schema_version=1,
        items=tuple(items),
        orphaned_event_ids=tuple(orphaned),
    )
