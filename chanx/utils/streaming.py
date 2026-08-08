"""Incremental streaming helpers.

LLM and generator APIs usually yield *cumulative* snapshots of the output so far.
Forwarding those snapshots straight to a WebSocket re-sends the whole response on every
tick, which gets quadratically expensive on long answers. ``DeltaTracker`` converts a
snapshot stream into an append-only delta stream.
"""

from dataclasses import dataclass, field


@dataclass
class DeltaTracker:
    """Convert cumulative text snapshots into incremental deltas.

    >>> tracker = DeltaTracker()
    >>> tracker.push("Hel")
    'Hel'
    >>> tracker.push("Hello")
    'lo'
    >>> tracker.push("Hello")
    ''

    If a snapshot is not an extension of the previous one — some providers rewrite the
    tail while streaming — the tracker reports the full new text and resynchronises.
    Consumers should treat a delta that arrives with ``rewritten`` set as a replacement
    rather than an append; use :meth:`advance` when you need that signal.
    """

    text: str = field(default="")

    def push(self, snapshot: str) -> str:
        """Return the new text in ``snapshot`` relative to what was already emitted."""
        return self.advance(snapshot)[0]

    def advance(self, snapshot: str) -> tuple[str, bool]:
        """Return ``(delta, rewritten)`` for ``snapshot``.

        ``rewritten`` is ``True`` when the snapshot diverged from the accumulated text,
        meaning ``delta`` is the full replacement rather than an append.
        """
        if snapshot.startswith(self.text):
            delta = snapshot[len(self.text) :]
            self.text = snapshot
            return delta, False

        self.text = snapshot
        return snapshot, True

    def reset(self) -> None:
        """Forget accumulated text, ready for the next response."""
        self.text = ""
