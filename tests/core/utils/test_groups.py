"""Tests for channel-layer-safe group naming."""

import pytest
from chanx.constants import MAX_GROUP_NAME_LENGTH
from chanx.utils.groups import safe_group_name


def test_joins_parts_with_a_namespace() -> None:
    assert (
        safe_group_name("user", 42, namespace="notification") == "notification.user.42"
    )


def test_replaces_unsupported_characters() -> None:
    assert safe_group_name("room", "Weekly Sync!") == "room.Weekly-Sync"


def test_empty_parts_are_dropped() -> None:
    assert safe_group_name("a", "", "b") == "a.b"


def test_nothing_left_raises() -> None:
    with pytest.raises(ValueError, match="empty name"):
        safe_group_name("!!!")


def test_long_names_are_truncated_deterministically() -> None:
    long = safe_group_name("x" * 200)
    again = safe_group_name("x" * 200)
    other = safe_group_name("x" * 199 + "y")

    assert len(long) <= MAX_GROUP_NAME_LENGTH
    assert long == again
    assert long != other
