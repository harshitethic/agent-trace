from __future__ import annotations

import unittest

from agent_trace.models import EventType, TraceEvent
from agent_trace.review import build_review_projection


class ReviewProjectionTests(unittest.TestCase):
    def test_orders_events_and_links_tool_result(self) -> None:
        call = TraceEvent(
            EventType.TOOL_CALL,
            timestamp=2.0,
            event_id="call-1",
            data={"name": "shell"},
        )
        result = TraceEvent(
            EventType.TOOL_RESULT,
            timestamp=3.0,
            event_id="result-1",
            parent_id="call-1",
            data={"output": "ok"},
        )
        prompt = TraceEvent(EventType.USER_PROMPT, timestamp=1.0, event_id="prompt-1")

        projection = build_review_projection([call, result, prompt])

        self.assertEqual([item.event_id for item in projection.items], ["prompt-1", "call-1", "result-1"])
        result_item = next(item for item in projection.items if item.event_id == "result-1")
        self.assertEqual(result_item.relationship, "linked")
        self.assertIn("tools", result_item.categories)

    def test_surfaces_orphan_as_gap_without_synthetic_parent(self) -> None:
        orphan = TraceEvent(
            EventType.TOOL_RESULT,
            timestamp=1.0,
            event_id="orphan-1",
            parent_id="missing-call",
        )

        projection = build_review_projection([orphan])

        self.assertEqual(projection.orphaned_event_ids, ("orphan-1",))
        self.assertEqual(projection.items[0].relationship, "orphaned")
        self.assertIn("gaps", projection.items[0].categories)
        self.assertEqual(projection.items[0].parent_id, "missing-call")

    def test_filters_explicit_review_categories(self) -> None:
        events = [
            TraceEvent(EventType.FILE_WRITE, timestamp=1, event_id="file"),
            TraceEvent(
                EventType.TOOL_CALL,
                timestamp=2,
                event_id="test",
                data={"is_test": True, "is_command": True},
            ),
            TraceEvent(
                EventType.ERROR,
                timestamp=3,
                event_id="failure",
                data={"retry": True},
            ),
            TraceEvent(
                EventType.TOOL_RESULT,
                timestamp=4,
                event_id="recovery",
                data={"recovered": True},
            ),
        ]

        projection = build_review_projection(events)

        self.assertEqual([item.event_id for item in projection.filter("files")], ["file"])
        self.assertEqual([item.event_id for item in projection.filter("tests")], ["test"])
        self.assertEqual([item.event_id for item in projection.filter("commands")], ["test"])
        self.assertEqual([item.event_id for item in projection.filter("failures")], ["failure"])
        self.assertEqual([item.event_id for item in projection.filter("retry")], ["failure"])
        self.assertEqual([item.event_id for item in projection.filter("recovery")], ["recovery"])

    def test_redaction_and_privacy_transform_are_visible(self) -> None:
        redacted = TraceEvent(
            EventType.USER_PROMPT,
            timestamp=1,
            event_id="redacted",
            redacted=True,
            data={"privacy_transformed": True},
        )

        projection = build_review_projection([redacted])

        item = projection.items[0]
        self.assertTrue(item.redacted)
        self.assertIn("privacy", item.categories)
        self.assertEqual(projection.to_dict()["schema_version"], 1)

    def test_timestamp_ties_preserve_recorded_order(self) -> None:
        first = TraceEvent(EventType.USER_PROMPT, timestamp=1, event_id="first")
        second = TraceEvent(EventType.ASSISTANT_RESPONSE, timestamp=1, event_id="second")

        projection = build_review_projection([first, second])

        self.assertEqual([item.event_id for item in projection.items], ["first", "second"])


if __name__ == "__main__":
    unittest.main()
