"""Server-Sent Events fan-out.

SSE rather than WebSockets: traffic is one-directional (server pushes state,
commands go over REST), browsers reconnect automatically, it passes through
proxies, and it needs no extra dependency. A WebSocket here would add a
protocol to debug for no benefit.

Every message carries a monotonic ``seq``. A client that sees a gap refetches
GET /api/simulation/state and re-snapshots, so a dropped frame self-heals
instead of leaving the console silently stale -- a failure mode that is very
hard to notice on a projector and very embarrassing when noticed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger("aiders.broadcast")

#: Per-subscriber buffer. A client that cannot keep up loses its oldest frames
#: and recovers via the seq-gap refetch, rather than growing the queue without
#: bound until the process dies.
QUEUE_MAXSIZE = 64


class Broadcaster:
    """Fan-out to every connected SSE client."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._dropped_frames = 0

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    @property
    def dropped_frames(self) -> int:
        return self._dropped_frames

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        self._subscribers.add(queue)
        logger.info("SSE client connected (%d total)", len(self._subscribers))
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        self._subscribers.discard(queue)
        logger.info("SSE client disconnected (%d remaining)", len(self._subscribers))

    def publish(self, *, seq: int, tick: int, type: str, payload: dict[str, Any]) -> None:
        """Queue one envelope for every subscriber.

        Synchronous by design: it is called from the tick loop, which already
        runs on the event loop thread. Never awaits, so a slow client cannot
        stall the simulation.
        """
        if not self._subscribers:
            return

        frame = _format_sse(
            event=type,
            data={"seq": seq, "tick": tick, "type": type, "payload": payload},
        )

        for queue in list(self._subscribers):
            try:
                queue.put_nowait(frame)
            except asyncio.QueueFull:
                # Drop the oldest frame and retry once. The client will detect
                # the seq gap and resynchronise.
                self._dropped_frames += 1
                try:
                    queue.get_nowait()
                    queue.put_nowait(frame)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass


def _format_sse(*, event: str, data: dict[str, Any]) -> str:
    body = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {body}\n\n"


def format_comment(text: str) -> str:
    """An SSE comment line. Used as a keep-alive through idle proxies."""
    return f": {text}\n\n"
