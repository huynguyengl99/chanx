"""
Channel layer group naming.

Group names are a shared namespace across every consumer in a project, and the
backends restrict what they may contain, so anything deriving a name from user data
has to go through here.
"""

import hashlib
import re

from chanx.constants import MAX_GROUP_NAME_LENGTH

# Channel layers only accept these characters in a group name.
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_DIGEST_LENGTH = 12


def safe_group_name(*parts: object, namespace: str | None = None) -> str:
    """
    Build a group name the channel layers accept, from arbitrary parts.

    >>> safe_group_name("user", 42, namespace="notification")
    'notification.user.42'
    >>> safe_group_name("room", "Weekly Sync!")
    'room.Weekly-Sync'

    Unsupported characters are replaced and empty parts dropped. A name over the
    backend limit is truncated with a digest suffix, so it stays deterministic and
    still distinguishes names sharing a prefix.

    Args:
        *parts: Segments to join, converted to strings
        namespace: Optional leading segment, to keep components from colliding
    """
    segments = [_slug(namespace)] if namespace is not None else []
    segments.extend(_slug(part) for part in parts)
    name = ".".join(segment for segment in segments if segment)

    if not name:
        raise ValueError("safe_group_name() produced an empty name")

    if len(name) > MAX_GROUP_NAME_LENGTH:
        digest = hashlib.blake2s(
            name.encode(), digest_size=_DIGEST_LENGTH // 2
        ).hexdigest()
        keep = MAX_GROUP_NAME_LENGTH - _DIGEST_LENGTH - 1
        name = f"{name[:keep]}.{digest}"

    return name


def _slug(value: object) -> str:
    """Replace unsupported characters in one segment."""
    return _UNSAFE_CHARS.sub("-", str(value)).strip("-")
