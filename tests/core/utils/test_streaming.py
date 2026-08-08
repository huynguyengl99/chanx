"""Tests for the cumulative-snapshot-to-delta tracker."""

from chanx.utils.streaming import DeltaTracker


def test_deltas_are_the_new_text_only() -> None:
    tracker = DeltaTracker()

    assert tracker.push("Hel") == "Hel"
    assert tracker.push("Hello") == "lo"
    assert tracker.push("Hello") == ""


def test_a_rewritten_snapshot_is_reported_as_a_replacement() -> None:
    tracker = DeltaTracker()
    tracker.push("Hello wor")

    delta, rewritten = tracker.advance("Hello world!")
    assert (delta, rewritten) == ("ld!", False)

    delta, rewritten = tracker.advance("Goodbye")
    assert (delta, rewritten) == ("Goodbye", True)


def test_reset_starts_the_next_response_clean() -> None:
    tracker = DeltaTracker()
    tracker.push("first response")
    tracker.reset()

    assert tracker.push("second") == "second"
